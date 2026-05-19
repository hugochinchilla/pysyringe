# Release process

Releases are published to PyPI by `.github/workflows/publish.yml` when a
`vN.N` or `vN.N.N` tag is pushed. The version lives in
`pysyringe/__init__.py` and is read by hatchling at build time, so the
committed file must match the tag — CI verifies this and fails the publish
if it doesn't.

## Steps

Pick the target version `X.Y.Z` (no `v` prefix here — the prefix is only
on the git tag).

```bash
# 1. Bump __version__ in pysyringe/__init__.py
uvx hatch version X.Y.Z

# 2. Sanity-check
uvx hatch version           # prints X.Y.Z
uv run pytest               # tests still pass
git diff pysyringe/__init__.py   # only __version__ changed

# 3. Commit, tag, push
git commit -am "prepare release X.Y.Z"
git tag vX.Y.Z
git push && git push --tags
```

`hatch version` also accepts `major` / `minor` / `patch` for segment bumps,
e.g. `uvx hatch version minor` takes `1.5.2` to `1.6.0`.

## Example: 1.5.2 → 1.6.0

```bash
$ uvx hatch version minor
Old: 1.5.2
New: 1.6.0

$ git commit -am "prepare release 1.6.0"
[master 1a2b3c4] prepare release 1.6.0
 1 file changed, 1 insertion(+), 1 deletion(-)

$ git tag v1.6.0

$ git push && git push --tags
```

CI then runs tests, verifies the tag matches `__version__`, updates
`CHANGELOG.md` (rewriting `## [Unreleased]` to `## [1.6.0] — <date>`),
builds the wheel and sdist, creates a GitHub Release, and uploads to PyPI.

## Before bumping

- Working tree is clean and on `master` up to date with `origin/master`.
- `CHANGELOG.md` has an `## [Unreleased]` section describing the changes —
  its contents become the release notes after CI rewrites the heading.
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
