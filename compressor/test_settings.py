import os

TEST_DIR = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'tests')


CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'unique-snowflake'
    }
}

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}

INSTALLED_APPS = [
    'django.contrib.staticfiles',
    'compressor',
    'sekizai',
]

STATICFILES_FINDERS = [
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
    'compressor.finders.CompressorFinder',
]

STATIC_URL = '/static/'


STATIC_ROOT = os.path.join(TEST_DIR, 'static')

TEMPLATES = [{
    'BACKEND': 'django.template.backends.django.DjangoTemplates',
    'APP_DIRS': True,
    'DIRS': [
        # Specifically choose a name that will not be considered
        # by app_directories loader, to make sure each test uses
        # a specific template without considering the others.
        os.path.join(TEST_DIR, 'test_templates'),
    ],
}, {
    'BACKEND': 'django.template.backends.jinja2.Jinja2',
    'APP_DIRS': True,
    'DIRS': [
        # Specifically choose a name that will not be considered
        # by app_directories loader, to make sure each test uses
        # a specific template without considering the others.
        os.path.join(TEST_DIR, 'test_templates_jinja2'),
    ],
}]

SECRET_KEY = "iufoj=mibkpdz*%bob952x(%49rqgv8gg45k36kjcg76&-y5=!"

PASSWORD_HASHERS = (
    'django.contrib.auth.hashers.UnsaltedMD5PasswordHasher',
)

MIDDLEWARE_CLASSES = []
