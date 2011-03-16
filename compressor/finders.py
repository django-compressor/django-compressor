from django.core.exceptions import ImproperlyConfigured

from compressor.conf import settings
from compressor.storage import CompressorFileStorage

if "django.contrib.staticfiles" in settings.INSTALLED_APPS:
    from django.contrib.staticfiles.finders import BaseStorageFinder
elif "staticfiles" in settings.INSTALLED_APPS:
    from staticfiles.finders import BaseStorageFinder
else:
    raise ImproperlyConfigured("When using the compressor staticfiles finder"
                               "either django.contrib.staticfiles or the "
                               "standalone version django-staticfiles needs "
                               "to be installed.")

class CompressorFinder(BaseStorageFinder):
    """
    A staticfiles finder that looks in COMPRESS_ROOT
    for compressed files, to be used during development
    with staticfiles development file server or during
    deployment.
    """
    storage = CompressorFileStorage
