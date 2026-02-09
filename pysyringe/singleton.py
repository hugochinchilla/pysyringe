import threading
from typing import ClassVar, TypeVar

T = TypeVar("T")
CacheKey = tuple[T, ...]


class _Cache:
    _entries: ClassVar[dict] = {}
    _lock: ClassVar[threading.Lock] = threading.Lock()

    @classmethod
    def get_or_create(cls, key: CacheKey[T], factory: object) -> T:
        if key in cls._entries:
            return cls._entries[key]

        with cls._lock:
            if key in cls._entries:
                return cls._entries[key]
            instance = factory()
            cls._entries[key] = instance
            return instance


def singleton(type_: type[T], *type_args, **type_kwargs) -> T:
    key = (*(type_,), *(type_args,), *tuple(*sorted(type_kwargs.items())))
    return _Cache.get_or_create(key, lambda: type_(*type_args, **type_kwargs))


class _ThreadLocalCache:
    _local: ClassVar[threading.local] = threading.local()

    @classmethod
    def get_or_create(cls, key: CacheKey[T], factory: object) -> T:
        entries = getattr(cls._local, "entries", None)
        if entries is None:
            entries = {}
            cls._local.entries = entries

        if key not in entries:
            entries[key] = factory()

        return entries[key]


def thread_local_singleton(type_: type[T], *type_args, **type_kwargs) -> T:
    key = (*(type_,), *(type_args,), *tuple(*sorted(type_kwargs.items())))
    return _ThreadLocalCache.get_or_create(
        key, lambda: type_(*type_args, **type_kwargs)
    )
