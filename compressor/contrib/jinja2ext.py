from django.core.exceptions import ImproperlyConfigured

from jinja2 import nodes
from jinja2.ext import Extension
from jinja2.exceptions import TemplateSyntaxError

from compressor.conf import settings
from compressor.utils import get_class
from compressor.templatetags.compress import OUTPUT_FILE
from compressor.cache import (cache_get, cache_set,
                              get_templatetag_cachekey)


class CompressorExtension(Extension):

    tags = set(['compress'])

    @property
    def compressors(self):
        return {
            'js': settings.COMPRESS_JS_COMPRESSOR,
            'css': settings.COMPRESS_CSS_COMPRESSOR,
        }

    def parse(self, parser):
        lineno = parser.stream.next().lineno
        kindarg = parser.parse_expression()
        # Allow kind to be defined as jinja2 name node
        if isinstance(kindarg, nodes.Name):
            kindarg = nodes.Const(kindarg.name)
        args = [kindarg]
        if args[0].value not in self.compressors:
            raise TemplateSyntaxError('compress kind may be one of: %s' %
                                      (', '.join(self.compressors.keys())),
                                       lineno)
        if parser.stream.skip_if('comma'):
            modearg = parser.parse_expression()
            # Allow mode to be defined as jinja2 name node
            if isinstance(modearg, nodes.Name):
                modearg = nodes.Const(modearg.name)
                args.append(modearg)
        else:
            args.append(nodes.Const('file'))
        body = parser.parse_statements(['name:endcompress'], drop_needle=True)
        return nodes.CallBlock(self.call_method('_compress', args), [], [],
            body).set_lineno(lineno)

    def _compress(self, kind, mode, caller):
        mode = mode or OUTPUT_FILE
        Compressor = get_class(self.compressors.get(kind),
            exception=ImproperlyConfigured)
        original_content = caller()
        compressor = Compressor(original_content)
        # This extension assumes that we won't force compression
        forced = False

        # Prepare the actual compressor and check cache
        cache_key, cache_content = self.render_cached(kind, mode, compressor,
            forced)
        if cache_content is not None:
            return cache_content

        # call compressor output method and handle exceptions
        try:
            rendered_output = compressor.output(mode, forced)
            if cache_key:
                cache_set(cache_key, rendered_output)
            return rendered_output
        except Exception, e:
            if settings.DEBUG:
                raise e

        # Or don't do anything in production
        return original_content

    def render_cached(self, kind, mode, compressor, forced):
        """
        If enabled checks the cache for the given compressor's cache key
        and return a tuple of cache key and output
        """
        if settings.COMPRESS_ENABLED and not forced:
            cache_key = get_templatetag_cachekey(compressor, mode, kind)
            cache_content = cache_get(cache_key)
            return cache_key, cache_content
        return None, None
