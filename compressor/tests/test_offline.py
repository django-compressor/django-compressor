import copy
import io
import os
from contextlib import contextmanager
from importlib import import_module
from unittest import SkipTest
from unittest.mock import patch

from django.conf import settings
from django.core.management import call_command, CommandError
from django.template import Context, Origin, Template
from django.test import override_settings, TestCase
from django.urls import get_script_prefix, set_script_prefix

from compressor.cache import flush_offline_manifest, get_offline_manifest
from compressor.exceptions import OfflineGenerationError
from compressor.management.commands.compress import Command as CompressCommand
from compressor.storage import default_offline_manifest_storage
from compressor.utils import get_mod_func


def offline_context_generator():
    for i in range(1, 4):
        yield {"content": "OK %d!" % i}


def static_url_context_generator():
    yield {"STATIC_URL": settings.STATIC_URL}


class LazyScriptNamePrefixedUrl(str):
    """
    Lazy URL with ``SCRIPT_NAME`` WSGI param as path prefix.

    .. code-block :: python

        settings.STATIC_URL = LazyScriptNamePrefixedUrl('/static/')

        # HTTP request to '/some/page/' without SCRIPT_NAME
        str(settings.STATIC_URL) == '/static/'

        # HTTP request to '/app/prefix/some/page/` with SCRIPT_NAME = '/app/prefix/'
        str(settings.STATIC_URL) == '/app/prefix/static/'

        # HTTP request to '/another/prefix/some/page/` with SCRIPT_NAME = '/another/prefix/'
        str(settings.STATIC_URL) == '/another/prefix/static/'

    The implementation is incomplete, all ``str`` methods must be overridden
    in order to work correctly with the rest of Django core.
    """

    def __str__(self):
        return get_script_prefix() + self[1:] if self.startswith("/") else self

    def __unicode__(self):
        return str(self)

    def __hash__(self):
        return str.__hash__(str(self))

    def split(self, *args, **kwargs):
        """
        Override ``.split()`` method to make it work with ``{% static %}``.
        """
        return str(self).split(*args, **kwargs)

    def replace(self, *args, **kwargs):
        """Override ``.replace()`` to make it work with ``{% static %}``.

        In ``django.core.files.storage``, ``FileSystemStorage.url()`` passes
        this object to ``urllib.parse.urljoin``.

        In ``urrlib.parse``, the function that calls ``replace()`` is
        ``_remove_unsafe_bytes_from_url()``.

        """
        return str(self).replace(*args, **kwargs)


@contextmanager
def script_prefix(new_prefix):
    """
    Override ``SCRIPT_NAME`` WSGI param, yield, then restore its original value.

    :param new_prefix: New ``SCRIPT_NAME`` value.
    """
    old_prefix = get_script_prefix()
    set_script_prefix(new_prefix)
    yield
    set_script_prefix(old_prefix)


