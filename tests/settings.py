import sys
from os.path import dirname, abspath, join
TEST_DIR = [dirname(abspath(__file__))]

ROOT_URLCONF = 'urls'

DATABASE_ENGINE = 'sqlite3'
DATABASE_NAME = 'django_inlines_tests.db'
 
INSTALLED_APPS = [
    'core',
    'django-compress',
]
TEMPLATE_LOADERS = (
    'django.template.loaders.app_directories.load_template_source',
)

TEMPLATE_DIRS = (
    join (TEST_DIR, 'templates'),
)