from typing import Union

import pytest

from pysyringe.container import (
    Container,
    RecursiveResolutionError,
    UnknownDependencyError,
    UnresolvableUnionTypeError,
)
from pysyringe.singleton import singleton, thread_local_singleton


class EmptyFactory:
    pass


class Database:
    def __init__(self, connection_string: str) -> None:
        self.connection_string = connection_string


class DatabaseFactory:
    def create_db(self) -> Database:
        return Database("sqlite://")


class DatabaseService:
    def __init__(self, database: Database) -> None:
        self.dependency = database


class ContainerTest:
    def test_create_class_from_inference(self):
        class A:
            pass

        container = Container(EmptyFactory())
        instance = container.provide(A)

        assert isinstance(instance, A)

    def test_provide_class_with_nested_inference(self):
        class A:
            pass

        class B:
            def __init__(self, dependency: A) -> None:
                self.dependency = dependency

        class Service:
            def __init__(self, dependency: B) -> None:
                self.dependency = dependency

        container = Container(EmptyFactory())

        service = container.provide(Service)

        assert isinstance(service.dependency.dependency, A)

    def test_raises_exception_when_creating_class_with_unknown_dependencies(self):
        class Person:
            def __init__(self, name: str) -> None:
                pass

        container = Container(EmptyFactory())

        with pytest.raises(
            UnknownDependencyError,
            match=r"Container does not know how to provide <class 'str'>",
        ):
            container.provide(Person)

    def test_nested_resolution_error_includes_chain(self):
        class C:
            def __init__(self, name: str) -> None:
                self.name = name

        class B:
            def __init__(self, c: C) -> None:
                self.c = c

        class Service:
            def __init__(self, b: B) -> None:
                self.b = b

        container = Container(EmptyFactory())

        with pytest.raises(UnknownDependencyError, match=r"str") as exc_info:
            container.provide(Service)

        message = str(exc_info.value)
        assert "Resolution chain:" in message
        assert "Service requires B (parameter 'b')" in message
        assert "B requires C (parameter 'c')" in message
        assert "C requires str (parameter 'name')" in message

    def test_register_and_use_factory(self):
        container = Container(DatabaseFactory())

        db = container.provide(Database)

        assert isinstance(db, Database)
        assert db.connection_string == "sqlite://"

    def test_use_mock_dependency(self):
        mock_database = object()
        container = Container(DatabaseFactory())
        container.use_mock(Database, mock_database)

        service = container.provide(DatabaseService)

        assert service.dependency is mock_database

    def test_clear_mock_dependencies(self):
        mock_database = object()
        container = Container(DatabaseFactory())
        container.use_mock(Database, mock_database)
        container.clear_mocks()

        service = container.provide(DatabaseService)

        assert service.dependency is not mock_database
        assert isinstance(service.dependency, Database)

    def test_use_type_alias(self):
        class Database:
            pass

        class Postgres(Database):
            pass

        container = Container(EmptyFactory())
        container.alias(Database, Postgres)

        db = container.provide(Database)

        assert isinstance(db, Postgres)

    def test_handle_optional_dependencies(self):
        class Service:
            def __init__(self, dependency: Database | None = None) -> None:
                self.dependency = dependency

        container = Container(DatabaseFactory())

        service = container.provide(Service)

        assert isinstance(service.dependency, Database)

    def test_raises_exception_for_union_types_using_or_syntax(self):
        class Service:
            def __init__(self, dependency: Database | object) -> None:
                self.dependency = dependency

        container = Container(EmptyFactory())

        with pytest.raises(UnresolvableUnionTypeError):
            container.provide(Service)

    def test_raises_exception_for_union_types_union_constructor_syntax(self):
        class Service:
            def __init__(
                self, dependency: Union[Database, object]  # noqa: UP007
            ) -> None:
                self.dependency = dependency

        container = Container(EmptyFactory())

        with pytest.raises(UnresolvableUnionTypeError):
            container.provide(Service)

    def test_inject_function(self):
        class Dependency:
            pass

        def function(dep: Dependency) -> Dependency:
            return dep

        container = Container(EmptyFactory())
        injected_function = container.inject(function)
        result = injected_function()

        assert isinstance(result, Dependency)

    def test_provide_blacklisted_dependency_results_in_error(self):
        class ForbiddenDependency:
            pass

        class Service:
            def __init__(self, dependency: ForbiddenDependency) -> None:
                self.dependency = dependency

        container = Container(EmptyFactory())
        container.never_provide(ForbiddenDependency)

        with pytest.raises(UnknownDependencyError):
            container.provide(Service)

    def test_container_without_factory_supports_inference_and_alias(self):
        class A:
            pass

        class B:
            def __init__(self, a: A) -> None:
                self.a = a

        container = Container(factory=None)
        # Pure inference
        instance_b = container.provide(B)
        assert isinstance(instance_b, B)
        assert isinstance(instance_b.a, A)

        # Alias without factory
        class Interface:
            pass

        container.alias(Interface, A)
        instance_interface = container.provide(Interface)
        assert isinstance(instance_interface, A)

    def test_container_with_factory_using_singleton_helper(self):
        class DatabaseClient:
            def __init__(self, connection_string: str) -> None:
                self.connection_string = connection_string

        class Factory:
            def get_database_client(self) -> DatabaseClient:
                # Use singleton to ensure same connection string = same instance
                return singleton(DatabaseClient, "postgresql://localhost:5432/mydb")

        container = Container(Factory())

        # Multiple calls should return the same instance
        client1 = container.provide(DatabaseClient)
        client2 = container.provide(DatabaseClient)

        assert client1 is client2
        assert isinstance(client1, DatabaseClient)
        assert client1.connection_string == "postgresql://localhost:5432/mydb"

    def test_resolve_with_non_class_type_handles_typeerror(self):
        """Test that resolve() handles TypeError when issubclass() fails with non-class types."""
        # Create a resolver with a never_provide list that will cause issubclass to fail
        container = Container(factory=None)
        container.never_provide(
            "not_a_class"
        )  # This will cause TypeError in issubclass

        # This should not raise an exception, but return _Unresolved
        # because issubclass() will raise TypeError for non-class types
        with pytest.raises(UnknownDependencyError):
            container.provide("not_a_class")

    def test_thread_local_mocks_do_not_leak_between_threads(self):
        from concurrent.futures import ThreadPoolExecutor

        container = Container(DatabaseFactory())

        def thread_one() -> object:
            mock_database = object()
            container.use_mock(Database, mock_database)
            service = container.provide(DatabaseService)
            # Sanity check within the same thread
            assert service.dependency is mock_database
            return mock_database

        def thread_two() -> DatabaseService:
            service: DatabaseService = container.provide(DatabaseService)
            return service

        # Run first thread that sets the mock
        with ThreadPoolExecutor(max_workers=1) as pool:
            mock_from_thread_one = pool.submit(thread_one).result()

        # After the first thread completes, start a second thread that should
        # not see the mock set by the first thread
        with ThreadPoolExecutor(max_workers=1) as pool:
            service_from_thread_two = pool.submit(thread_two).result()

        assert service_from_thread_two.dependency is not mock_from_thread_one
        assert isinstance(service_from_thread_two.dependency, Database)

    def test_init_service_with_default_argument(self):
        class Service:
            def __init__(self, data: list[str] | None = None) -> None:
                self.data = data or []

        container = Container()

        instance = container.provide(Service)

        assert instance.data == []

    def test_override_context_manager_replaces_dependency_while_inside_with_statement(
        self,
    ):
        mock_database = object()
        container = Container(DatabaseFactory())
        with container.overrides({Database: mock_database}):
            service = container.provide(DatabaseService)

        assert service.dependency is mock_database

    def test_override_context_manager_stops_replacing_dependency_after_with_statement(
        self,
    ):
        mock_database = object()
        container = Container(DatabaseFactory())
        with container.overrides({Database: mock_database}):
            pass

        service = container.provide(DatabaseService)

        assert service.dependency is not mock_database

    def test_override_single_dependency(self):
        mock_database = object()
        container = Container(DatabaseFactory())

        with container.override(Database, mock_database):
            service = container.provide(DatabaseService)
        non_mocked = container.provide(DatabaseService)

        assert service.dependency is mock_database
        assert non_mocked.dependency is not mock_database

    def test_positional_only_params_are_skipped_during_inference(self):
        class Dep:
            pass

        class Service:
            def __init__(self, dep: Dep, /) -> None:
                self.dep = dep

        container = Container(EmptyFactory())

        # positional-only param is skipped, so Service() is called with no args
        # which fails because dep is required but positional-only
        with pytest.raises(TypeError):
            container.provide(Service)

    def test_inject_function_without_return_type(self):
        class Dependency:
            pass

        def function(dep: Dependency):
            return dep

        container = Container(EmptyFactory())
        injected_function = container.inject(function)
        result = injected_function()

        assert isinstance(result, Dependency)

    def test_factory_method_receives_container_when_parameter_typed_as_container(self):
        class Config:
            def __init__(self) -> None:
                self.value = "from_inference"

        class Service:
            def __init__(self, config: Config) -> None:
                self.config = config

        class Factory:
            def create_service(self, container: Container) -> Service:
                config = container.provide(Config)
                return Service(config)

        container = Container(Factory())
        service = container.provide(Service)

        assert isinstance(service, Service)
        assert isinstance(service.config, Config)
        assert service.config.value == "from_inference"

    def test_factory_without_container_param_still_works(self):
        container = Container(DatabaseFactory())

        db = container.provide(Database)

        assert isinstance(db, Database)
        assert db.connection_string == "sqlite://"

    def test_factory_receives_container_that_respects_overrides(self):
        class Dep:
            def __init__(self) -> None:
                self.source = "real"

        class Service:
            def __init__(self, dep: Dep) -> None:
                self.dep = dep

        class Factory:
            def create_service(self, container: Container) -> Service:
                return Service(container.provide(Dep))

        container = Container(Factory())

        mock_dep = Dep()
        mock_dep.source = "mocked"

        with container.override(Dep, mock_dep):
            service = container.provide(Service)

        assert service.dep is mock_dep
        assert service.dep.source == "mocked"