class OfflineTestCaseMixin:
    CHARSET = "utf-8"
    template_name = "test_compressor_offline.html"
    # Change this for each test class
    templates_dir = ""
    expected_basename = "output"
    expected_hash = ""
    # Engines to test
    engines = ("django", "jinja2")
    additional_test_settings = None

    def setUp(self):
        # Reset template dirs, because it enables us to force compress to
        # consider only a specific directory (helps us make true,
        # independent unit tests).
        # Specify both Jinja2 and Django template locations. When the wrong
        # engine is used to parse a template, the TemplateSyntaxError will
        # cause the template to be skipped over.
        # We've hardcoded TEMPLATES[0] to be Django templates backend and
        # TEMPLATES[1] to be Jinja2 templates backend in test_settings.
        TEMPLATES = copy.deepcopy(settings.TEMPLATES)

        django_template_dir = os.path.join(TEMPLATES[0]["DIRS"][0], self.templates_dir)
        jinja2_template_dir = os.path.join(TEMPLATES[1]["DIRS"][0], self.templates_dir)

        TEMPLATES[0]["DIRS"] = [django_template_dir]
        TEMPLATES[1]["DIRS"] = [jinja2_template_dir]

        override_settings = {
            "TEMPLATES": TEMPLATES,
            "COMPRESS_ENABLED": True,
            "COMPRESS_OFFLINE": True,
        }

        if "jinja2" in self.engines:
            override_settings[
                "COMPRESS_JINJA2_GET_ENVIRONMENT"
            ] = lambda: self._get_jinja2_env()

        if self.additional_test_settings is not None:
            override_settings.update(self.additional_test_settings)

        self.override_settings = self.settings(**override_settings)
        self.override_settings.__enter__()

        if "django" in self.engines:
            self.template_path = os.path.join(django_template_dir, self.template_name)

            origin = Origin(
                name=self.template_path,  # Absolute path
                template_name=self.template_name,
            )  # Loader-relative path
            with io.open(self.template_path, encoding=self.CHARSET) as file_:
                self.template = Template(file_.read(), origin=origin)

        if "jinja2" in self.engines:
            self.template_path_jinja2 = os.path.join(
                jinja2_template_dir, self.template_name
            )
            jinja2_env = override_settings["COMPRESS_JINJA2_GET_ENVIRONMENT"]()

            with io.open(self.template_path_jinja2, encoding=self.CHARSET) as file_:
                self.template_jinja2 = jinja2_env.from_string(file_.read())

    def tearDown(self):
        self.override_settings.__exit__(None, None, None)

        manifest_filename = "manifest.json"
        if default_offline_manifest_storage.exists(manifest_filename):
            default_offline_manifest_storage.delete(manifest_filename)

    def _prepare_contexts(self, engine):
        contexts = settings.COMPRESS_OFFLINE_CONTEXT
        if not isinstance(contexts, (list, tuple)):
            contexts = [contexts]
        if engine == "django":
            return [Context(c) for c in contexts]
        if engine == "jinja2":
            return contexts
        return None

    def _render_template(self, engine):
        contexts = self._prepare_contexts(engine)
        if engine == "django":
            return "".join(self.template.render(c) for c in contexts)
        if engine == "jinja2":
            return "\n".join(self.template_jinja2.render(c) for c in contexts) + "\n"
        return None

    def _render_script(self, hash):
        return '<script src="{}CACHE/js/{}.{}.js">' "</script>".format(
            settings.COMPRESS_URL_PLACEHOLDER, self.expected_basename, hash
        )

    def _render_link(self, hash):
        return (
            '<link rel="stylesheet" href="{}CACHE/css/{}.{}.css" '
            'type="text/css">'.format(
                settings.COMPRESS_URL_PLACEHOLDER, self.expected_basename, hash
            )
        )

    def _render_result(self, result, separator="\n"):
        return (separator.join(result) + "\n").replace(
            settings.COMPRESS_URL_PLACEHOLDER, str(settings.COMPRESS_URL)
        )

    def _test_offline(self, engine, verbosity=0):
        hashes = self.expected_hash
        if not isinstance(hashes, (list, tuple)):
            hashes = [hashes]
        count, result = CompressCommand().handle_inner(
            engines=[engine], verbosity=verbosity
        )
        self.assertEqual(len(hashes), count)
        self.assertEqual([self._render_script(h) for h in hashes], result)
        rendered_template = self._render_template(engine)
        self.assertEqual(rendered_template, self._render_result(result))

    def test_offline_django(self):
        if "django" not in self.engines:
            raise SkipTest("This test class does not support django engine.")
        self._test_offline(engine="django")

    def test_offline_jinja2(self):
        if "jinja2" not in self.engines:
            raise SkipTest("This test class does not support jinja2 engine.")
        self._test_offline(engine="jinja2")

    def test_offline_django_verbosity_1(self):
        if "django" not in self.engines:
            raise SkipTest("This test class does not support django engine.")
        self._test_offline(engine="django", verbosity=1)

    def test_offline_jinja2_verbosity_1(self):
        if "jinja2" not in self.engines:
            raise SkipTest("This test class does not support jinja2 engine.")
        self._test_offline(engine="jinja2", verbosity=1)

    def test_offline_django_verbosity_2(self):
        if "django" not in self.engines:
            raise SkipTest("This test class does not support django engine.")
        self._test_offline(engine="django", verbosity=2)

    def test_offline_jinja2_verbosity_2(self):
        if "jinja2" not in self.engines:
            raise SkipTest("This test class does not support jinja2 engine.")
        self._test_offline(engine="jinja2", verbosity=2)

    def _get_jinja2_env(self):
        import jinja2.ext
        from compressor.offline.jinja2 import url_for, SpacelessExtension
        from compressor.contrib.jinja2ext import CompressorExtension

        # Extensions needed for the test cases only.
        extensions = [
            CompressorExtension,
            SpacelessExtension,
            jinja2.ext.do,
        ]
        loader = self._get_jinja2_loader()
        env = jinja2.Environment(extensions=extensions, loader=loader)
        env.globals["url_for"] = url_for

        return env

    def _get_jinja2_loader(self):
        import jinja2

        loader = jinja2.FileSystemLoader(
            settings.TEMPLATES[1]["DIRS"], encoding=self.CHARSET
        )
        return loader


