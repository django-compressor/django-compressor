from django.core.exceptions import ImproperlyConfigured

from compressor.conf import settings
from compressor.storage import CompressorFileStorage
from compressor.utils import get_staticfiles_finders

finders = get_staticfiles_finders()
if finders is None:
    raise ImproperlyConfigured("When using the compressor staticfiles finder"
                               "either django.contrib.staticfiles or the "
                               "standalone version django-staticfiles needs "
                               "to be installed.")


class CompressorFinder(finders.BaseStorageFinder):
    """
    A staticfiles finder that looks in COMPRESS_ROOT
    for compressed files, to be used during development
    with staticfiles development file server or during
    deployment.
    """
    storage = CompressorFileStorage
