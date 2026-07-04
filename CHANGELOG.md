# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed

- `override()` / `overrides()` no longer leak the override when the body of the
  `with` block raises; cleanup now happens in a `finally` block (#18).
- Overlapping `override()` blocks in different threads no longer corrupt the
  container. Override state now lives in a thread-local stack instead of
  swapping the container's resolver (#22).
- Cycle-detection and resolution-chain state is now thread-local, eliminating
  spurious `RecursiveResolutionError` when two threads resolve the same type
  concurrently (#23).
- Dependencies whose instances are falsy (empty collections, objects with
  `__len__`/`__bool__` returning zero/False) resolve correctly instead of
  raising `UnknownDependencyError` (#20).
- `@container.inject` no longer crashes on unhashable dependencies such as
  plain dataclasses (#19).
- `singleton()` / `thread_local_singleton()` no longer raise `TypeError` when
  called with two or more keyword arguments (#21).
- `singleton()` no longer deadlocks when a singleton's constructor itself
  calls `singleton()`; the creation lock is now reentrant (#34).

### Changed

- `@container.inject` no longer instantiates dependencies at decoration time;
  introspection happens once when decorating and resolution happens per call,
  so importing a module with injected functions has no side effects and calls
  are faster (#24). Injected parameters are now always removed from the
  wrapped signature, whether or not they are currently resolvable.
- Two factory methods declaring the same return type now raise
  `DuplicateFactoryMethodError` at container construction instead of one
  silently shadowing the other; factory methods without a return annotation
  are ignored (#25).
- Builtin types (`str`, `int`, `list`, ...) are never constructed through
  inference; requesting one without a factory raises
  `UnknownDependencyError` as documented.

## [2.0.0]

### Added

- `py.typed` PEP 561 marker for type-checker support.
- `Container` and `Provide` are now re-exported from the top-level package, so you
  can write `from pysyringe import Container, Provide`.
- `Container.register_instance(cls, instance)` for binding a pre-built object to
  one or more types. Useful when a single concrete object satisfies several
  abstract ports and its constructor takes runtime values (settings, secrets)
  that aren't container-resolvable. Registrations are process-wide, shared
  across threads, and take precedence over `alias()` and factory methods, while
  still being replaceable by `override()` in tests.

### Changed

- **Breaking:** `@container.inject` now requires explicit `Provide[T]` markers on
  parameters that should be injected. Unmarked parameters are left for the caller.
  This replaces the previous implicit behaviour where every resolvable parameter was
  injected automatically, which conflicted with frameworks like Django and Dramatiq
  that control their own function signatures.

  ```python
  from pysyringe import Container, Provide

  @container.inject
  def view(request, service: Provide[MyService]):
      ...
  ```

### Fixed

- `@container.inject` now preserves the decorated function's metadata (`__name__`,
  `__qualname__`, `__doc__`, `__module__`, `__wrapped__`, and custom attributes)
  via `functools.wraps`.

### Removed

- `Container.never_provide()` — no longer needed because `@container.inject` only
  injects `Provide[T]`-marked parameters. Framework types like `HttpRequest` are
  simply left unmarked.
- **Breaking:** `Container.use_mock()` and `Container.clear_mocks()`. The
  manual mock API was a footgun: forgetting `clear_mocks()` (or skipping
  teardown when a test failed before reaching it) silently leaked state into
  other tests. Use the `override()` / `overrides()` context managers instead —
  they always clean up, even on exceptions. See `MIGRATION.md` for the
  rewrite pattern, including a pytest fixture that yields inside the `with`
  block for shared setup.

## [1.5.2]

### Fixed

- Fix "IndexError: pop from empty list" during dependency resolution.

## [1.5.1]

What the build asset for 1.5.0 should have been

## [1.5.0]

⚠️ **Incorrectly tagged, use 1.5.1**

### Added

- Factory methods can now receive the `Container` as an argument. If a factory
  method declares a parameter typed as `Container`, the container passes itself
  when invoking the factory during resolution. This allows factories to resolve
  sub-dependencies through the container, benefiting from inference, mocks,
  overrides, and aliases.

## [1.4.2]

### Fixed

- `overrides()` / `override()` now preserves aliases and `never_provide`
  rules registered on the container, so that alias-based resolution and
  blacklisted types continue to work inside an override block.

## [1.4.1]

### Fixed

- `overrides()` / `override()` now carries over mocks previously set via
  `use_mock()`, so that mocks registered by pytest fixtures remain visible
  inside an override block.

## [1.4.0]

### Added

- `thread_local_singleton()` helper for per-thread instance caching, useful for
  resources that are not safe to share across threads (e.g. database sessions).
- Thread safety for `singleton()` — concurrent threads calling `singleton()` for
  the same key will never produce duplicate instances.
- `coverage-all` Makefile target that collects code coverage across all supported
  Python versions (3.11–3.14) using `coverage combine`.
- Documentation URL and changelog URL added to package metadata in
  `pyproject.toml`.
- README sections documenting `thread_local_singleton()`, thread safety
  guarantees, and a comparison table of singleton helpers.
- GitHub Pages documentation site with Markdown-based build system
  (`docs/build.py`, `docs/content.md`, `docs/template.html`).
- Automated CHANGELOG and docs version update in the publish workflow.

### Changed

- Simplified CI workflow by removing the Python version matrix; the Makefile
  already tests across all supported versions.
- Simplified `_Cache` to use a single lock-protected `get_or_create()` method
  instead of separate `has()`/`get()`/`set()` with double-checked locking.
- Refactored Makefile `test` target to loop over a `PYTHON_VERSIONS` variable
  instead of hard-coding each version.
- `UnknownDependencyError` now includes the full resolution chain for nested
  failures, showing the actual unresolvable type instead of just the top-level
  class.
- Removed unnecessary `try/except` around `typing.get_type_hints()` calls.

### Fixed

- Fixed dependency resolution when using `from __future__ import annotations`
  (PEP 563) by resolving string annotations back to actual types via
  `typing.get_type_hints()`.
- Removed unreachable guard for `p.name == "return"` in `_TypeHelper._is_resolvable()`
  that was dead code.

## [1.3.0]

### Added

- New syntax for configuring mocks.
- Ability to resolve dependencies using provided default values.

### Changed

- Ensured tests pass on all supported Python versions.
- Removed unsupported Python version from the test matrix.
- Added `.PHONY` markers to Makefile targets.

### Fixed

- Removed code that was not being needed.

[Unreleased]: https://github.com/hugochinchilla/pysyringe/compare/v2.0.0...HEAD
[2.0.0]: https://github.com/hugochinchilla/pysyringe/compare/v1.5.2...v2.0.0
[1.5.2]: https://github.com/hugochinchilla/pysyringe/compare/v1.5.1...v1.5.2
[1.5.1]: https://github.com/hugochinchilla/pysyringe/compare/v1.4.2...v1.5.1
[1.4.2]: https://github.com/hugochinchilla/pysyringe/compare/v1.4.1...v1.4.2
[1.4.1]: https://github.com/hugochinchilla/pysyringe/compare/v1.4.0...v1.4.1
[1.4.0]: https://github.com/hugochinchilla/pysyringe/compare/v1.3.0...v1.4.0
[1.3.0]: https://github.com/hugochinchilla/pysyringe/compare/v1.2.2...v1.3.0
