import os
import brotli

from django.core.files.base import ContentFile
from django.core.files.storage import get_storage_class
from django.test import TestCase
from django.test.utils import override_settings
from django.utils.functional import LazyObject

from compressor import storage
from compressor.conf import settings
from compressor.tests.test_base import css_tag
from compressor.tests.test_templatetags import render


class GzipStorage(LazyObject):
    def _setup(self):
        self._wrapped = get_storage_class('compressor.storage.GzipCompressorFileStorage')()


class BrotliStorage(LazyObject):
    def _setup(self):
        self._wrapped = get_storage_class('compressor.storage.BrotliCompressorFileStorage')()


@override_settings(COMPRESS_ENABLED=True)
class StorageTestCase(TestCase):
    def setUp(self):
        self.default_storage = storage.default_storage
        storage.default_storage = GzipStorage()
        storage.brotli_storage = BrotliStorage()

    def tearDown(self):
        storage.default_storage = self.default_storage

    def test_gzip_storage(self):
        storage.default_storage.save('test.txt', ContentFile('yeah yeah'))
        self.assertTrue(os.path.exists(os.path.join(settings.COMPRESS_ROOT, 'test.txt')))
        self.assertTrue(os.path.exists(os.path.join(settings.COMPRESS_ROOT, 'test.txt.gz')))

    def test_brotli_storage(self):
        payload = ','.join([str(i) for i in range(1000)]).encode()
        chunk_size = 1024
        storage.brotli_storage.save('test.txt', ContentFile(payload))
        self.assertTrue(os.path.exists(os.path.join(settings.COMPRESS_ROOT, 'test.txt')))
        self.assertTrue(os.path.exists(os.path.join(settings.COMPRESS_ROOT, 'test.txt.br')))
        decompressed_data = b''
        br_decompressor = brotli.Decompressor()
        with open(os.path.join(settings.COMPRESS_ROOT, 'test.txt.br'), 'rb') as f:
            for data in iter(lambda: f.read(chunk_size), b''):
                decompressed_data += br_decompressor.process(data)
        self.assertEqual(payload, decompressed_data)

    def test_css_tag_with_storage(self):
        template = """{% load compress %}{% compress css %}
        <link rel="stylesheet" href="{{ STATIC_URL }}css/one.css" type="text/css">
        <style type="text/css">p { border:5px solid white;}</style>
        <link rel="stylesheet" href="{{ STATIC_URL }}css/two.css" type="text/css">
        {% endcompress %}
        """
        context = {'STATIC_URL': settings.COMPRESS_URL}
        out = css_tag("/static/CACHE/css/output.e701f86c6430.css")
        self.assertEqual(out, render(template, context))

    def test_duplicate_save_overwrites_same_file(self):
        filename1 = self.default_storage.save('test.txt', ContentFile('yeah yeah'))
        filename2 = self.default_storage.save('test.txt', ContentFile('yeah yeah'))
        self.assertEqual(filename1, filename2)
        self.assertNotIn("_", filename2)

    def test_offline_manifest_storage(self):
        storage.default_offline_manifest_storage.save('test.txt', ContentFile('yeah yeah'))
        self.assertTrue(os.path.exists(os.path.join(settings.COMPRESS_ROOT, 'CACHE', 'test.txt')))
        # Check that the file is stored at the same default location as before the new manifest storage.
        self.assertTrue(self.default_storage.exists(os.path.join('CACHE', 'test.txt')))
