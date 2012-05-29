from __future__ import with_statement
import os
from StringIO import StringIO
from unittest2 import skipIf

import django
from django.template import Template, Context
from django.test import TestCase
from django.core.management.base import CommandError

from compressor.cache import flush_offline_manifest, get_offline_manifest
from compressor.conf import settings
from compressor.exceptions import OfflineGenerationError
from compressor.management.commands.compress import Command as CompressCommand
from compressor.storage import default_storage


class OfflineTestCaseMixin(object):
    template_name = "test_compressor_offline.html"
    verbosity = 0
    # Change this for each test class
    templates_dir = ""
    expected_hash = ""

    def setUp(self):
        self._old_compress = settings.COMPRESS_ENABLED
        self._old_compress_offline = settings.COMPRESS_OFFLINE
        self._old_template_dirs = settings.TEMPLATE_DIRS
        self._old_offline_context = settings.COMPRESS_OFFLINE_CONTEXT
        self.log = StringIO()

        # Reset template dirs, because it enables us to force compress to
        # consider only a specific directory (helps us make true,
        # independant unit tests).
        settings.TEMPLATE_DIRS = (
            os.path.join(settings.TEST_DIR, 'test_templates', self.templates_dir),
        )
        # Enable offline compress
        settings.COMPRESS_ENABLED = True
        settings.COMPRESS_OFFLINE = True
        self.template_path = os.path.join(settings.TEMPLATE_DIRS[0], self.template_name)
        self.template_file = open(self.template_path)
        self.template = Template(self.template_file.read().decode(settings.FILE_CHARSET))

    def tearDown(self):
        settings.COMPRESS_ENABLED = self._old_compress
        settings.COMPRESS_OFFLINE = self._old_compress_offline
        settings.TEMPLATE_DIRS = self._old_template_dirs
        self.template_file.close()
        manifest_path = os.path.join('CACHE', 'manifest.json')
        if default_storage.exists(manifest_path):
            default_storage.delete(manifest_path)

    def test_offline(self):
        count, result = CompressCommand().compress(log=self.log, verbosity=self.verbosity)
        self.assertEqual(1, count)
        self.assertEqual([
            u'<script type="text/javascript" src="/media/CACHE/js/%s.js"></script>' % (self.expected_hash, ),
        ], result)
        rendered_template = self.template.render(Context(settings.COMPRESS_OFFLINE_CONTEXT))
        self.assertEqual(rendered_template, "".join(result) + "\n")


class OfflineGenerationBlockSuperTestCase(OfflineTestCaseMixin, TestCase):
    templates_dir = "test_block_super"
    expected_hash = "7c02d201f69d"


class OfflineGenerationBlockSuperMultipleTestCase(OfflineTestCaseMixin, TestCase):
    templates_dir = "test_block_super_multiple"
    expected_hash = "2f6ef61c488e"


class OfflineGenerationBlockSuperMultipleWithCachedLoaderTestCase(OfflineTestCaseMixin, TestCase):
    templates_dir = "test_block_super_multiple_cached"
    expected_hash = "2f6ef61c488e"

    def setUp(self):
        self._old_template_loaders = settings.TEMPLATE_LOADERS
        settings.TEMPLATE_LOADERS = (
            ('django.template.loaders.cached.Loader', (
                'django.template.loaders.filesystem.Loader',
                'django.template.loaders.app_directories.Loader',
            )),
        )
        super(OfflineGenerationBlockSuperMultipleWithCachedLoaderTestCase, self).setUp()

    def tearDown(self):
        super(OfflineGenerationBlockSuperMultipleWithCachedLoaderTestCase, self).tearDown()
        settings.TEMPLATE_LOADERS = self._old_template_loaders


class OfflineGenerationBlockSuperTestCaseWithExtraContent(OfflineTestCaseMixin, TestCase):
    templates_dir = "test_block_super_extra"

    def test_offline(self):
        count, result = CompressCommand().compress(log=self.log, verbosity=self.verbosity)
        self.assertEqual(2, count)
        self.assertEqual([
            u'<script type="text/javascript" src="/media/CACHE/js/ced14aec5856.js"></script>',
            u'<script type="text/javascript" src="/media/CACHE/js/7c02d201f69d.js"></script>'
        ], result)
        rendered_template = self.template.render(Context(settings.COMPRESS_OFFLINE_CONTEXT))
        self.assertEqual(rendered_template, "".join(result) + "\n")


