import os

TEST_DIR = os.path.dirname(os.path.abspath(__file__))

COMPRESS_CACHE_BACKEND = 'locmem://'

DATABASE_ENGINE = 'sqlite3'

INSTALLED_APPS = [
    'django.contrib.contenttypes',
    'django.contrib.sites',
    'django.contrib.auth',
    'django.contrib.admin',
    'compressor',
    'tests',
]

MEDIA_URL = '/media/'

MEDIA_ROOT = os.path.join(TEST_DIR, 'media')

TEMPLATE_DIRS = (
    os.path.join(TEST_DIR, 'templates'),
)
