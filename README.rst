Django Compressor
=================

Django Compressor can concatenate and then compress linked and inline Javascript
& CSS into cached single static files.

The compress template tag parses all the HTML in between `{% compress js/css %}`
and `{% endcompress %}` and looks for linked stylesheets or JS. It then
concatenates the files and inline styles/scripts and (optionally) compresses them
using one or more of the provided or your own custom filters.

The concatenation and compressing process can also be started using the
Django management command `manage.py compress`.

HTML Parsing
-------------

The HTML parsing backend is also configurable and defaults to `BeautifulSoup`.
An abstract base class makes it easy to write a custom parser. An alternative
`lxml` parser already comes with django-compress.

CSS Compression
---------------

By default CSS is concatenated and paths to media are rewritten and fitted with
a cache busting timestamp.

Django Compressor also comes with a built in support for CSS Tidy,
YUI CSS minification and even a filter to convert (some) images into `data:`
URIs.

JS Compression
--------------

By default Javascript will be concatenated and minified using a port of
Douglas Crockford's jsmin.

But there's also support for YUI compression and the Google's Closure Compiler.

More
----

* More documentation about the usage and settings of django-compressor can be found
  on `readthedocs.org/docs/django_compressor/en/latest`_.

* The source code for django-compressor can be found and contributed to on
  `github.com/jezdez/django_compressor`_. There you can also file tickets.

The `in-development version`_ of django-compressor can be installed with
``pip install django_compressor==dev`` or ``easy_install django_compressor==dev``.

.. _readthedocs.org/docs/django_compressor/en/latest: http://readthedocs.org/docs/django_compressor/en/latest
.. _github.com/jezdez/django_compressor: http://github.com/jezdez/django_compressor
.. _in-development version: http://github.com/jezdez/django_compressor/tarball/master#egg=django_compressor-dev
