from __future__ import with_statement, unicode_literals
import io
import os
import sys

from django.core.management.base import CommandError
from django.template import Template, Context
from django.test import TestCase
from django.utils import six, unittest

from compressor.cache import flush_offline_manifest, get_offline_manifest
from compressor.conf import settings
from compressor.exceptions import OfflineGenerationError
from compressor.management.commands.compress import Command as CompressCommand
from compressor.storage import default_storage

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
# causes the error "unhashable type: 'Template'"
_TEST_JINJA2 = not(sys.version_info[0] == 3 and sys.version_info[1] == 2)


class OfflineTestCaseMixin(object):
    template_name = "test_compressor_offline.html"
    verbosity = 0
    # Change this for each test class
    templates_dir = ""
    expected_hash = ""
    # Engines to test
    if _TEST_JINJA2:
        engines = ("django", "jinja2")
    else:
        engines = ("django",)

    def setUp(self):
        self._old_compress = settings.COMPRESS_ENABLED
        self._old_compress_offline = settings.COMPRESS_OFFLINE
        self._old_template_dirs = settings.TEMPLATE_DIRS
        self._old_offline_context = settings.COMPRESS_OFFLINE_CONTEXT
        self.log = StringIO()

        # Reset template dirs, because it enables us to force compress to
        # consider only a specific directory (helps us make true,
        # independant unit tests).
        # Specify both Jinja2 and Django template locations. When the wrong engine
        # is used to parse a template, the TemplateSyntaxError will cause the
        # template to be skipped over.
        django_template_dir = os.path.join(settings.TEST_DIR, 'test_templates', self.templates_dir)
        jinja2_template_dir = os.path.join(settings.TEST_DIR, 'test_templates_jinja2', self.templates_dir)
        settings.TEMPLATE_DIRS = (django_template_dir, jinja2_template_dir)

        # Enable offline compress
        settings.COMPRESS_ENABLED = True
        settings.COMPRESS_OFFLINE = True

        if "django" in self.engines:
            self.template_path = os.path.join(django_template_dir, self.template_name)

            with io.open(self.template_path, encoding=settings.FILE_CHARSET) as file:
                self.template = Template(file.read())

        self._old_jinja2_get_environment = settings.COMPRESS_JINJA2_GET_ENVIRONMENT

        if "jinja2" in self.engines:
            # Setup Jinja2 settings.
            settings.COMPRESS_JINJA2_GET_ENVIRONMENT = lambda: self._get_jinja2_env()
            jinja2_env = settings.COMPRESS_JINJA2_GET_ENVIRONMENT()
            self.template_path_jinja2 = os.path.join(jinja2_template_dir, self.template_name)

            with io.open(self.template_path_jinja2, encoding=settings.FILE_CHARSET) as file:
                self.template_jinja2 = jinja2_env.from_string(file.read())

    def tearDown(self):
        settings.COMPRESS_JINJA2_GET_ENVIRONMENT = self._old_jinja2_get_environment
        settings.COMPRESS_ENABLED = self._old_compress
        settings.COMPRESS_OFFLINE = self._old_compress_offline
        settings.TEMPLATE_DIRS = self._old_template_dirs
        manifest_path = os.path.join('CACHE', 'manifest.json')
        if default_storage.exists(manifest_path):
            default_storage.delete(manifest_path)

    def _render_template(self, engine):
        if engine == "django":
            return self.template.render(Context(settings.COMPRESS_OFFLINE_CONTEXT))
        elif engine == "jinja2":
            return self.template_jinja2.render(settings.COMPRESS_OFFLINE_CONTEXT) + "\n"
        else:
            return None

    def _test_offline(self, engine):
        count, result = CompressCommand().compress(log=self.log, verbosity=self.verbosity, engine=engine)
        self.assertEqual(1, count)
        self.assertEqual([
            '<script type="text/javascript" src="/static/CACHE/js/%s.js"></script>' % (self.expected_hash, ),
        ], result)
        rendered_template = self._render_template(engine)
        self.assertEqual(rendered_template, "".join(result) + "\n")

    def test_offline(self):
        for engine in self.engines:
            self._test_offline(engine=engine)

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

        loader = jinja2.FileSystemLoader(settings.TEMPLATE_DIRS, encoding=settings.FILE_CHARSET)
        return loader


