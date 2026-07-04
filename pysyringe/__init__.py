__version__ = "2.0.0"

from pysyringe.container import (
    Container,
    DuplicateFactoryMethodError,
    Provide,
    RecursiveResolutionError,
    UnknownDependencyError,
    UnresolvableUnionTypeError,
)
from pysyringe.singleton import singleton, thread_local_singleton

__all__ = [
    "Container",
    "DuplicateFactoryMethodError",
    "Provide",
    "RecursiveResolutionError",
    "UnknownDependencyError",
    "UnresolvableUnionTypeError",
    "singleton",
    "thread_local_singleton",
]
