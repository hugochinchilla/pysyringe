# Release process

Releases are published to PyPI by `.github/workflows/publish.yml` when a
`vN.N`, `vN.N.N`, or `vN.N.NrcN` tag is pushed. The release commit must contain:

1. `__version__` in `pysyringe/__init__.py` set to the target version.
2. A `## [X.Y.Z]` section in `CHANGELOG.md` holding the notes for this
   release, with `## [Unreleased]` reset to an empty section above it.

CI verifies both before building and fails the publish if either is wrong.

## Steps

Pick the target version `X.Y.Z` (no `v` prefix here — the prefix is only
on the git tag).

```bash
# 1. Bump __version__ in pysyringe/__init__.py
uvx hatch version X.Y.Z

# 2. Wrap the Unreleased changelog section under [X.Y.Z]
#    - Rename "## [Unreleased]" to "## [X.Y.Z] — YYYY-MM-DD"
#    - Add a fresh empty "## [Unreleased]" above it
#    - Update the [Unreleased] compare link to point at vX.Y.Z...HEAD
#    - Add a new "[X.Y.Z]: ...compare/<prev-tag>...vX.Y.Z" link
$EDITOR CHANGELOG.md

# 3. Sanity-check
uvx hatch version                          # prints X.Y.Z
uv run pytest                              # tests still pass
grep "^## \[X.Y.Z\]" CHANGELOG.md          # entry exists

# 4. Commit, tag, push
git commit -am "prepare release X.Y.Z"
git tag vX.Y.Z
git push && git push --tags
```

`hatch version` also accepts `major` / `minor` / `patch` for segment bumps,
e.g. `uvx hatch version minor` takes `1.5.2` to `1.6.0`.

## Example: 1.5.2 → 1.6.0

Before:

```markdown
## [Unreleased]

### Added
- Foo bar baz.

## [1.5.2]
...

[Unreleased]: https://github.com/hugochinchilla/pysyringe/compare/v1.5.2...HEAD
[1.5.2]: https://github.com/hugochinchilla/pysyringe/compare/v1.5.1...v1.5.2
```

After:

```markdown
## [Unreleased]

## [1.6.0] — 2026-05-19

### Added
- Foo bar baz.

## [1.5.2]
...

[Unreleased]: https://github.com/hugochinchilla/pysyringe/compare/v1.6.0...HEAD
[1.6.0]: https://github.com/hugochinchilla/pysyringe/compare/v1.5.2...v1.6.0
[1.5.2]: https://github.com/hugochinchilla/pysyringe/compare/v1.5.1...v1.5.2
```

Then:

```bash
$ uvx hatch version minor
Old: 1.5.2
New: 1.6.0

$ git commit -am "prepare release 1.6.0"
[master 1a2b3c4] prepare release 1.6.0
 2 files changed, 5 insertions(+), 2 deletions(-)

$ git tag v1.6.0

$ git push && git push --tags
```

CI then runs tests, checks that the tag matches `__version__`, checks that
`CHANGELOG.md` contains `## [1.6.0]`, builds the wheel and sdist, creates a
GitHub Release, and uploads to PyPI.

## Release candidates

Pre-releases use PEP 440 `rc` versions (`X.Y.Zrc1`) tagged `vX.Y.Zrc1`.
The process is identical to a normal release, with the full rc version
everywhere: `__version__ = "X.Y.Zrc1"`, a `## [X.Y.Zrc1]` changelog
section (CI greps for the exact version, suffix included), and tag
`vX.Y.Zrc1`.

- The publish workflow marks the GitHub Release as a pre-release when the
  tag contains `rc`.
- PyPI treats `rc` versions as pre-releases automatically: plain
  `pip install pysyringe` keeps resolving to the latest stable release;
  users opt in with `pip install --pre pysyringe` or
  `pysyringe==X.Y.Zrc1`.
- When promoting to final, move the rc changelog notes under `## [X.Y.Z]`
  (keeping the rc section is fine too) and release `X.Y.Z` normally.

## Before bumping

- Working tree is clean and on `master` up to date with `origin/master`.
- `CHANGELOG.md` has an `## [Unreleased]` section describing the changes —
  its contents become this release's notes once you move them under
  `## [X.Y.Z]`.
- The new tag doesn't already exist: `git tag --list vX.Y.Z` is empty.
- The version on PyPI for `X.Y.Z` doesn't already exist (PyPI refuses
  reused versions).

## Recovering from a bad release

- **Tag pushed, CI failed before publishing:** delete the tag and redo.
  ```bash
  git tag -d vX.Y.Z
  git push --delete origin vX.Y.Z
  ```
- **Tag pushed and published to PyPI:** that version is permanent on PyPI.
  Bump to the next patch and release again.
