#!/usr/bin/env python
import os
import sys
import coverage
from os.path import join

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
    parent_dir = os.path.join(TEST_DIR, "..", "..")
    sys.path.insert(0, parent_dir)
    cov = coverage.coverage(branch=True,
        include=[
            os.path.join(parent_dir, 'compressor', '*.py')
            ],
        omit=[
            join(parent_dir, 'compressor', 'tests', '*.py'),
            join(parent_dir, 'compressor', 'utils', 'stringformat.py'),
            join(parent_dir, 'compressor', 'filters', 'jsmin', 'rjsmin.py'),
            join(parent_dir, 'compressor', 'filters', 'cssmin', 'cssmin.py'),
        ])
    cov.load()
    cov.start()
    failures = run_tests(test_args, verbosity=1, interactive=True)
    cov.stop()
    cov.save()
    sys.exit(failures)


if __name__ == '__main__':
    runtests(*sys.argv[1:])
