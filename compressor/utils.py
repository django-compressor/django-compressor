import os
from django.core.exceptions import ImproperlyConfigured
from django.utils.encoding import smart_str
from django.utils.hashcompat import sha_constructor
from django.utils.importlib import import_module

from compressor.cache import cache
from compressor.conf import settings
from compressor.exceptions import FilterError

try:
    any = any
except NameError:
    def any(seq):
        for item in seq:
            if item:
                return True
        return False

def get_hexdigest(plaintext):
    return sha_constructor(plaintext).hexdigest()

def get_mtime_cachekey(filename):
    return "django_compressor.mtime.%s" % filename

def get_offline_cachekey(source):
    return ("django_compressor.offline.%s"
            % get_hexdigest("".join(smart_str(s) for s in source)))

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


def walk(root, topdown=True, onerror=None, followlinks=False):
    """
    A version of os.walk that can follow symlinks for Python < 2.6
    """
    for dirpath, dirnames, filenames in os.walk(root, topdown, onerror):
        yield (dirpath, dirnames, filenames)
        if followlinks:
            for d in dirnames:
                p = os.path.join(dirpath, d)
                if os.path.islink(p):
                    for link_dirpath, link_dirnames, link_filenames in walk(p):
                        yield (link_dirpath, link_dirnames, link_filenames)


def find_template_loader(loader):
    if isinstance(loader, (tuple, list)):
        loader, args = loader[0], loader[1:]
    else:
        args = []
    if isinstance(loader, basestring):
        module, attr = loader.rsplit('.', 1)
        try:
            mod = import_module(module)
        except ImportError, e:
            raise ImproperlyConfigured(
                'Error importing template source loader %s: "%s"' % (loader, e))
        try:
            TemplateLoader = getattr(mod, attr)
        except AttributeError, e:
            raise ImproperlyConfigured(
                'Error importing template source loader %s: "%s"' % (loader, e))

        if hasattr(TemplateLoader, 'load_template_source'):
            func = TemplateLoader(*args)
        else:
            # Try loading module the old way - string is full path to callable
            if args:
                raise ImproperlyConfigured(
                    "Error importing template source loader %s - can't "
                    "pass arguments to function-based loader." % loader)
            func = TemplateLoader
        if not func.is_usable:
            import warnings
            warnings.warn(
                "Your TEMPLATE_LOADERS setting includes %r, but your Python "
                "installation doesn't support that type of template loading. "
                "Consider removing that line from TEMPLATE_LOADERS." % loader)
            return None
        else:
            return func
    else:
        raise ImproperlyConfigured('Loader does not define a "load_template" '
                                   'callable template source loader')
