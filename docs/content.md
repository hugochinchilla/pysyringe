## Introduction {#introduction}

PySyringe is a dependency injection container that does **not** require decorators on your domain classes. Instead of polluting your business logic with framework-specific annotations, PySyringe wraps only the views in your infrastructure layer---keeping your domain and application layer decoupled from the framework and the container.

The philosophy is simple: your domain code should not know that a DI container exists. Injection happens at the call site (HTTP handlers, CLI commands, message consumers) using the `@container.inject` decorator or explicit `container.provide()` calls.

## Installation {#installation}

```
pip install pysyringe
```

PySyringe requires **Python 3.11** or later and has no external dependencies.

## Quick Start {#quick-start}

Here is a complete Flask application using PySyringe for dependency injection:

```python
from datetime import datetime, timezone
from flask import Flask
from pysyringe.container import Container


# 1. Define an interface and its implementation
class CalendarInterface:
    def now(self) -> datetime:
        raise NotImplementedError


class Calendar(CalendarInterface):
    def now(self) -> datetime:
        return datetime.now(timezone.utc)


# 2. Create and configure the container
container = Container()
container.alias(CalendarInterface, Calendar)


# 3. Inject dependencies at the call site
app = Flask(__name__)

@app.get("/now")
@container.inject
def get_now(calendar: CalendarInterface):
    return {"now": calendar.now().isoformat()}
```

That's it. The `CalendarInterface` and `Calendar` classes are plain Python---no decorators, no registration. The container resolves the dependency at the call site.

## The Container {#container}

The `Container` class is the central piece of PySyringe. It manages dependency resolution, mocking, and injection.

```python
from pysyringe.container import Container

# Without a factory (inference-only)
container = Container()

# With a factory object
container = Container(MyFactory())
```

The optional `factory` argument is any object whose public methods serve as factory functions. The container inspects these methods at initialization, indexing them by return-type annotation for O(1) lookup.

## How Resolution Works {#resolution}

When you call `container.provide(SomeType)`, the container follows a strict resolution order:

1. **Blacklist check** --- If the type was registered with `never_provide()`, resolution stops immediately.
2. **Mock store** --- Check the current thread's mock store. If a mock was registered via `use_mock()` or `override()`, return it.
3. **Alias lookup** --- If the type was registered with `alias()`, recursively resolve the mapped implementation type.
4. **Factory methods** --- Look up a factory method by return-type annotation. If found, call it and return the result. If the factory method accepts a `Container` parameter, the container passes itself.
5. **Constructor inference** --- Inspect the type's constructor, recursively resolve each parameter by its type hint, and construct the instance.

If none of these strategies succeed, an `UnknownDependencyError` is raised.

!!! note "Note"
    Resolution does not cache instances. Each call to `provide()` creates a new instance (unless you use singleton helpers in your factory). The resolution *process* (parameter introspection, factory lookup) is cached for performance.

## Factory Methods {#factories}

Factories give you full control over how dependencies are constructed. A factory is any object---the container discovers its public methods and indexes them by their return-type annotation.

```python
from pysyringe.container import Container
from pysyringe.singleton import singleton


class EmailSender:
    def __init__(self, host: str, port: int) -> None:
        self.host = host
        self.port = port


class DatabaseClient:
    def __init__(self, connection_string: str) -> None:
        self.connection_string = connection_string


class Factory:
    def __init__(self, environment: str) -> None:
        self.environment = environment

    def get_mailer(self) -> EmailSender:
        if self.environment == "production":
            return EmailSender("smtp.example.org", 25)
        return EmailSender("localhost", 1025)

    def get_database(self) -> DatabaseClient:
        return singleton(DatabaseClient, "postgresql://localhost/mydb")


container = Container(Factory("development"))

mailer = container.provide(EmailSender)       # Uses factory method
db = container.provide(DatabaseClient)        # Uses factory + singleton
```

Key rules for factory methods:

- Methods must be **public** (no leading underscore).
- Methods must have a **return-type annotation**. The container matches requested types to factory methods by this annotation.
- The method name does not matter---only the return type is used for matching.
- Factory methods can use `singleton()` or `thread_local_singleton()` to control instance sharing.

### Container-Aware Factories {#container-aware-factories}

