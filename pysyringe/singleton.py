from typing import ClassVar, TypeVar

T = TypeVar("T")
CacheKey = tuple[T, ...]


class _Cache:
    _entries: ClassVar[dict] = {}

    @classmethod
    def has(cls, key: CacheKey[T]) -> bool:
        return key in cls._entries

    @classmethod
    def get(cls, key: CacheKey[T]) -> T:
        instance: T = cls._entries[key]
        return instance

    @classmethod
    def set(cls, key: CacheKey[T], value: T) -> None:
        cls._entries[key] = value


def singleton(type_: type[T], *type_args, **type_kwargs) -> T:
    key = (*(type_,), *(type_args,), *tuple(*sorted(type_kwargs.items())))

    if not _Cache.has(key):
        instance: T = type_(*type_args, **type_kwargs)
        _Cache.set(key, instance)

    inst: T = _Cache.get(key)
    return inst
