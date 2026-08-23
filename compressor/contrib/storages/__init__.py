# Django Compressor contrib storage backends

# Import utility functions
from compressor.contrib.storages.utils import create_content_copy

# Import storage backends to make them available through the module
try:
    from compressor.contrib.storages.s3 import CachedS3BotoStorage, CachedS3BotoStaticStorage
except ImportError:
    pass

try:
    from compressor.contrib.storages.gcloud import CachedGoogleCloudStorage, CachedGoogleCloudStaticStorage
except ImportError:
    pass

try:
    from compressor.contrib.storages.azure import CachedAzureStorage, CachedAzureStaticStorage
except ImportError:
    pass
