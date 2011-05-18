from django import template
from django.core.exceptions import ImproperlyConfigured

from compressor.cache import (cache, cache_get, cache_set,
                              get_offline_cachekey, get_templatetag_cachekey)
from compressor.conf import settings
from compressor.utils import get_class

register = template.Library()

OUTPUT_FILE = 'file'
OUTPUT_INLINE = 'inline'
OUTPUT_MODES = (OUTPUT_FILE, OUTPUT_INLINE)
COMPRESSORS = {
    "css": settings.COMPRESS_CSS_COMPRESSOR,
    "js": settings.COMPRESS_JS_COMPRESSOR,
}

class CompressorNode(template.Node):

    def __init__(self, nodelist, kind=None, mode=OUTPUT_FILE):
        self.nodelist = nodelist
        self.kind = kind
        self.mode = mode
        self.compressor_cls = get_class(
            COMPRESSORS.get(self.kind), exception=ImproperlyConfigured)

    def debug_mode(self, context):
        if settings.COMPRESS_DEBUG_TOGGLE:
            # Only check for the debug parameter
            # if a RequestContext was used
            request = context.get('request', None)
            if request is not None:
                return settings.COMPRESS_DEBUG_TOGGLE in request.GET

    def render_offline(self, forced):
        """
        If enabled and in offline mode, and not forced or in debug mode
        check the offline cache and return the result if given
        """
        if (settings.COMPRESS_ENABLED and
                settings.COMPRESS_OFFLINE) and not forced:
            return cache.get(get_offline_cachekey(self.nodelist))

    def render_cached(self, compressor, forced):
        """
        If enabled checks the cache for the given compressor's cache key
        and return a tuple of cache key and output
        """
        if settings.COMPRESS_ENABLED and not forced:
            cache_key = get_templatetag_cachekey(
                compressor, self.mode, self.kind)
            cache_content = cache_get(cache_key)
            return cache_key, cache_content
        return None, None

    def render(self, context, forced=False):
        # 1. Check if in debug mode
        if self.debug_mode(context):
            return self.nodelist.render(context)

        # 2. Try offline cache.
        cached_offline = self.render_offline(forced)
        if cached_offline:
            return cached_offline

        # 3. Prepare the actual compressor and check cache
        compressor = self.compressor_cls(self.nodelist.render(context))
        cache_key, cache_content = self.render_cached(compressor, forced)
        if cache_content is not None:
            return cache_content

        # 4. call compressor output method and handle exceptions
        try:
            rendered_output = compressor.output(self.mode, forced=forced)
            if cache_key:
                cache_set(cache_key, rendered_output)
            return rendered_output
        except Exception, e:
            if settings.DEBUG or forced:
                raise e

        # 5. Or don't do anything in production
        return self.nodelist.render(context)


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
    """

    nodelist = parser.parse(('endcompress',))
    parser.delete_first_token()

    args = token.split_contents()

    if not len(args) in (2, 3):
        raise template.TemplateSyntaxError(
            "%r tag requires either one or two arguments." % args[0])

    kind = args[1]
    if not kind in COMPRESSORS.keys():
        raise template.TemplateSyntaxError(
            "%r's argument must be 'js' or 'css'." % args[0])

    if len(args) == 3:
        mode = args[2]
        if not mode in OUTPUT_MODES:
            raise template.TemplateSyntaxError(
                "%r's second argument must be '%s' or '%s'." %
                (args[0], OUTPUT_FILE, OUTPUT_INLINE))
    else:
        mode = OUTPUT_FILE
    return CompressorNode(nodelist, kind, mode)
