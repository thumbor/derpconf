test:
	@pytest --cov=derpconf --cov-report=term-missing

tox:
	@PATH=$$PATH:~/.pythonbrew/pythons/Python-2.7.*/bin/:~/.pythonbrew/pythons/Python-3.0.*/bin/:~/.pythonbrew/pythons/Python-3.1.*/bin/:~/.pythonbrew/pythons/Python-3.2.3/bin/:~/.pythonbrew/pythons/Python-3.3.0/bin/ tox

setup:
	@pip install -Ue .\[tests,lint\]

flake flake8:
	@flake8 --config=.flake8 derpconf tests

isort isort-check:
	@isort --check-only --settings-file=pyproject.toml derpconf tests

pylint:
	@pylint derpconf tests

lint: flake8 isort-check pylint


