# Contributing to EVALSIG

Thanks for thinking about contributing. This page walks you through the
developer setup, the conventions we follow, and how to get a PR landed.

## Development setup

```bash
git clone https://github.com/vtensor/evalsig.git
cd evalsig
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev,docs]"
```

The `dev` extra pulls in the test runner; `docs` pulls in mkdocs +
material. If those extras are missing, install them manually:

```bash
pip install pytest mkdocs mkdocs-material
```

## Running the test suite

```bash
python -m unittest discover tests
```

You should see 45 tests pass. To run a single file:

```bash
python -m unittest tests.test_smoke
```

## Running the end-to-end validation

```bash
python research/validate.py
```

This is the script that proves the library does what the design doc
says. All four experiments must pass on every release.

## Building the docs locally

```bash
mkdocs serve
```

The docs site lives in `docs/` and is rendered by [Material for
MkDocs](https://squidfunk.github.io/mkdocs-material/). Pages are
plain Markdown; the navigation tree is configured in `mkdocs.yml`.

## Conventions

### Code

* **Pure functions in `inference/`.** No I/O, no globals, no defaults
  for the RNG.
* **Typed everywhere.** `from __future__ import annotations` at the top
  of every module. `mypy --strict` clean.
* **Modules are nouns.** New code goes into `inference/`, `io/`,
  `compare/`, or `store/`. Avoid `utils.py`, `helpers.py`, etc.
* **Comments are minimal and explain why.** The code already shows
  *what*. Avoid academic phrasing; we aim for plain English.

### Tests

* **One module = one test file.** New module `foo` -> `tests/test_foo.py`.
* **Each test pins one property.** A property test for coverage, a
  golden test against a reference implementation, a smoke test for the
  CLI.

### Commits

* Conventional Commits style headers: `feat: ...`, `fix: ...`,
  `docs: ...`, `test: ...`, `chore: ...`.
* Squash trivial fixups before opening the PR.

### Pull requests

* Run the full test suite plus `research/validate.py` before opening.
* Reference any issue you are closing in the description.
* Include screenshots or example output if the change affects the CLI.
* Update `docs/changelog.md` under the appropriate version heading.

## Release process

For maintainers:

```bash
# 1. Bump version in src/evalsig/_version.py and docs/changelog.md.
# 2. Re-run the full test suite + research/validate.py.
# 3. Tag and push:
git tag v0.1.1
git push --tags
# 4. GitHub Actions builds wheels, signs with Sigstore, and uploads to PyPI.
```

## Reporting bugs

Open an issue with:

1. EVALSIG version (`evalsig --version`).
2. Python version (`python --version`).
3. OS.
4. Minimal reproducer (a small RunFrame JSON pair is ideal).
5. Expected vs actual behaviour.

## Asking for help

* Documentation site: <https://evalsig.dev>
* GitHub Discussions: <https://github.com/vtensor/evalsig/discussions>
* Email: `hello@evalsig.dev`

## Code of Conduct

By participating, you agree to abide by the [Code of Conduct](CODE_OF_CONDUCT.md).
