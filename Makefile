testenv:
	pip install -e .
	pip install -r requirements/tests.txt
	pip install Django

flake8:
	flake8 compressor --ignore=E203,E501,W503

runtests:
	coverage run --branch --source=compressor `which django-admin` test --settings=compressor.test_settings compressor

coveragereport:
	coverage report --omit=compressor/test*

test: flake8 runtests coveragereport

.PHONY: test runtests flake8 coveragereport
