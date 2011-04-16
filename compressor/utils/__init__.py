# -*- coding: utf-8 -*-
import os
import re
import sys
from inspect import getmembers
from shlex import split as cmd_split

from django.conf import settings

from compressor.exceptions import FilterError

try:
    any = any

except NameError:

    def any(seq):
        for item in seq:
            if item:
                return True
        return False


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
            pass
        else:
            return cls
    raise exception('Failed to import %s' % class_string)


def get_mod_func(callback):
    """
    Converts 'django.views.news.stories.story_detail' to
    ('django.views.news.stories', 'story_detail')
    """
    try:
        dot = callback.rindex('.')
    except ValueError:
        return callback, ''
    return callback[:dot], callback[dot + 1:]


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


# Taken from Django 1.3 and before that from Python 2.7
# with permission from the original author.
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
        return getattr(settings, name)

    def __setattr__(self, name, value):
        super(AppSettings, self).__setattr__(name, value)
        if name in dir(settings):
            setattr(settings, name, value)

    def __init__(self, prefix):
        super(AppSettings, self).__setattr__('_prefix', prefix)
        for name, value in filter(self.issetting, getmembers(self.__class__)):
            prefixed_name = "%s_%s" % (prefix.upper(), name.upper())
            value = getattr(settings, prefixed_name, value)
            callback = getattr(self, "configure_%s" % name.lower(), None)
            if callable(callback):
                value = callback(value)
            delattr(self.__class__, name)
            setattr(self, prefixed_name, value)

    def issetting(self, (name, value)):
        return name == name.upper()


class cached_property(object):
    """Property descriptor that caches the return value
    of the get function.

    *Examples*

    .. code-block:: python

         @cached_property
         def connection(self):
              return Connection()

         @connection.setter  # Prepares stored value
         def connection(self, value):
              if value is None:
                    raise TypeError("Connection must be a connection")
              return value

         @connection.deleter
         def connection(self, value):
              # Additional action to do at del(self.attr)
              if value is not None:
                    print("Connection %r deleted" % (value, ))
    """
    def __init__(self, fget=None, fset=None, fdel=None, doc=None):
        self.__get = fget
        self.__set = fset
        self.__del = fdel
        self.__doc__ = doc or fget.__doc__
        self.__name__ = fget.__name__
        self.__module__ = fget.__module__

    def __get__(self, obj, type=None):
        if obj is None:
            return self
        try:
            return obj.__dict__[self.__name__]
        except KeyError:
            value = obj.__dict__[self.__name__] = self.__get(obj)
            return value

    def __set__(self, obj, value):
        if obj is None:
            return self
        if self.__set is not None:
            value = self.__set(obj, value)
        obj.__dict__[self.__name__] = value

    def __delete__(self, obj):
        if obj is None:
            return self
        try:
            value = obj.__dict__.pop(self.__name__)
        except KeyError:
            pass
        else:
            if self.__del is not None:
                self.__del(obj, value)

    def setter(self, fset):
        return self.__class__(self.__get, fset, self.__del)

    def deleter(self, fdel):
        return self.__class__(self.__get, self.__set, fdel)


"""Advanced string formatting for Python >= 2.4.

An implementation of the advanced string formatting (PEP 3101).

Author: Florent Xicluna
"""

if hasattr(str, 'partition'):
    def partition(s, sep):
        return s.partition(sep)
else:   # Python 2.4
    def partition(s, sep):
        try:
            left, right = s.split(sep, 1)
        except ValueError:
            return s, '', ''
        return left, sep, right

