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
- A virtualenv

Create a virtualenv and install derpconf in editable mode with its test
dependencies:

```bash
python3 -m venv .venv
. .venv/bin/activate
make setup
```

`make setup` runs `pip install -Ue .[tests]`, which installs the `tests`
extra declared in `pyproject.toml`.

## Running Tests

Run the suite with:

```bash
make test
```

The tests are [pyVows](https://github.com/heynemann/pyvows) contexts in
`vows/config_vows.py`, with fixtures in `vows/fixtures/`. Read the
`Vows Results` line for the outcome. The coverage table below it marks files
under 90% with ✗, but that does not fail the run.

CI runs the suite on Python 3.11, 3.12, 3.13, 3.14 and 3.15. To try another
version locally, create a virtualenv with that interpreter and run
`make setup` and `make test` in it. Ignore `tox.ini` and `make tox`: they
still target Python 2 and CI does not use them.

## Code Style

No formatter or linter is configured. Match the code around your change:
`%` string formatting, single-quoted strings, and the license header at the
top of every new module.

thumbor depends on `derpconf>=0.8.4,<1.0.0`, so keep `Config.define`,
`Config.alias`, `Config.load`, `Config.allow_environment_variables`,
`validates_presence_of`, `generate_config` and `verify_config` backward
compatible.

## Pull Requests

Before opening a pull request:

- Rebase your branch on top of the latest `master`
- Add or update a vow whenever behavior changes
- Run `make test` locally
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

## Reporting Security Issues

Please do not open a public issue for a vulnerability. Report it privately as
described in [SECURITY.md](SECURITY.md).
