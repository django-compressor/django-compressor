from __future__ import with_statement, unicode_literals
import copy
import io
import os
import sys
import unittest
from importlib import import_module

from mock import patch
from unittest import SkipTest

from django.core.management.base import CommandError
from django.template import Template, Context
from django.test import TestCase
from django.utils import six

from compressor.cache import flush_offline_manifest, get_offline_manifest
from compressor.conf import settings
from compressor.exceptions import OfflineGenerationError
from compressor.management.commands.compress import Command as CompressCommand
from compressor.storage import default_storage
from compressor.utils import get_mod_func

if six.PY3:
    # there is an 'io' module in python 2.6+, but io.StringIO does not
    # accept regular strings, just unicode objects
    from io import StringIO
else:
    try:
        from cStringIO import StringIO
    except ImportError:
        from StringIO import StringIO

# The Jinja2 tests fail on Python 3.2 due to the following:
# The line in compressor/management/commands/compress.py:
#     compressor_nodes.setdefault(template, []).extend(nodes)
# causes the error 'unhashable type: 'Template''
_TEST_JINJA2 = not(sys.version_info[0] == 3 and sys.version_info[1] == 2)


def offline_context_generator():
    for i in range(1, 4):
        yield {'content': 'OK %d!' % i}


class OfflineTestCaseMixin(object):
    template_name = 'test_compressor_offline.html'
    verbosity = 0
    # Change this for each test class
    templates_dir = ''
    expected_hash = ''
    # Engines to test
    if _TEST_JINJA2:
        engines = ('django', 'jinja2')
    else:
        engines = ('django',)
    additional_test_settings = None

    def setUp(self):
        self.log = StringIO()

        # Reset template dirs, because it enables us to force compress to
        # consider only a specific directory (helps us make true,
        # independent unit tests).
        # Specify both Jinja2 and Django template locations. When the wrong
        # engine is used to parse a template, the TemplateSyntaxError will
        # cause the template to be skipped over.
        # We've hardcoded TEMPLATES[0] to be Django templates backend and
        # TEMPLATES[1] to be Jinja2 templates backend in test_settings.
        TEMPLATES = copy.deepcopy(settings.TEMPLATES)

        django_template_dir = os.path.join(
            TEMPLATES[0]['DIRS'][0], self.templates_dir)
        jinja2_template_dir = os.path.join(
            TEMPLATES[1]['DIRS'][0], self.templates_dir)

        TEMPLATES[0]['DIRS'] = [django_template_dir]
        TEMPLATES[1]['DIRS'] = [jinja2_template_dir]

        override_settings = {
            'TEMPLATES': TEMPLATES,
            'COMPRESS_ENABLED': True,
            'COMPRESS_OFFLINE': True
        }

        if 'jinja2' in self.engines:
            override_settings['COMPRESS_JINJA2_GET_ENVIRONMENT'] = (
                lambda: self._get_jinja2_env())

        if self.additional_test_settings is not None:
            override_settings.update(self.additional_test_settings)

        self.override_settings = self.settings(**override_settings)
        self.override_settings.__enter__()

        if 'django' in self.engines:
            self.template_path = os.path.join(
                django_template_dir, self.template_name)

            with io.open(self.template_path,
                         encoding=settings.FILE_CHARSET) as file_:
                self.template = Template(file_.read())

        if 'jinja2' in self.engines:
            self.template_path_jinja2 = os.path.join(
                jinja2_template_dir, self.template_name)
            jinja2_env = override_settings['COMPRESS_JINJA2_GET_ENVIRONMENT']()

            with io.open(self.template_path_jinja2,
                         encoding=settings.FILE_CHARSET) as file_:
                self.template_jinja2 = jinja2_env.from_string(file_.read())

    def tearDown(self):
        self.override_settings.__exit__(None, None, None)

        manifest_path = os.path.join('CACHE', 'manifest.json')
        if default_storage.exists(manifest_path):
            default_storage.delete(manifest_path)

    def _prepare_contexts(self, engine):
        if engine == 'django':
            return [Context(settings.COMPRESS_OFFLINE_CONTEXT)]
        if engine == 'jinja2':
            return [settings.COMPRESS_OFFLINE_CONTEXT]
        return None

    def _render_template(self, engine):
        contexts = self._prepare_contexts(engine)
        if engine == 'django':
            return ''.join(self.template.render(c) for c in contexts)
        if engine == 'jinja2':
            return '\n'.join(
                self.template_jinja2.render(c) for c in contexts) + '\n'
        return None

    def _test_offline(self, engine):
        hashes = self.expected_hash
        if not isinstance(hashes, (list, tuple)):
            hashes = [hashes]
        count, result = CompressCommand().compress(
            log=self.log, verbosity=self.verbosity, engine=engine)
        self.assertEqual(len(hashes), count)
        self.assertEqual([
            '<script type="text/javascript" src="/static/CACHE/js/'
            '%s.js"></script>' % h for h in hashes], result)
        rendered_template = self._render_template(engine)
        self.assertEqual(rendered_template, '\n'.join(result) + '\n')

    def test_offline_django(self):
        if 'django' not in self.engines:
            raise SkipTest('This test class does not support django engine.')
        self._test_offline(engine='django')

    def test_offline_jinja2(self):
        if 'jinja2' not in self.engines:
            raise SkipTest('This test class does not support jinja2 engine.')
        self._test_offline(engine='jinja2')

    def _get_jinja2_env(self):
        import jinja2
        import jinja2.ext
        from compressor.offline.jinja2 import url_for, SpacelessExtension
        from compressor.contrib.jinja2ext import CompressorExtension

        # Extensions needed for the test cases only.
        extensions = [
            CompressorExtension,
            SpacelessExtension,
            jinja2.ext.with_,
            jinja2.ext.do,
        ]
        loader = self._get_jinja2_loader()
        env = jinja2.Environment(extensions=extensions, loader=loader)
        env.globals['url_for'] = url_for

        return env

    def _get_jinja2_loader(self):
        import jinja2

        loader = jinja2.FileSystemLoader(
            settings.TEMPLATES[1]['DIRS'], encoding=settings.FILE_CHARSET)
        return loader