class OfflineCompressBasicTestCase(OfflineTestCaseMixin, TestCase):
    templates_dir = "basic"
    expected_hash = "822ac7501287"

    @patch.object(CompressCommand, "compress")
    def test_handle_no_args(self, compress_mock):
        compress_mock.return_value = {}, 1, []
        CompressCommand().handle()
        self.assertEqual(compress_mock.call_count, 1)

    @patch.object(CompressCommand, "compress")
    def test_handle_compress_disabled(self, compress_mock):
        with self.settings(COMPRESS_ENABLED=False):
            with self.assertRaises(CommandError):
                CompressCommand().handle()
        self.assertEqual(compress_mock.call_count, 0)

    @patch.object(CompressCommand, "compress")
    def test_handle_compress_offline_disabled(self, compress_mock):
        with self.settings(COMPRESS_OFFLINE=False):
            with self.assertRaises(CommandError):
                CompressCommand().handle()
        self.assertEqual(compress_mock.call_count, 0)

    @patch.object(CompressCommand, "compress")
    def test_handle_compress_offline_disabled_force(self, compress_mock):
        compress_mock.return_value = {}, 1, []
        with self.settings(COMPRESS_OFFLINE=False):
            CompressCommand().handle(force=True)
        self.assertEqual(compress_mock.call_count, 1)

    def test_rendering_without_manifest_raises_exception(self):
        # flush cached manifest
        flush_offline_manifest()
        self.assertRaises(OfflineGenerationError, self.template.render, Context({}))

    def test_rendering_without_manifest_raises_exception_jinja2(self):
        # flush cached manifest
        flush_offline_manifest()
        self.assertRaises(OfflineGenerationError, self.template_jinja2.render, {})

    def _test_deleting_manifest_does_not_affect_rendering(self, engine):
        count, result = CompressCommand().handle_inner(engines=[engine], verbosity=0)
        get_offline_manifest()
        manifest_filename = "manifest.json"
        if default_offline_manifest_storage.exists(manifest_filename):
            default_offline_manifest_storage.delete(manifest_filename)
        self.assertEqual(1, count)
        self.assertEqual([self._render_script(self.expected_hash)], result)
        rendered_template = self._render_template(engine)
        self.assertEqual(rendered_template, self._render_result(result))

    def test_deleting_manifest_does_not_affect_rendering(self):
        for engine in self.engines:
            self._test_deleting_manifest_does_not_affect_rendering(engine)

    def test_get_loaders(self):
        TEMPLATE_LOADERS = (
            (
                "django.template.loaders.cached.Loader",
                (
                    "django.template.loaders.filesystem.Loader",
                    "django.template.loaders.app_directories.Loader",
                ),
            ),
        )
        with self.settings(TEMPLATE_LOADERS=TEMPLATE_LOADERS):
            from django.template.loaders.filesystem import Loader as FileSystemLoader
            from django.template.loaders.app_directories import (
                Loader as AppDirectoriesLoader,
            )

            loaders = CompressCommand().get_loaders()
            self.assertTrue(isinstance(loaders[0], FileSystemLoader))
            self.assertTrue(isinstance(loaders[1], AppDirectoriesLoader))

    @patch(
        "compressor.offline.django.DjangoParser.render_node",
        side_effect=Exception(b"non-ascii character here:\xc3\xa4"),
    )
    def test_non_ascii_exception_messages(self, mock):
        with self.assertRaises(CommandError):
            CompressCommand().handle(verbosity=0)


