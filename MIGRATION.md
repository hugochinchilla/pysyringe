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
- `container.use_mock(...)` and `container.clear_mocks()` work the same way.
- `singleton()` and `thread_local_singleton()` work the same way.
- Constructor inference for `container.provide()` is unchanged.
- Thread safety guarantees are unchanged.
