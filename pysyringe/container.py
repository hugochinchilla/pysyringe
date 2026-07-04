import functools
import inspect
import threading
import typing
from collections.abc import Callable, Hashable
from contextlib import contextmanager
from types import UnionType
from typing import TYPE_CHECKING, Any, TypeVar, cast

T = TypeVar("T")
NoneType = type(None)


class _Unresolved:
    pass


_unresolved = _Unresolved()


class _ProvideMarker:
    pass


_provide_marker = _ProvideMarker()


if TYPE_CHECKING:
    Provide: typing.TypeAlias = typing.Annotated[T, _provide_marker]
else:

    class Provide:
        """Type marker for explicit dependency injection.

        Use ``Provide[SomeType]`` in a function decorated with
        ``@container.inject`` to indicate which parameters should be
        injected by the container.  Only marked parameters are injected;
        all others are left for the caller.

        Example::

            @container.inject
            def view(request, service: Provide[MyService]):
                ...
        """

        def __class_getitem__(cls, item: type) -> typing.Any:
            return typing.Annotated[item, _provide_marker]


class UnknownDependencyError(Exception):
    def __init__(
        self,
        type_: type,
        resolution_chain: list[tuple[type, str, type]] | None = None,
    ) -> None:
        message = f"Container does not know how to provide {type_}"
        if resolution_chain:
            chain_lines = "\n".join(
                (
                    f"  -> {cls.__name__} requires {param_type} (parameter '{param_name}')"
                    if not isinstance(param_type, type)
                    else f"  -> {cls.__name__} requires {param_type.__name__} (parameter '{param_name}')"
                )
                for cls, param_name, param_type in resolution_chain
            )
            message += f"\n\nResolution chain:\n{chain_lines}"
        super().__init__(message)


class RecursiveResolutionError(Exception):
    def __init__(self, type_: type, cycle: list[type]) -> None:
        cycle_str = " -> ".join(t.__name__ for t in cycle)
        super().__init__(
            f"Recursive resolution detected for {type_.__name__}: {cycle_str}"
        )


class UnresolvableUnionTypeError(Exception):
    def __init__(self, type_: type) -> None:
        super().__init__(
            f"Cannot resolve [{type_}]: remove UnionType or define a factory",
        )


class DuplicateFactoryMethodError(Exception):
    def __init__(self, type_: type, first: Callable, second: Callable) -> None:
        first_name = getattr(first, "__name__", repr(first))
        second_name = getattr(second, "__name__", repr(second))
        super().__init__(
            f"Multiple factory methods return {type_}: "
            f"'{first_name}' and '{second_name}'",
        )


class ThreadLocalMockStore:
    """Thread-local stack of override maps to ensure thread safety."""

    def __init__(self) -> None:
        self._local = threading.local()

    def _stack(self) -> list[dict]:
        if not hasattr(self._local, "stack"):
            self._local.stack = []
        return cast("list", self._local.stack)

    def get_mocks(self) -> dict:
        """Get the active overrides for the current thread."""
        stack = self._stack()
        return stack[-1] if stack else {}

    def push(self, overrides: dict) -> None:
        """Activate *overrides* on top of the current ones for this thread."""
        self._stack().append({**self.get_mocks(), **overrides})

    def pop(self) -> None:
        self._stack().pop()


