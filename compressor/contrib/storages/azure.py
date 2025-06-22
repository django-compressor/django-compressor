from django.core.files import File
from django.core.files.storage import get_storage_class

try:
    from storages.backends.azure_storage import AzureStorage
except ImportError:
    raise ImportError(
        "django-storages with Azure backend is required to use Azure Storage with django-compressor"
    )

try:
    from io import BytesIO as StringIO
except ImportError:
    try:
        from cStringIO import StringIO
    except ImportError:
        from StringIO import StringIO

from compressor.contrib.storages.utils import create_content_copy


class CachedAzureStorage(AzureStorage):
    """
    Azure Storage backend that saves the files locally too.
    """
    def __init__(self, *args, **kwargs):
        super(CachedAzureStorage, self).__init__(*args, **kwargs)
        self.local_storage = get_storage_class(
            "compressor.storage.CompressorFileStorage")() 

    def save(self, name, content):
        # Create a safe copy of the content that preserves the original file position
        content_copy = create_content_copy(content)

        # Save to Azure
        name = super(CachedAzureStorage, self).save(name, content)

        # Save locally
        if hasattr(content_copy, 'seek'):
            content_copy.seek(0)
        self.local_storage._save(name, content_copy)

        return name


class CachedAzureStaticStorage(CachedAzureStorage):
    """
    Azure Storage backend for static files that saves the files locally too.
    """
    def __init__(self, *args, **kwargs):
        # Set Azure settings specifically for static files if they exist
        try:
            from django.conf import settings
            kwargs.setdefault('azure_container', getattr(settings, 'AZURE_STATIC_CONTAINER', 
                                                   getattr(settings, 'AZURE_CONTAINER', '')))
            kwargs.setdefault('expiration_secs', getattr(settings, 'AZURE_STATIC_EXPIRATION_TIMEOUT',
                                                    getattr(settings, 'AZURE_URL_EXPIRATION_SECS', None)))
        except ImportError:
            pass

        super(CachedAzureStaticStorage, self).__init__(*args, **kwargs)
