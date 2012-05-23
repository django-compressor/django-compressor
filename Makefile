test:
	coverage run --branch --source=compressor `which django-admin.py` test --settings=compressor.test_settings compressor
	coverage report --omit=compressor/test*