class _Resolver:
    def __init__(self, factory: object | None) -> None:
        self.factory = factory
        self.container: Container | None = None
        self.mock_store = ThreadLocalMockStore()
        self.aliases: dict = {}
        self.instances: dict = {}
        self._local = threading.local()
        # Maps return type -> (method, wants_container), with the container
        # check precomputed: get_type_hints() is too slow for the hot path.
        self._factory_by_return_type: dict[type, tuple[Callable, bool]] = (
            self.__map_factories_by_return_type() if self.factory is not None else {}
        )

    # Cycle detection and the error resolution chain are per-thread state:
    # sharing them across threads makes concurrent resolution of the same
    # type look like a recursive cycle.
    @property
    def _resolution_chain(self) -> list[tuple[type, str, type]]:
        if not hasattr(self._local, "chain"):
            self._local.chain = []
        return cast("list", self._local.chain)

    @property
    def _resolving(self) -> set[type]:
        if not hasattr(self._local, "resolving"):
            self._local.resolving = set()
        return cast("set", self._local.resolving)

    @property
    def _resolving_stack(self) -> list[type]:
        if not hasattr(self._local, "resolving_stack"):
            self._local.resolving_stack = []
        return cast("list", self._local.resolving_stack)

    def get_resolution_chain(self) -> list[tuple[type, str, type]]:
        return self._resolution_chain

    def __map_factories_by_return_type(self) -> dict[type, tuple[Callable, bool]]:
        factories: dict[type, tuple[Callable, bool]] = {}
        for method in self.__build_factories():
            return_type = _TypeHelper.get_return_type(method)
            if return_type is inspect.Signature.empty:
                continue
            if return_type in factories:
                raise DuplicateFactoryMethodError(
                    return_type,
                    factories[return_type][0],
                    method,
                )
            factories[return_type] = (method, _TypeHelper.accepts_container(method))
        return factories

    def resolve(
        self, cls: type[T], default: T | _Unresolved = _unresolved
    ) -> T | _Unresolved:
        mocks = self.mock_store.get_mocks()
        if cls in mocks:
            return cast("T", mocks[cls])

        if cls in self.instances:
            return cast("T", self.instances[cls])

        if cls in self._resolving:
            start = self._resolving_stack.index(cls)
            cycle = [*self._resolving_stack[start:], cls]
            raise RecursiveResolutionError(cls, cycle)

        self._resolving.add(cls)
        self._resolving_stack.append(cls)
        try:
            # Alias hops happen inside the tracked section so alias cycles
            # are reported as RecursiveResolutionError, not RecursionError.
            if cls in self.aliases:
                return self.resolve(self.aliases[cls], default)

            instance = self.__make_from_factory(cls)
            if instance is not None:
                return instance

            instance = self.__make_from_inference(cls)
            if instance is not None:
                return instance

            return default
        finally:
            self._resolving_stack.pop()
            self._resolving.discard(cls)

    def __make_from_factory(self, cls: type[T]) -> T | None:
        entry = self._factory_by_return_type.get(cls)
        if entry is None:
            return None
        factory, wants_container = entry
        if self.container is not None and wants_container:
            return cast("T", factory(self.container))
        return cast("T", factory())

    def __build_factories(self) -> list[Callable]:
        # getattr_static keeps properties/descriptors from firing as a side
        # effect of building the container; only plain callables qualify.
        methods = []
        for name in dir(self.factory):
            if name.startswith("_"):
                continue
            static = inspect.getattr_static(self.factory, name, None)
            if isinstance(static, (staticmethod, classmethod)):
                static = static.__func__
            if callable(static):
                methods.append(getattr(self.factory, name))
        return methods

    def __make_from_inference(self, cls: type[T]) -> T | None:
        # Builtins (str, int, list, ...) are all zero-arg constructible, but
        # "provide me a str" is always a wiring mistake — never infer them.
        if getattr(cls, "__module__", None) == "builtins":
            return None
        args = ()
        kwargs = {}
        for arg_name, arg_type, default in _TypeHelper.get_constructor_kwargs(cls):
            self._resolution_chain.append((cls, arg_name, arg_type))
            try:
                resolved = self.resolve(arg_type, default)
                if isinstance(resolved, _Unresolved):
                    raise UnknownDependencyError(
                        arg_type, resolution_chain=list(self._resolution_chain)
                    )
            finally:
                self._resolution_chain.pop()
            kwargs[arg_name] = resolved

        return cls(*args, **kwargs)


class Container:
    def __init__(self, factory: object | None = None) -> None:
        self._resolver = _Resolver(factory)
        self._resolver.container = self

    def provide(self, cls: type[T]) -> T:
        chain = self._resolver.get_resolution_chain()
        depth = len(chain)
        try:
            resolved = self._resolver.resolve(cls)
        finally:
            del chain[depth:]
        if isinstance(resolved, _Unresolved):
            raise UnknownDependencyError(cls)

        return resolved

    def inject(self, function: Callable) -> Callable:
        injector = _Injector(self._resolver)
        return injector.inject(function)

    @contextmanager
    def overrides(self, override_map: dict[type[T], T]) -> typing.Iterator[None]:
        # Pushing onto the thread-local stack keeps the resolver itself
        # untouched, so concurrent overrides in other threads are unaffected
        # and cleanup is guaranteed even when the body raises.
        self._resolver.mock_store.push(cast("dict", override_map))
        try:
            yield
        finally:
            self._resolver.mock_store.pop()

    @contextmanager
    def override(self, cls: type[T], mock: T) -> typing.Iterator[None]:
        with self.overrides({cls: mock}):
            yield

    def alias(self, interface: type, implementation: type) -> None:
        self._resolver.aliases[interface] = implementation

    def register_instance(self, cls: type[T], instance: T) -> None:
        """Bind a pre-built object as the implementation for a type.

        Use this when you need to construct an object yourself (e.g.
        because its constructor takes runtime values that aren't
        container-resolvable) and have the container return that exact
        object whenever the given type is requested.  The same instance
        can be registered for multiple types, which is the canonical way
        to share one concrete object across several abstract ports.

        Registrations are process-wide and shared across threads.  They
        beat ``alias()`` and factory methods, but can be replaced for
        the duration of a test via ``override()``.
        """
        self._resolver.instances[cls] = instance


