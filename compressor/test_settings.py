import os
import django

TEST_DIR = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'tests')

COMPRESS_CACHE_BACKEND = 'locmem://'

if django.VERSION[:2] >= (1, 3):
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': ':memory:',
        }
    }
else:
    DATABASE_ENGINE = 'sqlite3'

INSTALLED_APPS = [
    'compressor',
]

STATIC_URL = '/static/'


STATIC_ROOT = os.path.join(TEST_DIR, 'static')

TEMPLATE_DIRS = (
    # Specifically choose a name that will not be considered
    # by app_directories loader, to make sure each test uses
    # a specific template without considering the others.
    os.path.join(TEST_DIR, 'test_templates'),
)

TEST_RUNNER = 'discover_runner.DiscoverRunner'

SECRET_KEY = "iufoj=mibkpdz*%bob952x(%49rqgv8gg45k36kjcg76&-y5=!"
