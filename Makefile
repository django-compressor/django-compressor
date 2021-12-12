testenv:
	pip install -e .
	pip install -r requirements/tests.txt
	pip install Django

flake8:
	flake8 compressor --ignore=E501,E128,E701,E261,E301,E126,E127,E131,E402,W503

runtests:
	coverage run --branch --source=compressor `which django-admin` test --settings=compressor.test_settings compressor

coveragereport:
	coverage report --omit=compressor/test*

test: flake8 runtests coveragereport

.PHONY: test runtests flake8 coveragereport
