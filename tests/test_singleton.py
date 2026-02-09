import threading
from concurrent.futures import ThreadPoolExecutor

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

    def test_singleton_is_thread_safe(self):
        call_count = 0
        lock = threading.Lock()
        start_event = threading.Event()

        class SlowService:
            def __init__(self) -> None:
                nonlocal call_count
                with lock:
                    call_count += 1

        def create_singleton() -> SlowService:
            start_event.wait()
            return singleton(SlowService)

        with ThreadPoolExecutor(max_workers=10) as pool:
            futures = [pool.submit(create_singleton) for _ in range(10)]
            start_event.set()
            results = [f.result() for f in futures]

        assert call_count == 1
        assert all(r is results[0] for r in results)
