from django import VERSION as DJANGO_VERSION
from django.core.files import File
from django.core.files.storage import get_storage_class
from storages.backends.s3boto3 import S3Boto3Storage
from django_compressor.storage import CompressorFileStorage

try:
    from io import BytesIO, StringIO
except ImportError:
    from StringIO import StringIO
    BytesIO = StringIO

class CachedS3Boto3Storage(S3Boto3Storage):
    """
    S3 storage backend that saves compressed files locally for django-compressor.

    Supports Django versions >= 1.4 and handles gzipped content correctly.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.local_storage = get_storage_class("django_compressor.storage.CompressorFileStorage")()
        self.bucket_name = self._get_setting('AWS_STATIC_BUCKET_NAME', getattr(self, 'bucket_name', None))
        self.querystring_auth = self._get_setting('AWS_STATIC_QUERYSTRING_AUTH', False)
        self.location = self._get_setting('AWS_STATIC_LOCATION', '')
        self.headers = self._get_setting('AWS_STATIC_HEADERS', {
            'Cache-Control': 'max-age=31536000',
        })
        self.gzip = self._get_setting('AWS_STATIC_IS_GZIPPED', True)

    def _get_setting(self, name, default):
        from django.conf import settings
        return getattr(settings, name, default)

    def save(self, name, content):
        # Store original file pointer position
        original_pos = content.tell() if hasattr(content, 'tell') else 0

        # Save to S3 (may gzip content)
        name = super().save(name, content)

        # Reset file pointer for local storage
        content.seek(original_pos)

        # Create a new File object to avoid passing gzipped content
        if isinstance(content.file, (StringIO, BytesIO)):
            data = File(BytesIO(content.read()), name=name)
            if DJANGO_VERSION < (1, 5):
                data.seek(0, 2)  # SEEK_END
                data._size = data.tell()
                data.seek(0)
        else:
            data = File(content.file, name=name)

        # Save to local storage for compressor
        self.local_storage._save(name, data)

        return name