class OfflineGenerationSkipDuplicatesTestCase(OfflineTestCaseMixin, TestCase):
    templates_dir = "test_duplicate"

    # We don't need to test multiples engines here.
    engines = ("django",)

    def _test_offline(self, engine):
        count, result = CompressCommand().compress(log=self.log, verbosity=self.verbosity, engine=engine)
        # Only one block compressed, the second identical one was skipped.
        self.assertEqual(1, count)
        # Only 1 <script> block in returned result as well.
        self.assertEqual([
            '<script type="text/javascript" src="/static/CACHE/js/f5e179b8eca4.js"></script>',
        ], result)
        rendered_template = self._render_template(engine)
        # But rendering the template returns both (identical) scripts.
        self.assertEqual(rendered_template, "".join(result * 2) + "\n")


class OfflineGenerationBlockSuperTestCase(OfflineTestCaseMixin, TestCase):
    templates_dir = "test_block_super"
    expected_hash = "7c02d201f69d"
    # Block.super not supported for Jinja2 yet.
    engines = ("django",)


class OfflineGenerationBlockSuperMultipleTestCase(OfflineTestCaseMixin, TestCase):
    templates_dir = "test_block_super_multiple"
    expected_hash = "f8891c416981"
    # Block.super not supported for Jinja2 yet.
    engines = ("django",)


class OfflineGenerationBlockSuperMultipleWithCachedLoaderTestCase(OfflineTestCaseMixin, TestCase):
    templates_dir = "test_block_super_multiple_cached"
    expected_hash = "2f6ef61c488e"
    # Block.super not supported for Jinja2 yet.
    engines = ("django",)

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
    # Block.super not supported for Jinja2 yet.
    engines = ("django",)

    def _test_offline(self, engine):
        count, result = CompressCommand().compress(log=self.log, verbosity=self.verbosity, engine=engine)
        self.assertEqual(2, count)
        self.assertEqual([
            '<script type="text/javascript" src="/static/CACHE/js/ced14aec5856.js"></script>',
            '<script type="text/javascript" src="/static/CACHE/js/7c02d201f69d.js"></script>'
        ], result)
        rendered_template = self._render_template(engine)
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

    def _test_offline(self, engine):
        count, result = CompressCommand().compress(log=self.log, verbosity=self.verbosity, engine=engine)

        if engine == "django":
            self.assertEqual(2, count)
        else:
            # Because we use env.parse in Jinja2Parser, the engine does not
            # actually load the "extends" and "includes" templates, and so
            # it is unable to detect that they are missing. So all the "compress"
            # nodes are processed correctly.
            self.assertEqual(4, count)
            self.assertEqual(engine, "jinja2")
            self.assertIn('<link rel="stylesheet" href="/static/CACHE/css/78bd7a762e2d.css" type="text/css" />', result)
            self.assertIn('<link rel="stylesheet" href="/static/CACHE/css/e31030430724.css" type="text/css" />', result)

        self.assertIn('<script type="text/javascript" src="/static/CACHE/js/3872c9ae3f42.js"></script>', result)
        self.assertIn('<script type="text/javascript" src="/static/CACHE/js/cd8870829421.js"></script>', result)


