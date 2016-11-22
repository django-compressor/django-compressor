from django.conf import settings
from django.test import TestCase
from django.test.utils import override_settings

from compressor.exceptions import OfflineGenerationError
from compressor.management.commands.compress import Command as CompressCommand
import compressor.tests.test_offline


module_dict = globals()


for key in dir(compressor.tests.test_offline):
    value = getattr(compressor.tests.test_offline, key)
    if (
        key not in ('OfflineCompressStaticTemplateTagTestCase', 'TestCompressCommand') and
        # Find all the TestCase subclasess except the TestCase itself
        isinstance(value, type) and issubclass(value, TestCase) and value is not TestCase
    ):
        new_class = type(key, (value,), {})
        module_dict[key] = override_settings(COMPRESS_OFFLINE_USE_URL_PLACEHOLDER=True)(new_class)


@override_settings(COMPRESS_OFFLINE_USE_URL_PLACEHOLDER=True)
class OfflineCompressStaticTemplateTagTestCase(
    compressor.tests.test_offline.OfflineCompressStaticTemplateTagTestCase
):
    def _test_offline(self, engine):
        count, result = CompressCommand().compress(
            log=self.log, verbosity=self.verbosity, engine=engine
        )
        self.assertEqual(1, count)
        self.assertEqual([
            '<script type="text/javascript" src="/static/CACHE/js/{}.js"></script>'.format(
                self.expected_hash
            )
        ], result)
        self.assertEqual(self._render_template(engine), result[0] + '\n')

        # Changing settings.STATIC_URL doesn't affect the "offline decompression"
        with self.settings(STATIC_URL='/another/static/'):
            self.assertEqual(self._render_template(engine), result[0] + '\n')

        # But without settings.COMPRESS_OFFLINE_USE_URL_PLACEHOLDER it fails
        with self.settings(
            STATIC_URL='/another/static/', COMPRESS_OFFLINE_USE_URL_PLACEHOLDER=False
        ):
            with self.assertRaises(OfflineGenerationError):
                self._render_template(engine)


@override_settings(COMPRESS_OFFLINE_USE_URL_PLACEHOLDER=True)
class TestCompressCommand(compressor.tests.test_offline.TestCompressCommand):
    def _build_expected_manifest(self, expected):
        return {
            k: '<script type="text/javascript" src="{}CACHE/js/{}.js"></script>'.format(
               settings.COMPRESS_URL_PLACEHOLDER, v
            ) for k, v in expected.items()
        }
