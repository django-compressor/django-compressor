import errno
import gzip
from os import path
from datetime import datetime

from django.core.files.storage import FileSystemStorage, get_storage_class
from django.utils.functional import LazyObject, SimpleLazyObject

from compressor.conf import settings


class CompressorFileStorage(FileSystemStorage):
    """
    Standard file system storage for files handled by django-compressor.

    The defaults for ``location`` and ``base_url`` are ``COMPRESS_ROOT`` and
    ``COMPRESS_URL``.

    """
    def __init__(self, location=None, base_url=None, *args, **kwargs):
        if location is None:
            location = settings.COMPRESS_ROOT
        if base_url is None:
            base_url = settings.COMPRESS_URL
        super(CompressorFileStorage, self).__init__(location, base_url,
                                                    *args, **kwargs)

    def accessed_time(self, name):
        return datetime.fromtimestamp(path.getatime(self.path(name)))

    def created_time(self, name):
        return datetime.fromtimestamp(path.getctime(self.path(name)))

    def modified_time(self, name):
        return datetime.fromtimestamp(path.getmtime(self.path(name)))

    def get_available_name(self, name):
        """
        Deletes the given file if it exists.
        """
        if self.exists(name):
            self.delete(name)
        return name

    def delete(self, name):
        """
        Handle deletion race condition present in Django prior to 1.4
        https://code.djangoproject.com/ticket/16108
        """
        try:
            super(CompressorFileStorage, self).delete(name)
        except OSError, e:
            if e.errno != errno.ENOENT:
                raise


compressor_file_storage = SimpleLazyObject(
    lambda: get_storage_class('compressor.storage.CompressorFileStorage')())


class GzipCompressorFileStorage(CompressorFileStorage):
    """
    The standard compressor file system storage that gzips storage files
    additionally to the usual files.
    """
    def save(self, filename, content):
        filename = super(GzipCompressorFileStorage, self).save(filename, content)
        out = gzip.open(u'%s.gz' % self.path(filename), 'wb')
        out.writelines(open(self.path(filename), 'rb'))
        out.close()
        return filename


class DefaultStorage(LazyObject):
    def _setup(self):
        self._wrapped = get_storage_class(settings.COMPRESS_STORAGE)()

default_storage = DefaultStorage()
