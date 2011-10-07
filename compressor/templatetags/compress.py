from django import template
from django.core.exceptions import ImproperlyConfigured

from compressor.cache import (cache_get, cache_set, get_offline_hexdigest,
                              get_offline_manifest, get_templatetag_cachekey)
from compressor.conf import settings
from compressor.exceptions import OfflineGenerationError
from compressor.utils import get_class

register = template.Library()

OUTPUT_FILE = 'file'
OUTPUT_INLINE = 'inline'
OUTPUT_MODES = (OUTPUT_FILE, OUTPUT_INLINE)


class CompressorNode(template.Node):

    def __init__(self, nodelist, kind=None, mode=OUTPUT_FILE, name=None):
        self.nodelist = nodelist
        self.kind = kind
        self.mode = mode
        self.name = name

    def compressor_cls(self, *args, **kwargs):
        compressors = {
            "css": settings.COMPRESS_CSS_COMPRESSOR,
            "js": settings.COMPRESS_JS_COMPRESSOR,
        }
        if self.kind not in compressors.keys():
            raise template.TemplateSyntaxError(
                "The compress tag's argument must be 'js' or 'css'.")
        return get_class(compressors.get(self.kind),
                         exception=ImproperlyConfigured)(*args, **kwargs)

    def debug_mode(self, context):
        if settings.COMPRESS_DEBUG_TOGGLE:
            # Only check for the debug parameter
            # if a RequestContext was used
            request = context.get('request', None)
            if request is not None:
                return settings.COMPRESS_DEBUG_TOGGLE in request.GET

    def render_offline(self, compressor, forced):
        """
        If enabled and in offline mode, and not forced or in debug mode
        check the offline cache and return the result if given
        """
        if (settings.COMPRESS_ENABLED and
                settings.COMPRESS_OFFLINE) and not forced:
            key = get_offline_hexdigest(self.nodelist)
            offline_manifest = get_offline_manifest()
            if key in offline_manifest:
                return offline_manifest[key]
            else:
                raise OfflineGenerationError('You have offline compression enabled but key "%s" is missing from offline manifest. You may need to run "python manage.py compress".' % key)

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
        # Check if in debug mode
        if self.debug_mode(context):
            return self.nodelist.render(context)

        # Prepare the compressor
        context.update({'name': self.name})
        compressor = self.compressor_cls(content=self.nodelist.render(context),
                                         context=context)

        # See if it has been rendered offline
        cached_offline = self.render_offline(compressor, forced)
        if cached_offline:
            return cached_offline

        # Check cache
        cache_key, cache_content = self.render_cached(compressor, forced)
        if cache_content is not None:
            return cache_content

        # call compressor output method and handle exceptions
        rendered_output = compressor.output(self.mode, forced=forced)
        if cache_key:
            cache_set(cache_key, rendered_output)
        return rendered_output


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
