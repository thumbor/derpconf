test:
	@uv run pytest --cov=derpconf --cov-report=term-missing

setup:
	@uv sync

flake flake8:
	@uv run flake8 --config=.flake8 derpconf tests

isort isort-check:
	@uv run isort --check-only --settings-file=pyproject.toml derpconf tests

pylint:
	@uv run pylint derpconf tests

lint: flake8 isort-check pylint


