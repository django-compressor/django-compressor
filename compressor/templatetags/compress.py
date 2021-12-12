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
OUTPUT_PRELOAD = 'preload'
OUTPUT_MODES = (OUTPUT_FILE, OUTPUT_INLINE, OUTPUT_PRELOAD)


class CompressorMixin:

    def get_original_content(self, context):
        raise NotImplementedError

    @property
    def compressors(self):
        return settings.COMPRESSORS

    def compressor_cls(self, kind):
        if kind not in self.compressors.keys():
            raise template.TemplateSyntaxError(
                "The compress tag's argument must be one of: %s."
                % ', '.join(map(repr, self.compressors.keys())))
        return get_class(self.compressors.get(kind),
                         exception=ImproperlyConfigured)

    def get_compressor(self, context, kind, log, verbosity):
        cls = self.compressor_cls(kind)
        return cls(
            kind,
            content=self.get_original_content(context),
            context=context,
            log=log,
            verbosity=verbosity
        )

    def debug_mode(self, context):
        if settings.COMPRESS_DEBUG_TOGGLE:
            # Only check for the debug parameter if a RequestContext was used
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
        return (settings.COMPRESS_ENABLED
                and settings.COMPRESS_OFFLINE) or forced

    def render_offline(self, context):
        """
        If enabled and in offline mode, and not forced check the offline cache
        and return the result if given
        """
        original_content = self.get_original_content(context)
        key = get_offline_hexdigest(original_content)
        offline_manifest = get_offline_manifest()
        if key in offline_manifest:
            return offline_manifest[key].replace(
                settings.COMPRESS_URL_PLACEHOLDER,
                # Cast ``settings.COMPRESS_URL`` to a string to allow it to be
                # a string-alike object to e.g. add ``SCRIPT_NAME`` WSGI param
                # as a *path prefix* to the output URL.
                # See https://code.djangoproject.com/ticket/25598.
                str(settings.COMPRESS_URL)
            )
        else:
            raise OfflineGenerationError('You have offline compression '
                'enabled but key "%s" is missing from offline manifest. '
                'You may need to run "python manage.py compress". Here '
                'is the original content:\n\n%s' % (key, original_content))

    def render_cached(self, compressor, kind, mode):
        """
        If enabled checks the cache for the given compressor's cache key
        and return a tuple of cache key and output
        """
        cache_key = get_templatetag_cachekey(compressor, mode, kind)
        cache_content = cache_get(cache_key)
        return cache_key, cache_content

    def render_compressed(self, context, kind, mode, name=None, forced=False, log=None, verbosity=0):

        # See if it has been rendered offline
        if self.is_offline_compression_enabled(forced) and not forced:
            return self.render_offline(context)

        # Take a shortcut if we really don't have anything to do
        if (not settings.COMPRESS_ENABLED
                and not settings.COMPRESS_PRECOMPILERS and not forced):
            return self.get_original_content(context)

        name = name or getattr(self, 'name', None)
        context['compressed'] = {'name': name}
        compressor = self.get_compressor(context, kind, log, verbosity)

        # Check cache
        cache_key = None
        if settings.COMPRESS_ENABLED and not forced:
            cache_key, cache_content = self.render_cached(compressor, kind, mode)
            if cache_content is not None:
                return cache_content

        file_basename = name or getattr(self, 'basename', None)
        if file_basename is None:
            file_basename = 'output'

        rendered_output = compressor.output(mode, forced=forced, basename=file_basename)
        assert isinstance(rendered_output, str)
        if cache_key:
            cache_set(cache_key, rendered_output)
        return rendered_output


class CompressorNode(CompressorMixin, template.Node):

    def __init__(self, nodelist, kind=None, mode=OUTPUT_FILE, name=None):
        self.nodelist = nodelist
        self.kind = kind
        self.mode = mode
        self.name = name

    def get_original_content(self, context):
        return self.nodelist.render(context)

    def render(self, context, forced=False):

        # Check if in debug mode
        if self.debug_mode(context):
            return self.get_original_content(context)

        # pass logger to compressor object
        try:
            log, verbosity = context.template._log, context.template._log_verbosity
        except AttributeError:
            log, verbosity = None, 0

        return self.render_compressed(context, self.kind, self.mode, forced=forced, log=log, verbosity=verbosity)


@register.tag
def compress(parser, token):
    """
    Compresses linked and inline javascript or CSS into a single cached file.

    Syntax::

        {% compress <js/css> [<file/inline> [block_name]] %}
        <html of inline or linked JS/CSS>
        {% endcompress %}

    Examples::

        See docs/usage.rst

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
        if mode not in OUTPUT_MODES:
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
