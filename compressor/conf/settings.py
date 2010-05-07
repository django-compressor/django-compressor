from django.core.exceptions import ImproperlyConfigured
from django.conf import settings


MEDIA_URL = getattr(settings, 'COMPRESS_URL', settings.MEDIA_URL)
MEDIA_ROOT = getattr(settings, 'COMPRESS_ROOT', settings.MEDIA_ROOT)
OUTPUT_DIR = getattr(settings, 'COMPRESS_OUTPUT_DIR', 'CACHE')
STORAGE = getattr(settings, 'COMPRESS_STORAGE', 'compressor.storage.CompressorFileStorage')

COMPRESS = getattr(settings, 'COMPRESS', not settings.DEBUG)
COMPRESS_CSS_FILTERS = getattr(settings, 'COMPRESS_CSS_FILTERS', [])
COMPRESS_JS_FILTERS = getattr(settings, 'COMPRESS_JS_FILTERS', ['compressor.filters.jsmin.JSMinFilter'])

COMPRESS_LESSC_BINARY = getattr(settings, 'COMPRESS_LESSC_BINARY', 'lessc')

if COMPRESS_CSS_FILTERS is None:
    COMPRESS_CSS_FILTERS = []

if COMPRESS_JS_FILTERS is None:
    COMPRESS_JS_FILTERS = []

DATA_URI_MIN_SIZE = getattr(settings, 'COMPRESS_DATA_URI_MIN_SIZE', 1024)

# rebuilds the cache every 30 days if nothing has changed.
REBUILD_TIMEOUT = getattr(settings, 'COMPRESS_REBUILD_TIMEOUT', 2592000) # 30 days

# the upper bound on how long any compression should take to be generated
# (used against dog piling, should be a lot smaller than REBUILD_TIMEOUT
MINT_DELAY = getattr(settings, 'COMPRESS_MINT_DELAY', 30) # 30 seconds
