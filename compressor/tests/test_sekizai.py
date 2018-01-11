# -*- coding: utf-8 -*-
from __future__ import with_statement, unicode_literals

from django.test import TestCase
from django.test.utils import override_settings

from compressor.conf import settings
from compressor.tests.test_base import css_tag


class TestSekizaiCompressorExtension(TestCase):
    """
    Test case for Sekizai extension. Pilvered from test_jinja2.
    WORK in PROGRESS
    """
    def assertStrippedEqual(self, result, expected):
        self.assertEqual(result.strip(), expected.strip(), "%r != %r" % (
            result.strip(), expected.strip()))
