import inspect
import typing
from collections.abc import Callable
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
    def __init__(self, type_: UnionType) -> None:
        super().__init__(
            f"Cannot resolve [{type_}]: remove UnionType or define a factory",
        )


class _Resolver:
    def __init__(self, factory: object) -> None:
        self.factory = factory
        self.mocks: dict = {}
        self.aliases: dict = {}
        self.never_provide: list[type] = []

    def resolve(self, cls: type[T]) -> T | _Unresolved:  # noqa: PLR0911
        try:
            if issubclass(cls, tuple(self.never_provide)):
                return _Unresolved()
        except TypeError:
            return _Unresolved()

        if cls in self.mocks:
            return cast(T, self.mocks[cls])

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
        for factory in self.__get_factories():
            if cls == _TypeHelper.get_return_type(factory):
                return cast(T, factory())

        return None

    def __get_factories(self) -> list[Callable]:
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
    def __init__(self, factory: object) -> None:
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
        self._resolver.mocks = {}

    def use_mock(self, cls: type[T], mock: T) -> None:
        self._resolver.mocks[cls] = mock

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
        try:
            parameters = inspect.signature(subject).parameters.values()
        except ValueError:
            return []

        return [
            (p.name, cls._desambiguate(p.annotation))
            for p in parameters
            if p.name != "return"
        ]

    @classmethod
    def _desambiguate(cls, type_: type[T]) -> type[T]:
        if isinstance(type_, UnionType):
            if cls._is_optional(type_):  # type: ignore[unreachable]
                return cls._resolve_optional(type_)
            raise UnresolvableUnionTypeError(type_)
        return type_

    @staticmethod
    def _is_optional(type_: UnionType) -> bool:
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
