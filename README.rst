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

    <link rel="stylesheet" href="/media/CACHE/css/f7c661b7a124.css" type="text/css" media="all" charset="utf-8">

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


Settings
********

Django compressor has a number of settings that control it's behavior. 
They've been given sensible defaults.

`COMPRESS` default: the opposite of `DEBUG`
  Boolean that decides if compression will happen. 

`COMPRESS_URL` default: `MEDIA_URL`
  Controls the URL that linked media will be read from and compressed media
  will be written to.
  
`COMPRESS_ROOT` default: `MEDIA_ROOT`
  Controls the absolute file path that linked media will be read from and 
  compressed media will be written to.

`COMPRESS_OUTPUT_DIR` default: `CACHE`
  Conttrols the directory inside `COMPRESS_ROOT` that compressed files will 
  be written to.

`COMPRESS_CSS_FILTERS` default: []
  A list of filters that will be applied to CSS.

`COMPRESS_JS_FILTERS` default: ['compressor.filters.jsmin.JSMinFilter'])
  A list of filters that will be applied to javascript.
