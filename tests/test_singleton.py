import threading
from concurrent.futures import ThreadPoolExecutor

from pysyringe.singleton import singleton, thread_local_singleton


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

    def test_singleton_with_multiple_keyword_arguments(self):
        """Regression: two or more kwargs used to raise TypeError while
        building the cache key."""

        class DummyClass:
            def __init__(self, host: str, port: int) -> None:
                self.host = host
                self.port = port

        instance = singleton(DummyClass, host="localhost", port=5432)
        same_kwargs_other_order = singleton(DummyClass, port=5432, host="localhost")
        other = singleton(DummyClass, host="localhost", port=5433)

        assert instance is same_kwargs_other_order
        assert instance is not other

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


class ThreadLocalSingletonTest:
    def test_create_from_type(self):
        class Service:
            pass

        instance = thread_local_singleton(Service)

        again = thread_local_singleton(Service)

        assert isinstance(instance, Service)
        assert instance is again

    def test_with_arguments(self):
        class Service:
            def __init__(self, value: str) -> None:
                self._value = value

        instance = thread_local_singleton(Service, "test")

        instance_again = thread_local_singleton(Service, "test")

        assert isinstance(instance, Service)
        assert instance is instance_again

    def test_different_arguments_create_different_instances(self):
        class Service:
            def __init__(self, value: str) -> None:
                self._value = value

        instance = thread_local_singleton(Service, "one")
        other = thread_local_singleton(Service, "two")

        assert instance is not other

    def test_with_multiple_keyword_arguments(self):
        class Service:
            def __init__(self, host: str, port: int) -> None:
                self.host = host
                self.port = port

        instance = thread_local_singleton(Service, host="localhost", port=5432)
        again = thread_local_singleton(Service, port=5432, host="localhost")

        assert instance is again

    def test_different_threads_get_different_instances(self):
        class Service:
            pass

        def create_in_thread() -> Service:
            return thread_local_singleton(Service)

        main_instance = thread_local_singleton(Service)

        with ThreadPoolExecutor(max_workers=1) as pool:
            thread_instance = pool.submit(create_in_thread).result()

        assert main_instance is not thread_instance

    def test_same_thread_gets_same_instance(self):
        class Service:
            pass

        results = []

        def create_twice() -> list[Service]:
            a = thread_local_singleton(Service)
            b = thread_local_singleton(Service)
            return [a, b]

        with ThreadPoolExecutor(max_workers=1) as pool:
            results = pool.submit(create_twice).result()

        assert results[0] is results[1]