Factory methods can receive the `Container` itself as an argument. If a factory method declares a parameter typed as `Container`, the container passes itself when invoking the factory. This lets factories resolve sub-dependencies through the container, benefiting from inference, mocks, overrides, and aliases.

```python
from pysyringe.container import Container


class AppConfig:
    def __init__(self) -> None:
        self.smtp_host = "smtp.example.org"
        self.smtp_port = 25


class Factory:
    def get_mailer(self, container: Container) -> EmailSender:
        config = container.provide(AppConfig)
        return EmailSender(config.smtp_host, config.smtp_port)


container = Container(Factory())
mailer = container.provide(EmailSender)  # Factory receives the container
```

This is especially useful when:

- A factory needs dependencies that are themselves resolvable by the container (via inference or other factories).
- You want factory-created objects to respect active `override()` or `use_mock()` replacements during tests.
- You need to combine factory logic with the container's recursive resolution.

Factory methods without a `Container` parameter continue to work exactly as before---called with no arguments.

## Constructor Inference {#inference}

When no factory method or alias matches, PySyringe falls back to **constructor inference**. It inspects the class's `__init__` parameters, resolves each by type hint, and constructs the instance.

```python
class Logger:
    pass


class UserRepository:
    def __init__(self, logger: Logger) -> None:
        self.logger = logger


class UserService:
    def __init__(self, repo: UserRepository, logger: Logger) -> None:
        self.repo = repo
        self.logger = logger


container = Container()
service = container.provide(UserService)

# UserService was constructed with:
#   - a UserRepository (auto-constructed with its own Logger)
#   - a Logger
```

Inference rules:

- Parameters **must have type annotations**. Unannotated parameters are skipped.
- **Positional-only** parameters are skipped.
- Parameters with **default values** use the default if the type cannot be resolved.
- Resolution is **recursive**---nested dependencies are resolved automatically.

## Aliases {#aliases}

Aliases map an interface (or abstract class) to a concrete implementation. When the container is asked to provide the interface type, it resolves the mapped implementation instead.

```python
class NotificationService:
    def send(self, message: str) -> None:
        raise NotImplementedError


class SlackNotificationService(NotificationService):
    def send(self, message: str) -> None:
        ...  # send via Slack API


container = Container()
container.alias(NotificationService, SlackNotificationService)

service = container.provide(NotificationService)
# Returns a SlackNotificationService instance
```

The implementation is constructed via inference, so its dependencies are resolved recursively. You don't need a factory method for aliased types.

## Blacklist {#blacklist}

Use `never_provide()` to tell the container it should never attempt to construct certain types. This is useful for framework-provided types that should not be auto-wired.

```python
from django.http import HttpRequest, HttpResponse

container.never_provide(HttpRequest)
container.never_provide(HttpResponse)
```

When a blacklisted type appears as a constructor parameter, the container skips it. If the parameter has a default value, the default is used. If it doesn't, inference for the enclosing type fails gracefully.

## The @inject Decorator {#inject-decorator}

The `@container.inject` decorator is the primary way to wire dependencies into your application's entry points (HTTP handlers, CLI commands, etc.).

```python
@app.get("/users")
@container.inject
def list_users(user_service: UserService, page: int = 1):
    return user_service.list(page=page)
```

How it works:

1. The decorator inspects the function's signature.
2. For each parameter, it attempts to resolve the type from the container.
3. Parameters that **can** be resolved are pre-filled automatically.
4. Parameters that **cannot** be resolved remain as normal function parameters.
5. The function's `__signature__` is updated to reflect only the remaining parameters.

In the example above, `user_service` is injected by the container while `page` remains a normal parameter.

!!! note "Note"
    Dependencies are resolved at **call time**, not at decoration time. This means mocks set after the decorator is applied will still be picked up.

## Providing Dependencies {#provide}

You can also request dependencies directly without using the decorator:

```python
service = container.provide(UserService)
```

This is useful for programmatic access to dependencies, such as in application setup code, background workers, or management commands.

If the type cannot be resolved, an `UnknownDependencyError` is raised.

## Global Singleton {#singleton}

The `singleton()` helper creates or retrieves a globally shared instance. It is designed for use inside factory methods to ensure a single instance is shared across all threads.