class OfflineGenerationTestCaseWithError(OfflineTestCaseMixin, TestCase):
    templates_dir = 'test_error_handling'

    def setUp(self):
        self._old_compress_precompilers = settings.COMPRESS_PRECOMPILERS
        settings.COMPRESS_PRECOMPILERS = (('text/coffeescript', 'non-existing-binary'),)
        super(OfflineGenerationTestCaseWithError, self).setUp()

    def _test_offline(self, engine):
        """
        Test that a CommandError is raised with DEBUG being False as well as
        True, as otherwise errors in configuration will never show in
        production.
        """
        self._old_debug = settings.DEBUG

        try:
            settings.DEBUG = True
            self.assertRaises(CommandError, CompressCommand().compress, engine=engine)

            settings.DEBUG = False
            self.assertRaises(CommandError, CompressCommand().compress, engine=engine)

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

    @unittest.skipIf(not _TEST_JINJA2, "No Jinja2 testing")
    def test_rendering_without_manifest_raises_exception_jinja2(self):
        # flush cached manifest
        flush_offline_manifest()
        self.assertRaises(OfflineGenerationError,
                          self.template_jinja2.render, {})

    def _test_deleting_manifest_does_not_affect_rendering(self, engine):
        count, result = CompressCommand().compress(log=self.log, verbosity=self.verbosity, engine=engine)
        get_offline_manifest()
        manifest_path = os.path.join('CACHE', 'manifest.json')
        if default_storage.exists(manifest_path):
            default_storage.delete(manifest_path)
        self.assertEqual(1, count)
        self.assertEqual([
            '<script type="text/javascript" src="/static/CACHE/js/%s.js"></script>' % (self.expected_hash, ),
        ], result)
        rendered_template = self._render_template(engine)
        self.assertEqual(rendered_template, "".join(result) + "\n")

    def test_deleting_manifest_does_not_affect_rendering(self):
        for engine in self.engines:
            self._test_deleting_manifest_does_not_affect_rendering(engine)

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


class OfflineGenerationBlockSuperBaseCompressed(OfflineTestCaseMixin, TestCase):
    template_names = ["base.html", "base2.html", "test_compressor_offline.html"]
    templates_dir = 'test_block_super_base_compressed'
    expected_hash = ['028c3fc42232', '2e9d3f5545a6', 'f8891c416981']
    # Block.super not supported for Jinja2 yet.
    engines = ("django",)

    def setUp(self):
        super(OfflineGenerationBlockSuperBaseCompressed, self).setUp()

        self.template_paths = []
        self.templates = []
        for template_name in self.template_names:
            template_path = os.path.join(settings.TEMPLATE_DIRS[0], template_name)
            self.template_paths.append(template_path)
            with io.open(template_path, encoding=settings.FILE_CHARSET) as file:
                template = Template(file.read())
            self.templates.append(template)

    def _render_template(self, template, engine):
        if engine == "django":
            return template.render(Context(settings.COMPRESS_OFFLINE_CONTEXT))
        elif engine == "jinja2":
            return template.render(settings.COMPRESS_OFFLINE_CONTEXT) + "\n"
        else:
            return None

    def _test_offline(self, engine):
        count, result = CompressCommand().compress(log=self.log, verbosity=self.verbosity, engine=engine)
        self.assertEqual(len(self.expected_hash), count)
        for expected_hash, template in zip(self.expected_hash, self.templates):
            expected_output = '<script type="text/javascript" src="/static/CACHE/js/%s.js"></script>' % (expected_hash, )
            self.assertIn(expected_output, result)
            rendered_template = self._render_template(template, engine)
            self.assertEqual(rendered_template, expected_output + '\n')


class OfflineGenerationInlineNonAsciiTestCase(OfflineTestCaseMixin, TestCase):
    templates_dir = "test_inline_non_ascii"

    def setUp(self):
        self.old_offline_context = settings.COMPRESS_OFFLINE_CONTEXT
        settings.COMPRESS_OFFLINE_CONTEXT = {
            'test_non_ascii_value': '\u2014',
        }
        super(OfflineGenerationInlineNonAsciiTestCase, self).setUp()

    def tearDown(self):
        self.COMPRESS_OFFLINE_CONTEXT = self.old_offline_context
        super(OfflineGenerationInlineNonAsciiTestCase, self).tearDown()

    def _test_offline(self, engine):
        count, result = CompressCommand().compress(log=self.log, verbosity=self.verbosity, engine=engine)
        rendered_template = self._render_template(engine)
        self.assertEqual(rendered_template, "".join(result) + "\n")


