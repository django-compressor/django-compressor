from django.core.files.storage import FileSystemStorage
from django.core.files.storage import get_storage_class
from django.utils.functional import LazyObject

from compressor.conf import settings

class CompressorFileStorage(FileSystemStorage):
    """
    Standard file system storage for files handled by django-compressor.

    The defaults for ``location`` and ``base_url`` are ``COMPRESS_ROOT`` and
    ``COMPRESS_URL``.

    """
    def __init__(self, location=None, base_url=None, *args, **kwargs):
        if location is None:
            location = settings.MEDIA_ROOT
        if base_url is None:
            base_url = settings.MEDIA_URL
        super(CompressorFileStorage, self).__init__(location, base_url,
                                                    *args, **kwargs)

class DefaultStorage(LazyObject):
    def _setup(self):
        self._wrapped = get_storage_class(settings.STORAGE)()

default_storage = DefaultStorage()
