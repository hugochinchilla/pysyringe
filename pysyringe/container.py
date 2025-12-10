import functools
import inspect
import threading
import typing
from collections.abc import Callable, Hashable
from contextlib import contextmanager
from types import UnionType
from typing import Any, TypeVar, cast

T = TypeVar("T")
NoneType = type(None)


class _Unresolved:
    pass


_unresolved = _Unresolved()


class UnknownDependencyError(Exception):
    def __init__(self, type_: type) -> None:
        super().__init__(f"Container does not know how to provide {type_}")


class UnresolvableUnionTypeError(Exception):
    def __init__(self, type_: type) -> None:
        super().__init__(
            f"Cannot resolve [{type_}]: remove UnionType or define a factory",
        )


class ThreadLocalMockStore:
    """Thread-local storage for mocks to ensure thread safety."""

    def __init__(self) -> None:
        self._local = threading.local()

    def get_mocks(self) -> dict:
        """Get the mocks dictionary for the current thread."""
        if not hasattr(self._local, "mocks"):
            self._local.mocks = {}
        return cast(dict, self._local.mocks)

    def set_mock(self, cls: type, mock: Any) -> None:
        """Set a mock for a class in the current thread."""
        mocks = self.get_mocks()
        mocks[cls] = mock

    def clear_mocks(self) -> None:
        """Clear all mocks for the current thread."""
        self._local.mocks = {}


class _Resolver:
    def __init__(self, factory: object | None) -> None:
        self.factory = factory
        self.mock_store = ThreadLocalMockStore()
        self.aliases: dict = {}
        self.never_provide: list[type] = []
        self._factory_by_return_type: dict[type, Callable] = (
            {
                _TypeHelper.get_return_type(factory): factory
                for factory in self.__build_factories()
            }
            if self.factory is not None
            else {}
        )

    def resolve(
        self, cls: type[T], default: T | _Unresolved = _unresolved
    ) -> T | _Unresolved:
        try:
            if issubclass(cls, tuple(self.never_provide)):
                return default
        except TypeError:
            return default

        mocks = self.mock_store.get_mocks()
        if cls in mocks:
            return cast(T, mocks[cls])

        if cls in self.aliases:
            return self.resolve(self.aliases[cls], default)

        instance = self.__make_from_factory(cls)
        if instance:
            return instance

        instance = self.__make_from_inference(cls)
        if instance:
            return instance

        return default

    def __make_from_factory(self, cls: type[T]) -> T | None:
        factory = self._factory_by_return_type.get(cls)
        if factory is None:
            return None
        return cast(T, factory())

    def __build_factories(self) -> list[Callable]:
        attrs = [
            getattr(self.factory, x) for x in dir(self.factory) if not x.startswith("_")
        ]
        return [attr for attr in attrs if callable(attr)]

    def __make_from_inference(self, cls: type[T]) -> T | None:
        args = ()
        kwargs = {}
        for arg_name, arg_type, default in _TypeHelper.get_constructor_kwargs(cls):
            resolved = self.resolve(arg_type, default)
            if isinstance(resolved, _Unresolved):
                return None
            kwargs[arg_name] = resolved

        return cls(*args, **kwargs)


class Container:
    def __init__(self, factory: object | None = None) -> None:
        self._resolver = _Resolver(factory)

    def never_provide(self, cls: type[T]) -> None:
        self._resolver.never_provide.append(cls)

    def provide(self, cls: type[T]) -> T:
        resolved = self._resolver.resolve(cls)
        if isinstance(resolved, _Unresolved):
            raise UnknownDependencyError(cls)

        return resolved

    def inject(self, function: Callable) -> Callable:
        injector = _Injector(self._resolver)
        return injector.inject(function)

    def clear_mocks(self) -> None:
        self._resolver.mock_store.clear_mocks()

    def use_mock(self, cls: type[T], mock: T) -> None:
        self._resolver.mock_store.set_mock(cls, mock)

    @contextmanager
    def overrides(self, override_map: dict[type[T], T]) -> typing.Iterator[None]:
        temp_resolver = _Resolver(self._resolver.factory)
        for class_type, implementation in override_map.items():
            temp_resolver.mock_store.set_mock(class_type, implementation)
        original_resolver = self._resolver
        self._resolver = temp_resolver
        yield
        self._resolver = original_resolver
        del temp_resolver

    @contextmanager
    def override(self, cls: type[T], mock: T) -> typing.Iterator[None]:
        with self.overrides({cls: mock}):
            yield

    def alias(self, interface: type, implementation: type) -> None:
        self._resolver.aliases[interface] = implementation