class OfflineCompressBasicTestCase(OfflineTestCaseMixin, TestCase):
    templates_dir = 'basic'
    expected_hash = 'f5e179b8eca4'

    @patch.object(CompressCommand, 'compress')
    def test_handle_no_args(self, compress_mock):
        CompressCommand().handle()
        self.assertEqual(compress_mock.call_count, 1)

    @patch.object(CompressCommand, 'compress')
    def test_handle_compress_disabled(self, compress_mock):
        with self.settings(COMPRESS_ENABLED=False):
            with self.assertRaises(CommandError):
                CompressCommand().handle()
        self.assertEqual(compress_mock.call_count, 0)

    @patch.object(CompressCommand, 'compress')
    def test_handle_compress_offline_disabled(self, compress_mock):
        with self.settings(COMPRESS_OFFLINE=False):
            with self.assertRaises(CommandError):
                CompressCommand().handle()
        self.assertEqual(compress_mock.call_count, 0)

    @patch.object(CompressCommand, 'compress')
    def test_handle_compress_offline_disabled_force(self, compress_mock):
        with self.settings(COMPRESS_OFFLINE=False):
            CompressCommand().handle(force=True)
        self.assertEqual(compress_mock.call_count, 1)

    def test_rendering_without_manifest_raises_exception(self):
        # flush cached manifest
        flush_offline_manifest()
        self.assertRaises(OfflineGenerationError,
                          self.template.render, Context({}))

    @unittest.skipIf(not _TEST_JINJA2, 'No Jinja2 testing')
    def test_rendering_without_manifest_raises_exception_jinja2(self):
        # flush cached manifest
        flush_offline_manifest()
        self.assertRaises(OfflineGenerationError,
                          self.template_jinja2.render, {})

    def _test_deleting_manifest_does_not_affect_rendering(self, engine):
        count, result = CompressCommand().compress(
            log=self.log, verbosity=self.verbosity, engine=engine)
        get_offline_manifest()
        manifest_path = os.path.join('CACHE', 'manifest.json')
        if default_storage.exists(manifest_path):
            default_storage.delete(manifest_path)
        self.assertEqual(1, count)
        self.assertEqual([
            '<script type="text/javascript" src="/static/CACHE/js/'
            '%s.js"></script>' % (self.expected_hash, )], result)
        rendered_template = self._render_template(engine)
        self.assertEqual(rendered_template, ''.join(result) + '\n')

    def test_deleting_manifest_does_not_affect_rendering(self):
        for engine in self.engines:
            self._test_deleting_manifest_does_not_affect_rendering(engine)

    def test_get_loaders(self):
        TEMPLATE_LOADERS = (
            ('django.template.loaders.cached.Loader', (
                'django.template.loaders.filesystem.Loader',
                'django.template.loaders.app_directories.Loader',
            )),
        )
        with self.settings(TEMPLATE_LOADERS=TEMPLATE_LOADERS):
            from django.template.loaders.filesystem import (
                Loader as FileSystemLoader)
            from django.template.loaders.app_directories import (
                Loader as AppDirectoriesLoader)
            loaders = CompressCommand().get_loaders()
            self.assertTrue(isinstance(loaders[0], FileSystemLoader))
            self.assertTrue(isinstance(loaders[1], AppDirectoriesLoader))


