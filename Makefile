testenv:
	pip install -e .
	pip install -r requirements/tests.txt
	pip install Django

test:
	flake8 compressor --ignore=E501,E128,E701,E261,E301,E126,E127,E131
	coverage run --branch --source=compressor `which django-admin.py` test --settings=compressor.test_settings compressor
	coverage report --omit=compressor/test*,compressor/filters/jsmin/rjsmin*,compressor/filters/cssmin/cssmin*,compressor/utils/stringformat*

.PHONY: test