class OfflineGenerationConditionTestCase(OfflineTestCaseMixin, TestCase):
    templates_dir = "test_condition"
    expected_hash = "4e3758d50224"

    def setUp(self):
        self.old_offline_context = settings.COMPRESS_OFFLINE_CONTEXT
        settings.COMPRESS_OFFLINE_CONTEXT = {
            'condition': 'red',
        }
        super(OfflineGenerationConditionTestCase, self).setUp()

    def tearDown(self):
        self.COMPRESS_OFFLINE_CONTEXT = self.old_offline_context
        super(OfflineGenerationConditionTestCase, self).tearDown()


class OfflineGenerationTemplateTagTestCase(OfflineTestCaseMixin, TestCase):
    templates_dir = "test_templatetag"
    expected_hash = "a27e1d3a619a"


class OfflineGenerationStaticTemplateTagTestCase(OfflineTestCaseMixin, TestCase):
    templates_dir = "test_static_templatetag"
    expected_hash = "dfa2bb387fa8"
# This test uses {% static %} which was introduced in django 1.4
OfflineGenerationStaticTemplateTagTestCase = skipIf(
    django.VERSION[1] < 4, 'Django 1.4 not found'
)(OfflineGenerationStaticTemplateTagTestCase)


class OfflineGenerationTestCaseWithContext(OfflineTestCaseMixin, TestCase):
    templates_dir = "test_with_context"
    expected_hash = "5838e2fd66af"

    def setUp(self):
        self.old_offline_context = settings.COMPRESS_OFFLINE_CONTEXT
        settings.COMPRESS_OFFLINE_CONTEXT = {
            'content': 'OK!',
        }
        super(OfflineGenerationTestCaseWithContext, self).setUp()

    def tearDown(self):
        settings.COMPRESS_OFFLINE_CONTEXT = self.old_offline_context
        super(OfflineGenerationTestCaseWithContext, self).tearDown()


class OfflineGenerationTestCaseErrors(OfflineTestCaseMixin, TestCase):
    templates_dir = "test_error_handling"

    def test_offline(self):
        count, result = CompressCommand().compress(log=self.log, verbosity=self.verbosity)
        self.assertEqual(2, count)
        self.assertIn(u'<script type="text/javascript" src="/media/CACHE/js/3872c9ae3f42.js"></script>', result)
        self.assertIn(u'<script type="text/javascript" src="/media/CACHE/js/cd8870829421.js"></script>', result)


class OfflineGenerationTestCaseWithError(OfflineTestCaseMixin, TestCase):
    templates_dir = 'test_error_handling'

    def setUp(self):
        self._old_compress_precompilers = settings.COMPRESS_PRECOMPILERS
        settings.COMPRESS_PRECOMPILERS = (('text/coffeescript', 'non-existing-binary'),)
        super(OfflineGenerationTestCaseWithError, self).setUp()

    def test_offline(self):
        """
        Test that a CommandError is raised with DEBUG being False as well as
        True, as otherwise errors in configuration will never show in
        production.
        """
        self._old_debug = settings.DEBUG

        try:
            settings.DEBUG = True
            self.assertRaises(CommandError, CompressCommand().compress)

            settings.DEBUG = False
            self.assertRaises(CommandError, CompressCommand().compress)

        finally:
            settings.DEBUG = self._old_debug

    def tearDown(self):
        settings.COMPRESS_PRECOMPILERS = self._old_compress_precompilers
        super(OfflineGenerationTestCaseWithError, self).tearDown()


class OfflineGenerationTestCase(OfflineTestCaseMixin, TestCase):
    templates_dir = "basic"
    expected_hash = "f5e179b8eca4"

    def test_rendering_without_manifest_raises_exception(self):
        # flush cached manifest
        flush_offline_manifest()
        self.assertRaises(OfflineGenerationError,
                          self.template.render, Context({}))

    def test_deleting_manifest_does_not_affect_rendering(self):
        count, result = CompressCommand().compress(log=self.log, verbosity=self.verbosity)
        get_offline_manifest()
        manifest_path = os.path.join('CACHE', 'manifest.json')
        if default_storage.exists(manifest_path):
            default_storage.delete(manifest_path)
        self.assertEqual(1, count)
        self.assertEqual([
            u'<script type="text/javascript" src="/media/CACHE/js/%s.js"></script>' % (self.expected_hash, ),
        ], result)
        rendered_template = self.template.render(Context(settings.COMPRESS_OFFLINE_CONTEXT))
        self.assertEqual(rendered_template, "".join(result) + "\n")

    def test_requires_model_validation(self):
        self.assertFalse(CompressCommand.requires_model_validation)

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
