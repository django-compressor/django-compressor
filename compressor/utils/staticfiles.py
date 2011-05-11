from __future__ import absolute_import

from django.conf import settings as django_settings
from django.core.exceptions import ImproperlyConfigured

INSTALLED = ("staticfiles" in django_settings.INSTALLED_APPS or
    "django.contrib.staticfiles" in django_settings.INSTALLED_APPS)

finders = None
settings = None

if INSTALLED:
    if "django.contrib.staticfiles" in django_settings.INSTALLED_APPS:
        from django.contrib.staticfiles import finders
        settings = django_settings
    else:
        try:
            from staticfiles import finders
            from staticfiles.conf import settings
        except ImportError:
            # Old (pre 1.0) and incompatible version of staticfiles
            INSTALLED = False

    if (INSTALLED and "compressor.finders.CompressorFinder"
            not in settings.STATICFILES_FINDERS):
        raise ImproperlyConfigured(
            "When using Django Compressor together with staticfiles, "
            "please add 'compressor.finders.CompressorFinder' to the "
            "STATICFILES_FINDERS setting.")
