test:
	flake8 compressor --ignore=E501,E128
	coverage run --branch --source=compressor `which django-admin.py` test --settings=compressor.test_settings compressor
	coverage report --omit=compressor/test*,compressor/filters/jsmin/rjsmin*,compressor/filters/cssmin/cssmin*,compressor/utils/stringformat*
