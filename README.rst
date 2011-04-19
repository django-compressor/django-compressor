Django Compressor
=================

Django Compressor combines and compresses linked and inline Javascript
or CSS in a Django templates into cacheable static files by using the
``compress`` template tag.

HTML in between ``{% compress js/css %}`` and ``{% endcompress %}`` is
parsed and searched for CSS or JS. These styles and scripts are subsequently
processed with optional, configurable compilers and filters.

The default filter for CSS rewrites paths to static files to be absolute
and adds a cache busting timestamp. For Javascript the default filter
compresses it using ``jsmin``.

As the final result the template tag outputs a ``<script>`` or ``<link>``
tag pointing to the optimized file. These files are stored inside a folder
and given an unique name based on their content. Alternatively it can also
return the resulting content to the original template directly.

Since the file name is dependend on the content these files can be given
a far future expiration date without worrying about stale browser caches.

The concatenation and compressing process can also be jump started outside
of the request/response cycle by using the Django management command
``manage.py compress``.

Configurability & Extendibility
-------------------------------

Django Compressor is highly configurable and extendible. The HTML parsing
is done using lxml_ or if it's not available Python's built-in HTMLParser by
default. As an alternative Django Compressor provides a BeautifulSoup_ and a
html5lib_ based parser, as well as an abstract base class that makes it easy to
write a custom parser.

Django Compressor also comes with built-in support for `CSS Tidy`_,
`YUI CSS and JS`_ compressor, the Google's `Closure Compiler`_, a Python
port of Douglas Crockford's JSmin_, a Python port of the YUI CSS Compressor
cssmin_ and a filter to convert (some) images into `data URIs`_.

If your setup requires a different compressor or other post-processing
tool it will be fairly easy to implement a custom filter. Simply extend
from one of the available base classes.

More documentation about the usage and settings of Django Compressor can be
found on `django_compressor.readthedocs.org`_.

The source code for Django Compressor can be found and contributed to on
`github.com/jezdez/django_compressor`_. There you can also file tickets.

The `in-development version`_ of Django Compressor can be installed with
``pip install django_compressor==dev`` or ``easy_install django_compressor==dev``.

.. _BeautifulSoup: http://www.crummy.com/software/BeautifulSoup/
.. _lxml: http://lxml.de/
.. _html5lib: http://code.google.com/p/html5lib/
.. _CSS Tidy: http://csstidy.sourceforge.net/
.. _YUI CSS and JS: http://developer.yahoo.com/yui/compressor/
.. _Closure Compiler: http://code.google.com/closure/compiler/
.. _JSMin: http://www.crockford.com/javascript/jsmin.html
.. _cssmin: https://github.com/zacharyvoase/cssmin
.. _data URIs: http://en.wikipedia.org/wiki/Data_URI_scheme
.. _django_compressor.readthedocs.org: http://django_compressor.readthedocs.org/
.. _github.com/jezdez/django_compressor: https://github.com/jezdez/django_compressor
.. _in-development version: http://github.com/jezdez/django_compressor/tarball/develop#egg=django_compressor-dev
