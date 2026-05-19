<p align="center">
  <img src="assets/banner.svg" alt="PySyringe - Dependency Injection for Python" width="100%"/>
</p>

<p align="center">
  <a href="https://github.com/hugochinchilla/pysyringe/actions/workflows/test.yml"><img src="https://github.com/hugochinchilla/pysyringe/actions/workflows/test.yml/badge.svg" alt="Tests"/></a>
  <a href="https://codecov.io/gh/hugochinchilla/pysyringe"><img src="https://codecov.io/gh/hugochinchilla/pysyringe/graph/badge.svg?token=SN3JSCBB4U" alt="Coverage"/></a>
  <a href="https://badge.fury.io/py/pysyringe"><img src="https://badge.fury.io/py/pysyringe.svg" alt="PyPI version"/></a>
  <a href="https://www.hugochinchilla.net/pysyringe/"><img src="https://img.shields.io/badge/docs-pysyringe-blue" alt="Docs"/></a>
</p>

<p align="center">
  <strong>Dependency injection for Python that keeps your domain clean.</strong>
</p>

Your business logic should not know a DI container exists. No decorators on your classes, no registration boilerplate. PySyringe resolves dependencies through type hints and injects them at the call site --- your HTTP handlers, CLI commands, or message consumers --- so the rest of your code stays framework-free.

## ✨ Features

- 🚀 **Zero-decorator DI**: keep your domain clean; inject only at call sites.
- 🎯 **Explicit injection with `Provide[T]`**: mark exactly which parameters should be injected — no conflicts with framework signatures.
- 🏭 **Factory-based wiring**: resolve by return type annotations on your factory.
- 🧩 **Inference-based construction**: auto-wire constructor dependencies by type hints.
- 🧪 **Test-friendly overrides**: replace any dependency per test with the `override(...)` context manager — automatic cleanup, even on exceptions.
- 🔒 **Thread-safe overrides**: overrides are scoped to the current thread; aliases are global.
- 🧰 **Aliases**: map interfaces to implementations without writing factory methods.
- 📌 **Pre-built instances**: bind a single object to one or more ports with `register_instance(...)`.
- ⚡ **Resolution cache**: caches factory lookups and constructor introspection (not instances).

## Installation

```
pip install pysyringe
```

## Example

```python
from myapp.domain import EmailSenderInterface
from myapp.infra import LoggingEmailSender, SmtpEmailSender


class Factory:
    def __init__(self, environment: str) -> None:
        self.environment = environment

    def get_mailer(self) -> EmailSenderInterface:
        if self.environment == "production":
            return SmtpEmailSender("mta.example.org", 25)
        return LoggingEmailSender()
```

Factory methods can also receive the container to resolve sub-dependencies. Just add a `container: Container` parameter:

```python
from pysyringe import Container


class Factory:
    def get_mailer(self, container: Container) -> EmailSenderInterface:
        config = container.provide(AppConfig)
        if config.environment == "production":
            return SmtpEmailSender(config.smtp_host, config.smtp_port)
        return LoggingEmailSender()
```

The container passes itself automatically when it detects a `Container`-typed parameter. This means your factory benefits from the container's full resolution capabilities (inference, mocks, overrides, and aliases). Factory methods without a `Container` parameter continue to work as before.

### 2) Create the container

```python
from os import getenv
from pysyringe import Container

factory = Factory(getenv("ENVIRONMENT", "development"))
container = Container(factory)
```

### 3) Configure aliases

`alias(interface, implementation)` maps an interface to a concrete class without needing a factory method. The container builds the implementation using constructor introspection, recursively resolving its dependencies.

```python
from myapp.domain import CalendarInterface
from myapp.infra import Calendar

container.alias(CalendarInterface, Calendar)
```

### 3.1) Register a pre-built instance

Sometimes you have a single concrete object that satisfies several ports, and you'd rather build it yourself than describe it to the container — typically because its constructor takes runtime values (settings, secrets) that aren't themselves container-resolvable. `register_instance(port, instance)` binds an existing object to a type; the same instance can be registered for multiple ports.

```python
import os
from myapp.domain import Cache, RateLimiter
from myapp.infra import RedisClient

# RedisClient implements both Cache and RateLimiter; its constructor
# takes runtime values that aren't container-resolvable.
client = RedisClient(url=os.environ["REDIS_URL"], max_connections=20)

container.register_instance(Cache, client)
container.register_instance(RateLimiter, client)
```

Registrations are process-wide and shared across threads. They take precedence over `alias()` and factory methods, but `override()` can still replace them in tests.

### 4) Inject at the call site

