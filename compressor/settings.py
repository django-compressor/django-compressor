import os

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
    OUTPUT_DIR = 'cache'
    STORAGE = 'compressor.storage.CompressorFileStorage'

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

    def configure_url(self, value):
        # Uses the 1.3 STATIC_URL setting by default
        url = getattr(settings, 'STATIC_URL', value)
        # Check for emptyness since STATIC_URL can be None and ''
        if url:
            # Then on to extensive testing
            root = getattr(settings, 'STATIC_ROOT', None)
            if not root:
                raise ImproperlyConfigured('The COMPRESS_ROOT setting (or its '
                                           'fallback STATIC_ROOT) must be set.')
            # In case staticfiles is used, make sure COMPRESS_URL can be used
            # by checking if the the FileSystemFinder is installed, and if is
            # checking if COMPRESS_ROOT is in STATICFILES_DIRS to allow finding
            # compressed files.
            if ("staticfiles" in self.INSTALLED_APPS or
                    "django.contrib.staticfiles" in self.INSTALLED_APPS):
                try:
                    from staticfiles.conf import settings as staticfiles_settings
                    finders = staticfiles_settings.STATICFILES_FINDERS
                    standalone = True
                except ImportError:
                    finders = []
                    standalone = False
                if not finders:
                    finders = getattr(settings, 'STATICFILES_FINDERS', [])
                if ("django.contrib.staticfiles.finders.FileSystemFinder" not in finders and
                        "staticfiles.finders.FileSystemFinder" not in finders):
                    raise ImproperlyConfigured(
                        'Please enable the FileSystemFinder finder of the '
                        'staticfiles app to use it with django_compressor.')
                abs_paths = []
                output_path = os.path.join(root, self.COMPRESS_OUTPUT_DIR)
                for path in getattr(settings, 'STATICFILES_DIRS', []):
                    if isinstance(path, tuple) or isinstance(path, list): # stupid Python 2.4
                        path = path[1] # in case the STATICFILES_DIRS setting has a prefix
                    abs_paths.append(os.path.abspath(path))
                if os.path.abspath(output_path) not in abs_paths:
                    extension = ((self.COMPRESS_OUTPUT_DIR, output_path),)
                    if standalone:
                        from staticfiles.conf import settings as staticfiles_settings
                        staticfiles_settings.STATICFILES_DIRS += extension
                    else:
                        settings.STATICFILES_DIRS += extension
        else:
            # Fallback to good ol' times of ambiguity
            url, root = settings.MEDIA_URL, settings.MEDIA_ROOT

        if not url.endswith('/'):
            raise ImproperlyConfigured('The URL settings (e.g. COMPRESS_URL) '
                                       'must have a trailing slash.')
        self.COMPRESS_ROOT = root
        return url

    def configure_cache_backend(self, value):
        if value is None:
            # If we are on Django 1.3 AND using the new CACHES setting...
            if getattr(settings, "CACHES", None):
                return "default"
            # fallback for people still using the old CACHE_BACKEND setting
            return settings.CACHE_BACKEND
        return value

    def configure_offline_context(self, value):
        if value:
            value = {
                'MEDIA_URL': settings.MEDIA_URL,
            }
            # Adds the 1.3 STATIC_URL setting to the context if available
            if getattr(settings, 'STATIC_URL', None):
                value['STATIC_URL'] = settings.STATIC_URL
        return value