```python
from pysyringe.singleton import singleton


class DatabaseClient:
    def __init__(self, connection_string: str) -> None:
        self.connection_string = connection_string


class Factory:
    def get_database(self) -> DatabaseClient:
        return singleton(DatabaseClient, "postgresql://localhost:5432/mydb")


container = Container(Factory())

client1 = container.provide(DatabaseClient)
client2 = container.provide(DatabaseClient)
assert client1 is client2  # Same instance everywhere
```

The cache key includes the class, positional arguments, and keyword arguments (order-independent for keywords). Different arguments produce different instances.

Creation is **thread-safe** using double-checked locking---concurrent threads will never produce duplicate instances for the same key.

Best for: connection pools, HTTP clients, configuration objects, and other thread-safe resources that should be shared globally.

## Thread-Local Singleton {#thread-local-singleton}

The `thread_local_singleton()` helper creates or retrieves a per-thread instance. Each thread gets its own instance; within the same thread, repeated calls return the same object.

```python
from pysyringe.singleton import thread_local_singleton


class DatabaseSession:
    def __init__(self, dsn: str) -> None:
        self.dsn = dsn


class Factory:
    def get_session(self) -> DatabaseSession:
        return thread_local_singleton(DatabaseSession, "postgresql://localhost/mydb")
```

Best for: database sessions, request-scoped state, and other resources that are not thread-safe and should not be shared across threads.

| Helper | Scope | Thread Safety | Use Case |
|--------|-------|---------------|----------|
| `singleton()` | Global | Double-checked locking | Connection pools, HTTP clients |
| `thread_local_singleton()` | Per-thread | Thread-local storage | Database sessions, request state |

## Mocks & Overrides {#mocks}

PySyringe makes it easy to replace dependencies in tests. The recommended approach uses the `override()` context manager.

### Override Context Manager {#override-context}

The `override()` and `overrides()` context managers temporarily replace dependencies for the duration of a `with` block. When the block exits, the original behavior is automatically restored.

#### Single dependency

```python
def test_user_signup():
    mock_repo = InMemoryUserRepository()

    with container.override(UserRepository, mock_repo):
        service = container.provide(SignupUserService)
        service.signup("Jane", "jane@example.org")

    assert mock_repo.get_by_email("jane@example.org")
```

#### Multiple dependencies

```python
def test_with_multiple_overrides():
    with container.overrides({
        UserRepository: InMemoryUserRepository(),
        EmailSender: FakeEmailSender(),
    }):
        service = container.provide(SignupUserService)
        service.signup("Jane", "jane@example.org")
```

!!! note "Recommended"
    Prefer `override()` / `overrides()` over the legacy `use_mock()` API. Context managers guarantee cleanup, preventing mock leakage between tests.

### Legacy Mock API {#legacy-mocks}

The `use_mock()` and `clear_mocks()` methods provide a manual mock API. You are responsible for clearing mocks after each test.

```python
import pytest


@pytest.fixture(autouse=True)
def clear_container_mocks():
    yield
    container.clear_mocks()


def test_user_signup():
    container.use_mock(UserRepository, InMemoryUserRepository())
    service = container.provide(SignupUserService)
    service.signup("Jane", "jane@example.org")
```

## Thread Safety {#thread-safety}

PySyringe is designed with thread safety in mind:

| Feature | Scope | Details |
|---------|-------|---------|
| `alias()` | Global | Shared across all threads. Configure at startup. |
| `never_provide()` | Global | Shared across all threads. Configure at startup. |
| Factory methods | Global | Indexed at container initialization. Shared across threads. |
| `use_mock()` | Per-thread | Stored in thread-local storage. No cross-thread leakage. |
| `clear_mocks()` | Per-thread | Clears only the current thread's mocks. |
| `singleton()` | Global | Thread-safe creation via double-checked locking. |
| `thread_local_singleton()` | Per-thread | One instance per thread via `threading.local()`. |

Implications:

- Calling `use_mock(SomeType, mock)` in one thread does not affect other threads.
- Calling `clear_mocks()` clears only the current thread's mocks.
- To share behavior globally, use `alias()` or a factory method instead of mocks.

## Resolution Cache {#resolution-cache}

PySyringe includes a lightweight cache to speed up dependency resolution without affecting instance semantics.

#### What is cached

