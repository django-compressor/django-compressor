from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

# Main switch
ENABLED = getattr(settings, 'COMPRESS', not settings.DEBUG)

# Uses the 1.3 STATIC_URL setting by default
URL = getattr(settings, 'COMPRESS_URL', getattr(settings, 'STATIC_URL', None))
# Check for emptyness since STATIC_URL can be None and ''
if URL:
    # Then on to extensive testing
    ROOT = getattr(settings, 'COMPRESS_ROOT', getattr(settings, 'STATIC_ROOT', None))
    if not ROOT:
        raise ImproperlyConfigured('The COMPRESS_ROOT setting (or its '
                                   'fallback STATIC_ROOT) must be set.')
    # In case staticfiles is used make sure COMPRESS_URL can be used
    # by checking if the the FileSystemFinder is installed, and if is
    # checking if COMPRESS_ROOT is in STATICFILES_DIRS to allow finding
    # compressed files.
    if ("staticfiles" in settings.INSTALLED_APPS or
            "django.contrib.staticfiles" in settings.INSTALLED_APPS):
        finders = getattr(settings, 'STATICFILES_FINDERS', [])
        if ("django.contrib.staticfiles.finders.FileSystemFinder" not in finders and
                "staticfiles.finders.FileSystemFinder" not in finders):
            raise ImproperlyConfigured('Please enable the FileSystemFinder '
                                       'finder of the staticfiles app to '
                                       'use it with django_compressor.')
        abs_paths = []
        for path in getattr(settings, 'STATICFILES_DIRS', []):
            if isinstance(path, tuple) or isinstance(path, list): # stupid Python 2.4
                path = path[1] # in case the STATICFILES_DIRS setting has a prefix
            abs_paths.append(os.path.abspath(path))
        if os.path.abspath(ROOT) not in abs_paths:
            raise ImproperlyConfigured('Please add COMPRESS_ROOT to the '
                                       'STATICFILES_DIRS setting when using the '
                                       'staticfiles app.')
else:
    # Fallback to good ol' time of double meaning
    URL, ROOT = settings.MEDIA_URL, settings.MEDIA_ROOT

if not URL.endswith('/'):
    raise ImproperlyConfigured('The URL settings (e.g. COMPRESS_URL) '
                               'must have a trailing slash.')

OUTPUT_DIR = getattr(settings, 'COMPRESS_OUTPUT_DIR', 'cache')
STORAGE = getattr(settings, 'COMPRESS_STORAGE', 'compressor.storage.CompressorFileStorage')

CSS_FILTERS = getattr(settings, 'COMPRESS_CSS_FILTERS', ['compressor.filters.css_default.CssAbsoluteFilter'])
JS_FILTERS = getattr(settings, 'COMPRESS_JS_FILTERS', ['compressor.filters.jsmin.JSMinFilter'])

if CSS_FILTERS is None:
    CSS_FILTERS = []

if JS_FILTERS is None:
    JS_FILTERS = []

LESSC_BINARY = LESSC_BINARY = getattr(settings, 'COMPRESS_LESSC_BINARY', 'lessc')

CLOSURE_COMPILER_BINARY = getattr(settings, 'COMPRESS_CLOSURE_COMPILER_BINARY', 'java -jar compiler.jar')
CLOSURE_COMPILER_ARGUMENTS = getattr(settings, 'COMPRESS_CLOSURE_COMPILER_ARGUMENTS', '')

CSSTIDY_BINARY = getattr(settings, 'CSSTIDY_BINARY',
    getattr(settings, 'COMPRESS_CSSTIDY_BINARY', 'csstidy'))
CSSTIDY_ARGUMENTS = getattr(settings, 'CSSTIDY_ARGUMENTS',
    getattr(settings, 'COMPRESS_CSSTIDY_ARGUMENTS', '--template=highest'))

YUI_BINARY = getattr(settings, 'COMPRESS_YUI_BINARY', 'java -jar yuicompressor.jar')
YUI_CSS_ARGUMENTS = getattr(settings, 'COMPRESS_YUI_CSS_ARGUMENTS', '')
YUI_JS_ARGUMENTS = getattr(settings, 'COMPRESS_YUI_JS_ARGUMENTS', '')

DATA_URI_MIN_SIZE = getattr(settings, 'COMPRESS_DATA_URI_MIN_SIZE', 1024)

# rebuilds the cache every 30 days if nothing has changed.
REBUILD_TIMEOUT = getattr(settings, 'COMPRESS_REBUILD_TIMEOUT', 60 * 60 * 24 * 30) # 30 days

# the upper bound on how long any compression should take to be generated
# (used against dog piling, should be a lot smaller than REBUILD_TIMEOUT
MINT_DELAY = getattr(settings, 'COMPRESS_MINT_DELAY', 30) # 30 seconds

# check for file changes only after a delay (in seconds, disabled by default)
MTIME_DELAY = getattr(settings, 'COMPRESS_MTIME_DELAY', None)

# the backend to use when parsing the JavaScript or Stylesheet files
PARSER = getattr(settings, 'COMPRESS_PARSER', 'compressor.parser.BeautifulSoupParser')

# Allows changing verbosity from the settings.
VERBOSE = getattr(settings, "COMPRESS_VERBOSE", False)

# the cache backend to use
CACHE_BACKEND = getattr(settings, 'COMPRESS_CACHE_BACKEND', None)
if CACHE_BACKEND is None:
    # If we are on Django 1.3 AND using the new CACHES setting...
    if getattr(settings, "CACHES", None):
        CACHE_BACKEND = "default"
    else:
        # fallback for people still using the old CACHE_BACKEND setting
        CACHE_BACKEND = settings.CACHE_BACKEND

# enables the offline cache -- a cache that is filled by the compress management command
OFFLINE = getattr(settings, 'COMPRESS_OFFLINE', False)

# invalidates the offline cache after one year
OFFLINE_TIMEOUT = getattr(settings, 'COMPRESS_OFFLINE_TIMEOUT', 60 * 60 * 24 * 365) # 1 year

# The context to be used when compressing the files "offline"
OFFLINE_CONTEXT = getattr(settings, 'COMPRESS_OFFLINE_CONTEXT', {})
if not OFFLINE_CONTEXT:
    OFFLINE_CONTEXT = {
        'MEDIA_URL': settings.MEDIA_URL,
    }
    # Adds the 1.3 STATIC_URL setting to the context if available
    if getattr(settings, 'STATIC_URL', None):
        OFFLINE_CONTEXT['STATIC_URL'] = settings.STATIC_URL
