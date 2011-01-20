#!/usr/bin/env python
import os
import sys

from django.conf import settings

TEST_DIR = os.path.dirname(os.path.abspath(__file__))

if not settings.configured:
    settings.configure(
        COMPRESS_CACHE_BACKEND = 'dummy://',
        DATABASE_ENGINE='sqlite3',
        INSTALLED_APPS=[
            'compressor',
            'compressor.tests',
        ],
        MEDIA_URL = '/media/',
        MEDIA_ROOT = os.path.join(TEST_DIR, 'media'),
        TEMPLATE_DIRS = (
            os.path.join(TEST_DIR, 'templates'),
        ),
        TEST_DIR = TEST_DIR,
    )

from django.test.simple import run_tests


def runtests(*test_args):
    if not test_args:
        test_args = ['tests']
    parent = os.path.join(TEST_DIR, "..", "..")
    sys.path.insert(0, parent)
    failures = run_tests(test_args, verbosity=1, interactive=True)
    sys.exit(failures)


if __name__ == '__main__':
    runtests(*sys.argv[1:])
