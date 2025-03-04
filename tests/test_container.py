import pytest

from pysyringe.container import Container, UnknownDependencyError


class EmptyFactory:
    pass


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
