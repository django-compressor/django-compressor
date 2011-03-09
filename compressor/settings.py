import os

from django import VERSION as DJANGO_VERSION
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from compressor.utils import AppSettings

class CompressorSettings(AppSettings):
    # Main switch
    ENABLED = not settings.DEBUG
    # Allows changing verbosity from the settings.
    VERBOSE = False
    # the backend to use when parsing the JavaScript or Stylesheet files
    PARSER = 'compressor.parser.BeautifulSoupParser'
    OUTPUT_DIR = 'CACHE'
    STORAGE = 'compressor.storage.CompressorFileStorage'

    CSS_COMPRESSOR = "compressor.css.CssCompressor"
    JS_COMPRESSOR = "compressor.js.JsCompressor"

    URL = None
    ROOT = None

    CSS_FILTERS = ['compressor.filters.css_default.CssAbsoluteFilter']
    JS_FILTERS = ['compressor.filters.jsmin.JSMinFilter']

    LESSC_BINARY = LESSC_BINARY = 'lessc'
    CLOSURE_COMPILER_BINARY = 'java -jar compiler.jar'
    CLOSURE_COMPILER_ARGUMENTS = ''
    CSSTIDY_BINARY = 'csstidy'
    CSSTIDY_ARGUMENTS = '--template=highest'
    YUI_BINARY = 'java -jar yuicompressor.jar'
    YUI_CSS_ARGUMENTS = ''
    YUI_JS_ARGUMENTS = 'COMPRESS_YUI_JS_ARGUMENTS'
    DATA_URI_MIN_SIZE = 1024
    # the cache backend to use
    CACHE_BACKEND = None
    # rebuilds the cache every 30 days if nothing has changed.
    REBUILD_TIMEOUT = 60 * 60 * 24 * 30 # 30 days
    # the upper bound on how long any compression should take to be generated
    # (used against dog piling, should be a lot smaller than REBUILD_TIMEOUT
    MINT_DELAY = 30 # seconds
    # check for file changes only after a delay
    MTIME_DELAY = 10 # seconds
    # enables the offline cache -- a cache that is filled by the compress management command
    OFFLINE = False
    # invalidates the offline cache after one year
    OFFLINE_TIMEOUT = 60 * 60 * 24 * 365 # 1 year
    # The context to be used when compressing the files "offline"
    OFFLINE_CONTEXT = {}

    def configure_enabled(self, value):
        return value or getattr(settings, 'COMPRESS', value)

    def configure_root(self, value):
        if value is None:
            value = getattr(settings, 'STATIC_ROOT', None)
            if not value:
                value = settings.MEDIA_ROOT
        if not value:
            raise ImproperlyConfigured("The COMPRESS_ROOT setting must be set.")
        # In case staticfiles is used, make sure the FileSystemFinder is
        # installed, and if it is, check if COMPRESS_ROOT is listed in
        # STATICFILES_DIRS to allow finding compressed files
        staticfiles_settings = None
        if "staticfiles" in self.INSTALLED_APPS:
            from staticfiles.conf import settings as staticfiles_settings
        elif "django.contrib.staticfiles" in self.INSTALLED_APPS:
            staticfiles_settings = settings
        if staticfiles_settings is not None:
            if ("compressor.finders.CompressorFinder" not in
                    staticfiles_settings.STATICFILES_FINDERS):
                raise ImproperlyConfigured(
                    "When using django_compressor together with staticfiles, "
                    "please add 'compressor.finders.CompressorFinder' to the "
                    "STATICFILES_FINDERS setting.")
        return value

    def configure_url(self, value):
        # Falls back to the 1.3 STATIC_URL setting by default or falls back to MEDIA_URL
        if value is None:
            value = getattr(settings, 'STATIC_URL', None)
            if not value:
                value = settings.MEDIA_URL
        if not value.endswith('/'):
            raise ImproperlyConfigured('The URL settings (e.g. COMPRESS_URL) '
                                       'must have a trailing slash.')
        return value

    def configure_cache_backend(self, value):
        if value is None:
            # If we are on Django 1.3 AND using the new CACHES setting...
            if DJANGO_VERSION[:2] >= (1, 3) and hasattr(settings, "CACHES"):
                value = "default"
            else:
                # falling back to the old CACHE_BACKEND setting
                value = getattr(settings, "CACHE_BACKEND", None)
                if not value:
                    raise ImproperlyConfigured(
                        "Please specify a cache backend in your settings.")
        return value

    def configure_offline_context(self, value):
        if not value:
            value = {
                'MEDIA_URL': settings.MEDIA_URL,
            }
            # Adds the 1.3 STATIC_URL setting to the context if available
            if getattr(settings, 'STATIC_URL', None):
                value['STATIC_URL'] = settings.STATIC_URL
        return value
