"""Test PEP 563 support: from __future__ import annotations."""

from __future__ import annotations

from pysyringe.container import Container, Provide


class ServiceA:
    pass


class ServiceB:
    def __init__(self, dep: ServiceA) -> None:
        self.dep = dep


class ServiceC:
    def __init__(self, dep: ServiceB) -> None:
        self.dep = dep


class Database:
    def __init__(self, connection_string: str) -> None:
        self.connection_string = connection_string


class DatabaseFactory:
    def create_database(self) -> Database:
        return Database("test://localhost")


class ServiceWithFactory:
    def __init__(self, db: Database) -> None:
        self.db = db


class FutureAnnotationsTest:
    def test_basic_inference(self):
        container = Container()
        instance = container.provide(ServiceB)

        assert isinstance(instance, ServiceB)
        assert isinstance(instance.dep, ServiceA)

    def test_nested_inference(self):
        container = Container()
        instance = container.provide(ServiceC)

        assert isinstance(instance, ServiceC)
        assert isinstance(instance.dep, ServiceB)
        assert isinstance(instance.dep.dep, ServiceA)

    def test_factory_return_type(self):
        container = Container(DatabaseFactory())
        db = container.provide(Database)

        assert isinstance(db, Database)
        assert db.connection_string == "test://localhost"

    def test_factory_and_inference_mixed(self):
        container = Container(DatabaseFactory())
        service = container.provide(ServiceWithFactory)

        assert isinstance(service, ServiceWithFactory)
        assert isinstance(service.db, Database)
        assert service.db.connection_string == "test://localhost"

    def test_inject_decorator(self):
        def function(dep: Provide[ServiceA]) -> ServiceA:
            return dep

        container = Container()
        injected = container.inject(function)
        result = injected()

        assert isinstance(result, ServiceA)

    def test_inject_with_provide_marker_leaves_unmarked_params(self):
        def handler(request: object, dep: Provide[ServiceA]):
            return (request, dep)

        container = Container()
        injected = container.inject(handler)

        sentinel = object()
        req, dep = injected(sentinel)

        assert req is sentinel
        assert isinstance(dep, ServiceA)

    def test_optional_dependency(self):
        class ServiceWithOptional:
            def __init__(self, dep: ServiceA | None = None) -> None:
                self.dep = dep

        container = Container()
        instance = container.provide(ServiceWithOptional)

        assert isinstance(instance, ServiceWithOptional)
        assert isinstance(instance.dep, ServiceA)