def _is_provide_marker(hint: object) -> bool:
    """Return True if *hint* is ``Provide[T]``."""
    if typing.get_origin(hint) is not typing.Annotated:
        return False
    return any(arg is _provide_marker for arg in typing.get_args(hint)[1:])


def _unwrap_provide(hint: type) -> type:
    """Extract the inner type *T* from ``Provide[T]``."""
    return cast("type", typing.get_args(hint)[0])


class _Injector:
    def __init__(self, _resolver: _Resolver) -> None:
        self._resolver = _resolver

    def inject(self, function: Callable) -> Callable:
        targets = self.__get_injection_targets(function)

        @functools.wraps(function)
        def partial_function(*args, **kwargs) -> Any:
            # Caller-supplied keyword arguments win over container resolution.
            pending = [t for t in targets if t[0] not in kwargs]
            return function(*args, **kwargs, **self.__resolve_targets(pending))

        cast("Any", partial_function).__signature__ = self.__create_new_signature(
            function,
            {name for name, _ in targets},
        )

        return partial_function

    def __get_injection_targets(self, function: Callable) -> list[tuple[str, type]]:
        """Collect ``(parameter name, type)`` for ``Provide[T]``-marked params.

        Introspection happens once at decoration time; resolution happens
        per call, so decorating a function has no side effects.
        """
        signature = inspect.signature(function)
        hints = typing.get_type_hints(function, include_extras=True)
        targets: list[tuple[str, type]] = []
        for p in signature.parameters.values():
            if p.name == "self":
                continue

            hint = hints.get(p.name, p.annotation)
            if not _is_provide_marker(hint):
                continue

            targets.append((p.name, _TypeHelper.disambiguate(_unwrap_provide(hint))))
        return targets

    def __resolve_targets(self, targets: list[tuple[str, type]]) -> dict[str, object]:
        injections: dict[str, object] = {}
        chain = self._resolver.get_resolution_chain()
        for name, target_type in targets:
            depth = len(chain)
            try:
                resolved = self._resolver.resolve(target_type)
            finally:
                del chain[depth:]
            if isinstance(resolved, _Unresolved):
                raise UnknownDependencyError(target_type)
            injections[name] = resolved
        return injections

    def __create_new_signature(
        self,
        function: Callable,
        injected_names: set[str],
    ) -> inspect.Signature:
        remaining_parameters = [
            p
            for p in inspect.signature(function).parameters.values()
            if p.name not in injected_names
        ]

        return inspect.Signature(
            parameters=remaining_parameters,
            return_annotation=(_TypeHelper.get_return_type(function)),
        )


class _TypeHelper:
    @classmethod
    def get_constructor_kwargs(cls, subject: type[T]) -> list[tuple]:
        return cls._cached_constructor_kwargs(cast("Hashable", subject))

    @staticmethod
    @functools.lru_cache(maxsize=512)
    def _cached_constructor_kwargs(key: Hashable) -> list[tuple]:
        subject = cast("type", key)
        try:
            parameters = inspect.signature(subject).parameters.values()
        except ValueError:
            return []

        hints = typing.get_type_hints(subject.__init__)

        return [
            (
                p.name,
                _TypeHelper.disambiguate(hints.get(p.name, p.annotation)),
                _TypeHelper._default_or_unresolved(p.default, p.empty),
            )
            for p in parameters
            if _TypeHelper._is_resolvable(p)
        ]

    @classmethod
    def _is_resolvable(cls, p: inspect.Parameter) -> bool:
        # *args/**kwargs cannot be passed by name; inference leaves them empty.
        if p.kind in (p.POSITIONAL_ONLY, p.VAR_POSITIONAL, p.VAR_KEYWORD):
            return False

        return p.annotation is not p.empty

    @classmethod
    def disambiguate(cls, type_: type[T]) -> type[T]:
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
        # Covers both the Union[object, str] and the "object | str" syntax.
        return typing.get_origin(type_) is typing.Union or isinstance(type_, UnionType)

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
        return cast("type[T]", types.pop())

    @staticmethod
    def accepts_container(method: Callable) -> bool:
        hints = typing.get_type_hints(method)
        return any(
            hint is Container for name, hint in hints.items() if name != "return"
        )

    @staticmethod
    def get_return_type(method: Callable) -> type:
        hints = typing.get_type_hints(method)
        if "return" in hints:
            return cast("type", hints["return"])
        return cast("type", inspect.signature(method).return_annotation)
