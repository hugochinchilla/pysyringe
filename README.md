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
  <strong>An opinionated dependency injection library for Python.</strong>
</p>

A container that does not rely on adding decorators to your domain classes. It only wraps views in the infrastructure layer to keep your domain and app layer decoupled from the framework and the container.

[Read the full documentation](https://www.hugochinchilla.net/pysyringe/)

## ✨ Features

- 🚀 **Uninstrusive**: keep your domain clean; doesn't require markers, sentinels, or framework-specific constructs in your function signatures.
- 🏭 **Factory-based wiring**: resolve by return type annotations on your factory.
- 🧩 **Inference-based construction**: auto-wire constructor dependencies by type hints.
- 🧪 **Test-friendly mocks**: replace any dependency per test with `use_mock(...)`.
- 🔒 **Thread-safe mocks**: mocks are stored per-thread; aliases and blacklists are global.
- 🧰 **Aliases & blacklists**: map interfaces to implementations and mark types as non-creatable.
- ⚡ **Resolution cache**: caches factory lookups and constructor introspection (not instances).
- 🔐 **Thread-safe**: singleton creation uses locking; per-thread singletons via `thread_local_singleton`.
- ✅ **High test coverage**: comprehensive test suite ensuring reliability and correctness.

## 📦 Installation

```bash
pip install pysyringe
```

[pysyringe on PyPI](https://pypi.org/project/pysyringe/)

## 🚀 Usage


### 1) Define a factory with return-type annotations

Your factory can be any class. The container inspects public methods and uses the return-type annotation to know what it can provide.

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
from pysyringe.container import Container


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
from pysyringe.container import Container

factory = Factory(getenv("ENVIRONMENT", "development"))
container = Container(factory)
```

### 3) Configure blacklist and aliases

- `never_provide(type)` blacklists types you don't want the container to try to resolve when processing functions decorated with `@container.inject`. This is helpful to prevent the container from attempting to build framework types (e.g., Django/Starlette requests) via constructor inference.

- `alias(interface, implementation)` is a simple way to map an interface to a concrete class without having to provide a factory method. The container will build the implementation using constructor introspection, recursively resolving its dependencies.

```python
from django.core.http import HttpRequest, HttpResponse
from myapp.domain import CalendarInterface
from myapp.infra import Calendar

# Never try to construct these framework types during injection
container.never_provide(HttpRequest)
container.never_provide(HttpResponse)

# Map an interface to a concrete implementation (no factory needed)
container.alias(CalendarInterface, Calendar)
```

### 4) Inject at the call site

Use `@container.inject` to supply arguments by type. Only parameters that can be resolved will be injected; the rest stay as normal function parameters. The decorator returns a partial function with all the dependencies wired; you are responsible for passing the remaining parameters to your methods.

A complete Flask example that prints the current time using an alias:

```python
# app.py
from datetime import datetime, timezone
from flask import Flask
from pysyringe.container import Container


# 1) Define an interface and an implementation in your app
class CalendarInterface:
    def now(self) -> datetime:
        raise NotImplementedError


class Calendar(CalendarInterface):
    def now(self) -> datetime:
        return datetime.now(timezone.utc)


# 2) Create the container and configure an alias
container = Container()                       # No factory needed for this example
container.alias(CalendarInterface, Calendar)  # resolve CalendarInterface -> Calendar


# 3) Write your application and leverage the container.inject to provide dependencies
app = Flask(__name__)

@app.get("/now")
@container.inject
def get_now(calendar: CalendarInterface):
    return {"now": calendar.now().isoformat()}

if __name__ == "__main__":
    app.run(debug=True)
```

### 5.1) Test with mocks (new syntax)

Mocks are thread-local. Configure them per-test and clear afterwards.

```python
import pytest
from pysyringe.container import Container
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

### 5.2) Test with mocks (old syntax)

Mocks are thread-local. Configure them per-test and clear afterwards.

```python
import pytest
from pysyringe.container import Container
from myapp.domain import UserRepository
from myapp.usecases import SignupUserService
from myapp.infra.testing import InMemoryUserRepository


@pytest.fixture(autouse=True)
def clear_container_mocks_after_each_test():
    yield
    container.clear_mocks()


def test_create_user():
    user_repository = InMemoryUserRepository()
    container.use_mock(UserRepository, user_repository)
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
from pysyringe.container import Container


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

The `Container` is thread-safe with respect to mocks. Mocks configured after the container has been created are stored in thread-local storage, so changes made to mocks in one thread do not affect other threads.

- **Shared across all threads**: `alias(...)`, `never_provide(...)`, and the factory configuration (methods on your factory used for resolution).
- **Thread-local**: `use_mock(...)` and `clear_mocks()` operate only on the calling thread's mock store.

Implications:
- Using `use_mock(SomeType, mock_instance)` in one thread will not change what another thread receives for `SomeType`.
- Calling `clear_mocks()` clears only the current thread's mocks.
- To share a behavior globally across threads, prefer `alias(...)` or implement a factory method instead of relying on mocks.
