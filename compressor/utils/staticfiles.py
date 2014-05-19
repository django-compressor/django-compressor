from __future__ import absolute_import, unicode_literals

from django.core.exceptions import ImproperlyConfigured

from compressor.conf import settings

INSTALLED = ("staticfiles" in settings.INSTALLED_APPS or
             "django.contrib.staticfiles" in settings.INSTALLED_APPS)

if INSTALLED:
    if "django.contrib.staticfiles" in settings.INSTALLED_APPS:
        from django.contrib.staticfiles import finders
    else:
        try:
            from staticfiles import finders  # noqa
        except ImportError:
            # Old (pre 1.0) and incompatible version of staticfiles
            INSTALLED = False

    if (INSTALLED and "compressor.finders.CompressorFinder"
            not in settings.STATICFILES_FINDERS):
        raise ImproperlyConfigured(
            "When using Django Compressor together with staticfiles, "
            "please add 'compressor.finders.CompressorFinder' to the "
            "STATICFILES_FINDERS setting.")
else:
    finders = None  # noqa
