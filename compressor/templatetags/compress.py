from django import template
from django.utils.importlib import import_module

from compressor.conf import settings


register = template.Library()

OUTPUT_FILE = 'file'
OUTPUT_INLINE = 'inline'
OUTPUT_MODES = (OUTPUT_FILE, OUTPUT_INLINE)

#Backwards compatibility
CompressorNode = import_module(settings.COMPRESS_NODE_CLASS).CompressorNode


@register.tag
def compress(parser, token):
    """
    Compresses linked and inline javascript or CSS into a single cached file.

    Syntax::

        {% compress <js/css> %}
        <html of inline or linked JS/CSS>
        {% endcompress %}

    Examples::

        {% compress css %}
        <link rel="stylesheet" href="/static/css/one.css" type="text/css" charset="utf-8">
        <style type="text/css">p { border:5px solid green;}</style>
        <link rel="stylesheet" href="/static/css/two.css" type="text/css" charset="utf-8">
        {% endcompress %}

    Which would be rendered something like::

        <link rel="stylesheet" href="/static/CACHE/css/f7c661b7a124.css" type="text/css" media="all" charset="utf-8">

    or::

        {% compress js %}
        <script src="/static/js/one.js" type="text/javascript" charset="utf-8"></script>
        <script type="text/javascript" charset="utf-8">obj.value = "value";</script>
        {% endcompress %}

    Which would be rendered something like::

        <script type="text/javascript" src="/static/CACHE/js/3f33b9146e12.js" charset="utf-8"></script>

    Linked files must be on your COMPRESS_URL (which defaults to STATIC_URL).
    If DEBUG is true off-site files will throw exceptions. If DEBUG is false
    they will be silently stripped.
    """

    nodelist = parser.parse(('endcompress',))
    parser.delete_first_token()

    args = token.split_contents()

    if not len(args) in (2, 3, 4):
        raise template.TemplateSyntaxError(
            "%r tag requires either one, two or three arguments." % args[0])
    kind = args[1]
    if len(args) >= 3:
        mode = args[2]
        if not mode in OUTPUT_MODES:
            raise template.TemplateSyntaxError(
                "%r's second argument must be '%s' or '%s'." %
                (args[0], OUTPUT_FILE, OUTPUT_INLINE))
    else:
        mode = OUTPUT_FILE
    if len(args) == 4:
        name = args[3]
    else:
        name = None
    return CompressorNode(nodelist, kind, mode, name)
