# Contributing

Want to contribute to derpconf? Welcome aboard.

This guide covers setting up your environment, running the tests, and
preparing a pull request. For a tour of the code and of how a setting is
resolved, see [AGENTS.md](AGENTS.md).

## Getting Started

Fork the repository and clone your fork locally. If you need a refresher on
that workflow, GitHub's fork documentation is a good place to start:
<https://docs.github.com/en/pull-requests/how-tos/work-with-forks/fork-a-repo>.

## Dependencies

- Python 3.11 to 3.15
- [uv](https://docs.astral.sh/uv/)

Install derpconf in editable mode with its test and lint dependencies:

```bash
make setup
```

`make setup` runs `uv sync`, which creates `.venv` and installs the `dev`
dependency group declared in `pyproject.toml` at the versions pinned in
`uv.lock`. The other Makefile targets run their tools through `uv run`, so
there is no virtualenv to activate.

## Running Tests

Run the suite with:

```bash
make test
```

The tests use [pytest](https://docs.pytest.org/) and live in
`tests/test_config.py`, with fixtures in `tests/fixtures/`. An autouse fixture
gives every test fresh `Config` class attributes, so set environment
variables with `monkeypatch.setenv` and let pytest clean them up. Coverage is
reported after the run, without a threshold.

The suite used to run on pyVows, and the `vows/` directory is gone. If your
branch still adds or changes vows in `vows/config_vows.py`, port them to
`tests/test_config.py` when you rebase: each `should_*` method becomes a
`test_*` function, its topic becomes the test body or a fixture, and each
`expect(...)` becomes a plain `assert` or `pytest.raises`.

CI runs the suite on Python 3.11, 3.12, 3.13, 3.14 and 3.15. To try another
version locally, set `UV_PYTHON`, and `uv sync` recreates `.venv` with that
interpreter:

```bash
UV_PYTHON=3.12 make setup test
```

## Code Style

CI runs flake8, isort and pylint. Run them locally before pushing:

```bash
make lint
```

There is no formatter, so match the code around your change: f-strings
(except in `logging` calls, which take `%s` placeholders and the values as
arguments), single-quoted strings, and the license header at the top of
every new module.

thumbor depends on `derpconf>=0.8.4,<1.0.0`, so keep `Config.define`,
`Config.alias`, `Config.load`, `Config.allow_environment_variables`,
`validates_presence_of`, `generate_config` and `verify_config` backward
compatible.

## Pull Requests

Before opening a pull request:

- Rebase your branch on top of the latest `master`
- Add or update a test in `tests/test_config.py` whenever behavior changes
- Run `make test` and `make lint` locally
- Update `README.md` when you change public behavior
- Keep the change focused, and leave `derpconf/version.py` alone; the version
  is bumped when a release is cut

If you want to track the upstream repository as an extra remote:

```bash
git remote add derpconf https://github.com/thumbor/derpconf.git
```

To update your branch with upstream `master`:

```bash
git fetch derpconf
git rebase derpconf/master
```

If the rebase brings in changes, run the test suite again before opening your
pull request.

## Releasing

Releases are published to PyPI by the `release` GitHub Actions workflow when a
tag that matches the package version is pushed. To cut a release:

1. Bump `__version__` in `derpconf/version.py` in a `Release X.Y.Z` commit and
   merge it into `master`.
2. Tag the merged commit with the same version, without a `v` prefix, and
   push the tag to `thumbor/derpconf`, not to your fork. With the `derpconf`
   remote above and the release commit at the tip of `master`:

   ```bash
   git fetch derpconf
   git tag 0.8.5 derpconf/master
   git push derpconf 0.8.5
   ```

The workflow builds the sdist and wheel, fails if the tag does not match
`__version__`, and uploads the artifacts to PyPI through the `pypi`
environment using trusted publishing, which also uploads attestations, so no
API token is needed.

Publishing depends on settings outside the repository. On PyPI, the project
needs a trusted publisher for the `thumbor/derpconf` repository, workflow
`release.yml` and environment `pypi`. In the repository settings, the `pypi`
environment should require reviewers and allow deployments only from tags
that match the release pattern, and a tag ruleset should limit who can create
those tags. Without that, anyone with write access can publish a release by
pushing a tag at any commit.

## Reporting Security Issues

Please do not open a public issue for a vulnerability. Report it privately as
described in [SECURITY.md](SECURITY.md).