class OfflineCompressSkipDuplicatesTestCase(OfflineTestCaseMixin, TestCase):
    templates_dir = 'test_duplicate'

    # We don't need to test multiples engines here.
    engines = ('django',)

    def _test_offline(self, engine):
        count, result = CompressCommand().compress(
            log=self.log, verbosity=self.verbosity, engine=engine)
        # Only one block compressed, the second identical one was skipped.
        self.assertEqual(1, count)
        # Only 1 <script> block in returned result as well.
        self.assertEqual([
            '<script type="text/javascript" src="/static/CACHE/js/'
            'f5e179b8eca4.js"></script>',
        ], result)
        rendered_template = self._render_template(engine)
        # But rendering the template returns both (identical) scripts.
        self.assertEqual(rendered_template, ''.join(result * 2) + '\n')


class OfflineCompressBlockSuperTestCase(OfflineTestCaseMixin, TestCase):
    templates_dir = 'test_block_super'
    expected_hash = '7c02d201f69d'
    # Block.super not supported for Jinja2 yet.
    engines = ('django',)


class OfflineCompressBlockSuperMultipleTestCase(
        OfflineTestCaseMixin, TestCase):
    templates_dir = 'test_block_super_multiple'
    expected_hash = 'f8891c416981'
    # Block.super not supported for Jinja2 yet.
    engines = ('django',)


class OfflineCompressBlockSuperMultipleCachedLoaderTestCase(
        OfflineTestCaseMixin, TestCase):
    templates_dir = 'test_block_super_multiple_cached'
    expected_hash = '2f6ef61c488e'
    # Block.super not supported for Jinja2 yet.
    engines = ('django',)
    additional_test_settings = {
        'TEMPLATE_LOADERS': (
            ('django.template.loaders.cached.Loader', (
                'django.template.loaders.filesystem.Loader',
                'django.template.loaders.app_directories.Loader',
            )),
        )
    }


class OfflineCompressBlockSuperTestCaseWithExtraContent(
        OfflineTestCaseMixin, TestCase):
    templates_dir = 'test_block_super_extra'
    # Block.super not supported for Jinja2 yet.
    engines = ('django',)

    def _test_offline(self, engine):
        count, result = CompressCommand().compress(
            log=self.log, verbosity=self.verbosity, engine=engine)
        self.assertEqual(2, count)
        self.assertEqual([
            '<script type="text/javascript" src="/static/CACHE/js/'
            'ced14aec5856.js"></script>',
            '<script type="text/javascript" src="/static/CACHE/js/'
            '7c02d201f69d.js"></script>',
        ], result)
        rendered_template = self._render_template(engine)
        self.assertEqual(rendered_template, ''.join(result) + '\n')


