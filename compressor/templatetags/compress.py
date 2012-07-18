import re

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


class CompressorMixin(object):

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

    def get_compressor(self, context, kind, tag_opts):
        return self.compressor_cls(kind,
            content=self.get_original_content(context), context=context, opts=tag_opts)

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
        but can be overriden to completely disable compression for
        a subclass, for instance.
        """
        return (settings.COMPRESS_ENABLED and
                settings.COMPRESS_OFFLINE) or forced

    def render_offline(self, context, forced):
        """
        If enabled and in offline mode, and not forced check the offline cache
        and return the result if given
        """
        if self.is_offline_compression_enabled(forced) and not forced:
            key = get_offline_hexdigest(self.nodelist.render(context))
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
        if settings.COMPRESS_ENABLED and not forced:
            cache_key = get_templatetag_cachekey(compressor, mode, kind)
            cache_content = cache_get(cache_key)
            return cache_key, cache_content
        return None, None

    def render_compressed(self, context, kind, mode, tag_opts=None, forced=False):
        deferred = getattr(self, 'name', None) and tag_opts and tag_opts.get('deferred', 'false') == 'true'

        # See if it has been rendered offline
        cached_offline = self.render_offline(context, forced=forced)
        if cached_offline:
            return self.render_result(cached_offline, context, deferred, mode)

        # Take a shortcut if we really don't have anything to do
        if ((not settings.COMPRESS_ENABLED and
             not settings.COMPRESS_PRECOMPILERS) and not forced):
            return self.render_result(self.get_original_content(context), context, deferred, mode)

        context['compressed'] = {'name': getattr(self, 'name', None)}
        compressor = self.get_compressor(context, kind, tag_opts)

        # Prepare the actual compressor and check cache
        cache_key, cache_content = self.render_cached(compressor, kind, mode, forced=forced)
        if cache_content is not None:
            return self.render_result(cache_content, context, deferred, mode)

        # call compressor output method and handle exceptions
        try:
            rendered_output = self.render_output(compressor, mode, forced=forced)
            if cache_key:
                cache_set(cache_key, rendered_output)
            return self.render_result(rendered_output.decode('utf-8'), context, deferred, mode)
        except Exception:
            if settings.DEBUG or forced:
                raise

        # Or don't do anything in production
        return self.render_result(self.get_original_content(context), context, deferred)

    def render_output(self, compressor, mode, forced=False):
        return compressor.output(mode, forced=forced)

    def render_result(self, content, context, deferred, mode):
        if deferred:
            if mode == OUTPUT_FILE:
                match = re.search(r'(?:src|href)=["\']([^"\']+)', content)
                if match:
                    context[self.name] = match.group(1)
                    return ""
            context[self.name] = content
            return ""
        return content


class CompressorNode(CompressorMixin, template.Node):

    def __init__(self, nodelist, kind=None, mode=OUTPUT_FILE, name=None, tag_opts={}):
        self.nodelist = nodelist
        self.kind = kind
        self.mode = mode
        self.name = name
        self.tag_opts = tag_opts

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

        self.resolve_variables(context)
        return self.render_compressed(context, self.kind, self.mode, self.tag_opts, forced=forced)

    def resolve_variables(self, context):
        for option, value in self.tag_opts.items():
            try:
                value = value.resolve(context)
            except template.VariableDoesNotExist:
                value = unicode(value)
            self.tag_opts[option] = value


@register.tag
def compress(parser, token):
    """
    Compresses linked and inline javascript or CSS into a single cached file.

    Syntax::

        {% compress js|css [file|inline] [<option>=<value>[ <option>=<value>...]] [as <variable_name>] %}
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

    if not len(args) >= 2:
        raise template.TemplateSyntaxError(
            "%r tag requires at least one argument." % args[0])

    kind = args[1]
    name = None
    mode = OUTPUT_FILE
    tag_opts = {}
    if len(args) >= 3:
        looking_for_name = False
        for i in range(2, len(args)):
            if looking_for_name:
                name = args[i]
                looking_for_name = False
            elif args[i] == "as":
                looking_for_name = True
            elif '=' in args[i]:
                option, value = args[i].split("=")
                tag_opts[option] = template.Variable(value)
            elif args[i] in OUTPUT_MODES:
                mode = args[i]
            else:
                raise template.TemplateSyntaxError(
                    "%r's third argument on must either be (file|input) or <option>=<value> or 'as <name>'" %
                    args[0])

    return CompressorNode(nodelist, kind, mode, name, tag_opts)
