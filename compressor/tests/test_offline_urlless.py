from django.conf import settings
from django.test import TestCase
from django.test.utils import override_settings

from compressor.exceptions import OfflineGenerationError
from compressor.management.commands.compress import Command as CompressCommand
import compressor.tests.test_offline


module_dict = globals()


class UrllessTestCaseMixin(object):
    compress_url = settings.COMPRESS_URL_PLACEHOLDER

    def _render_result(self, result, placeholder='\n'):
        rendered_result = super(UrllessTestCaseMixin, self)._render_result(result, placeholder)
        return rendered_result.replace(settings.COMPRESS_URL_PLACEHOLDER, settings.COMPRESS_URL)


# Reuse tests from compressor.tests.test_offline.* with enabled settings.COMPRESS_OFFLINE_URLLESS
for key in dir(compressor.tests.test_offline):
    value = getattr(compressor.tests.test_offline, key)
    # Skip the test because we customize it below
    if key == 'OfflineCompressStaticTemplateTagTestCase':
        continue
    # Find all the TestCase sub-classes except the TestCase itself
    if isinstance(value, type) and issubclass(value, TestCase) and value is not TestCase:
        # Create new test class inherited from the one from compressor.tests.test_offline.*
        new_class = type(key, (UrllessTestCaseMixin, value,), {})
        # Override settings.COMPRESS_OFFLINE_URLLESS
        new_class = override_settings(COMPRESS_OFFLINE_URLLESS=True)(new_class)
        # Assign it to the current module
        module_dict[key] = new_class


@override_settings(COMPRESS_OFFLINE_URLLESS=True)
class OfflineCompressStaticTemplateTagTestCase(
    UrllessTestCaseMixin, compressor.tests.test_offline.OfflineCompressStaticTemplateTagTestCase
):
    def _test_offline(self, engine):
        count, result = CompressCommand().compress(
            log=self.log, verbosity=self.verbosity, engine=engine
        )
        self.assertEqual(1, count)
        self.assertEqual([self._render_script(self.expected_hash)], result)
        self.assertEqual(self._render_template(engine), self._render_result(result))

        # Changing settings.STATIC_URL doesn't affect the "offline decompression"
        with self.settings(STATIC_URL='/another/static/'):
            self.assertEqual(self._render_template(engine), self._render_result(result))

        # But without settings.COMPRESS_OFFLINE_URLLESS it fails
        with self.settings(STATIC_URL='/another/static/', COMPRESS_OFFLINE_URLLESS=False):
            with self.assertRaises(OfflineGenerationError):
                self._render_template(engine)
