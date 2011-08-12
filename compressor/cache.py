import os
import socket
import time

from django.core.cache import get_cache
from django.utils.encoding import smart_str
from django.utils.hashcompat import md5_constructor
from django.utils.importlib import import_module

from compressor.conf import settings
from compressor.utils import get_mod_func


def get_hexdigest(plaintext, length=None):
    digest = md5_constructor(smart_str(plaintext)).hexdigest()
    if length:
        return digest[:length]
    return digest

def simple_cachekey(key):
    return 'django_compressor.%s' % smart_str(key)

def socket_cachekey(key):
    return "django_compressor.%s.%s" % (socket.gethostname(), smart_str(key))

try:
    mod_name, func_name = get_mod_func(settings.COMPRESS_CACHE_KEY_FUNCTION)
    get_cachekey = getattr(import_module(mod_name), func_name)
except (AttributeError, ImportError), e:
    raise ImportError("Couldn't import cache key function %s: %s" %
                      (settings.COMPRESS_CACHE_KEY_FUNCTION, e))

def get_mtime_cachekey(filename):
    return get_cachekey("mtime.%s" % get_hexdigest(filename))


def get_offline_cachekey(source):
    to_hexdigest = [smart_str(getattr(s, 's', s)) for s in source]
    return get_cachekey("offline.%s" % get_hexdigest(to_hexdigest))


def get_templatetag_cachekey(compressor, mode, kind):
    return get_cachekey(
        "templatetag.%s.%s.%s" % (compressor.cachekey, mode, kind))


def get_mtime(filename):
    if settings.COMPRESS_MTIME_DELAY:
        key = get_mtime_cachekey(filename)
        mtime = cache.get(key)
        if mtime is None:
            mtime = os.path.getmtime(filename)
            cache.set(key, mtime, settings.COMPRESS_MTIME_DELAY)
        return mtime
    return os.path.getmtime(filename)


def get_hashed_mtime(filename, length=12):
    try:
        filename = os.path.realpath(filename)
        mtime = str(int(get_mtime(filename)))
    except OSError:
        return None
    return get_hexdigest(mtime, length)


def cache_get(key):
    packed_val = cache.get(key)
    if packed_val is None:
        return None
    val, refresh_time, refreshed = packed_val
    if (time.time() > refresh_time) and not refreshed:
        # Store the stale value while the cache
        # revalidates for another MINT_DELAY seconds.
        cache_set(key, val, refreshed=True,
            timeout=settings.COMPRESS_MINT_DELAY)
        return None
    return val


def cache_set(key, val, refreshed=False,
        timeout=settings.COMPRESS_REBUILD_TIMEOUT):
    refresh_time = timeout + time.time()
    real_timeout = timeout + settings.COMPRESS_MINT_DELAY
    packed_val = (val, refresh_time, refreshed)
    return cache.set(key, packed_val, real_timeout)


cache = get_cache(settings.COMPRESS_CACHE_BACKEND)
