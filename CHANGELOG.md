# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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

[Unreleased]: https://github.com/hugochinchilla/pysyringe/compare/v1.4.1...HEAD
[1.4.1]: https://github.com/hugochinchilla/pysyringe/compare/v1.4.0...v1.4.1
[1.4.0]: https://github.com/hugochinchilla/pysyringe/compare/v1.3.0...v1.4.0
[1.3.0]: https://github.com/hugochinchilla/pysyringe/compare/v1.2.2...v1.3.0
