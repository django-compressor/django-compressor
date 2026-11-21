import os
import django
from django.conf import settings

# Set up Django settings if not already configured
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'compressor.test_settings')

def pytest_configure():
    # Configure Django if it's not already configured
    if not settings.configured:
        django.setup()
