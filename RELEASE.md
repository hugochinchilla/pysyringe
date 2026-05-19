# Release process

This project publishes to PyPI from CI on tag push. The release flow is:

1. Bump `__version__` in `pysyringe/__init__.py`.
2. Commit the bump.
3. Tag the commit `vX.Y.Z`.
4. Push the commit and the tag.

CI (`.github/workflows/publish.yml`) takes over from there: it runs tests,
updates `CHANGELOG.md`, builds the wheel and sdist, creates a GitHub Release,
and publishes to PyPI.

## Prerequisites: one-time config change

The current `pyproject.toml` uses `hatch-vcs` to derive the version from git
tags and write it back into `pysyringe/__init__.py` at build time. That makes
the committed `__version__` a build artifact and prevents the tag-and-file
values from staying in sync. To make this release flow work,
`pysyringe/__init__.py` must be the source of truth.

In `pyproject.toml`:

- Replace the `[tool.hatch.version]` and `[tool.hatch.build.hooks.vcs]`
  blocks with:

  ```toml
  [tool.hatch.version]
  path = "pysyringe/__init__.py"
  ```

- Drop `hatch-vcs` from `[build-system].requires`.

In `.github/workflows/publish.yml`:

- Remove the `SETUPTOOLS_SCM_PRETEND_VERSION` env on the build step — it is
  a setuptools-scm variable and was never used by hatch-vcs.

After this change, `pysyringe/__init__.py` is hand-maintained and `hatch
version` reads and writes it directly.

## Release commands

Replace `X.Y.Z` with the target version (no `v` prefix here — `hatch version`
takes a bare version string; the tag gets the `v` prefix).

```bash
# 1. Bump the version in pysyringe/__init__.py
uv run hatch version X.Y.Z

# 2. Sanity-check: confirm the new value
uv run hatch version

# 3. Commit, tag, push
git commit -am "prepare release X.Y.Z"
git tag vX.Y.Z
git push && git push --tags
```

`hatch version` also accepts segment bumps: `major`, `minor`, `patch`. For
example `uv run hatch version minor` bumps `1.5.2` to `1.6.0`.

## Pre-flight checks

Before bumping, verify:

- Working tree is clean (`git status`).
- You are on `master` and up to date with `origin/master`.
- `CHANGELOG.md` has an `## [Unreleased]` section with the changes for this
  release. CI rewrites that heading to `## [X.Y.Z] — YYYY-MM-DD` during
  publish, so the content under it is what ships in the release notes.
- Tests pass locally: `uv run pytest`.
- The tag does not already exist: `git tag --list vX.Y.Z` is empty.

## Versioning rules

The project follows [SemVer](https://semver.org/). The publish workflow only
fires on tags matching `vN.N` or `vN.N.N` (see `publish.yml`), so stick to
those shapes. Pre-release suffixes (`-rc1`, `-beta`) will not trigger a
publish under the current workflow — add them to the tag filter first if you
need them.

## If something goes wrong

- **Tests fail in CI after tag push:** the publish job will not run. Fix the
  issue on `master`, delete the tag locally and on the remote
  (`git tag -d vX.Y.Z && git push --delete origin vX.Y.Z`), then redo the
  release from step 1.
- **Wrong version committed:** if the tag is not yet pushed, amend or reset
  and re-tag. If the tag is pushed but the PyPI upload has not happened
  (CI still running or failed), delete the tag as above and re-release. Once
  a version is on PyPI it cannot be reused — bump to the next version
  instead.