class _Injector:
    def __init__(self, _resolver: _Resolver) -> None:
        self._resolver = _resolver

    def inject(self, function: Callable) -> Callable:
        injections = self.__get_injectable_arguments(function)

        def partial_function(*args, **kwargs) -> Any:
            injections = self.__get_injectable_arguments(function)
            return function(*args, **kwargs, **injections)

        partial_function.__signature__ = self.__create_new_signature(  # type: ignore[attr-defined]
            function,
            injections,
        )
        partial_function.__name__ = function.__name__

        return partial_function

    def __get_injectable_arguments(self, function: Callable) -> dict[str, object]:
        signature = inspect.signature(function)
        resolved_arguments = {
            (p.name, self._resolver.resolve(p.annotation))
            for p in signature.parameters.values()
            if p.name != "self"
        }
        only_resolved = {
            (parameter_name, value)
            for (parameter_name, value) in resolved_arguments
            if not isinstance(value, _Unresolved)
        }
        return dict(only_resolved)

    def __create_new_signature(
        self,
        function: Callable,
        injections: dict[str, T],
    ) -> inspect.Signature:
        remaining_parameters = [
            p
            for p in inspect.signature(function).parameters.values()
            if p.name not in injections
        ]

        return inspect.Signature(
            parameters=remaining_parameters,
            return_annotation=(_TypeHelper.get_return_type(function)),
        )


class _TypeHelper:
    @classmethod
    def get_constructor_kwargs(cls, subject: type[T]) -> list[tuple]:
        return cls._cached_constructor_kwargs(cast(Hashable, subject))

    @staticmethod
    @functools.lru_cache(maxsize=512)
    def _cached_constructor_kwargs(key: Hashable) -> list[tuple]:
        subject = cast(type, key)
        try:
            parameters = inspect.signature(subject).parameters.values()
        except ValueError:
            return []

        return [
            (
                p.name,
                _TypeHelper._desambiguate(p.annotation),
                _TypeHelper._default_or_unresolved(p.default, p.empty),
            )
            for p in parameters
            if _TypeHelper._is_resolvable(p)
        ]

    @classmethod
    def _is_resolvable(cls, p: inspect.Parameter) -> bool:
        if p.kind is p.POSITIONAL_ONLY:
            return False

        if p.annotation is p.empty:
            return False

        return True

    @classmethod
    def _desambiguate(cls, type_: type[T]) -> type[T] | _Unresolved:
        if cls._is_union(type_):
            if cls._is_optional(type_):
                return cls._resolve_optional(type_)
            raise UnresolvableUnionTypeError(type_)
        return type_

    @classmethod
    def _default_or_unresolved(cls, default: T, empty: Any) -> T | _Unresolved:
        if default is empty:
            return _Unresolved()
        return default

    @classmethod
    def _is_union(cls, type_: T) -> bool:
        if typing.get_origin(type_) is typing.Union:
            return True  # Syntax using "Union[object, str]"

        if isinstance(type_, UnionType):
            return True  # Syntax using "object | str"

        return False

    @staticmethod
    def _is_optional(type_: object) -> bool:
        types = set(typing.get_args(type_))
        has_two_types = len(types) == 2
        one_of_them_is_optional = NoneType in types
        return has_two_types and one_of_them_is_optional

    @staticmethod
    def _resolve_optional(type_: type[T | None]) -> type[T]:
        types = set(typing.get_args(type_))
        types.remove(type(None))
        return cast(type[T], types.pop())

    @staticmethod
    def get_return_type(method: Callable) -> type:
        return cast(type, inspect.signature(method).return_annotation)
