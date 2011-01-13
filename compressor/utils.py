import os
from shlex import split as cmd_split

from compressor.cache import cache
from compressor.conf import settings
from compressor.exceptions import FilterError

def get_hexdigest(plaintext):
    try:
        import hashlib
        return hashlib.sha1(plaintext).hexdigest()
    except ImportError:
        import sha
        return sha.new(plaintext).hexdigest()

def get_mtime_cachekey(filename):
    return "django_compressor.mtime.%s" % filename

def get_mtime(filename):
    if settings.MTIME_DELAY:
        key = get_mtime_cachekey(filename)
        mtime = cache.get(key)
        if mtime is None:
            mtime = os.path.getmtime(filename)
            cache.set(key, mtime, settings.MTIME_DELAY)
        return mtime
    return os.path.getmtime(filename)

def get_hashed_mtime(filename, length=12):
    filename = os.path.realpath(filename)
    mtime = str(int(get_mtime(filename)))
    return get_hexdigest(mtime)[:length]


def get_class(class_string, exception=FilterError):
    """
    Convert a string version of a function name to the callable object.
    """

    if not hasattr(class_string, '__bases__'):

        try:
            class_string = class_string.encode('ascii')
            mod_name, class_name = get_mod_func(class_string)
            if class_name != '':
                cls = getattr(__import__(mod_name, {}, {}, ['']), class_name)
        except (ImportError, AttributeError):
            raise exception('Failed to import filter %s' % class_string)

    return cls


def get_mod_func(callback):
    """
    Converts 'django.views.news.stories.story_detail' to
    ('django.views.news.stories', 'story_detail')
    """

    try:
        dot = callback.rindex('.')
    except ValueError:
        return callback, ''
    return callback[:dot], callback[dot+1:]
