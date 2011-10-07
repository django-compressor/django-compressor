from __future__ import with_statement
import os

from django.template import Template, Context
from django.test import TestCase

from compressor.conf import settings
from compressor.exceptions import OfflineGenerationError
from compressor.management.commands.compress import Command as CompressCommand
from compressor.storage import default_storage

from .base import test_dir, css_tag

class OfflineGenerationTestCase(TestCase):
    """Uses templates/test_compressor_offline.html"""
    maxDiff = None

    def setUp(self):
        self._old_compress = settings.COMPRESS_ENABLED
        self._old_compress_offline = settings.COMPRESS_OFFLINE
        settings.COMPRESS_ENABLED = True
        settings.COMPRESS_OFFLINE = True
        self.template_file = open(os.path.join(test_dir, "templates/test_compressor_offline.html"))
        self.template = Template(self.template_file.read().decode(settings.FILE_CHARSET))

    def tearDown(self):
        settings.COMPRESS_ENABLED = self._old_compress
        settings.COMPRESS_OFFLINE = self._old_compress_offline
        self.template_file.close()
        if default_storage.exists('CACHE/manifest.json'):
            default_storage.delete('CACHE/manifest.json')

    def test_rendering_without_compressing_raises_exception(self):
        self.assertRaises(OfflineGenerationError,
                          self.template.render, Context({}))

    def test_requires_model_validation(self):
        self.assertFalse(CompressCommand.requires_model_validation)

    def test_offline(self):
        count, result = CompressCommand().compress()
        self.assertEqual(5, count)
        self.assertEqual([
            css_tag('/media/CACHE/css/cd579b7deb7d.css'),
            u'<script type="text/javascript" src="/media/CACHE/js/0a2bb9a287c0.js"></script>',
            u'<script type="text/javascript" src="/media/CACHE/js/fb1736ad48b7.js"></script>',
            u'<script type="text/javascript" src="/media/CACHE/js/770a7311729e.js"></script>',
            u'<link rel="stylesheet" href="/media/CACHE/css/67ed6aff7f7b.css" type="text/css" />',
        ], result)
        # Template rendering should use the cache. FIXME: how to make sure of it ? Should we test the cache
        # key<->values ourselves?
        rendered_template = self.template.render(Context({})).replace("\n", "")
        self.assertEqual(rendered_template, "".join(result).replace("\n", ""))

    def test_offline_with_context(self):
        self._old_offline_context = settings.COMPRESS_OFFLINE_CONTEXT
        settings.COMPRESS_OFFLINE_CONTEXT = {
            'color': 'blue',
        }
        count, result = CompressCommand().compress()
        self.assertEqual(5, count)
        self.assertEqual([
            css_tag('/media/CACHE/css/ee62fbfd116a.css'),
            u'<script type="text/javascript" src="/media/CACHE/js/0a2bb9a287c0.js"></script>',
            u'<script type="text/javascript" src="/media/CACHE/js/fb1736ad48b7.js"></script>',
            u'<script type="text/javascript" src="/media/CACHE/js/770a7311729e.js"></script>',
            u'<link rel="stylesheet" href="/media/CACHE/css/73e015f740c6.css" type="text/css" />',
        ], result)
        # Template rendering should use the cache. FIXME: how to make sure of it ? Should we test the cache
        # key<->values ourselves?
        rendered_template = self.template.render(Context(settings.COMPRESS_OFFLINE_CONTEXT)).replace("\n", "")
        self.assertEqual(rendered_template, "".join(result).replace("\n", ""))
        settings.COMPRESS_OFFLINE_CONTEXT = self._old_offline_context

    def test_get_loaders(self):
        old_loaders = settings.TEMPLATE_LOADERS
        settings.TEMPLATE_LOADERS = (
            ('django.template.loaders.cached.Loader', (
                'django.template.loaders.filesystem.Loader',
                'django.template.loaders.app_directories.Loader',
            )),
        )
        try:
            from django.template.loaders.filesystem import Loader as FileSystemLoader
            from django.template.loaders.app_directories import Loader as AppDirectoriesLoader
        except ImportError:
            pass
        else:
            loaders = CompressCommand().get_loaders()
            self.assertTrue(isinstance(loaders[0], FileSystemLoader))
            self.assertTrue(isinstance(loaders[1], AppDirectoriesLoader))
        finally:
            settings.TEMPLATE_LOADERS = old_loaders