class OfflineGenerationComplexTestCase(OfflineTestCaseMixin, TestCase):
    templates_dir = "test_complex"

    def setUp(self):
        self.old_offline_context = settings.COMPRESS_OFFLINE_CONTEXT
        settings.COMPRESS_OFFLINE_CONTEXT = {
            'condition': 'OK!',
            # Django templating does not allow definition of tuples in the
            # templates. Make sure this is same as test_templates_jinja2/test_complex.
            'my_names': ("js/one.js", "js/nonasc.js"),
        }
        super(OfflineGenerationComplexTestCase, self).setUp()

    def tearDown(self):
        self.COMPRESS_OFFLINE_CONTEXT = self.old_offline_context
        super(OfflineGenerationComplexTestCase, self).tearDown()

    def _test_offline(self, engine):
        count, result = CompressCommand().compress(log=self.log, verbosity=self.verbosity, engine=engine)
        self.assertEqual(3, count)
        self.assertEqual([
            '<script type="text/javascript" src="/static/CACHE/js/0e8807bebcee.js"></script>',
            '<script type="text/javascript" src="/static/CACHE/js/eed1d222933e.js"></script>',
            '<script type="text/javascript" src="/static/CACHE/js/00b4baffe335.js"></script>',
        ], result)
        rendered_template = self._render_template(engine)
        result = (result[0], result[2])
        self.assertEqual(rendered_template, "".join(result) + "\n")


# Coffin does not work on Python 3.2+ due to:
# The line at coffin/template/__init__.py:15
#     from library import *
# causing 'ImportError: No module named library'.
# It seems there is no evidence nor indicated support for Python 3+.
@unittest.skipIf(sys.version_info >= (3, 2),
    "Coffin does not support 3.2+")
class OfflineGenerationCoffinTestCase(OfflineTestCaseMixin, TestCase):
    templates_dir = "test_coffin"
    expected_hash = "32c8281e3346"
    engines = ("jinja2",)

    def _get_jinja2_env(self):
        import jinja2
        from coffin.common import env
        from compressor.contrib.jinja2ext import CompressorExtension

        # Could have used the env.add_extension method, but it's only available
        # in Jinja2 v2.5
        new_env = jinja2.Environment(extensions=[CompressorExtension])
        env.extensions.update(new_env.extensions)

        return env


# Jingo does not work when using Python 3.2 due to the use of Unicode string
# prefix (and possibly other stuff), but it actually works when using Python 3.3
# since it tolerates the use of the Unicode string prefix. Python 3.3 support
# is also evident in its tox.ini file.
@unittest.skipIf(sys.version_info >= (3, 2) and sys.version_info < (3, 3),
    "Jingo does not support 3.2")
class OfflineGenerationJingoTestCase(OfflineTestCaseMixin, TestCase):
    templates_dir = "test_jingo"
    expected_hash = "61ec584468eb"
    engines = ("jinja2",)

    def _get_jinja2_env(self):
        import jinja2
        import jinja2.ext
        from jingo import env
        from compressor.contrib.jinja2ext import CompressorExtension
        from compressor.offline.jinja2 import SpacelessExtension, url_for

        # Could have used the env.add_extension method, but it's only available
        # in Jinja2 v2.5
        new_env = jinja2.Environment(extensions=[CompressorExtension, SpacelessExtension, jinja2.ext.with_])
        env.extensions.update(new_env.extensions)
        env.globals['url_for'] = url_for

        return env
