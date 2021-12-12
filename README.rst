Django Compressor
=================

.. image:: https://codecov.io/github/django-compressor/django-compressor/coverage.svg?branch=develop
    :target: https://codecov.io/github/django-compressor/django-compressor?branch=develop

.. image:: https://img.shields.io/pypi/v/django_compressor.svg
        :target: https://pypi.python.org/pypi/django_compressor

.. image:: https://img.shields.io/github/workflow/status/django-compressor/django-compressor/CI?label=CI&logo=github&branch=develop
    :alt: Build Status
    :target: https://github.com/django-compressor/django-compressor/actions?query=workflow%3ACI

Django Compressor processes, combines and minifies linked and inline
Javascript or CSS in a Django template into cacheable static files.

It supports compilers such as coffeescript, LESS and SASS and is
extensible by custom processing steps.

How it works
------------
In your templates, all HTML code between the tags ``{% compress js/css %}`` and
``{% endcompress %}`` is parsed and searched for CSS or JS. These styles and
scripts are subsequently processed with optional, configurable compilers and
filters.

The default filter for CSS rewrites paths to static files to be absolute.
Both Javascript and CSS files are by default concatenated and minified.

As the final step the template tag outputs a ``<script>`` or ``<link>``
tag pointing to the optimized file. Alternatively it can also
inline the resulting content into the original template directly.

Since the file name is dependent on the content, these files can be given
a far future expiration date without worrying about stale browser caches.

For increased performance, the concatenation and compressing process
can also be run once manually outside of the request/response cycle by using
the Django management command ``manage.py compress``.

Configurability & Extensibility
-------------------------------

Django Compressor is highly configurable and extensible. The HTML parsing
is done using lxml_ or if it's not available Python's built-in HTMLParser by
default. As an alternative Django Compressor provides a BeautifulSoup_ and a
html5lib_ based parser, as well as an abstract base class that makes it easy to
write a custom parser.

Django Compressor also comes with built-in support for
`YUI CSS and JS`_ compressor, `yUglify CSS and JS`_ compressor, Google's
`Closure Compiler`_, a Python port of Douglas Crockford's JSmin_, a Python port
of the YUI CSS Compressor csscompressor_ and a filter to convert (some) images into
`data URIs`_.

If your setup requires a different compressor or other post-processing
tool it will be fairly easy to implement a custom filter. Simply extend
from one of the available base classes.

More documentation about the usage and settings of Django Compressor can be
found on `django-compressor.readthedocs.org`_.

The source code for Django Compressor can be found and contributed to on
`github.com/django-compressor/django-compressor`_. There you can also file tickets.

The in-development version of Django Compressor can be installed with
``pip install git+https://github.com/django-compressor/django-compressor.git``

.. _BeautifulSoup: http://www.crummy.com/software/BeautifulSoup/
.. _lxml: http://lxml.de/
.. _html5lib: https://github.com/html5lib/html5lib-python
.. _YUI CSS and JS: http://developer.yahoo.com/yui/compressor/
.. _yUglify CSS and JS: https://github.com/yui/yuglify
.. _Closure Compiler: http://code.google.com/closure/compiler/
.. _JSMin: http://www.crockford.com/javascript/jsmin.html
.. _csscompressor: https://github.com/sprymix/csscompressor
.. _data URIs: http://en.wikipedia.org/wiki/Data_URI_scheme
.. _django-compressor.readthedocs.org: https://django-compressor.readthedocs.io/en/latest/
.. _github.com/django-compressor/django-compressor: https://github.com/django-compressor/django-compressor