class ThreadLocalSingletonWithMocksTest:
    """Verify that thread_local_singleton factories work correctly with
    both ``override`` and ``use_mock`` APIs."""

    def test_override_beats_thread_local_singleton_factory(self):
        class DbClient:
            def __init__(self, dsn: str) -> None:
                self.dsn = dsn

        class Factory:
            def get_db(self) -> DbClient:
                return thread_local_singleton(DbClient, "prod://db")

        container = Container(Factory())
        mock_client = DbClient("mock://db")

        with container.override(DbClient, mock_client):
            provided = container.provide(DbClient)

        assert provided is mock_client

    def test_override_restores_thread_local_singleton_after_context(self):
        class DbClient:
            def __init__(self, dsn: str) -> None:
                self.dsn = dsn

        class Factory:
            def get_db(self) -> DbClient:
                return thread_local_singleton(DbClient, "prod://db")

        container = Container(Factory())
        mock_client = DbClient("mock://db")

        with container.override(DbClient, mock_client):
            pass

        after = container.provide(DbClient)

        assert after is not mock_client
        assert after.dsn == "prod://db"

    def test_use_mock_beats_thread_local_singleton_factory(self):
        class DbClient:
            def __init__(self, dsn: str) -> None:
                self.dsn = dsn

        class Factory:
            def get_db(self) -> DbClient:
                return thread_local_singleton(DbClient, "prod://db")

        container = Container(Factory())
        mock_client = DbClient("mock://db")
        container.use_mock(DbClient, mock_client)

        provided = container.provide(DbClient)

        assert provided is mock_client

    def test_use_mock_clear_restores_thread_local_singleton(self):
        class DbClient:
            def __init__(self, dsn: str) -> None:
                self.dsn = dsn

        class Factory:
            def get_db(self) -> DbClient:
                return thread_local_singleton(DbClient, "prod://db")

        container = Container(Factory())
        mock_client = DbClient("mock://db")
        container.use_mock(DbClient, mock_client)
        container.clear_mocks()

        provided = container.provide(DbClient)

        assert provided is not mock_client
        assert provided.dsn == "prod://db"

    def test_override_thread_local_singleton_does_not_leak_to_other_threads(self):
        from concurrent.futures import ThreadPoolExecutor

        class DbClient:
            def __init__(self, dsn: str) -> None:
                self.dsn = dsn

        class Factory:
            def get_db(self) -> DbClient:
                return thread_local_singleton(DbClient, "prod://db")

        container = Container(Factory())
        mock_client = DbClient("mock://db")

        with container.override(DbClient, mock_client):
            # The override mock is thread-local, so another thread
            # should NOT see it — it gets the real factory result.
            def provide_in_thread() -> DbClient:
                return container.provide(DbClient)

            with ThreadPoolExecutor(max_workers=1) as pool:
                from_thread = pool.submit(provide_in_thread).result()

            assert from_thread is not mock_client
            assert from_thread.dsn == "prod://db"

    def test_use_mock_thread_local_singleton_does_not_leak_across_threads(self):
        from concurrent.futures import ThreadPoolExecutor

        class DbClient:
            def __init__(self, dsn: str) -> None:
                self.dsn = dsn

        class Factory:
            def get_db(self) -> DbClient:
                return thread_local_singleton(DbClient, "prod://db")

        container = Container(Factory())

        def set_mock_and_provide() -> DbClient:
            mock_client = DbClient("mock://db")
            container.use_mock(DbClient, mock_client)
            return container.provide(DbClient)

        def provide_without_mock() -> DbClient:
            return container.provide(DbClient)

        with ThreadPoolExecutor(max_workers=1) as pool:
            mock_result = pool.submit(set_mock_and_provide).result()

        with ThreadPoolExecutor(max_workers=1) as pool:
            clean_result = pool.submit(provide_without_mock).result()

        assert mock_result.dsn == "mock://db"
        assert clean_result.dsn == "prod://db"
        assert mock_result is not clean_result

    def test_override_preserves_use_mock_set_by_fixture(self):
        """Simulate a pytest fixture that sets a mock via use_mock, then
        a test that adds an override for a *different* service.  The
        fixture mock must still be visible inside the override block."""

        class BackendNotifier:
            def notify(self) -> str:
                return "real"

        class PageRotator:
            def rotate(self) -> str:
                return "real"

        class Workflow:
            def __init__(
                self, notifier: BackendNotifier, rotator: PageRotator
            ) -> None:
                self.notifier = notifier
                self.rotator = rotator

        class Factory:
            def get_notifier(self) -> BackendNotifier:
                return thread_local_singleton(BackendNotifier)

            def get_rotator(self) -> PageRotator:
                return thread_local_singleton(PageRotator)

        container = Container(Factory())

        # ---- fixture: set a mock for BackendNotifier via use_mock ----
        mock_notifier = BackendNotifier()
        mock_notifier.notify = lambda: "mocked"  # type: ignore[assignment]
        container.use_mock(BackendNotifier, mock_notifier)

        # ---- test body: override PageRotator only ----
        mock_rotator = PageRotator()
        mock_rotator.rotate = lambda: "mocked"  # type: ignore[assignment]

        with container.override(PageRotator, mock_rotator):
            workflow = container.provide(Workflow)

        # The override for PageRotator should work
        assert workflow.rotator is mock_rotator
        # The fixture mock for BackendNotifier should still be active
        assert workflow.notifier is mock_notifier

        # ---- fixture teardown ----
        container.clear_mocks()

    def test_nested_overrides_carry_outer_mock_into_inner_block(self):
        class ServiceA:
            pass

        class ServiceB:
            pass

        class ServiceC:
            def __init__(self, a: ServiceA, b: ServiceB) -> None:
                self.a = a
                self.b = b

        container = Container()
        mock_a = ServiceA()
        mock_b = ServiceB()

        with container.override(ServiceA, mock_a):
            with container.override(ServiceB, mock_b):
                result = container.provide(ServiceC)

            assert result.a is mock_a
            assert result.b is mock_b

    def test_nested_overrides_restore_correctly_after_inner_block(self):
        class ServiceA:
            pass

        class ServiceB:
            pass

        class Composite:
            def __init__(self, a: ServiceA, b: ServiceB) -> None:
                self.a = a
                self.b = b

        container = Container()
        mock_a = ServiceA()
        mock_b = ServiceB()

        with container.override(ServiceA, mock_a):
            with container.override(ServiceB, mock_b):
                pass

            # After inner block, ServiceB override is gone but ServiceA stays
            result = container.provide(Composite)

            assert result.a is mock_a
            assert result.b is not mock_b

        # After outer block, both overrides are gone
        result = container.provide(Composite)

        assert result.a is not mock_a
        assert result.b is not mock_b

    def test_inner_override_can_shadow_outer_override_for_same_type(self):
        class Service:
            pass

        container = Container()
        outer_mock = Service()
        inner_mock = Service()

        with container.override(Service, outer_mock):
            assert container.provide(Service) is outer_mock

            with container.override(Service, inner_mock):
                assert container.provide(Service) is inner_mock

            assert container.provide(Service) is outer_mock

        # After both blocks, the real inference kicks in
        result = container.provide(Service)
        assert result is not outer_mock
        assert result is not inner_mock

    def test_overrides_preserves_aliases(self):
        class Interface:
            pass

        class Implementation(Interface):
            pass

        class Service:
            def __init__(self, dep: Interface) -> None:
                self.dep = dep

        container = Container()
        container.alias(Interface, Implementation)

        mock_impl = Implementation()
        with container.override(Implementation, mock_impl):
            service = container.provide(Service)

        assert service.dep is mock_impl

    def test_resolution_chain_cleanup_does_not_crash_when_factory_calls_provide(self):
        """Regression: IndexError: pop from empty list.

        When a factory method calls container.provide() internally
        and that inner provide() fails, its ``finally`` block calls
        ``_resolution_chain.clear()``.  Control then returns to the
        outer ``__make_from_inference`` which tries to ``pop()`` from
        the now-empty chain.

        The fix wraps the resolve + unresolved check in try/finally
        so ``pop()`` always runs before the chain can be cleared by
        an inner ``provide()`` call.
        """

        class Unresolvable:
            def __init__(self, name: str) -> None:
                self.name = name

        class Dep:
            pass

        class Service:
            def __init__(self, dep: Dep) -> None:
                self.dep = dep

        class Factory:
            def create_dep(self, container: Container) -> Dep:
                # This inner provide() will fail and its finally
                # block will clear the shared _resolution_chain.
                try:
                    container.provide(Unresolvable)
                except UnknownDependencyError:
                    pass
                return Dep()

        container = Container(Factory())

        # Without the fix, this raises IndexError: pop from empty list
        service = container.provide(Service)
        assert isinstance(service, Service)
        assert isinstance(service.dep, Dep)

    def test_overrides_preserves_never_provide(self):
        class Forbidden:
            pass

        class Service:
            def __init__(self, dep: Forbidden) -> None:
                self.dep = dep

        container = Container()
        container.never_provide(Forbidden)

        mock_service = Service(Forbidden())
        with container.override(Service, mock_service):
            with pytest.raises(UnknownDependencyError):
                container.provide(Forbidden)


