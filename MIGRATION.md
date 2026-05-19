# Migrating from 1.x to 2.0

## `@container.inject` requires `Provide[T]` markers

In 1.x, `@container.inject` automatically injected every parameter whose type
the container could resolve. This caused conflicts with frameworks like Django
and Dramatiq that control their own function signatures.

In 2.0, you must explicitly mark which parameters should be injected using the
`Provide[T]` type annotation. All other parameters are left for the caller.

### Before (1.x)

```python
from pysyringe.container import Container

container = Container()
container.never_provide(HttpRequest)

@container.inject
def view(request: HttpRequest, service: MyService):
    ...
```

### After (2.0)

```python
from pysyringe import Container, Provide

container = Container()

@container.inject
def view(request: HttpRequest, service: Provide[MyService]):
    ...
```

**What changed:**

1. Add `Provide[...]` around the type of each parameter you want the container
   to inject.
2. Remove all `container.never_provide(...)` calls — they no longer exist.
   Framework types like `HttpRequest` are simply left without a `Provide[T]`
   marker, so the container ignores them.
3. Update imports: `Container` and `Provide` can now be imported directly from
   `pysyringe` instead of `pysyringe.container`.

### Step by step

1. **Find all `@container.inject` usages** in your codebase.
2. For each decorated function, **wrap injected parameter types** with
   `Provide[...]`:
   ```python
   # Before
   def view(request, repo: UserRepository, mailer: EmailSender): ...

   # After
   def view(request, repo: Provide[UserRepository], mailer: Provide[EmailSender]): ...
   ```
3. **Delete all `container.never_provide(...)` calls.**
4. **Update imports** — add `Provide` to your import:
   ```python
   from pysyringe import Container, Provide
   ```

### `Provide[T]` is transparent to type checkers

`Provide[T]` expands to `typing.Annotated[T, ...]` at runtime. Type checkers
(mypy, pyright) treat it as equivalent to `T`, so your type checking continues
to work without changes.

## `Container.never_provide()` removed

This method no longer exists. It was a workaround for the implicit injection
behaviour. With explicit `Provide[T]` markers, the container only touches
parameters you explicitly mark — there is nothing to blacklist.

## `Container.use_mock()` and `Container.clear_mocks()` removed

The manual mock API has been removed in favor of the `override()` /
`overrides()` context managers. The manual API was a footgun: forgetting
`clear_mocks()` (or skipping teardown when a test failed before reaching
it) silently leaked state into other tests. The context managers always
clean up, even on exceptions.

### Before (1.x)

```python
import pytest


@pytest.fixture(autouse=True)
def clear_container_mocks():
    yield
    container.clear_mocks()


def test_create_user():
    container.use_mock(UserRepository, InMemoryUserRepository())
    service = container.provide(SignupUserService)
    ...
```

### After (2.0)

```python
def test_create_user():
    with container.override(UserRepository, InMemoryUserRepository()):
        service = container.provide(SignupUserService)
        ...
```

For shared setup, wrap `override()` in a pytest fixture and yield from
inside the `with` block — exception-safe by construction, no
`autouse` teardown needed:

```python
import pytest


@pytest.fixture
def user_repository():
    repo = InMemoryUserRepository()
    with container.override(UserRepository, repo):
        yield repo


def test_create_user(user_repository):
    service = container.provide(SignupUserService)
    ...
```

For replacing several dependencies at once, use `overrides()`:

```python
with container.overrides({
    UserRepository: InMemoryUserRepository(),
    EmailSender: FakeEmailSender(),
}):
    service = container.provide(SignupUserService)
    ...
```

## New package-level imports

`Container` and `Provide` are now re-exported from the `pysyringe` package:

```python
# 2.0 (preferred)
from pysyringe import Container, Provide

# Still works (unchanged)
from pysyringe.container import Container, Provide
```

## Everything else is unchanged

- `container.provide(SomeType)` works the same way.
- `container.alias(...)` works the same way.
- `container.override(...)` and `container.overrides(...)` work the same way.
- `singleton()` and `thread_local_singleton()` work the same way.
- Constructor inference for `container.provide()` is unchanged.
- Thread safety guarantees are unchanged.