class OfflineCompressConditionTestCase(OfflineTestCaseMixin, TestCase):
    templates_dir = 'test_condition'
    expected_hash = '4e3758d50224'
    additional_test_settings = {
        'COMPRESS_OFFLINE_CONTEXT': {
            'condition': 'red',
        }
    }


class OfflineCompressTemplateTagTestCase(OfflineTestCaseMixin, TestCase):
    templates_dir = 'test_templatetag'
    expected_hash = 'a27e1d3a619a'


class OfflineCompressStaticTemplateTagTestCase(OfflineTestCaseMixin, TestCase):
    templates_dir = 'test_static_templatetag'
    expected_hash = 'dfa2bb387fa8'


class OfflineCompressTestCaseWithContext(OfflineTestCaseMixin, TestCase):
    templates_dir = 'test_with_context'
    expected_hash = '5838e2fd66af'
    additional_test_settings = {
        'COMPRESS_OFFLINE_CONTEXT': {
            'content': 'OK!',
        }
    }


class OfflineCompressTestCaseWithContextSuper(OfflineTestCaseMixin, TestCase):
    templates_dir = 'test_with_context_super'
    expected_hash = 'b1d0a333a4ef'
    additional_test_settings = {
        'COMPRESS_OFFLINE_CONTEXT': {
            'content': 'OK!',
        }
    }
    # Block.super not supported for Jinja2 yet.
    engines = ('django',)


class OfflineCompressTestCaseWithContextList(OfflineTestCaseMixin, TestCase):
    templates_dir = 'test_with_context'
    expected_hash = ['f8bcaea049b3', 'db12749b1e80', 'e9f4a0054a06']
    additional_test_settings = {
        'COMPRESS_OFFLINE_CONTEXT': list(offline_context_generator())
    }

    def _prepare_contexts(self, engine):
        if engine == 'django':
            return [Context(c) for c in settings.COMPRESS_OFFLINE_CONTEXT]
        if engine == 'jinja2':
            return settings.COMPRESS_OFFLINE_CONTEXT
        return None


class OfflineCompressTestCaseWithContextListSuper(
        OfflineCompressTestCaseWithContextList):
    templates_dir = 'test_with_context_super'
    expected_hash = ['b11543f1e174', 'aedf6d2a7ec7', '0dbb8c29f23a']
    additional_test_settings = {
        'COMPRESS_OFFLINE_CONTEXT': list(offline_context_generator())
    }
    # Block.super not supported for Jinja2 yet.
    engines = ('django',)


class OfflineCompressTestCaseWithContextGenerator(
        OfflineTestCaseMixin, TestCase):
    templates_dir = 'test_with_context'
    expected_hash = ['f8bcaea049b3', 'db12749b1e80', 'e9f4a0054a06']
    additional_test_settings = {
        'COMPRESS_OFFLINE_CONTEXT': 'compressor.tests.test_offline.'
                                    'offline_context_generator'
    }

    def _prepare_contexts(self, engine):
        module, function = get_mod_func(settings.COMPRESS_OFFLINE_CONTEXT)
        contexts = getattr(import_module(module), function)()
        if engine == 'django':
            return (Context(c) for c in contexts)
        if engine == 'jinja2':
            return contexts
        return None


class OfflineCompressTestCaseWithContextGeneratorSuper(
        OfflineCompressTestCaseWithContextGenerator):
    templates_dir = 'test_with_context_super'
    expected_hash = ['b11543f1e174', 'aedf6d2a7ec7', '0dbb8c29f23a']
    additional_test_settings = {
        'COMPRESS_OFFLINE_CONTEXT': 'compressor.tests.test_offline.'
                                    'offline_context_generator'
    }
    # Block.super not supported for Jinja2 yet.
    engines = ('django',)


