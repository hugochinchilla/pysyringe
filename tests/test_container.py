from typing import Union

import pytest

from pysyringe.container import (
    Container,
    UnknownDependencyError,
    UnresolvableUnionTypeError,
)


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
            match=r"Container does not know how to provide <class '.*\.Person'>",
        ):
            container.provide(Person)

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
