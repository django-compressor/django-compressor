# noqa
import six

try:
    from django.utils.encoding import force_text, force_bytes
    from django.utils.encoding import smart_text, smart_bytes
except ImportError:
    # django < 1.4.2
    from django.utils.encoding import force_unicode as force_text
    from django.utils.encoding import force_str as force_bytes
    from django.utils.encoding import smart_unicode as smart_text
    from django.utils.encoding import smart_str as smart_bytes


try:
    from django.utils import unittest
except ImportError:
    import unittest2 as unittest


if six.PY3:
    # there is an 'io' module in python 2.6+, but io.StringIO does not
    # accept regular strings, just unicode objects
    from io import StringIO
else:
    try:
        from cStringIO import StringIO
    except ImportError:
        from StringIO import StringIO

try:
    from urllib.request import url2pathname
except ImportError:
    from urllib import url2pathname