class OfflineCompressTestCaseWithContextGeneratorImportError(
        OfflineTestCaseMixin, TestCase):
    templates_dir = 'test_with_context'

    def _test_offline(self, engine):
        # Test that we are properly generating ImportError when
        # COMPRESS_OFFLINE_CONTEXT looks like a function but can't be imported
        # for whatever reason.

        with self.settings(
                COMPRESS_OFFLINE_CONTEXT='invalid_mod.invalid_func'):
            # Path with invalid module name -- ImportError:
            self.assertRaises(
                ImportError, CompressCommand().compress, engine=engine)

        with self.settings(COMPRESS_OFFLINE_CONTEXT='compressor'):
            # Valid module name only without function -- AttributeError:
            self.assertRaises(
                ImportError, CompressCommand().compress, engine=engine)

        with self.settings(
                COMPRESS_OFFLINE_CONTEXT='compressor.tests.invalid_function'):
            # Path with invalid function name -- AttributeError:
            self.assertRaises(
                ImportError, CompressCommand().compress, engine=engine)

        with self.settings(
                COMPRESS_OFFLINE_CONTEXT='compressor.tests.test_offline'):
            # Path without function attempts call on module -- TypeError:
            self.assertRaises(
                ImportError, CompressCommand().compress, engine=engine)

        valid_path = 'compressor.tests.test_offline.offline_context_generator'
        with self.settings(COMPRESS_OFFLINE_CONTEXT=valid_path):
            # Valid path to generator function -- no ImportError:

            try:
                CompressCommand().compress(engine=engine)
            except ImportError:
                self.fail('Valid path to offline context generator must'
                          ' not raise ImportError.')


class OfflineCompressTestCaseErrors(OfflineTestCaseMixin, TestCase):
    templates_dir = 'test_error_handling'

    def _test_offline(self, engine):
        count, result = CompressCommand().compress(
            log=self.log, verbosity=self.verbosity, engine=engine)

        if engine == 'django':
            self.assertEqual(2, count)
        else:
            # Because we use env.parse in Jinja2Parser, the engine does not
            # actually load the 'extends' and 'includes' templates, and so
            # it is unable to detect that they are missing. So all the
            # 'compress' nodes are processed correctly.
            self.assertEqual(4, count)
            self.assertEqual(engine, 'jinja2')
            self.assertIn(
                '<link rel="stylesheet" href="/static/CACHE/css/'
                '78bd7a762e2d.css" type="text/css" />', result)
            self.assertIn(
                '<link rel="stylesheet" href="/static/CACHE/css/'
                'e31030430724.css" type="text/css" />', result)

        self.assertIn(
            '<script type="text/javascript" src="/static/CACHE/js/'
            '3872c9ae3f42.js"></script>', result)
        self.assertIn(
            '<script type="text/javascript" src="/static/CACHE/js/'
            'cd8870829421.js"></script>', result)


class OfflineCompressTestCaseWithError(OfflineTestCaseMixin, TestCase):
    templates_dir = 'test_error_handling'
    additional_test_settings = {
        'COMPRESS_PRECOMPILERS': (('text/coffeescript', 'nonexisting-binary'),)
    }

    def _test_offline(self, engine):
        """
        Test that a CommandError is raised with DEBUG being False as well as
        True, as otherwise errors in configuration will never show in
        production.
        """
        with self.settings(DEBUG=True):
            self.assertRaises(
                CommandError, CompressCommand().compress, engine=engine)

        with self.settings(DEBUG=False):
            self.assertRaises(
                CommandError, CompressCommand().compress, engine=engine)