Use `@container.inject` combined with `Provide[T]` type markers to indicate which parameters should be injected. Only parameters annotated with `Provide[T]` are injected; all others are left for the caller. This makes `@container.inject` safe to use with any framework (Django, Flask, Dramatiq, etc.) since the container never interferes with framework-controlled parameters.

A complete Django example:

```python
# views.py
from django.http import HttpRequest, HttpResponse
from pysyringe import Container, Provide
from myapp.domain import CalendarInterface
from myapp.infra import Calendar

container = Container()
container.alias(CalendarInterface, Calendar)

@container.inject
def get_now(request: HttpRequest, calendar: Provide[CalendarInterface]) -> HttpResponse:
    return HttpResponse(calendar.now().isoformat())
```

`request` is provided by Django as usual. `calendar` is injected by the container. No `never_provide()` needed — the container only touches what you explicitly mark.

### 5) Replace dependencies in tests

Use the `override()` context manager (or `overrides()` for multiple at once)
to swap dependencies for the duration of a `with` block. Cleanup is automatic
— even if the test raises — so state never leaks between tests.

```python
from pysyringe import Container
from myapp.domain import UserRepository
from myapp.usecases import SignupUserService
from myapp.infra.testing import InMemoryUserRepository


def test_create_user():
    user_repository = InMemoryUserRepository()
    with container.override(UserRepository, user_repository):
        service = container.provide(SignupUserService)
        service.signup("John Doe", "john.doe@example.org")

    assert user_repository.get_by_email("john.doe@example.org")
```

For shared setup, wrap `override()` in a pytest fixture and yield from inside
the `with` block:

```python
import pytest


@pytest.fixture
def user_repository():
    repo = InMemoryUserRepository()
    with container.override(UserRepository, repo):
        yield repo


def test_create_user(user_repository):
    service = container.provide(SignupUserService)
    service.signup("John Doe", "john.doe@example.org")

    assert user_repository.get_by_email("john.doe@example.org")
```

### ⚡ Resolution cache

PySyringe includes a lightweight resolution cache to speed up dependency resolution without caching instances.

**What is cached:**
  - A precomputed map of factory methods keyed by their return type (built once at `Container` initialization) for O(1) lookups.
  - Constructor parameter introspection is LRU-cached to avoid repeated signature parsing and type disambiguation.

**What is NOT cached:**
  - Resolved instances. The cache accelerates how dependencies are located and wired, not the objects produced.

This means singleton semantics or any custom sharing strategy you define remain unchanged. The cache only reduces overhead during resolution.

### 🧷 Singleton helpers

PySyringe provides two singleton helpers for use inside your factory methods. Both cache instances keyed by the class and its constructor arguments.

| Helper | Scope | Use case |
|--------|-------|----------|
| `singleton()` | Global (shared across threads) | Thread-safe resources like connection pools or HTTP clients |
| `thread_local_singleton()` | Per-thread | Resources that are not safe to share, like database sessions |

#### `singleton()` — shared across all threads

```python
from pysyringe.singleton import singleton
from pysyringe import Container


class DatabaseClient:
    def __init__(self, connection_string: str) -> None:
        self.connection_string = connection_string


class Factory:
    def get_database_client(self) -> DatabaseClient:
        return singleton(DatabaseClient, "postgresql://localhost:5432/mydb")


container = Container(Factory())

client1 = container.provide(DatabaseClient)
client2 = container.provide(DatabaseClient)
assert client1 is client2  # Same instance, even across threads
```

Creation is thread-safe: concurrent threads calling `singleton()` for the same key will never produce duplicate instances (double-checked locking).

#### `thread_local_singleton()` — one instance per thread

```python
from pysyringe.singleton import thread_local_singleton


class Factory:
    def get_session(self) -> DatabaseSession:
        return thread_local_singleton(DatabaseSession, "postgresql://localhost:5432/mydb")
```

Each thread gets its own `DatabaseSession` instance. Within the same thread, repeated calls return the same object. This is useful for resources that are not thread-safe, such as database sessions or request-scoped state.

#### Notes

- The cache key includes: the class, positional args, and keyword args (order-independent for keywords).
- Perfect for database connections, HTTP clients, or any resource that should be shared per configuration.

### 🔒 Thread safety

The `Container` is thread-safe with respect to overrides. Overrides configured via `override()` / `overrides()` are stored in thread-local storage, so a `with` block in one thread does not affect what other threads see.

- **Shared across all threads**: `alias(...)`, `register_instance(...)`, and the factory configuration (methods on your factory used for resolution).
- **Thread-local**: `override(...)` and `overrides(...)` apply only to the calling thread.

Implications:
- A `with container.override(SomeType, mock)` block in one thread will not change what another thread receives for `SomeType`.
- To share a behavior globally across threads, prefer `alias(...)` or implement a factory method.
