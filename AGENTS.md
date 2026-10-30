# AGENTS.md

derpconf is a small Python library that loads configuration files for an
application. It was extracted from
[thumbor](https://github.com/thumbor/thumbor), which still builds all of its
settings on it. Applications register settings with `Config.define`, load
Python-syntax `.conf` files with `Config.load`, and can generate a commented
sample file from the registered defaults. The whole library lives in
`derpconf/config.py`.

## Dev environment setup

- **Prerequisites:** Python 3.11 to 3.15, the versions listed in the
  `pyproject.toml` classifiers and in the CI matrix, and
  [uv](https://docs.astral.sh/uv/). There are no runtime dependencies.
- Create `.venv` with the package in editable mode and the `dev` dependency
  group, at the versions in `uv.lock`:

  ```
  make setup
  ```

  Equivalent to: `uv sync`

- The Makefile targets go through `uv run`. Use `uv run ...` for commands
  you run directly, so they use the same environment as CI.

## Running tests

- Run the full suite:

  ```
  make test
  ```

  Equivalent to: `uv run pytest --cov=derpconf --cov-report=term-missing`

- Tests use pytest and live in `tests/test_config.py`; `testpaths` in
  `pyproject.toml` points pytest at `tests/`, and `pythonpath` makes the
  working tree win over any derpconf installed in the virtualenv. Coverage is
  reported but no threshold is enforced.
- Fixtures live in `tests/fixtures/`. `conf.d/` covers directory loading, and
  its `.bak` file checks that only `*.conf` files are executed.
- `Config` keeps defaults, groups, aliases and the environment variable flag
  and prefix in class attributes. The autouse `isolated_config` fixture gives
  each test fresh ones, so tests may call `Config.define`, `Config.alias` and
  `Config.allow_environment_variables()` freely. Set environment variables
  with `monkeypatch.setenv` so they are removed afterwards.
- The suite used to run on pyVows. Older branches and open pull requests that
  still touch `vows/config_vows.py` need their vows ported to
  `tests/test_config.py`: each `should_*` method becomes a test, its topic
  becomes the test body or a fixture, and each `expect(...)` becomes a plain
  `assert` or `pytest.raises`.
- Test another Python version by setting `UV_PYTHON`, which makes `uv sync`
  recreate `.venv` with that interpreter: `UV_PYTHON=3.12 make setup test`.
- CI (`.github/workflows/test.yml`) runs `uv sync --locked` and `make test` on
  Python 3.11, 3.12, 3.13, 3.14 and 3.15 on every push and when a pull
  request is opened or reopened. New commits pushed to a pull request from a
  fork do not re-run it.

## Code style

- flake8, isort and pylint use the same rules as libthumbor: `.flake8`,
  `[tool.isort]` in `pyproject.toml` (black profile, 88 columns) and
  `.pylintrc`, which only turns off the docstring checks. Run all three
  with:

  ```
  make lint
  ```

  `make flake8`, `make isort-check` and `make pylint` run one at a time.
  `.github/workflows/lint.yml` runs each as its own job on Python 3.11, with
  the same triggers as the test workflow.
- There is no formatter and `make isort-check` only checks. Keep
  single-quoted strings and write f-strings, except in `logging` calls,
  which take `%s` placeholders and the values as arguments.
- Non-empty modules start with the shebang, the `coding: utf-8` line and the
  MIT license header (`# derpconf`, repository URL, license link, copyright).
  Copy it into new modules.

## Project structure

```
derpconf/
  config.py              ← Config, ConfigurationError, verify_config,
                           generate_config and the sample-text formatters
  version.py             ← __version__, read by setuptools at build time
  __init__.py            ← empty
tests/
  test_config.py         ← pytest suite
  fixtures/              ← sample.conf, missing.conf, conf.d/
pyproject.toml           ← package metadata, the `dev` dependency group,
                           isort settings
uv.lock                  ← locked versions of the `dev` group
Makefile                 ← setup, test, lint
.flake8                  ← flake8 settings
.pylintrc                ← pylint settings
.github/workflows/       ← unittests matrix, lint jobs and PyPI release
```

## How loading works

- `Config.load(path, conf_name=None, lookup_paths=None, defaults=None)` loads
  `path`. When `path` is `None`, it uses the first entry of `lookup_paths`
  that contains `conf_name`; with neither, it returns a `Config` holding only
  defaults. A path that does not exist raises `ConfigurationError`.
- A file is executed with the built-in `exec` in a fresh module namespace.
  Every top-level name that equals its own uppercase becomes a setting;
  lowercase names are ignored.
- Files are read as UTF-8, whatever the locale.
- A directory loads every `*.conf` file in it in sorted order, later files
  overriding earlier ones. `config_file` ends up pointing at the last file,
  so `reload()` after a directory load re-executes only that file.
- Reading a setting checks, in order: the environment (only after
  `allow_environment_variables()`, with its `prefix` prepended to the
  name), values from the loaded files, the `defaults` passed to `load`, the
  default from `Config.define`, and finally raises `AttributeError`.
- `Config.alias(old_name, new_name)` makes `old_name` a deprecated alias:
  reading or setting it logs a warning and redirects to `new_name`. Aliases
  of aliases resolve to the final name.
- `get_config_text()` (printed by `generate_config()`) renders every group and
  setting, with its description, aliases and default, as a commented sample
  file.

## Contribution guidelines

- Keep changes focused and add or update a test whenever behavior changes.
- thumbor pins `derpconf>=0.8.4,<1.0.0` and calls `Config.define`,
  `Config.alias`, `Config.load`, `Config.allow_environment_variables`,
  `validates_presence_of` and `generate_config`. Treat their behavior as
  public API: a change to the lookup order, the uppercase filter or the sample
  text format changes thumbor too.
- Declare every dependency in `pyproject.toml` as a `>=X.Y.Z,<N.0.0` range,
  where `N` is the next major, the same style thumbor uses. derpconf is
  installed next to thumbor's own dependencies, so never pin an exact
  version. `uv.lock` pins the `dev` group for CI and local work only and is
  not shipped in the package. After changing a range, run `uv lock` and
  commit `uv.lock`: CI runs `uv sync --locked`, which fails on a stale lock.
  Dependabot's uv ecosystem keeps `uv.lock` current.
- `.github/workflows/release.yml` publishes releases. A maintainer bumps
  `__version__` in `derpconf/version.py` in a `Release X.Y.Z` commit, merges
  it into `master` and pushes an `X.Y.Z` tag, without a `v` prefix, at that
  commit. The workflow builds the sdist and wheel with `uv build`, fails when
  the tag does not match `__version__`, and uploads both to PyPI with trusted
  publishing. It also builds, without uploading, on every pull request to
  `master`. Do not bump the version in feature or fix changes.
- New work targets `master`.

## Security considerations

- Configuration files are Python code. `load`, `reload`, `verify` and
  `verify_config` execute them with the privileges of the process. Any change
  that widens which files get executed (new extensions, recursive directory
  walks, extra lookup paths) is a security change and needs a test.
- Once `allow_environment_variables()` is called, it and its `prefix` apply
  to every `Config` in the process. `__getattribute__` checks the
  environment for every attribute name except `_allow_environment_variables`
  and `_environment_variables_prefix`, including methods such as `get` and
  `reload` and internals such as `defaults`. The value it returns is cast to
  the type of the `Config.define` default (aliases resolved, keyed on the
  unprefixed name) through `ENVIRONMENT_PARSERS`; a `None`, `str` or other
  default, or no definition at all, keeps the raw string. A value that does
  not parse raises `ConfigurationError` naming the variable, never echoing
  the value, since it may be a secret.
- `verify_config` prints the default used for each missing key, and
  `generate_config` prints every default. Never put real secrets in
  `Config.define` defaults, fixtures or examples.
- Report vulnerabilities privately as described in
  [SECURITY.md](SECURITY.md), never in a public issue.
