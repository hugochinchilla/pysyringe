from pysyringe.singleton import singleton


class EmptyFactory:
    pass


class SingletonTest:
    def test_create_from_type(self):
        instance = singleton(EmptyFactory)

        again = singleton(EmptyFactory)

        assert isinstance(instance, EmptyFactory)
        assert instance == again

    def test_singleton_provide_with_arguments(self):
        class DummyClass:
            def __init__(self, value: str) -> None:
                self._value = value

        instance = singleton(DummyClass, "test")

        instance_again = singleton(DummyClass, "test")

        assert isinstance(instance, DummyClass)
        assert instance == instance_again

    def test_singleton_provide_with_different_arguments(self):
        class DummyClass:
            def __init__(self, value: str) -> None:
                self._value = value

        instance = singleton(DummyClass, "some value")
        other_instance = singleton(DummyClass, "another value")

        assert instance != other_instance
