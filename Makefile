test:
	@uv run pytest --cov=derpconf --cov-report=term-missing

setup:
	@uv sync
	@echo "\n\nYou are strongly recommended to run 'make pre-commit-install'\n"

black:
	@uv run black --check --config=pyproject.toml derpconf tests

flake flake8:
	@uv run flake8 --config=.flake8 derpconf tests

isort isort-check:
	@uv run isort --check-only --settings-file=pyproject.toml derpconf tests

pylint:
	@uv run pylint derpconf tests

pre-commit-install:
	@uv run pre-commit install

pre-commit:
	@uv run pre-commit run --all-files

lint: black flake8 isort-check pylint
