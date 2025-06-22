from django.core.files import File
from django.core.files.storage import get_storage_class

try:
    from storages.backends.gcloud import GoogleCloudStorage
except ImportError:
    raise ImportError(
        "django-storages with GCloud backend is required to use Google Cloud Storage with django-compressor"
    )

try:
    from io import BytesIO as StringIO
except ImportError:
    try:
        from cStringIO import StringIO
    except ImportError:
        from StringIO import StringIO

from compressor.contrib.storages.utils import create_content_copy


class CachedGoogleCloudStorage(GoogleCloudStorage):
    """
    Google Cloud Storage backend that saves the files locally too.
    """
    def __init__(self, *args, **kwargs):
        super(CachedGoogleCloudStorage, self).__init__(*args, **kwargs)
        self.local_storage = get_storage_class(
            "compressor.storage.CompressorFileStorage")() 

    def save(self, name, content):
        # Create a safe copy of the content that preserves the original file position
        content_copy = create_content_copy(content)

        # Save to GCS
        name = super(CachedGoogleCloudStorage, self).save(name, content)

        # Save locally
        if hasattr(content_copy, 'seek'):
            content_copy.seek(0)
        self.local_storage._save(name, content_copy)

        return name


class CachedGoogleCloudStaticStorage(CachedGoogleCloudStorage):
    """
    Google Cloud Storage backend for static files that saves the files locally too.
    """
    def __init__(self, *args, **kwargs):
        # Set GCS settings specifically for static files if they exist
        location = kwargs.pop('location', None)
        try:
            from django.conf import settings
            kwargs.setdefault('location', location or getattr(settings, 'GS_STATIC_LOCATION', ''))
            kwargs.setdefault('bucket_name', getattr(settings, 'GS_STATIC_BUCKET_NAME', 
                                                getattr(settings, 'GS_BUCKET_NAME', None)))
            kwargs.setdefault('custom_endpoint', getattr(settings, 'GS_STATIC_CUSTOM_ENDPOINT', 
                                                 getattr(settings, 'GS_CUSTOM_ENDPOINT', None)))
            kwargs.setdefault('default_acl', getattr(settings, 'GS_STATIC_DEFAULT_ACL', 'publicRead'))
            kwargs.setdefault('file_overwrite', getattr(settings, 'GS_STATIC_FILE_OVERWRITE', True))
            kwargs.setdefault('cache_control', getattr(settings, 'GS_STATIC_CACHE_CONTROL', 'max-age=86400'))
        except ImportError:
            pass

        super(CachedGoogleCloudStaticStorage, self).__init__(*args, **kwargs)
