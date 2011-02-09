import os
import sys

from django.core.exceptions import ImproperlyConfigured
from django.utils.encoding import smart_str
from django.utils.hashcompat import sha_constructor

from compressor.cache import cache
from compressor.conf import settings
from compressor.exceptions import FilterError

from shlex import split as cmd_split

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

# Taken from Django 1.3-beta1 and before that from Python 2.7 with permission from/by the original author.
def _resolve_name(name, package, level):
   """Return the absolute name of the module to be imported."""
   if not hasattr(package, 'rindex'):
       raise ValueError("'package' not set to a string")
   dot = len(package)
   for x in xrange(level, 1, -1):
       try:
           dot = package.rindex('.', 0, dot)
       except ValueError:
           raise ValueError("attempted relative import beyond top-level "
                             "package")
   return "%s.%s" % (package[:dot], name)

def import_module(name, package=None):
   """Import a module.

   The 'package' argument is required when performing a relative import. It
   specifies the package to use as the anchor point from which to resolve the
   relative import to an absolute import.

   """
   if name.startswith('.'):
       if not package:
           raise TypeError("relative imports require the 'package' argument")
       level = 0
       for character in name:
           if character != '.':
               break
           level += 1
       name = _resolve_name(name[level:], package, level)
   __import__(name)
   return sys.modules[name]


class AppSettings(object):
   """
   An app setting object to be used for handling app setting defaults
   gracefully and providing a nice API for them. Say you have an app
   called ``myapp`` and want to define a few defaults, and refer to the
   defaults easily in the apps code. Add a ``settings.py`` to your app::

       from path.to.utils import AppSettings

       class MyAppSettings(AppSettings):
           SETTING_1 = "one"
           SETTING_2 = (
               "two",
           )

   Then initialize the setting with the correct prefix in the location of
   of your choice, e.g. ``conf.py`` of the app module::

       settings = MyAppSettings(prefix="MYAPP")

   The ``MyAppSettings`` instance will automatically look at Django's
   global setting to determine each of the settings and respect the
   provided ``prefix``. E.g. adding this to your site's ``settings.py``
   will set the ``SETTING_1`` setting accordingly::

       MYAPP_SETTING_1 = "uno"

   Usage
   -----

   Instead of using ``from django.conf import settings`` as you would
   usually do, you can switch to using your apps own settings module
   to access the app settings::

       from myapp.conf import settings

       print myapp_settings.MYAPP_SETTING_1

   ``AppSettings`` instances also work as pass-throughs for other
   global settings that aren't related to the app. For example the
   following code is perfectly valid::

       from myapp.conf import settings

       if "myapp" in settings.INSTALLED_APPS:
           print "yay, myapp is installed!"

   Custom handling
   ---------------

   Each of the settings can be individually configured with callbacks.
   For example, in case a value of a setting depends on other settings
   or other dependencies. The following example sets one setting to a
   different value depending on a global setting::

       from django.conf import settings

       class MyCustomAppSettings(AppSettings):
           ENABLED = True

           def configure_enabled(self, value):
               return value and not self.DEBUG

       custom_settings = MyCustomAppSettings("MYAPP")

   The value of ``custom_settings.MYAPP_ENABLED`` will vary depending on the
   value of the global ``DEBUG`` setting.

   Each of the app settings can be customized by providing
   a method ``configure_<lower_setting_name>`` that takes the default
   value as defined in the class attributes as the only parameter.
   The method needs to return the value to be use for the setting in
   question.
   """
   def __dir__(self):
       return sorted(list(set(self.__dict__.keys() + dir(settings))))

   __members__ = lambda self: self.__dir__()

   def __getattr__(self, name):
       if name.startswith(self._prefix):
           raise AttributeError("%r object has no attribute %r" %
                                (self.__class__.__name__, name))
       try:
           return getattr(settings, name)
       except AttributeError:
           raise

   def __init__(self, prefix):
       defaults = filter(self.issetting, inspect.getmembers(self.__class__))
       self._prefix = prefix
       for name, value in defaults:
           prefixed_name = "%s_%s" % (self._prefix.upper(), name.upper())
           value = getattr(settings, prefixed_name, value)
           try:
               callback = getattr(self, "configure_%s" % name.lower())
               if callable(callback):
                   callback_value = callback(value)
                   if callback_value is not None:
                       value = callback_value
           except AttributeError:
               pass
           delattr(self.__class__, name)
           setattr(self, prefixed_name, value)

   def issetting(self, setting):
       return setting[0] == setting[0].upper()
