from __future__ import with_statement
import errno
import os

from django.core.files.base import ContentFile
from django.core.files.storage import get_storage_class
from django.test import TestCase

from compressor import base
from compressor.conf import settings
from compressor.tests.test_base import css_tag
from compressor.tests.test_templatetags import render


class StorageTestCase(TestCase):
    def setUp(self):
        self._storage = base.default_storage
        base.default_storage = get_storage_class(
            'compressor.storage.GzipCompressorFileStorage')()
        settings.COMPRESS_ENABLED = True

    def tearDown(self):
        base.default_storage = self._storage

    def test_css_tag_with_storage(self):
        template = u"""{% load compress %}{% compress css %}
        <link rel="stylesheet" href="{{ STATIC_URL }}css/one.css" type="text/css">
        <style type="text/css">p { border:5px solid white;}</style>
        <link rel="stylesheet" href="{{ STATIC_URL }}css/two.css" type="text/css">
        {% endcompress %}
        """
        context = {'STATIC_URL': settings.COMPRESS_URL}
        out = css_tag("/static/CACHE/css/1d4424458f88.css")
        self.assertEqual(out, render(template, context))

    def test_race_condition_handling(self):
        # Hold on to original os.remove
        original_remove = os.remove

        def race_remove(path):
            "Patched os.remove to raise ENOENT (No such file or directory)"
            original_remove(path)
            raise OSError(errno.ENOENT, u'Fake ENOENT')

        try:
            os.remove = race_remove
            self._storage.save('race.file', ContentFile('Fake ENOENT'))
            self._storage.delete('race.file')
            self.assertFalse(self._storage.exists('race.file'))
        finally:
            # Restore os.remove
            os.remove = original_remove
