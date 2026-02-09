# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased] — 1.4.0

### Added

- `thread_local_singleton()` helper for per-thread instance caching, useful for
  resources that are not safe to share across threads (e.g. database sessions).
- Thread safety for `singleton()` using double-checked locking — concurrent
  threads calling `singleton()` for the same key will never produce duplicate
  instances.
- `coverage-all` Makefile target that collects code coverage across all supported
  Python versions (3.11–3.14) using `coverage combine`.
- Documentation URL added to package metadata in `pyproject.toml`.
- README sections documenting `thread_local_singleton()`, thread safety
  guarantees, and a comparison table of singleton helpers.

### Changed

- Simplified CI workflow by removing the Python version matrix; the Makefile
  already tests across all supported versions.
- Refactored `_Cache` to use a single `get_or_create()` method with a lock
  instead of separate `has()`/`get()`/`set()` methods, eliminating race
  conditions.
- Refactored Makefile `test` target to loop over a `PYTHON_VERSIONS` variable
  instead of hard-coding each version.

### Fixed

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

[Unreleased]: https://github.com/hugochinchilla/pysyringe/compare/v1.3.0...HEAD
[1.3.0]: https://github.com/hugochinchilla/pysyringe/compare/v1.2.2...v1.3.0
