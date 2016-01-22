from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase
from compressor.cache import get_offline_manifest


class TestCompressCommand(TestCase):
    def test_multiple_engines(self):
        call_command('compress', force=True, engine="django")
        manifest_django = get_offline_manifest()
        
        call_command('compress', force=True, engine="jinja2")
        manifest_jinja2 = get_offline_manifest()
        
        call_command('compress', force=True, engine="django, jinja2")
        manifest_both = get_offline_manifest()
        
        manifest_both_expected = {}
        manifest_both_expected.update(manifest_django)
        manifest_both_expected.update(manifest_jinja2)
        
        self.assertTrue(manifest_django)
        self.assertTrue(manifest_jinja2)
        self.assertEqual(manifest_both, manifest_both_expected)