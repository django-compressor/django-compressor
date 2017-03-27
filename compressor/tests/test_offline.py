from __future__ import with_statement, unicode_literals
import copy
import django
import io
import os
import sys
import unittest
from importlib import import_module

from mock import patch
from unittest import SkipTest, skipIf

from django.core.management import call_command
from django.core.management.base import CommandError
from django.template import Template, Context
from django.test import TestCase
from django.test.utils import override_settings
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


def static_url_context_generator():
    yield {'STATIC_URL': settings.STATIC_URL}


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
        contexts = settings.COMPRESS_OFFLINE_CONTEXT
        if not isinstance(contexts, (list, tuple)):
            contexts = [contexts]
        if engine == 'django':
            return [Context(c) for c in contexts]
        if engine == 'jinja2':
            return contexts
        return None

    def _render_template(self, engine):
        contexts = self._prepare_contexts(engine)
        if engine == 'django':
            return ''.join(self.template.render(c) for c in contexts)
        if engine == 'jinja2':
            return '\n'.join(
                self.template_jinja2.render(c) for c in contexts) + '\n'
        return None

    def _render_script(self, hash):
        return (
            '<script type="text/javascript" src="{}CACHE/js/{}.js">'
            '</script>'.format(
                settings.COMPRESS_URL_PLACEHOLDER, hash
            )
        )

    def _render_link(self, hash):
        return (
            '<link rel="stylesheet" href="{}CACHE/css/{}.css" '
            'type="text/css" />'.format(
                settings.COMPRESS_URL_PLACEHOLDER, hash
            )
        )

    def _render_result(self, result, separator='\n'):
        return (separator.join(result) + '\n').replace(
            settings.COMPRESS_URL_PLACEHOLDER, settings.COMPRESS_URL
        )

    def _test_offline(self, engine):
        hashes = self.expected_hash
        if not isinstance(hashes, (list, tuple)):
            hashes = [hashes]
        count, result = CompressCommand().compress(
            log=self.log, verbosity=self.verbosity, engine=engine)
        self.assertEqual(len(hashes), count)
        self.assertEqual([self._render_script(h) for h in hashes], result)
        rendered_template = self._render_template(engine)
        self.assertEqual(rendered_template, self._render_result(result))

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
    expected_hash = 'a2d34b854194'

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
        self.assertEqual([self._render_script(self.expected_hash)], result)
        rendered_template = self._render_template(engine)
        self.assertEqual(rendered_template, self._render_result(result))

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

    @patch("compressor.offline.django.DjangoParser.render_node",
           side_effect=Exception(b"non-ascii character here:\xc3\xa4"))
    def test_non_ascii_exception_messages(self, mock):
        with self.assertRaises(CommandError):
            CompressCommand().handle()


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
        self.assertEqual([self._render_script('a2d34b854194')], result)
        rendered_template = self._render_template(engine)
        # But rendering the template returns both (identical) scripts.
        self.assertEqual(
            rendered_template, self._render_result(result * 2, ''))


class OfflineCompressBlockSuperTestCase(OfflineTestCaseMixin, TestCase):
    templates_dir = 'test_block_super'
    expected_hash = '09424aa0fc45'
    # Block.super not supported for Jinja2 yet.
    engines = ('django',)


class OfflineCompressBlockSuperMultipleTestCase(
        OfflineTestCaseMixin, TestCase):
    templates_dir = 'test_block_super_multiple'
    expected_hash = '86520b469e89'
    # Block.super not supported for Jinja2 yet.
    engines = ('django',)


class OfflineCompressBlockSuperMultipleCachedLoaderTestCase(
        OfflineTestCaseMixin, TestCase):
    templates_dir = 'test_block_super_multiple_cached'
    expected_hash = 'd31f4d9bbd99'
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
            self._render_script('85482ad42724'),
            self._render_script('09424aa0fc45')
        ], result)
        rendered_template = self._render_template(engine)
        self.assertEqual(rendered_template, self._render_result(result, ''))


