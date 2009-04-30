from django.core.exceptions import ImproperlyConfigured
from django.conf import settings


MEDIA_URL = getattr(settings, 'COMPRESS_URL', settings.MEDIA_URL)
MEDIA_ROOT = getattr(settings, 'COMPRESS_ROOT', settings.MEDIA_ROOT)
OUTPUT_DIR = getattr(settings, 'COMPRESS_OUTPUT_DIR', 'CACHE')

COMPRESS = getattr(settings, 'COMPRESS', not settings.DEBUG)
COMPRESS_CSS_FILTERS = getattr(settings, 'COMPRESS_CSS_FILTERS', [])
COMPRESS_JS_FILTERS = getattr(settings, 'COMPRESS_JS_FILTERS', ['compressor.filters.jsmin.JSMinFilter'])

if COMPRESS_CSS_FILTERS is None:
    COMPRESS_CSS_FILTERS = []

if COMPRESS_JS_FILTERS is None:
    COMPRESS_JS_FILTERS = []
