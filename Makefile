test:
	@pytest --cov=derpconf --cov-report=term-missing

setup:
	@pip install -Ue .\[tests,lint\]

flake flake8:
	@flake8 --config=.flake8 derpconf tests

isort isort-check:
	@isort --check-only --settings-file=pyproject.toml derpconf tests

pylint:
	@pylint derpconf tests

lint: flake8 isort-check pylint


