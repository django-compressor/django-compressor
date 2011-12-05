import os

TEST_DIR = os.path.dirname(os.path.abspath(__file__))

COMPRESS_CACHE_BACKEND = 'locmem://'

DATABASE_ENGINE = 'sqlite3'

INSTALLED_APPS = [
    'django.contrib.contenttypes',
    'django.contrib.sites',
    'django.contrib.auth',
    'django.contrib.admin',
    'django_jenkins',
    'compressor',
    'tests',
]

MEDIA_URL = '/media/'

MEDIA_ROOT = os.path.join(TEST_DIR, 'media')

TEMPLATE_DIRS = (
    # Specifically choose a name that will not be considered
    # by app_directories loader, to make sure each test uses
    # a specific template without considering the others.
    os.path.join(TEST_DIR, 'test_templates'),
)

JENKINS_TASKS = (
    'django_jenkins.tasks.run_pyflakes',
    'django_jenkins.tasks.run_pep8',
    'django_jenkins.tasks.with_coverage',
    'django_jenkins.tasks.django_tests',
)