class OfflineCompressSkipDuplicatesTestCase(OfflineTestCaseMixin, TestCase):
    templates_dir = "test_duplicate"

    def _test_offline(self, engine, verbosity=0):
        count, result = CompressCommand().handle_inner(
            engines=[engine], verbosity=verbosity
        )
        # Only one block compressed, the second identical one was skipped.
        self.assertEqual(1, count)
        # Only 1 <script> block in returned result as well.
        self.assertEqual([self._render_script("822ac7501287")], result)
        rendered_template = self._render_template(engine)
        # But rendering the template returns both (identical) scripts.
        self.assertEqual(rendered_template, self._render_result(result * 2, ""))


class SuperMixin:
    # Block.super not supported for Jinja2 yet.
    engines = ("django",)


class OfflineCompressBlockSuperTestCase(SuperMixin, OfflineTestCaseMixin, TestCase):
    templates_dir = "test_block_super"
    expected_hash = "817b5defb197"


class OfflineCompressBlockSuperMultipleTestCase(
    SuperMixin, OfflineTestCaseMixin, TestCase
):
    templates_dir = "test_block_super_multiple"
    expected_hash = "d3f749e83c81"


class OfflineCompressBlockSuperMultipleCachedLoaderTestCase(
    SuperMixin, OfflineTestCaseMixin, TestCase
):
    templates_dir = "test_block_super_multiple_cached"
    expected_hash = "055f88f4751f"
    additional_test_settings = {
        "TEMPLATE_LOADERS": (
            (
                "django.template.loaders.cached.Loader",
                (
                    "django.template.loaders.filesystem.Loader",
                    "django.template.loaders.app_directories.Loader",
                ),
            ),
        )
    }


class OfflineCompressBlockSuperTestCaseWithExtraContent(
    SuperMixin, OfflineTestCaseMixin, TestCase
):
    templates_dir = "test_block_super_extra"

    def _test_offline(self, engine, verbosity=0):
        count, result = CompressCommand().handle_inner(
            engines=[engine], verbosity=verbosity
        )
        self.assertEqual(2, count)
        self.assertEqual(
            [self._render_script("bfcec76e0f28"), self._render_script("817b5defb197")],
            result,
        )
        rendered_template = self._render_template(engine)
        self.assertEqual(rendered_template, self._render_result(result, ""))


class OfflineCompressConditionTestCase(OfflineTestCaseMixin, TestCase):
    templates_dir = "test_condition"
    expected_hash = "a3275743dc69"
    additional_test_settings = {
        "COMPRESS_OFFLINE_CONTEXT": {
            "condition": "red",
        }
    }


class OfflineCompressTemplateTagTestCase(OfflineTestCaseMixin, TestCase):
    templates_dir = "test_templatetag"
    expected_hash = "2bb88185b4f5"


class OfflineCompressStaticTemplateTagTestCase(OfflineTestCaseMixin, TestCase):
    templates_dir = "test_static_templatetag"
    expected_hash = "be0b1eade28b"


class OfflineCompressTemplateTagNamedTestCase(OfflineTestCaseMixin, TestCase):
    templates_dir = "test_templatetag_named"
    expected_basename = "output_name"
    expected_hash = "822ac7501287"


class OfflineCompressTestCaseWithContext(OfflineTestCaseMixin, TestCase):
    templates_dir = "test_with_context"
    expected_hash = "c6bf81bca7ad"
    additional_test_settings = {
        "COMPRESS_OFFLINE_CONTEXT": {
            "content": "OK!",
        }
    }


class OfflineCompressTestCaseWithContextSuper(
    SuperMixin, OfflineTestCaseMixin, TestCase
):
    templates_dir = "test_with_context_super"
    expected_hash = "dd79e1bd1527"
    additional_test_settings = {
        "COMPRESS_OFFLINE_CONTEXT": {
            "content": "OK!",
        }
    }


class OfflineCompressTestCaseWithContextList(OfflineTestCaseMixin, TestCase):
    templates_dir = "test_with_context"
    expected_hash = ["8b4a7452e1c5", "55b3123e884c", "bfc63829cc58"]
    additional_test_settings = {
        "COMPRESS_OFFLINE_CONTEXT": list(offline_context_generator())
    }

    def _prepare_contexts(self, engine):
        if engine == "django":
            return [Context(c) for c in settings.COMPRESS_OFFLINE_CONTEXT]
        if engine == "jinja2":
            return settings.COMPRESS_OFFLINE_CONTEXT
        return None


