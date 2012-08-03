import os
from django import VERSION as DJANGO_VERSION
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from appconf import AppConf


class CompressorConf(AppConf):
    # Main switch
    ENABLED = not settings.DEBUG
    # Allows changing verbosity from the settings.
    VERBOSE = False
    # GET variable that disables compressor e.g. "nocompress"
    DEBUG_TOGGLE = 'None'
    # the backend to use when parsing the JavaScript or Stylesheet files
    PARSER = 'compressor.parser.AutoSelectParser'
    OUTPUT_DIR = 'CACHE'
    STORAGE = 'compressor.storage.CompressorFileStorage'

    CSS_COMPRESSOR = 'compressor.css.CssCompressor'
    JS_COMPRESSOR = 'compressor.js.JsCompressor'

    URL = None
    ROOT = None

    CSS_FILTERS = ['compressor.filters.css_default.CssAbsoluteFilter']
    CSS_HASHING_METHOD = 'mtime'

    JS_FILTERS = ['compressor.filters.jsmin.JSMinFilter']
    PRECOMPILERS = (
        # ('text/coffeescript', 'coffee --compile --stdio'),
        # ('text/less', 'lessc {infile} {outfile}'),
        # ('text/x-sass', 'sass {infile} {outfile}'),
        # ('text/x-scss', 'sass --scss {infile} {outfile}'),
    )
    CLOSURE_COMPILER_BINARY = 'java -jar compiler.jar'
    CLOSURE_COMPILER_ARGUMENTS = ''
    CSSTIDY_BINARY = 'csstidy'
    CSSTIDY_ARGUMENTS = '--template=highest'
    YUI_BINARY = 'java -jar yuicompressor.jar'
    YUI_CSS_ARGUMENTS = ''
    YUI_JS_ARGUMENTS = ''
    DATA_URI_MAX_SIZE = 1024

    # the cache backend to use
    CACHE_BACKEND = None
    # the dotted path to the function that creates the cache key
    CACHE_KEY_FUNCTION = 'compressor.cache.simple_cachekey'
    # rebuilds the cache every 30 days if nothing has changed.
    REBUILD_TIMEOUT = 60 * 60 * 24 * 30  # 30 days
    # the upper bound on how long any compression should take to be generated
    # (used against dog piling, should be a lot smaller than REBUILD_TIMEOUT
    MINT_DELAY = 30  # seconds
    # check for file changes only after a delay
    MTIME_DELAY = 10  # seconds
    # enables the offline cache -- also filled by the compress command
    OFFLINE = False
    # invalidates the offline cache after one year
    OFFLINE_TIMEOUT = 60 * 60 * 24 * 365  # 1 year
    # The context to be used when compressing the files "offline"
    OFFLINE_CONTEXT = {}
    # The name of the manifest file (e.g. filename.ext)
    OFFLINE_MANIFEST = 'manifest.json'
    # The Context to be used when TemplateFilter is used
    TEMPLATE_FILTER_CONTEXT = {}

    class Meta:
        prefix = 'compress'

    def configure_root(self, value):
        if value is None:
            value = getattr(settings, 'STATIC_ROOT', None)
            if not value:
                value = settings.MEDIA_ROOT
        if value is None:
            raise ImproperlyConfigured("COMPRESS_ROOT setting must be set")
        return os.path.normcase(os.path.abspath(value))

    def configure_url(self, value):
        # Uses Django 1.3's STATIC_URL by default or falls back to MEDIA_URL
        if value is None:
            value = getattr(settings, 'STATIC_URL', None)
            if not value:
                value = settings.MEDIA_URL
        if not value.endswith('/'):
            raise ImproperlyConfigured("URL settings (e.g. COMPRESS_URL) "
                                       "must have a trailing slash")
        return value

    def configure_cache_backend(self, value):
        if value is None:
            # If we are on Django 1.3 AND using the new CACHES setting...
            if DJANGO_VERSION[:2] >= (1, 3) and hasattr(settings, 'CACHES'):
                value = 'default'
            else:
                # falling back to the old CACHE_BACKEND setting
                value = getattr(settings, 'CACHE_BACKEND', None)
                if not value:
                    raise ImproperlyConfigured("Please specify a cache "
                                               "backend in your settings.")
        return value

    def configure_offline_context(self, value):
        if not value:
            value = {'MEDIA_URL': settings.MEDIA_URL}
            # Adds the 1.3 STATIC_URL setting to the context if available
            if getattr(settings, 'STATIC_URL', None):
                value['STATIC_URL'] = settings.STATIC_URL
        return value

    def configure_template_filter_context(self, value):
        if not value:
            value = {'MEDIA_URL': settings.MEDIA_URL}
            # Adds the 1.3 STATIC_URL setting to the context if available
            if getattr(settings, 'STATIC_URL', None):
                value['STATIC_URL'] = settings.STATIC_URL
        return value

    def configure_precompilers(self, value):
        if not isinstance(value, (list, tuple)):
            raise ImproperlyConfigured("The COMPRESS_PRECOMPILERS setting "
                                       "must be a list or tuple. Check for "
                                       "missing commas.")
        return value