class OfflineCompressEmptyTag(OfflineTestCaseMixin, TestCase):
    """
        In case of a compress template tag with no content, an entry
        will be added to the manifest with an empty string as value.
        This test makes sure there is no recompression happening when
        compressor encounters such an emptystring in the manifest.
    """
    templates_dir = 'basic'
    expected_hash = 'f5e179b8eca4'
    engines = ('django',)

    def _test_offline(self, engine):
        count, result = CompressCommand().compress(
            log=self.log, verbosity=self.verbosity, engine=engine)
        manifest = get_offline_manifest()
        manifest[list(manifest)[0]] = ''
        self.assertEqual(self._render_template(engine), '\n')


class OfflineCompressBlockSuperBaseCompressed(OfflineTestCaseMixin, TestCase):
    template_names = ['base.html', 'base2.html',
                      'test_compressor_offline.html']
    templates_dir = 'test_block_super_base_compressed'
    expected_hash = ['028c3fc42232', '2e9d3f5545a6', 'f8891c416981']
    # Block.super not supported for Jinja2 yet.
    engines = ('django',)

    def setUp(self):
        super(OfflineCompressBlockSuperBaseCompressed, self).setUp()

        self.template_paths = []
        self.templates = []
        for template_name in self.template_names:
            template_path = os.path.join(
                settings.TEMPLATES[0]['DIRS'][0], template_name)
            self.template_paths.append(template_path)
            with io.open(template_path,
                         encoding=settings.FILE_CHARSET) as file_:
                template = Template(file_.read())
            self.templates.append(template)

    def _render_template(self, template, engine):
        if engine == 'django':
            return template.render(Context(settings.COMPRESS_OFFLINE_CONTEXT))
        elif engine == 'jinja2':
            return template.render(settings.COMPRESS_OFFLINE_CONTEXT) + '\n'
        else:
            return None

    def _test_offline(self, engine):
        count, result = CompressCommand().compress(
            log=self.log, verbosity=self.verbosity, engine=engine)
        self.assertEqual(len(self.expected_hash), count)
        for expected_hash, template in zip(self.expected_hash, self.templates):
            expected = ('<script type="text/javascript" src="/static/CACHE/js/'
                        '%s.js"></script>' % (expected_hash, ))
            self.assertIn(expected, result)
            rendered_template = self._render_template(template, engine)
            self.assertEqual(rendered_template, expected + '\n')


class OfflineCompressInlineNonAsciiTestCase(OfflineTestCaseMixin, TestCase):
    templates_dir = 'test_inline_non_ascii'
    additional_test_settings = {
        'COMPRESS_OFFLINE_CONTEXT': {
            'test_non_ascii_value': '\u2014',
        }
    }

    def _test_offline(self, engine):
        count, result = CompressCommand().compress(
            log=self.log, verbosity=self.verbosity, engine=engine)
        rendered_template = self._render_template(engine)
        self.assertEqual(rendered_template, ''.join(result) + '\n')


class OfflineCompressComplexTestCase(OfflineTestCaseMixin, TestCase):
    templates_dir = 'test_complex'
    additional_test_settings = {
        'COMPRESS_OFFLINE_CONTEXT': {
            'condition': 'OK!',
            # Django templating does not allow definition of tuples in the
            # templates.
            # Make sure this is same as test_templates_jinja2/test_complex.
            'my_names': ('js/one.js', 'js/nonasc.js'),
        }
    }

    def _test_offline(self, engine):
        count, result = CompressCommand().compress(
            log=self.log, verbosity=self.verbosity, engine=engine)
        self.assertEqual(3, count)
        self.assertEqual([
            '<script type="text/javascript" src="/static/CACHE/js/'
            '0e8807bebcee.js"></script>',
            '<script type="text/javascript" src="/static/CACHE/js/'
            'eed1d222933e.js"></script>',
            '<script type="text/javascript" src="/static/CACHE/js/'
            '00b4baffe335.js"></script>',
        ], result)
        rendered_template = self._render_template(engine)
        result = (result[0], result[2])
        self.assertEqual(rendered_template, ''.join(result) + '\n')