class OfflineCompressTestCaseWithContextListSuper(
    SuperMixin, OfflineCompressTestCaseWithContextList
):
    templates_dir = "test_with_context_super"
    expected_hash = ["b39975a8f6ea", "ed565a1d262f", "6ac9e4b29feb"]
    additional_test_settings = {
        "COMPRESS_OFFLINE_CONTEXT": list(offline_context_generator())
    }


class OfflineCompressTestCaseWithContextGenerator(OfflineTestCaseMixin, TestCase):
    templates_dir = "test_with_context"
    expected_hash = ["8b4a7452e1c5", "55b3123e884c", "bfc63829cc58"]
    additional_test_settings = {
        "COMPRESS_OFFLINE_CONTEXT": "compressor.tests.test_offline."
        "offline_context_generator"
    }

    def _prepare_contexts(self, engine):
        module, function = get_mod_func(settings.COMPRESS_OFFLINE_CONTEXT)
        contexts = getattr(import_module(module), function)()
        if engine == "django":
            return (Context(c) for c in contexts)
        if engine == "jinja2":
            return contexts
        return None


class OfflineCompressTestCaseWithContextGeneratorSuper(
    SuperMixin, OfflineCompressTestCaseWithContextGenerator
):
    templates_dir = "test_with_context_super"
    expected_hash = ["b39975a8f6ea", "ed565a1d262f", "6ac9e4b29feb"]
    additional_test_settings = {
        "COMPRESS_OFFLINE_CONTEXT": "compressor.tests.test_offline."
        "offline_context_generator"
    }


class OfflineCompressStaticUrlIndependenceTestCase(
    OfflineCompressTestCaseWithContextGenerator
):
    """
    Test that the offline manifest is independent of STATIC_URL.
    I.e. users can use the manifest with any other STATIC_URL in the future.
    """

    templates_dir = "test_static_url_independence"
    expected_hash = "b0bfc3754fd4"
    additional_test_settings = {
        "STATIC_URL": "/custom/static/url/",
        # We use ``COMPRESS_OFFLINE_CONTEXT`` generator to make sure that
        # ``STATIC_URL`` is not cached when rendering the template.
        "COMPRESS_OFFLINE_CONTEXT": (
            "compressor.tests.test_offline.static_url_context_generator"
        ),
    }

    def _test_offline(self, engine, verbosity=0):
        count, result = CompressCommand().handle_inner(
            engines=[engine], verbosity=verbosity
        )
        self.assertEqual(1, count)
        self.assertEqual([self._render_script(self.expected_hash)], result)
        self.assertEqual(self._render_template(engine), self._render_result(result))

        # Changing STATIC_URL setting doesn't break things despite that
        # offline compression was made with different STATIC_URL.
        with self.settings(STATIC_URL="/another/static/url/"):
            self.assertEqual(self._render_template(engine), self._render_result(result))


class OfflineCompressTestCaseWithContextVariableInheritance(
    OfflineTestCaseMixin, TestCase
):
    templates_dir = "test_with_context_variable_inheritance"
    expected_hash = "b8376aad1357"
    additional_test_settings = {
        "COMPRESS_OFFLINE_CONTEXT": {
            "parent_template": "base.html",
        }
    }

    def _render_result(self, result, separator="\n"):
        return "\n" + super()._render_result(result, separator)


class OfflineCompressTestCaseWithContextVariableInheritanceSuper(
    SuperMixin, OfflineTestCaseMixin, TestCase
):
    templates_dir = "test_with_context_variable_inheritance_super"
    additional_test_settings = {
        "COMPRESS_OFFLINE_CONTEXT": [
            {
                "parent_template": "base1.html",
            },
            {
                "parent_template": "base2.html",
            },
        ]
    }
    expected_hash = ["cee48db7cedc", "c877c436363a"]