_format_str_re = re.compile(
    r'((?<!{)(?:{{)+'                       # '{{'
    r'|(?:}})+(?!})'                        # '}}
    r'|{(?:[^{](?:[^{}]+|{[^{}]*})*)?})'    # replacement field
)
_format_sub_re = re.compile(r'({[^{}]*})')  # nested replacement field
_format_spec_re = re.compile(
    r'((?:[^{}]?[<>=^])?)'      # alignment
    r'([-+ ]?)'                 # sign
    r'(#?)' r'(\d*)' r'(,?)'    # base prefix, minimal width, thousands sep
    r'((?:\.\d+)?)'             # precision
    r'(.?)$'                    # type
)
_field_part_re = re.compile(
    r'(?:(\[)|\.|^)'            # start or '.' or '['
    r'((?(1)[^]]*|[^.[]*))'     # part
    r'(?(1)(?:\]|$)([^.[]+)?)'  # ']' and invalid tail
)

if hasattr(re, '__version__'):
    _format_str_sub = _format_str_re.sub
else:
    # Python 2.4 fails to preserve the Unicode type
    def _format_str_sub(repl, s):
        if isinstance(s, unicode):
            return unicode(_format_str_re.sub(repl, s))
        return _format_str_re.sub(repl, s)

if hasattr(int, '__index__'):
    def _is_integer(value):
        return hasattr(value, '__index__')
else:   # Python 2.4
    def _is_integer(value):
        return isinstance(value, (int, long))


def _strformat(value, format_spec=""):
    """Internal string formatter.

    It implements the Format Specification Mini-Language.
    """
    m = _format_spec_re.match(str(format_spec))
    if not m:
        raise ValueError('Invalid conversion specification')
    align, sign, prefix, width, comma, precision, conversion = m.groups()
    is_numeric = hasattr(value, '__float__')
    is_integer = is_numeric and _is_integer(value)
    if prefix and not is_integer:
        raise ValueError('Alternate form (#) not allowed in %s format '
                         'specifier' % (is_numeric and 'float' or 'string'))
    if is_numeric and conversion == 'n':
        # Default to 'd' for ints and 'g' for floats
        conversion = is_integer and 'd' or 'g'
    elif sign:
        if not is_numeric:
            raise ValueError("Sign not allowed in string format specifier")
        if conversion == 'c':
            raise ValueError("Sign not allowed with integer "
                             "format specifier 'c'")
    if comma:
        # TODO: thousand separator
        pass
    try:
        if ((is_numeric and conversion == 's') or
            (not is_integer and conversion in set('cdoxX'))):
            raise ValueError
        if conversion == 'c':
            conversion = 's'
            value = chr(value % 256)
        rv = ('%' + prefix + precision + (conversion or 's')) % (value,)
    except ValueError:
        raise ValueError("Unknown format code %r for object of type %r" %
                         (conversion, value.__class__.__name__))
    if sign not in '-' and value >= 0:
        # sign in (' ', '+')
        rv = sign + rv
    if width:
        zero = (width[0] == '0')
        width = int(width)
    else:
        zero = False
        width = 0
    # Fastpath when alignment is not required
    if width <= len(rv):
        if not is_numeric and (align == '=' or (zero and not align)):
            raise ValueError("'=' alignment not allowed in string format "
                             "specifier")
        return rv
    fill, align = align[:-1], align[-1:]
    if not fill:
        fill = zero and '0' or ' '
    if align == '^':
        padding = width - len(rv)
        # tweak the formatting if the padding is odd
        if padding % 2:
            rv += fill
        rv = rv.center(width, fill)
    elif align == '=' or (zero and not align):
        if not is_numeric:
            raise ValueError("'=' alignment not allowed in string format "
                             "specifier")
        if value < 0 or sign not in '-':
            rv = rv[0] + rv[1:].rjust(width - 1, fill)
        else:
            rv = rv.rjust(width, fill)
    elif align in ('>', '=') or (is_numeric and not align):
        # numeric value right aligned by default
        rv = rv.rjust(width, fill)
    else:
        rv = rv.ljust(width, fill)
    return rv