class OfflineCompressConditionTestCase(OfflineTestCaseMixin, TestCase):
    templates_dir = 'test_condition'
    expected_hash = '2b3ab9ad7158'
    additional_test_settings = {
        'COMPRESS_OFFLINE_CONTEXT': {
            'condition': 'red',
        }
    }


class OfflineCompressTemplateTagTestCase(OfflineTestCaseMixin, TestCase):
    templates_dir = 'test_templatetag'
    expected_hash = 'a62a1cfcd3b5'


class OfflineCompressStaticTemplateTagTestCase(OfflineTestCaseMixin, TestCase):
    templates_dir = 'test_static_templatetag'
    expected_hash = 'c6ecb8d4ce7e'


class OfflineCompressTestCaseWithContext(OfflineTestCaseMixin, TestCase):
    templates_dir = 'test_with_context'
    expected_hash = '0b939b10df08'
    additional_test_settings = {
        'COMPRESS_OFFLINE_CONTEXT': {
            'content': 'OK!',
        }
    }


class OfflineCompressTestCaseWithContextSuper(OfflineTestCaseMixin, TestCase):
    templates_dir = 'test_with_context_super'
    expected_hash = '9fad27eba458'
    additional_test_settings = {
        'COMPRESS_OFFLINE_CONTEXT': {
            'content': 'OK!',
        }
    }
    # Block.super not supported for Jinja2 yet.
    engines = ('django',)


class OfflineCompressTestCaseWithContextList(OfflineTestCaseMixin, TestCase):
    templates_dir = 'test_with_context'
    expected_hash = ['a92d67d3304a', '0ad21f77e74e', 'a3598381c14f']
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
    expected_hash = ['1a40a7565816', 'f91a43f26ad3', 'b6e00dc2000c']
    additional_test_settings = {
        'COMPRESS_OFFLINE_CONTEXT': list(offline_context_generator())
    }
    # Block.super not supported for Jinja2 yet.
    engines = ('django',)


class OfflineCompressTestCaseWithContextGenerator(
        OfflineTestCaseMixin, TestCase):
    templates_dir = 'test_with_context'
    expected_hash = ['a92d67d3304a', '0ad21f77e74e', 'a3598381c14f']
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
    expected_hash = ['1a40a7565816', 'f91a43f26ad3', 'b6e00dc2000c']
    additional_test_settings = {
        'COMPRESS_OFFLINE_CONTEXT': 'compressor.tests.test_offline.'
                                    'offline_context_generator'
    }
    # Block.super not supported for Jinja2 yet.
    engines = ('django',)


class OfflineCompressStaticUrlIndependenceTestCase(
        OfflineCompressTestCaseWithContextGenerator):
    """
    Test that the offline manifest is independent of STATIC_URL.
    I.e. users can use the manifest with any other STATIC_URL in the future.

    We use COMPRESS_OFFLINE_CONTEXT generator to make sure that
    STATIC_URL is not cached when rendering the template.
    """
    templates_dir = 'test_static_url_independence'
    expected_hash = '12772534f095'
    additional_test_settings = {
        'STATIC_URL': '/custom/static/url/',
        'COMPRESS_OFFLINE_CONTEXT': (
            'compressor.tests.test_offline.static_url_context_generator'
        )
    }

    def _test_offline(self, engine):
        count, result = CompressCommand().compress(
            log=self.log, verbosity=self.verbosity, engine=engine
        )
        self.assertEqual(1, count)
        self.assertEqual([self._render_script(self.expected_hash)], result)
        self.assertEqual(
            self._render_template(engine), self._render_result(result))

        # Changing STATIC_URL setting doesn't break things despite that
        # offline compression was made with different STATIC_URL.
        with self.settings(STATIC_URL='/another/static/url/'):
            self.assertEqual(
                self._render_template(engine), self._render_result(result))


class OfflineCompressTestCaseWithContextVariableInheritance(
        OfflineTestCaseMixin, TestCase):
    templates_dir = 'test_with_context_variable_inheritance'
    expected_hash = 'fbf0ed0604e3'
    additional_test_settings = {
        'COMPRESS_OFFLINE_CONTEXT': {
            'parent_template': 'base.html',
        }
    }

    def _render_result(self, result, separator='\n'):
        return '\n' + super(
            OfflineCompressTestCaseWithContextVariableInheritance, self
        )._render_result(result, separator)