class OfflineCompressTestCaseWithContextGeneratorImportError(
    OfflineTestCaseMixin, TestCase
):
    templates_dir = "test_with_context"

    def _test_offline(self, engine, verbosity=0):
        # Test that we are properly generating ImportError when
        # COMPRESS_OFFLINE_CONTEXT looks like a function but can't be imported
        # for whatever reason.

        with self.settings(COMPRESS_OFFLINE_CONTEXT="invalid_mod.invalid_func"):
            # Path with invalid module name -- ImportError:
            self.assertRaises(
                ImportError, CompressCommand().handle_inner, engines=[engine]
            )

        with self.settings(COMPRESS_OFFLINE_CONTEXT="compressor"):
            # Valid module name only without function -- AttributeError:
            self.assertRaises(
                ImportError, CompressCommand().handle_inner, engines=[engine]
            )

        with self.settings(
            COMPRESS_OFFLINE_CONTEXT="compressor.tests.invalid_function"
        ):
            # Path with invalid function name -- AttributeError:
            self.assertRaises(
                ImportError, CompressCommand().handle_inner, engines=[engine]
            )

        with self.settings(COMPRESS_OFFLINE_CONTEXT="compressor.tests.test_offline"):
            # Path without function attempts call on module -- TypeError:
            self.assertRaises(
                ImportError, CompressCommand().handle_inner, engines=[engine]
            )

        valid_path = "compressor.tests.test_offline.offline_context_generator"
        with self.settings(COMPRESS_OFFLINE_CONTEXT=valid_path):
            # Valid path to generator function -- no ImportError:

            try:
                CompressCommand().handle_inner(engines=[engine], verbosity=verbosity)
            except ImportError:
                self.fail(
                    "Valid path to offline context generator must"
                    " not raise ImportError."
                )


class OfflineCompressTestCaseErrors(OfflineTestCaseMixin, TestCase):
    templates_dir = "test_error_handling"

    def _test_offline(self, engine, verbosity=0):
        count, result = CompressCommand().handle_inner(
            engines=[engine], verbosity=verbosity
        )

        if engine == "django":
            self.assertEqual(2, count)
        else:
            # Because we use env.parse in Jinja2Parser, the engine does not
            # actually load the 'extends' and 'includes' templates, and so
            # it is unable to detect that they are missing. So all the
            # 'compress' nodes are processed correctly.
            self.assertEqual(4, count)
            self.assertEqual(engine, "jinja2")
            self.assertIn(self._render_link("187e2ce75808"), result)
            self.assertIn(self._render_link("fffafcdf428e"), result)

        self.assertIn(self._render_script("eeabdac29232"), result)
        self.assertIn(self._render_script("9a7f06880ce3"), result)


class OfflineCompressTestCaseWithError(OfflineTestCaseMixin, TestCase):
    templates_dir = "test_error_handling"
    additional_test_settings = {
        "COMPRESS_PRECOMPILERS": (("text/coffeescript", "nonexisting-binary"),)
    }

    def _test_offline(self, engine, verbosity=0):
        """
        Test that a CommandError is raised with DEBUG being False as well as
        True, as otherwise errors in configuration will never show in
        production.
        """
        with self.settings(DEBUG=True):
            self.assertRaises(
                CommandError,
                CompressCommand().handle_inner,
                engines=[engine],
                verbosity=verbosity,
            )

        with self.settings(DEBUG=False):
            self.assertRaises(
                CommandError,
                CompressCommand().handle_inner,
                engines=[engine],
                verbosity=verbosity,
            )


class OfflineCompressEmptyTag(OfflineTestCaseMixin, TestCase):
    """
    In case of a compress template tag with no content, an entry
    will be added to the manifest with an empty string as value.
    This test makes sure there is no recompression happening when
    compressor encounters such an emptystring in the manifest.
    """

    templates_dir = "basic"
    expected_hash = "822ac7501287"

    def _test_offline(self, engine, verbosity=0):
        CompressCommand().handle_inner(engines=[engine], verbosity=verbosity)
        manifest = get_offline_manifest()
        manifest[list(manifest)[0]] = ""
        self.assertEqual(self._render_template(engine), "\n")