def _format_field(value, parts, conv, spec, want_bytes=False):
    """Format a replacement field."""
    for k, part, _ in parts:
        if k:
            if part.isdigit():
                value = value[int(part)]
            else:
                value = value[part]
        else:
            value = getattr(value, part)
    if conv:
        value = ((conv == 'r') and '%r' or '%s') % (value,)
    if hasattr(value, '__format__'):
        value = value.__format__(spec)
    elif hasattr(value, 'strftime') and spec:
        value = value.strftime(str(spec))
    else:
        value = _strformat(value, spec)
    if want_bytes and isinstance(value, unicode):
        return str(value)
    return value


class FormattableString(object):
    """Class which implements method format().

    The method format() behaves like str.format() in python 2.6+.

    >>> FormattableString(u'{a:5}').format(a=42)
    ... # Same as u'{a:5}'.format(a=42)
    u'   42'

    """

    __slots__ = '_index', '_kwords', '_nested', '_string', 'format_string'

    def __init__(self, format_string):
        self._index = 0
        self._kwords = {}
        self._nested = {}

        self.format_string = format_string
        self._string = _format_str_sub(self._prepare, format_string)

    def __eq__(self, other):
        if isinstance(other, FormattableString):
            return self.format_string == other.format_string
        # Compare equal with the original string.
        return self.format_string == other

    def _prepare(self, match):
        # Called for each replacement field.
        part = match.group(0)
        if part[0] == part[-1]:
            # '{{' or '}}'
            assert part == part[0] * len(part)
            return part[:len(part) // 2]
        repl = part[1:-1]
        field, _, format_spec = partition(repl, ':')
        literal, sep, conversion = partition(field, '!')
        if sep and not conversion:
            raise ValueError("end of format while looking for "
                             "conversion specifier")
        if len(conversion) > 1:
            raise ValueError("expected ':' after format specifier")
        if conversion not in 'rsa':
            raise ValueError("Unknown conversion specifier %s" %
                             str(conversion))
        name_parts = _field_part_re.findall(literal)
        if literal[:1] in '.[':
            # Auto-numbering
            if self._index is None:
                raise ValueError("cannot switch from manual field "
                                 "specification to automatic field numbering")
            name = str(self._index)
            self._index += 1
            if not literal:
                del name_parts[0]
        else:
            name = name_parts.pop(0)[1]
            if name.isdigit() and self._index is not None:
                # Manual specification
                if self._index:
                    raise ValueError("cannot switch from automatic field "
                                     "numbering to manual field specification")
                self._index = None
        empty_attribute = False
        for k, v, tail in name_parts:
            if not v:
                empty_attribute = True
            if tail:
                raise ValueError("Only '.' or '[' may follow ']' "
                                 "in format field specifier")
        if name_parts and k == '[' and not literal[-1] == ']':
            raise ValueError("Missing ']' in format string")
        if empty_attribute:
            raise ValueError("Empty attribute in format string")
        if '{' in format_spec:
            format_spec = _format_sub_re.sub(self._prepare, format_spec)
            rv = (name_parts, conversion, format_spec)
            self._nested.setdefault(name, []).append(rv)
        else:
            rv = (name_parts, conversion, format_spec)
            self._kwords.setdefault(name, []).append(rv)
        return r'%%(%s)s' % id(rv)

    def format(self, *args, **kwargs):
        """Same as str.format() and unicode.format() in Python 2.6+."""
        if args:
            kwargs.update(dict((str(i), value)
                               for (i, value) in enumerate(args)))
        # Encode arguments to ASCII, if format string is bytes
        want_bytes = isinstance(self._string, str)
        params = {}
        for name, items in self._kwords.items():
            value = kwargs[name]
            for item in items:
                parts, conv, spec = item
                params[str(id(item))] = _format_field(value, parts, conv, spec,
                                                      want_bytes)
        for name, items in self._nested.items():
            value = kwargs[name]
            for item in items:
                parts, conv, spec = item
                spec = spec % params
                params[str(id(item))] = _format_field(value, parts, conv, spec,
                                                      want_bytes)
        return self._string % params