class RecursiveResolutionTest:
    def test_factory_that_provides_its_own_return_type_raises_error(self):
        class Service:
            pass

        class Factory:
            def create_service(self, container: Container) -> Service:
                return container.provide(Service)

        container = Container(Factory())

        with pytest.raises(RecursiveResolutionError, match="Recursive resolution detected for Service"):
            container.provide(Service)

    def test_indirect_recursion_through_factory_raises_error(self):
        class A:
            pass

        class B:
            pass

        class Factory:
            def create_a(self, container: Container) -> A:
                container.provide(B)
                return A()

            def create_b(self, container: Container) -> B:
                container.provide(A)
                return B()

        container = Container(Factory())

        with pytest.raises(RecursiveResolutionError):
            container.provide(A)

    def test_non_recursive_factory_still_works(self):
        """A factory that calls provide() for a *different* type should work fine."""

        class Config:
            def __init__(self) -> None:
                self.value = "ok"

        class Service:
            def __init__(self, config: Config) -> None:
                self.config = config

        class Factory:
            def create_service(self, container: Container) -> Service:
                config = container.provide(Config)
                return Service(config)

        container = Container(Factory())

        service = container.provide(Service)
        assert isinstance(service, Service)
        assert service.config.value == "ok"

    def test_recursive_resolution_error_message_shows_cycle(self):
        class A:
            pass

        class B:
            pass

        class Factory:
            def create_a(self, container: Container) -> A:
                container.provide(B)
                return A()

            def create_b(self, container: Container) -> B:
                container.provide(A)
                return B()

        container = Container(Factory())

        with pytest.raises(RecursiveResolutionError) as exc_info:
            container.provide(A)

        message = str(exc_info.value)
        assert "A" in message
        assert "B" in message

    def test_resolving_set_is_cleaned_up_after_error(self):
        """After a RecursiveResolutionError, the type should be resolvable
        again if the recursion is fixed (e.g. via a mock)."""

        class Service:
            pass

        class Factory:
            def create_service(self, container: Container) -> Service:
                return container.provide(Service)

        container = Container(Factory())

        with pytest.raises(RecursiveResolutionError):
            container.provide(Service)

        # After the error, using a mock should work fine
        mock_service = Service()
        container.use_mock(Service, mock_service)
        assert container.provide(Service) is mock_service