class OfflineCompressBlockSuperBaseCompressed(OfflineTestCaseMixin, TestCase):
    template_names = ["base.html", "base2.html", "test_compressor_offline.html"]
    templates_dir = "test_block_super_base_compressed"
    expected_hash_offline = ["e4e9263fa4c0", "9cecd41a505f", "d3f749e83c81"]
    expected_hash = ["028c3fc42232", "2e9d3f5545a6", "d3f749e83c81"]
    # Block.super not supported for Jinja2 yet.
    engines = ("django",)

    def setUp(self):
        super().setUp()

        self.template_paths = []
        self.templates = []
        for template_name in self.template_names:
            template_path = os.path.join(
                settings.TEMPLATES[0]["DIRS"][0], template_name
            )
            self.template_paths.append(template_path)
            with io.open(template_path, encoding=self.CHARSET) as file_:
                template = Template(file_.read())
            self.templates.append(template)

    def _render_template(self, template, engine):
        if engine == "django":
            return template.render(Context(settings.COMPRESS_OFFLINE_CONTEXT))
        elif engine == "jinja2":
            return template.render(settings.COMPRESS_OFFLINE_CONTEXT) + "\n"
        else:
            return None

    def _test_offline(self, engine, verbosity=0):
        count, result = CompressCommand().handle_inner(
            engines=[engine], verbosity=verbosity
        )
        self.assertEqual(len(self.expected_hash), count)
        for expected_hash, template in zip(self.expected_hash_offline, self.templates):
            expected = self._render_script(expected_hash)
            self.assertIn(expected, result)
            rendered_template = self._render_template(template, engine)
            self.assertEqual(rendered_template, self._render_result([expected]))


class OfflineCompressInlineNonAsciiTestCase(OfflineTestCaseMixin, TestCase):
    templates_dir = "test_inline_non_ascii"
    additional_test_settings = {
        "COMPRESS_OFFLINE_CONTEXT": {
            "test_non_ascii_value": "\u2014",
        }
    }

    def _test_offline(self, engine, verbosity=0):
        _, result = CompressCommand().handle_inner(
            engines=[engine], verbosity=verbosity
        )
        rendered_template = self._render_template(engine)
        self.assertEqual(rendered_template, "".join(result) + "\n")


class OfflineCompressComplexTestCase(OfflineTestCaseMixin, TestCase):
    templates_dir = "test_complex"
    additional_test_settings = {
        "COMPRESS_OFFLINE_CONTEXT": {
            "condition": "OK!",
            # Django templating does not allow definition of tuples in the
            # templates.
            # Make sure this is same as test_templates_jinja2/test_complex.
            "my_names": ("js/one.js", "js/nonasc.js"),
        }
    }

    def _test_offline(self, engine, verbosity=0):
        count, result = CompressCommand().handle_inner(
            engines=[engine], verbosity=verbosity
        )
        self.assertEqual(3, count)
        self.assertEqual(
            [
                self._render_script("76a82cfab9ab"),
                self._render_script("7219642b8ab4"),
                self._render_script("567bb77b13db"),
            ],
            result,
        )
        rendered_template = self._render_template(engine)
        self.assertEqual(
            rendered_template, self._render_result([result[0], result[2]], "")
        )


class OfflineCompressExtendsRecursionTestCase(OfflineTestCaseMixin, TestCase):
    """
    Test that templates extending templates with the same name
    (e.g. admin/index.html) don't cause an infinite test_extends_recursion
    """

    templates_dir = "test_extends_recursion"

    INSTALLED_APPS = [
        "django.contrib.admin",
        "django.contrib.auth",
        "django.contrib.contenttypes",
        "django.contrib.staticfiles",
        "compressor",
    ]

    @override_settings(INSTALLED_APPS=INSTALLED_APPS)
    def _test_offline(self, engine, verbosity=0):
        count, _ = CompressCommand().handle_inner(engines=[engine], verbosity=verbosity)
        self.assertEqual(count, 1)


class OfflineCompressExtendsRelativeTestCase(
    SuperMixin, OfflineTestCaseMixin, TestCase
):
    """
    Test that templates extending templates using relative paths
    (e.g. ./base.html) are evaluated correctly
    """

    templates_dir = "test_extends_relative"
    expected_hash = "817b5defb197"


