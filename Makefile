test:
	@pytest --cov=derpconf --cov-report=term-missing

tox:
	@PATH=$$PATH:~/.pythonbrew/pythons/Python-2.7.*/bin/:~/.pythonbrew/pythons/Python-3.0.*/bin/:~/.pythonbrew/pythons/Python-3.1.*/bin/:~/.pythonbrew/pythons/Python-3.2.3/bin/:~/.pythonbrew/pythons/Python-3.3.0/bin/ tox

setup:
	@pip install -Ue .\[tests\]


