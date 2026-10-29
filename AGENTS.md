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
  `pyproject.toml` classifiers and in the CI matrix. `six` is the only runtime
  dependency.
- Install the package in editable mode with the test extras, inside a
  virtualenv:

  ```
  make setup
  ```

  Equivalent to: `pip install -Ue .[tests]`

- CI installs `librtmp-dev` and `libevent-dev` with apt before running
  `make setup`.

## Running tests

- Run the full suite:

  ```
  make test
  ```

  Equivalent to:

  ```
  PYTHONPATH=. pyvows -v --profile --cover --cover-package=derpconf \
      --cover-threshold=90 vows/
  ```

- Tests use [pyVows](https://github.com/heynemann/pyvows) (`Vows.batch`,
  `topic`, `expect`), not pytest. Read the `Vows Results` line for the
  outcome. The coverage report marks files below 90% with ✗, but the
  threshold does not fail the run: `config.py` is below it today and
  `make test` still exits 0.
- Fixtures live in `vows/fixtures/`. `conf.d/` covers directory loading, and
  its `.bak` file checks that only `*.conf` files are executed.
- `Config` keeps defaults, groups, aliases and the environment variable flag
  in class attributes, so that state is shared by every vow. A new vow that
  calls `Config.define`, `Config.allow_environment_variables()` or sets an
  environment variable should restore what it changed.
- `tox.ini` (py27, py32, py33, pypy) and `make tox` (pythonbrew paths) are
  leftovers from the Python 2 era and CI does not use them. Test each Python
  version with `make setup` and `make test` in its own virtualenv.
- CI (`.github/workflows/test.yml`) runs `make setup` and `make test` on
  Python 3.11, 3.12, 3.13, 3.14 and 3.15 on every push and when a pull
  request is opened or reopened. New commits pushed to a pull request from a
  fork do not re-run it.

## Code style

- No formatter, linter or type checker is configured. Match the existing
  code: `%` string formatting, `six` for Python 2/3 compatibility, classes
  that derive from `object`, and single-quoted strings.
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
vows/
  config_vows.py         ← pyVows suite
  fixtures/              ← sample.conf, missing.conf, conf.d/
pyproject.toml           ← package metadata and the `tests` extra
Makefile                 ← setup, test (and the stale tox target)
tox.ini                  ← stale Python 2 era envlist
.github/workflows/       ← unittests matrix
```

## How loading works

- `Config.load(path, conf_name=None, lookup_paths=[], defaults={})` loads
  `path`. When `path` is `None`, it uses the first entry of `lookup_paths`
  that contains `conf_name`; with neither, it returns a `Config` holding only
  defaults. A path that does not exist raises `ConfigurationError`.
- A file is executed with `six.exec_` in a fresh module namespace. Every
  top-level name that equals its own uppercase becomes a setting; lowercase
  names are ignored.
- A directory loads every `*.conf` file in it in sorted order, later files
  overriding earlier ones. `config_file` ends up pointing at the last file,
  so `reload()` after a directory load re-executes only that file.
- Reading a setting checks, in order: the environment (only after
  `allow_environment_variables()`), values from the loaded files, the
  `defaults` passed to `load`, the default from `Config.define`, and finally
  raises `AttributeError`.
- `Config.alias(old_name, new_name)` makes `old_name` a deprecated alias:
  reading or setting it logs a warning and redirects to `new_name`. Aliases
  of aliases resolve to the final name.
- `get_config_text()` (printed by `generate_config()`) renders every group and
  setting, with its description, aliases and default, as a commented sample
  file.

## Contribution guidelines

- Keep changes focused and add or update a vow whenever behavior changes.
- thumbor pins `derpconf>=0.8.4,<1.0.0` and calls `Config.define`,
  `Config.alias`, `Config.load`, `Config.allow_environment_variables`,
  `validates_presence_of` and `generate_config`. Treat their behavior as
  public API: a change to the lookup order, the uppercase filter or the sample
  text format changes thumbor too.
- There is no release workflow. A maintainer bumps `__version__` in
  `derpconf/version.py` in a `Release X.Y.Z` commit and publishes to PyPI. Do
  not bump the version in feature or fix changes.
- New work targets `master`.

## Security considerations

- Configuration files are Python code. `load`, `reload`, `verify` and
  `verify_config` execute them with the privileges of the process. Any change
  that widens which files get executed (new extensions, recursive directory
  walks, extra lookup paths) is a security change and needs a vow.
- Once `allow_environment_variables()` is called, it applies to every
  `Config` in the process. `__getattribute__` checks the environment for
  every attribute name except `_allow_environment_variables`, including
  methods such as `get` and `reload` and internals such as `defaults`, and
  the values it returns are always strings.
- `verify_config` prints the default used for each missing key, and
  `generate_config` prints every default. Never put real secrets in
  `Config.define` defaults, fixtures or examples.
- Report vulnerabilities privately as described in
  [SECURITY.md](SECURITY.md), never in a public issue.