- A precomputed map of factory methods keyed by their return type, built once at container initialization for O(1) lookups.
- Constructor parameter introspection, cached via `functools.lru_cache` (512 entries) to avoid repeated signature parsing.

#### What is NOT cached

- **Instances.** Each call to `provide()` creates a fresh instance unless you use `singleton()` or `thread_local_singleton()` in your factory.

This means your singleton semantics, custom sharing strategies, and factory logic remain fully in your control. The cache only reduces the overhead of figuring out *how* to construct dependencies.

## Optional & Union Types {#optional-types}

PySyringe handles Optional and Union types as follows:

#### Optional types

`Optional[T]` (or `T | None`) is automatically unwrapped. The container resolves the non-None type.

```python
class Service:
    def __init__(self, logger: Logger | None = None) -> None:
        self.logger = logger

# The container resolves Logger for the logger parameter.
# If Logger cannot be resolved, it uses the default value (None).
```

#### Union types

Non-Optional union types like `A | B` are **not supported** and will raise an `UnresolvableUnionTypeError`. The container cannot determine which type to provide when multiple options exist.

```python
class Service:
    def __init__(self, store: RedisStore | MemoryStore) -> None:
        ...

# Raises UnresolvableUnionTypeError
# Solution: use an alias or define a factory method instead.
```

## Error Handling {#errors}

PySyringe raises clear exceptions when resolution fails:

#### UnknownDependencyError

Raised when `container.provide(SomeType)` cannot resolve the requested type through any strategy (mocks, aliases, factory, or inference).

```python
from pysyringe.container import UnknownDependencyError

try:
    container.provide(SomeUnknownType)
except UnknownDependencyError as e:
    print(e)  # "Container does not know how to provide <class 'SomeUnknownType'>"
```

#### UnresolvableUnionTypeError

Raised during resolution when a constructor parameter uses a non-Optional union type like `A | B`.

```python
from pysyringe.container import UnresolvableUnionTypeError
# "Cannot resolve [A | B]: remove UnionType or define a factory"
```

## Container API {#api-container}

### Container(factory=None)

<code class="api-signature">Container(factory: object | None = None)</code>

Create a new dependency injection container.

<table class="param-table">
<thead><tr><th>Parameter</th><th>Type</th><th>Description</th></tr></thead>
<tbody>
<tr><td>factory</td><td>object | None</td><td>An optional factory object. Public methods with return-type annotations are indexed as factory methods. If <code>None</code>, the container uses inference only.</td></tr>
</tbody>
</table>

### container.provide(cls)

<code class="api-signature">provide(cls: type[T]) -> T</code>

Resolve and return an instance of the requested type. Raises `UnknownDependencyError` if the type cannot be resolved.

<table class="param-table">
<thead><tr><th>Parameter</th><th>Type</th><th>Description</th></tr></thead>
<tbody>
<tr><td>cls</td><td>type[T]</td><td>The type to resolve.</td></tr>
</tbody>
</table>

### container.inject(function)

<code class="api-signature">inject(function: Callable) -> Callable</code>

Decorator that injects resolvable dependencies into a function. Returns a wrapped function with resolved parameters pre-filled. Unresolvable parameters remain as normal parameters. The returned function's `__signature__` is updated to reflect only the remaining parameters.

<table class="param-table">
<thead><tr><th>Parameter</th><th>Type</th><th>Description</th></tr></thead>
<tbody>
<tr><td>function</td><td>Callable</td><td>The function to decorate.</td></tr>
</tbody>
</table>

### container.alias(interface, implementation)

<code class="api-signature">alias(interface: type, implementation: type) -> None</code>

Map an interface type to a concrete implementation. When the interface is requested, the container resolves the implementation instead (via inference).

<table class="param-table">
<thead><tr><th>Parameter</th><th>Type</th><th>Description</th></tr></thead>
<tbody>
<tr><td>interface</td><td>type</td><td>The abstract type or interface.</td></tr>
<tr><td>implementation</td><td>type</td><td>The concrete type to use.</td></tr>
</tbody>
</table>

### container.never_provide(cls)

<code class="api-signature">never_provide(cls: type[T]) -> None</code>

Blacklist a type so the container will never attempt to resolve it. Useful for framework types like HTTP request/response objects.

