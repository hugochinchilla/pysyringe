import functools
import inspect
import threading
import typing
from collections.abc import Callable, Hashable
from types import UnionType
from typing import Any, TypeVar, cast

T = TypeVar("T")
NoneType = type(None)


class _Unresolved:
    pass


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

    def resolve(self, cls: type[T]) -> T | _Unresolved:  # noqa: PLR0911
        try:
            if issubclass(cls, tuple(self.never_provide)):
                return _Unresolved()
        except TypeError:
            return _Unresolved()

        mocks = self.mock_store.get_mocks()
        if cls in mocks:
            return cast(T, mocks[cls])

        if cls in self.aliases:
            return self.resolve(self.aliases[cls])

        instance = self.__make_from_factory(cls)
        if instance:
            return instance

        instance = self.__make_from_inference(cls)
        if instance:
            return instance

        return _Unresolved()

    def __make_from_factory(self, cls: type[T]) -> T | None:
        factory = self._factory_by_return_type.get(cls)
        if factory is None:
            return None
        return cast(T, factory())

    def __build_factories(self) -> list[Callable]:
        if self.factory is None:
            return []
        attrs = [
            getattr(self.factory, x) for x in dir(self.factory) if not x.startswith("_")
        ]
        return [attr for attr in attrs if callable(attr)]

    def __make_from_inference(self, cls: type[T]) -> T | None:
        dependencies = {}
        for arg_name, arg_type in _TypeHelper.get_constructor_arguments(cls):
            resolved = self.resolve(arg_type)
            if isinstance(resolved, _Unresolved):
                return None
            dependencies[arg_name] = resolved

        return cls(**dependencies)


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
    def get_constructor_arguments(cls, subject: type[T]) -> list[tuple]:
        return cls._cached_constructor_arguments(cast(Hashable, subject))

    @staticmethod
    @functools.lru_cache(maxsize=512)
    def _cached_constructor_arguments(key: Hashable) -> list[tuple]:
        subject = cast(type, key)
        try:
            parameters = inspect.signature(subject).parameters.values()
        except ValueError:
            return []

        return [
            (p.name, _TypeHelper._desambiguate(p.annotation))
            for p in parameters
            if p.name != "return"
        ]

    @classmethod
    def _desambiguate(cls, type_: type[T]) -> type[T]:
        if cls._is_union(type_):
            if cls._is_optional(type_):
                return cls._resolve_optional(type_)
            raise UnresolvableUnionTypeError(type_)
        return type_

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
