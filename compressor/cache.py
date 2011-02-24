import os
import socket

from django.core.cache import get_cache
from django.utils.encoding import smart_str
from django.utils.hashcompat import sha_constructor

from compressor.conf import settings

def get_hexdigest(plaintext):
    return sha_constructor(plaintext).hexdigest()

def get_mtime_cachekey(filename):
    return "django_compressor.mtime.%s.%s" % (socket.gethostname(),
                                              get_hexdigest(filename))

def get_offline_cachekey(source):
    return ("django_compressor.offline.%s.%s" %
            (socket.gethostname(),
             get_hexdigest("".join(smart_str(s) for s in source))))

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
    filename = os.path.realpath(filename)
    mtime = str(int(get_mtime(filename)))
    return get_hexdigest(mtime)[:length]

cache = get_cache(settings.COMPRESS_CACHE_BACKEND)
