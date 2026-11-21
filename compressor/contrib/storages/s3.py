from django import VERSION as DJANGO_VERSION
from django.core.files import File
from django.core.files.storage import get_storage_class

try:
    from storages.backends.s3boto3 import S3Boto3Storage
    S3BaseStorage = S3Boto3Storage
except ImportError:
    try:
        from storages.backends.s3boto import S3BotoStorage
        S3BaseStorage = S3BotoStorage
    except ImportError:
        raise ImportError(
            "django-storages with S3 backends is required to use S3 storage with django-compressor"
        )

try:
    from io import BytesIO as StringIO
except ImportError:
    try:
        from cStringIO import StringIO
    except ImportError:
        from StringIO import StringIO

from compressor.contrib.storages.utils import create_content_copy


class CachedS3BotoStorage(S3BaseStorage):
    """
    S3 storage backend that saves the files locally too.

    This is the base implementation that can be extended for specific
    use cases like static files or media files.
    """
    def __init__(self, *args, **kwargs):
        super(CachedS3BotoStorage, self).__init__(*args, **kwargs)
        self.local_storage = get_storage_class(
            "compressor.storage.CompressorFileStorage")() 

    def save(self, name, content):
        # Create a safe copy of the content that preserves the original file position
        content_copy = create_content_copy(content)

        # Save to S3
        name = super(CachedS3BotoStorage, self).save(name, content)

        # Save locally
        if hasattr(content_copy, 'seek'):
            content_copy.seek(0)
        self.local_storage._save(name, content_copy)

        return name


class CachedS3BotoStaticStorage(CachedS3BotoStorage):
    """
    S3 storage backend for static files that saves the files locally too.
    """
    def __init__(self, *args, **kwargs):
        # Set S3 settings specifically for static files if they exist
        location = kwargs.pop('location', None)
        try:
            from django.conf import settings
            kwargs.setdefault('location', location or getattr(settings, 'AWS_STATIC_LOCATION', 
                                                        getattr(settings, 'STATIC_ROOT', '')))
            kwargs.setdefault('bucket_name', getattr(settings, 'AWS_STATIC_BUCKET_NAME', 
                                                getattr(settings, 'AWS_STORAGE_BUCKET_NAME', None)))
            kwargs.setdefault('querystring_auth', getattr(settings, 'AWS_STATIC_QUERYSTRING_AUTH', False))
            kwargs.setdefault('custom_domain', getattr(settings, 'AWS_STATIC_CUSTOM_DOMAIN', 
                                                 getattr(settings, 'AWS_S3_CUSTOM_DOMAIN', None)))
            kwargs.setdefault('file_overwrite', getattr(settings, 'AWS_STATIC_FILE_OVERWRITE', True))
            kwargs.setdefault('object_parameters', getattr(settings, 'AWS_STATIC_OBJECT_PARAMETERS', {
                'CacheControl': 'max-age=31536000',  # 1 year
            }))
        except ImportError:
            pass

        super(CachedS3BotoStaticStorage, self).__init__(*args, **kwargs)


class CachedS3BotoMediaStorage(CachedS3BotoStorage):
    """
    S3 storage backend for media files that saves the files locally too.
    """
    def __init__(self, *args, **kwargs):
        # Set S3 settings specifically for media files if they exist
        location = kwargs.pop('location', None)
        try:
            from django.conf import settings
            kwargs.setdefault('location', location or getattr(settings, 'AWS_MEDIA_LOCATION', 
                                                        getattr(settings, 'MEDIA_ROOT', '')))
            kwargs.setdefault('bucket_name', getattr(settings, 'AWS_MEDIA_BUCKET_NAME', 
                                                getattr(settings, 'AWS_STORAGE_BUCKET_NAME', None)))
            kwargs.setdefault('querystring_auth', getattr(settings, 'AWS_MEDIA_QUERYSTRING_AUTH', True))
            kwargs.setdefault('custom_domain', getattr(settings, 'AWS_MEDIA_CUSTOM_DOMAIN', 
                                                 getattr(settings, 'AWS_S3_CUSTOM_DOMAIN', None)))
            kwargs.setdefault('file_overwrite', getattr(settings, 'AWS_MEDIA_FILE_OVERWRITE', False))
        except ImportError:
            pass

        super(CachedS3BotoMediaStorage, self).__init__(*args, **kwargs)