class OfflineCompressTestCaseWithContextVariableInheritanceSuper(
        OfflineTestCaseMixin, TestCase):
    templates_dir = 'test_with_context_variable_inheritance_super'
    additional_test_settings = {
        'COMPRESS_OFFLINE_CONTEXT': [{
            'parent_template': 'base1.html',
        }, {
            'parent_template': 'base2.html',
        }]
    }
    expected_hash = ['11c0a6708293', '3bb007b509b3']
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
            self.assertIn(self._render_link('78bd7a762e2d'), result)
            self.assertIn(self._render_link('e31030430724'), result)

        self.assertIn(self._render_script('e847d9758dbf'), result)
        self.assertIn(self._render_script('1c8d9c2db1fb'), result)


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
    expected_hash = 'a2d34b854194'
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
    expected_hash_offline = ['e74d9424467d', '9df645ef1c05', '86520b469e89']
    expected_hash = ['028c3fc42232', '2e9d3f5545a6', '86520b469e89']
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
        for expected_hash, template in zip(self.expected_hash_offline, self.templates):
            expected = self._render_script(expected_hash)
            self.assertIn(expected, result)
            rendered_template = self._render_template(template, engine)
            self.assertEqual(
                rendered_template, self._render_result([expected]))


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
            self._render_script('ea8d7c940f0d'),
            self._render_script('10ae6904bcc6'),
            self._render_script('8c7c068d5973')
        ], result)
        rendered_template = self._render_template(engine)
        self.assertEqual(
            rendered_template, self._render_result([result[0], result[2]], ''))


@skipIf(
    django.VERSION < (1, 9),
    "Needs Django >= 1.9, recursive templates were fixed in Django 1.9"
)
class OfflineCompressExtendsRecursionTestCase(OfflineTestCaseMixin, TestCase):
    """
    Test that templates extending templates with the same name
    (e.g. admin/index.html) don't cause an infinite test_extends_recursion
    """
    templates_dir = 'test_extends_recursion'
    engines = ('django',)

    INSTALLED_APPS = [
        'django.contrib.admin',
        'django.contrib.auth',
        'django.contrib.contenttypes',
        'django.contrib.staticfiles',
        'compressor',
    ]

    @override_settings(INSTALLED_APPS=INSTALLED_APPS)
    def _test_offline(self, engine):
        count, result = CompressCommand().compress(
            log=self.log, verbosity=self.verbosity, engine=engine)
        self.assertEqual(count, 1)


@skipIf(not _TEST_JINJA2, "Test only run if we are testing Jinja2")
class TestCompressCommand(OfflineTestCaseMixin, TestCase):
    templates_dir = "test_compress_command"

    def _test_offline(self, engine):
        raise SkipTest("Not utilized for this test case")

    def _build_expected_manifest(self, expected):
        return {
            k: self._render_script(v) for k, v in expected.items()
        }

    def test_multiple_engines(self):
        opts = {
            "force": True,
            "verbosity": 0,
            "log": StringIO(),
        }

        call_command('compress', engines=["django"], **opts)
        manifest_django = get_offline_manifest()
        manifest_django_expected = self._build_expected_manifest(
            {'8464063aa0729700fca0452e009582af': 'f3bfcd635b36'})
        self.assertEqual(manifest_django, manifest_django_expected)

        call_command('compress', engines=["jinja2"], **opts)
        manifest_jinja2 = get_offline_manifest()
        manifest_jinja2_expected = self._build_expected_manifest(
            {'0ec631f01496b28bbecad129c5532db4': '9ddf4527a67d'})
        self.assertEqual(manifest_jinja2, manifest_jinja2_expected)

        call_command('compress', engines=["django", "jinja2"], **opts)
        manifest_both = get_offline_manifest()
        manifest_both_expected = self._build_expected_manifest(
            {'8464063aa0729700fca0452e009582af': 'f3bfcd635b36',
             '0ec631f01496b28bbecad129c5532db4': '9ddf4527a67d'})
        self.assertEqual(manifest_both, manifest_both_expected)
