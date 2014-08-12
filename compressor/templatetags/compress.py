from django import template
from django.core.exceptions import ImproperlyConfigured
from django.utils import six

from compressor.cache import (cache_get, cache_set, get_offline_hexdigest,
                              get_offline_manifest, get_templatetag_cachekey)
from compressor.conf import settings
from compressor.exceptions import OfflineGenerationError
from compressor.utils import get_class

register = template.Library()

OUTPUT_FILE = 'file'
OUTPUT_INLINE = 'inline'
OUTPUT_MODES = (OUTPUT_FILE, OUTPUT_INLINE)


class CompressorMixin(object):

    def enabled(self):
        return settings.COMPRESS_ENABLED

    def get_original_content(self, context):
        raise NotImplementedError

    @property
    def compressors(self):
        return {
            'js': settings.COMPRESS_JS_COMPRESSOR,
            'css': settings.COMPRESS_CSS_COMPRESSOR,
        }

    def compressor_cls(self, kind, *args, **kwargs):
        if kind not in self.compressors.keys():
            raise template.TemplateSyntaxError(
                "The compress tag's argument must be 'js' or 'css'.")
        return get_class(self.compressors.get(kind),
                         exception=ImproperlyConfigured)(*args, **kwargs)

    def get_compressor(self, context, kind):
        return self.compressor_cls(kind,
            content=self.get_original_content(context), context=context)

    def debug_mode(self, context):
        if settings.COMPRESS_DEBUG_TOGGLE:
            # Only check for the debug parameter
            # if a RequestContext was used
            request = context.get('request', None)
            if request is not None:
                return settings.COMPRESS_DEBUG_TOGGLE in request.GET

    def is_offline_compression_enabled(self, forced):
        """
        Check if offline compression is enabled or forced

        Defaults to just checking the settings and forced argument,
        but can be overridden to completely disable compression for
        a subclass, for instance.
        """
        return (self.enabled() and settings.COMPRESS_OFFLINE) or forced

    def render_offline(self, context, forced):
        """
        If enabled and in offline mode, and not forced check the offline cache
        and return the result if given
        """
        if self.is_offline_compression_enabled(forced) and not forced:
            key = get_offline_hexdigest(self.get_original_content(context))
            offline_manifest = get_offline_manifest()
            if key in offline_manifest:
                return offline_manifest[key]
            else:
                raise OfflineGenerationError('You have offline compression '
                    'enabled but key "%s" is missing from offline manifest. '
                    'You may need to run "python manage.py compress".' % key)

    def render_cached(self, compressor, kind, mode, forced=False):
        """
        If enabled checks the cache for the given compressor's cache key
        and return a tuple of cache key and output
        """
        if self.enabled() and not forced:
            cache_key = get_templatetag_cachekey(compressor, mode, kind)
            cache_content = cache_get(cache_key)
            return cache_key, cache_content
        return None, None

    def render_compressed(self, context, kind, mode, forced=False):

        # See if it has been rendered offline
        cached_offline = self.render_offline(context, forced=forced)
        if cached_offline:
            return cached_offline

        # Take a shortcut if we really don't have anything to do
        if not forced and not settings.COMPRESS_PRECOMPILERS and not self.enabled():
            return self.get_original_content(context)

        context['compressed'] = {'name': getattr(self, 'name', None)}
        compressor = self.get_compressor(context, kind)

        # Prepare the actual compressor and check cache
        cache_key, cache_content = self.render_cached(compressor, kind, mode, forced=forced)
        if cache_content is not None:
            return cache_content

        # call compressor output method and handle exceptions
        try:
            rendered_output = self.render_output(compressor, mode, forced=forced)
            if cache_key:
                cache_set(cache_key, rendered_output)
            assert isinstance(rendered_output, six.string_types)
            return rendered_output
        except Exception:
            if settings.DEBUG or forced:
                raise

        # Or don't do anything in production
        return self.get_original_content(context)

    def render_output(self, compressor, mode, forced=False):
        return compressor.output(mode, forced=forced)


class CompressorNode(CompressorMixin, template.Node):

    def __init__(self, nodelist, kind=None, mode=OUTPUT_FILE, name=None,
                 enabled=False):
        self.nodelist = nodelist
        self.kind = kind
        self.mode = mode
        self.name = name
        self._enabled = enabled

    def enabled(self):
        return settings.COMPRESS_ENABLED or self._enabled

    def get_original_content(self, context):
        return self.nodelist.render(context)

    def debug_mode(self, context):
        if settings.COMPRESS_DEBUG_TOGGLE:
            # Only check for the debug parameter
            # if a RequestContext was used
            request = context.get('request', None)
            if request is not None:
                return settings.COMPRESS_DEBUG_TOGGLE in request.GET

    def render(self, context, forced=False):

        # Check if in debug mode
        if self.debug_mode(context):
            return self.get_original_content(context)

        return self.render_compressed(context, self.kind, self.mode, forced=forced)


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

    # 3 -> enabled | mode
    # 4 -> mode, enabled | name
    # 5 -> mode, name, enabled

    kind = args[1]
    mode = OUTPUT_FILE
    name = None
    enabled = False

    length = len(args)
    if length == 3:
        if args[2] == 'enabled':
            enabled = True
        else:
            name = args[2]
    elif length == 4:
        mode, enabled_or_name = args[2:]
        if enabled_or_name == 'enabled':
            enabled = True
        else:
            name = enabled_or_name
    elif length == 5:
        mode, name, enabled = args[2:]
    elif length != 2:
        raise template.TemplateSyntaxError(
            "%r tag requires one to five arguments." % args[0])

    if mode not in OUTPUT_MODES:
        raise template.TemplateSyntaxError(
            "%r's second argument must be '%s' or '%s'." %
            (args[0], OUTPUT_FILE, OUTPUT_INLINE))

    return CompressorNode(nodelist, kind, mode, name, enabled=enabled)
