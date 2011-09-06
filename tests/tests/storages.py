from __future__ import with_statement

from django.core.files.storage import get_storage_class
from django.test import TestCase

from compressor import base
from compressor.conf import settings

from .base import css_tag
from .templatetags import render


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
        <link rel="stylesheet" href="{{ MEDIA_URL }}css/one.css" type="text/css">
        <style type="text/css">p { border:5px solid white;}</style>
        <link rel="stylesheet" href="{{ MEDIA_URL }}css/two.css" type="text/css">
        {% endcompress %}
        """
        context = {'MEDIA_URL': settings.COMPRESS_URL}
        out = css_tag("/media/CACHE/css/1d4424458f88.css")
        self.assertEqual(out, render(template, context))

