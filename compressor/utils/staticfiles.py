from __future__ import absolute_import, unicode_literals

import django
from django.core.exceptions import ImproperlyConfigured

from compressor.conf import settings


def staticfiles_installed():
    if django.VERSION < (1, 7):
        return "django.contrib.staticfiles" in settings.INSTALLED_APPS
    from django.apps import apps
    return apps.is_installed("django.contrib.staticfiles")


if staticfiles_installed():
    from django.contrib.staticfiles import finders  # noqa

    if ("compressor.finders.CompressorFinder"
            not in settings.STATICFILES_FINDERS):
        raise ImproperlyConfigured(
            "When using Django Compressor together with staticfiles, "
            "please add 'compressor.finders.CompressorFinder' to the "
            "STATICFILES_FINDERS setting.")
else:
    finders = None  # noqa
