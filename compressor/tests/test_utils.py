from django.test import TestCase
from django.test.utils import override_settings
from django.conf import settings
import django.contrib.staticfiles.finders
import django

import compressor.utils.staticfiles
from compressor.exceptions import FilterError
from compressor.utils import get_class

from imp import reload


def get_apps_without_staticfiles(apps):
    return [x for x in apps if x != 'django.contrib.staticfiles']


def get_apps_with_staticfiles_using_appconfig(apps):
    return get_apps_without_staticfiles(apps) + [
        'django.contrib.staticfiles.apps.StaticFilesConfig',
    ]


class StaticFilesTestCase(TestCase):

    def test_has_finders_from_staticfiles(self):
        self.assertTrue(compressor.utils.staticfiles.finders is
                        django.contrib.staticfiles.finders)

    def test_has_finders_from_staticfiles_if_configured_per_appconfig(self):
        apps = get_apps_with_staticfiles_using_appconfig(
            settings.INSTALLED_APPS)
        try:
            with override_settings(INSTALLED_APPS=apps):
                reload(compressor.utils.staticfiles)
                self.assertTrue(compressor.utils.staticfiles.finders is
                                django.contrib.staticfiles.finders)
        finally:
            reload(compressor.utils.staticfiles)

    def test_finders_is_none_if_staticfiles_is_not_installed(self):
        apps = get_apps_without_staticfiles(settings.INSTALLED_APPS)
        try:
            with override_settings(INSTALLED_APPS=apps):
                reload(compressor.utils.staticfiles)
                self.assertTrue(compressor.utils.staticfiles.finders is None)
        finally:
            reload(compressor.utils.staticfiles)


class TestGetClass(TestCase):

    def test_get_class_import_exception(self):
        with self.assertRaises(FilterError) as context:
            get_class('common.uglify.JsUglifySourcemapCompressor')

        self.assertTrue(('Failed to import common.uglify.JsUglifySourcemapCompressor. '
                         'ImportError is: No module named' in str(context.exception)))
