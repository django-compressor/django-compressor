Django Compressor
=================

Django Compressor can combine and compress linked and inline Javascript
or CSS found inside a Django template into cacheable static files. It does so
through use of a template tag called `compress`.

HTML in between `{% compress js/css %}` and `{% endcompress %}` is parsed
and searched for CSS or JS. These styles and scripts are then processed and
concatenated.

The default action for CSS is to rewrite paths to static files and fit them
with a cache busting timestamp. For Javascript it is to compress it using
`jsmin`.

As the final result the template tag outputs a `<script>` or `<link>` tag
pointing to the optimized file. These files are stored inside Django's static
media folder and given an unique name based on their content.

Since the file name is dependend on the content these files can be given a far
future expiration date without worrying about stale browser caches.

The concatenation and compressing process can also be jump started outside of
the request/response cycle by using the Django management command
`manage.py compress`.

Configurability & Extendibility
-------------------------------

Django Compressor is highly configurable and extendible. By default HTML parsing
is done using `BeautifulSoup`. As an alternative django-compress provides an
`lxml` based parser, as well as an abstract base class that makes it easy to
write a custom parser.

Django Compressor also comes with built in support for CSS Tidy, YUI CSS and
JS minification, the Google's Closure Compiler and a filter to convert (some)
images into `data:` URIs.

If your setup requires a different compressor, or other post-processing tool it
will be fairly easy to implement a custom filter. Simply extend from one of
the available base classes.

More documentation about the usage and settings of django-compressor can be
found on `readthedocs.org/docs/django_compressor/en/latest`_.

The source code for django-compressor can be found and contributed to on
`github.com/jezdez/django_compressor`_. There you can also file tickets.

The `in-development version`_ of django-compressor can be installed with
``pip install django_compressor==dev`` or ``easy_install django_compressor==dev``.

.. _readthedocs.org/docs/django_compressor/en/latest: http://readthedocs.org/docs/django_compressor/en/latest
.. _github.com/jezdez/django_compressor: http://github.com/jezdez/django_compressor
.. _in-development version: http://github.com/jezdez/django_compressor/tarball/master#egg=django_compressor-dev
