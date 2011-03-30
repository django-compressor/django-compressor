import time
import re

from django import template
from django.core.exceptions import ImproperlyConfigured

from compressor.cache import cache, get_offline_cachekey
from compressor.conf import settings
from compressor.utils import get_class

OUTPUT_FILE = 'file'
OUTPUT_INLINE = 'inline'
OUTPUT_MODES = (OUTPUT_FILE, OUTPUT_INLINE)
COMPRESSORS = {
    "css": settings.COMPRESS_CSS_COMPRESSOR,
    "js": settings.COMPRESS_JS_COMPRESSOR,
}
PROCESSORS = {
    "css": settings.COMPRESS_CSS_PROCESSOR,
    "js": settings.COMPRESS_JS_PROCESSOR,
}
PRECOMPILERS = settings.COMPRESS_PRECOMPILERS

register = template.Library()

class CacheMixin(object):
    def cache_get(self, key):
        packed_val = cache.get(key)
        if packed_val is None:
            return None
        val, refresh_time, refreshed = packed_val
        if (time.time() > refresh_time) and not refreshed:
            # Store the stale value while the cache
            # revalidates for another MINT_DELAY seconds.
            self.cache_set(key, val, refreshed=True,
                timeout=settings.COMPRESS_MINT_DELAY)
            return None
        return val

    def cache_set(self, key, val, refreshed=False,
            timeout=settings.COMPRESS_REBUILD_TIMEOUT):
        refresh_time = timeout + time.time()
        real_timeout = timeout + settings.COMPRESS_MINT_DELAY
        packed_val = (val, refresh_time, refreshed)
        return cache.set(key, packed_val, real_timeout)

    def cache_key(self, cls, mode, type):
        return "%s.%s.%s" % (cls.cachekey, mode, type)
    

class CompressorNode(template.Node, CacheMixin):
    def __init__(self, nodelist, kind=None, mode=OUTPUT_FILE):
        self.nodelist = nodelist
        self.kind = kind
        self.mode = mode
        self.compressor_cls = get_class(
            COMPRESSORS.get(self.kind), exception=ImproperlyConfigured)


    def render(self, context, forced=False):
        if (settings.COMPRESS_ENABLED and
                settings.COMPRESS_OFFLINE) and not forced:
            key = get_offline_cachekey(self.nodelist)
            content = cache.get(key)
            if content:
                return content
        content = self.nodelist.render(context)
        if (not settings.COMPRESS_ENABLED or
                not len(content.strip())) and not forced:
            return content
        compressor = self.compressor_cls(content)
        cachekey = self.cache_key(compressor, self.mode, self.kind)
        output = self.cache_get(cachekey)
        if output is None or forced:
            try:
                if self.mode == OUTPUT_INLINE:
                    return compressor.output_inline()
                output = compressor.output(forced=forced)
                self.cache_set(cachekey, output)
            except:
                if settings.DEBUG:
                    from traceback import format_exc
                    raise Exception(format_exc())
                else:
                    return content
        return output

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

class ProcessorNode(template.Node, CacheMixin):
    def __init__(self, value, is_inline=False, content_type=None, output_mode=OUTPUT_FILE):
        if content_type not in PRECOMPILERS:
            raise ImproperlyConfigured("Type %s is not configured in settings" % content_type) 
        self.value = value
        self.content_type = content_type
        self.mode = output_mode
        self.is_inline = is_inline
        self.type = PRECOMPILERS[content_type]["type"]
        self.processor_cls = get_class(
            PROCESSORS.get(self.type), exception=ImproperlyConfigured)

    def render(self, context):                
        def _render_one(value):
            processor = self.processor_cls(value, 
                                           "hunk" if self.is_inline else "file",
                                           self.content_type)
            cachekey = self.cache_key(processor, self.mode, self.type)
            output = self.cache_get(cachekey)
            if output is None:
                try:
                    output = processor.output(self.mode)
                    self.cache_set(cachekey, output)
                except:
                    if settings.DEBUG:
                        from traceback import format_exc
                        raise Exception(format_exc())
                    else:
                        return content
            return output
        if self.is_inline:
            return _render_one(self.value)
        else:
            return "\n".join(_render_one(file) for file in self.value)
            


@register.tag
def process(parser, token):
    args = token.split_contents()
    type = args[1]
    files = [f.strip()[1:-1] for f in args[2:]]
    
    return ProcessorNode(files, content_type=type, output_mode=OUTPUT_FILE, is_inline=False)
