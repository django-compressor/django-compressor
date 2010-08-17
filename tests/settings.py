import sys
from os.path import dirname, abspath, join
TEST_DIR = dirname(abspath(__file__))

DEBUG = True

ROOT_URLCONF = 'urls'

MEDIA_URL = '/media/'
MEDIA_ROOT = join(TEST_DIR, 'media')

DATABASE_ENGINE = 'sqlite3'
DATABASE_NAME = 'django_compressor_tests.db'
 
INSTALLED_APPS = [
    'core',
    'compressor',
]
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
)

TEMPLATE_DIRS = (
    join(TEST_DIR, 'templates'),
)