<table class="param-table">
<thead><tr><th>Parameter</th><th>Type</th><th>Description</th></tr></thead>
<tbody>
<tr><td>cls</td><td>type[T]</td><td>The type to blacklist.</td></tr>
</tbody>
</table>

### container.override(cls, mock)

<code class="api-signature">@contextmanager override(cls: type[T], mock: T) -> Iterator[None]</code>

Context manager that temporarily replaces a single dependency. The original behavior is restored when the `with` block exits.

<table class="param-table">
<thead><tr><th>Parameter</th><th>Type</th><th>Description</th></tr></thead>
<tbody>
<tr><td>cls</td><td>type[T]</td><td>The type to override.</td></tr>
<tr><td>mock</td><td>T</td><td>The replacement instance.</td></tr>
</tbody>
</table>

### container.overrides(override_map)

<code class="api-signature">@contextmanager overrides(override_map: dict[type[T], T]) -> Iterator[None]</code>

Context manager that temporarily replaces multiple dependencies at once.

<table class="param-table">
<thead><tr><th>Parameter</th><th>Type</th><th>Description</th></tr></thead>
<tbody>
<tr><td>override_map</td><td>dict[type, object]</td><td>A mapping of types to their replacement instances.</td></tr>
</tbody>
</table>

### container.use_mock(cls, mock)

<code class="api-signature">use_mock(cls: type[T], mock: T) -> None</code>

Set a mock for a type in the current thread. Thread-local: does not affect other threads. Prefer `override()` for new code.

<table class="param-table">
<thead><tr><th>Parameter</th><th>Type</th><th>Description</th></tr></thead>
<tbody>
<tr><td>cls</td><td>type[T]</td><td>The type to mock.</td></tr>
<tr><td>mock</td><td>T</td><td>The mock instance.</td></tr>
</tbody>
</table>

### container.clear_mocks()

<code class="api-signature">clear_mocks() -> None</code>

Clear all mocks for the current thread. Only affects the calling thread.

## Singleton API {#api-singleton}

### singleton(type_, *args, **kwargs)

<code class="api-signature">singleton(type_: type[T], *type_args, **type_kwargs) -> T</code>

Create or retrieve a globally shared singleton instance. Thread-safe via double-checked locking. The cache key is the combination of the class, positional args, and keyword args.

<table class="param-table">
<thead><tr><th>Parameter</th><th>Type</th><th>Description</th></tr></thead>
<tbody>
<tr><td>type_</td><td>type[T]</td><td>The class to instantiate.</td></tr>
<tr><td>*type_args</td><td>Any</td><td>Positional arguments for the constructor.</td></tr>
<tr><td>**type_kwargs</td><td>Any</td><td>Keyword arguments for the constructor.</td></tr>
</tbody>
</table>

### thread_local_singleton(type_, *args, **kwargs)

<code class="api-signature">thread_local_singleton(type_: type[T], *type_args, **type_kwargs) -> T</code>

Create or retrieve a per-thread singleton instance. Each thread gets its own instance; within the same thread, repeated calls return the same object. Uses `threading.local()` for storage.

<table class="param-table">
<thead><tr><th>Parameter</th><th>Type</th><th>Description</th></tr></thead>
<tbody>
<tr><td>type_</td><td>type[T]</td><td>The class to instantiate.</td></tr>
<tr><td>*type_args</td><td>Any</td><td>Positional arguments for the constructor.</td></tr>
<tr><td>**type_kwargs</td><td>Any</td><td>Keyword arguments for the constructor.</td></tr>
</tbody>
</table>

## Exceptions {#api-exceptions}

### UnknownDependencyError

<code class="api-signature">class UnknownDependencyError(Exception)</code>

Raised when `container.provide()` cannot resolve the requested type.

Message format: `"Container does not know how to provide <type>"`

```python
from pysyringe.container import UnknownDependencyError
```

### UnresolvableUnionTypeError

<code class="api-signature">class UnresolvableUnionTypeError(Exception)</code>

Raised when a constructor parameter uses a non-Optional union type (e.g. `A | B`) that the container cannot disambiguate.

Message format: `"Cannot resolve [type]: remove UnionType or define a factory"`

```python
from pysyringe.container import UnresolvableUnionTypeError
```
