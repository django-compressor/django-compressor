Django compressor
=================

Compresses linked and inline javascript or CSS into a single cached file.

Syntax::

    {% compress <js/css> %}
    <html of inline or linked JS/CSS>
    {% endcompress %}

Examples::

    {% compress css %}
    <link rel="stylesheet" href="/media/css/one.css" type="text/css" charset="utf-8">
    <style type="text/css">p { border:5px solid green;}</style>
    <link rel="stylesheet" href="/media/css/two.css" type="text/css" charset="utf-8">
    {% endcompress %}

Which would be rendered something like::

    <link rel="stylesheet" href="/media/CACHE/css/f7c661b7a124.css" type="text/css" charset="utf-8">

or::

    {% compress js %}
    <script src="/media/js/one.js" type="text/javascript" charset="utf-8"></script>
    <script type="text/javascript" charset="utf-8">obj.value = "value";</script>
    {% endcompress %}

Which would be rendered something like::

    <script type="text/javascript" src="/media/CACHE/js/3f33b9146e12.js" charset="utf-8"></script>

Linked files must be on your COMPRESS_URL (which defaults to MEDIA_URL).
If DEBUG is true off-site files will throw exceptions. If DEBUG is false
they will be silently stripped.

If COMPRESS is False (defaults to the opposite of DEBUG) the compress tag
simply returns exactly what it was given, to ease development.


CSS Notes:
**********

All relative url() bits specified in linked CSS files are automatically
converted to absolute URLs while being processed. Any local absolute URLs (those
starting with a '/') are left alone.

Stylesheets that are @import'd are not compressed into the main file. They are
left alone.

If the media attribute is set on <style> and <link> elements, a separate
compressed file is created and linked for each media value you specified.
This allows the media attribute to remain on the generated link element,
instead of wrapping your CSS with @media blocks (which can break your own
@media queries or @font-face declarations). It also allows browsers to avoid
downloading CSS for irrelevant media types.

**Recommendations:**

* Use only relative or full domain absolute URLs in your CSS files.
* Avoid @import! Simply list all your CSS files in the HTML, they'll be combined anyway.


Why another static file combiner for django?
********************************************

Short version: None of them did exactly what I needed.

Long version:

**JS/CSS belong in the templates**
  Every static combiner for django I've seen makes you configure
  your static files in your settings.py. While that works, it doesn't make
  sense. Static files are for display. And it's not even an option if your
  settings are in completely different repositories and use different deploy
  processes from the templates that depend on them.

**Flexibility**
  django_compressor doesn't care if different pages use different combinations
  of statics. It doesn't care if you use inline scripts or styles. It doesn't
  get in the way.

**Automatic regeneration and cache-foreverable generated output**
  Statics are never stale and browsers can be told to cache the output forever.

**Full test suite**
  I has one.


Settings
********

Django compressor has a number of settings that control it's behavior.
They've been given sensible defaults.

``COMPRESS``
------------

:Default: the opposite of ``DEBUG``

Boolean that decides if compression will happen.

``COMPRESS_URL``
----------------

:Default: ``MEDIA_URL``

Controls the URL that linked media will be read from and compressed media
will be written to.

``COMPRESS_ROOT``
-----------------

:Default: ``MEDIA_ROOT``

Controls the absolute file path that linked media will be read from and
compressed media will be written to.

``COMPRESS_OUTPUT_DIR``
-----------------------

:Default: ``'CACHE'``

Conttrols the directory inside `COMPRESS_ROOT` that compressed files will
be written to.

``COMPRESS_CSS_FILTERS``
------------------------

:Default: ``[]``

A list of filters that will be applied to CSS.

``COMPRESS_JS_FILTERS``
-----------------------

:Default: ``['compressor.filters.jsmin.JSMinFilter']``

A list of filters that will be applied to javascript.

``COMPRESS_STORAGE``
--------------------

:Default: ``'compressor.storage.CompressorFileStorage'``

The dotted path to a Django Storage backend to be used to save the
compressed files.

``COMPRESS_PARSER``
--------------------

:Default: ``'compressor.parser.BeautifulSoupParser'``

The backend to use when parsing the JavaScript or Stylesheet files.
The backends included in ``compressor``:

  - ``compressor.parser.BeautifulSoupParser``
  - ``compressor.parser.LxmlParser``

See `Dependencies`_ for more info about the packages you need for each parser.

``COMPRESS_REBUILD_TIMEOUT``
----------------------------

:Default: ``2592000`` (30 days in seconds)

The period of time after which the the compressed files are rebuilt even if
no file changes are detected.

``COMPRESS_MINT_DELAY``
------------------------

:Default: ``30`` (seconds)

The upper bound on how long any compression should take to run. Prevents
dog piling, should be a lot smaller than ``COMPRESS_REBUILD_TIMEOUT``.


``COMPRESS_MTIME_DELAY``
------------------------

:Default: ``None``

The amount of time (in seconds) to cache the result of the check of the
modification timestamp of a file. Disabled by default. Should be smaller
than ``COMPRESS_REBUILD_TIMEOUT`` and ``COMPRESS_MINT_DELAY``.


Dependencies
************

* BeautifulSoup_ (for the default ``compressor.parser.BeautifulSoupParser``)

::

    pip install BeautifulSoup

* lxml_ (for the optional ``compressor.parser.LxmlParser``, requires libxml2_)

::

    STATIC_DEPS=true pip install lxml

.. _BeautifulSoup: http://www.crummy.com/software/BeautifulSoup/
.. _lxml: http://codespeak.net/lxml/
.. _libxml2: http://xmlsoft.org/