class TestCompressCommand(OfflineTestCaseMixin, TestCase):
    templates_dir = "test_compress_command"

    def _test_offline(self, engine, verbosity=0):
        raise SkipTest("Not utilized for this test case")

    def _build_expected_manifest(self, expected):
        return {k: self._render_script(v) for k, v in expected.items()}

    def test_multiple_engines(self):
        opts = {
            "force": True,
            "verbosity": 0,
        }

        call_command("compress", engines=["django"], **opts)
        manifest_django = get_offline_manifest()
        manifest_django_expected = self._build_expected_manifest(
            {
                "0fed9c02607acba22316a328075a81a74e0983ae79470daa9d3707a337623dc3": "0241107e9a9a"
            }
        )
        self.assertEqual(manifest_django, manifest_django_expected)

        call_command("compress", engines=["jinja2"], **opts)
        manifest_jinja2 = get_offline_manifest()
        manifest_jinja2_expected = self._build_expected_manifest(
            {
                "077408d23d4a829b8f88db2eadcf902b29d71b14f94018d900f38a3f8ed24c94": "5694ca83dd14"
            }
        )
        self.assertEqual(manifest_jinja2, manifest_jinja2_expected)

        call_command("compress", engines=["django", "jinja2"], **opts)
        manifest_both = get_offline_manifest()
        manifest_both_expected = self._build_expected_manifest(
            {
                "0fed9c02607acba22316a328075a81a74e0983ae79470daa9d3707a337623dc3": "0241107e9a9a",
                "077408d23d4a829b8f88db2eadcf902b29d71b14f94018d900f38a3f8ed24c94": "5694ca83dd14",
            }
        )
        self.assertEqual(manifest_both, manifest_both_expected)


class OfflineCompressTestCaseWithLazyStringAlikeUrls(
    OfflineCompressTestCaseWithContextGenerator
):
    """
    Test offline compressing with ``STATIC_URL`` and ``COMPRESS_URL`` as instances of
    *lazy string-alike objects* instead of strings.

    In particular, lazy string-alike objects that add ``SCRIPT_NAME`` WSGI param
    as URL path prefix.

    For example:

    - We've generated offline assets and deployed them with our Django project.
    - We've configured HTTP server (e.g. Nginx) to serve our app at two different URLs:
      ``http://example.com/my/app/`` and ``http://app.example.com/``.
    - Both URLs are leading to the same app, but in the first case we pass
      ``SCRIPT_NAME = /my/app/`` to WSGI app server (e.g. to uWSGI, which is *behind* Nginx).
    - Django (1.11.7, as of today) *ignores* ``SCRIPT_NAME`` when generating
      static URLs, while it uses ``SCRIPT_NAME`` when generating Django views URLs -
      see https://code.djangoproject.com/ticket/25598.
    - As a solution - we can use a lazy string-alike object instead of ``str`` for ``STATIC_URL``
      so it will know about ``SCRIPT_NAME`` and add it as a prefix every time we do any
      string operation with ``STATIC_URL``.
    - However, there are some cases when we cannot force CPython to render our lazy string
      correctly - e.g. ``some_string.replace(STATIC_URL, '...')``. So we need to do explicit
      ``str`` type cast: ``some_string.replace(str(STATIC_URL), '...')``.
    """

    templates_dir = "test_static_templatetag"
    additional_test_settings = {
        "STATIC_URL": LazyScriptNamePrefixedUrl("/static/"),
        "COMPRESS_URL": LazyScriptNamePrefixedUrl("/static/"),
        # We use ``COMPRESS_OFFLINE_CONTEXT`` generator to make sure that
        # ``STATIC_URL`` is not cached when rendering the template.
        "COMPRESS_OFFLINE_CONTEXT": (
            "compressor.tests.test_offline.static_url_context_generator"
        ),
    }
    expected_hash = "be0b1eade28b"

    def _test_offline(self, engine, verbosity=0):
        count, result = CompressCommand().handle_inner(
            engines=[engine], verbosity=verbosity
        )
        self.assertEqual(1, count)

        # Change ``SCRIPT_NAME`` WSGI param - it can be changed on every HTTP request,
        # e.g. passed via HTTP header.
        for script_name in ["", "/app/prefix/", "/another/prefix/"]:
            with script_prefix(script_name):
                self.assertEqual(
                    str(settings.STATIC_URL), script_name.rstrip("/") + "/static/"
                )

                self.assertEqual(
                    str(settings.COMPRESS_URL), script_name.rstrip("/") + "/static/"
                )

                expected_result = self._render_result(result)
                actual_result = self._render_template(engine)

                self.assertEqual(actual_result, expected_result)
                self.assertIn(str(settings.COMPRESS_URL), actual_result)
