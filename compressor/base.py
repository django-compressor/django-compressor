import os

from django.core.files.base import ContentFile
from django.template.loader import render_to_string
from django.utils.encoding import smart_unicode

from compressor.cache import get_hexdigest, get_mtime
from compressor.conf import settings
from compressor.exceptions import CompressorError, UncompressableFileError
from compressor.filters import CompilerFilter
from compressor.storage import default_storage
from compressor.utils import get_class, staticfiles
from compressor.utils.decorators import cached_property

# Some constants for nicer handling.
SOURCE_HUNK, SOURCE_FILE = 1, 2
METHOD_INPUT, METHOD_OUTPUT = 'input', 'output'


class Compressor(object):
    """
    Base compressor object to be subclassed for content type
    depending implementations details.
    """
    type = None

    def __init__(self, content=None, output_prefix="compressed"):
        self.content = content or ""
        self.output_prefix = output_prefix
        self.charset = settings.DEFAULT_CHARSET
        self.storage = default_storage
        self.split_content = []
        self.extra_context = {}
        self.all_mimetypes = dict(settings.COMPRESS_PRECOMPILERS)
        self.finders = staticfiles.finders

    def split_contents(self):
        """
        To be implemented in a subclass, should return an
        iterable with four values: kind, value, basename, element
        """
        raise NotImplementedError

    def get_basename(self, url):
        try:
            base_url = self.storage.base_url
        except AttributeError:
            base_url = settings.COMPRESS_URL
        if not url.startswith(base_url):
            raise UncompressableFileError(
                "'%s' isn't accesible via COMPRESS_URL ('%s') and can't be"
                " compressed" % (url, base_url))
        basename = url.replace(base_url, "", 1)
        # drop the querystring, which is used for non-compressed cache-busting.
        return basename.split("?", 1)[0]

    def get_filename(self, basename):
        # first try to find it with staticfiles (in debug mode)
        filename = None
        if settings.DEBUG and self.finders:
            filename = self.finders.find(basename)
        # secondly try finding the file in the root
        elif self.storage.exists(basename):
            filename = self.storage.path(basename)
        if filename:
            return filename
        # or just raise an exception as the last resort
        raise UncompressableFileError(
            "'%s' could not be found in the COMPRESS_ROOT '%s'%s" % (
                basename, settings.COMPRESS_ROOT,
                self.finders and " or with staticfiles." or "."))

    @cached_property
    def parser(self):
        return get_class(settings.COMPRESS_PARSER)(self.content)

    @cached_property
    def cached_filters(self):
        return [get_class(filter_cls) for filter_cls in self.filters]

    @cached_property
    def mtimes(self):
        return [str(get_mtime(value))
                for kind, value, basename, elem in self.split_contents()
                if kind == SOURCE_FILE]

    @cached_property
    def cachekey(self):
        return get_hexdigest(''.join(
            [self.content] + self.mtimes).encode(self.charset), 12)

    @cached_property
    def hunks(self):
        for kind, value, basename, elem in self.split_contents():
            if kind == SOURCE_HUNK:
                content = self.filter(value, METHOD_INPUT,
                    elem=elem, kind=kind, basename=basename)
                yield smart_unicode(content)
            elif kind == SOURCE_FILE:
                content = ""
                fd = open(value, 'rb')
                try:
                    content = fd.read()
                except IOError, e:
                    raise UncompressableFileError(
                        "IOError while processing '%s': %s" % (value, e))
                finally:
                    fd.close()
                content = self.filter(content, METHOD_INPUT,
                    filename=value, basename=basename, elem=elem, kind=kind)
                attribs = self.parser.elem_attribs(elem)
                charset = attribs.get("charset", self.charset)
                yield smart_unicode(content, charset.lower())

    @cached_property
    def concat(self):
        return '\n'.join((hunk.encode(self.charset) for hunk in self.hunks))

    def precompile(self, content, kind=None, elem=None, filename=None, **kwargs):
        if not kind:
            return content
        attrs = self.parser.elem_attribs(elem)
        mimetype = attrs.get("type", None)
        if mimetype:
            command = self.all_mimetypes.get(mimetype)
            if command is None:
                if mimetype not in ("text/css", "text/javascript"):
                    raise CompressorError("Couldn't find any precompiler in "
                                          "COMPRESS_PRECOMPILERS setting for "
                                          "mimetype '%s'." % mimetype)
            else:
                return CompilerFilter(content, filter_type=self.type,
                    command=command, filename=filename).output(**kwargs)
        return content

    def filter(self, content, method, **kwargs):
        # run compiler
        if method == METHOD_INPUT:
            content = self.precompile(content, **kwargs)

        for filter_cls in self.cached_filters:
            filter_func = getattr(
                filter_cls(content, filter_type=self.type), method)
            try:
                if callable(filter_func):
                    content = filter_func(**kwargs)
            except NotImplementedError:
                pass
        return content

    @cached_property
    def combined(self):
        return self.filter(self.concat, method=METHOD_OUTPUT)

    def filepath(self, content):
        return os.path.join(settings.COMPRESS_OUTPUT_DIR.strip(os.sep),
            self.output_prefix, "%s.%s" % (get_hexdigest(content, 12), self.type))

    def output(self, mode='file', forced=False):
        """
        The general output method, override in subclass if you need to do
        any custom modification. Calls other mode specific methods or simply
        returns the content directly.
        """
        # First check whether we should do the full compression,
        # including precompilation (or if it's forced)
        if settings.COMPRESS_ENABLED or forced:
            content = self.combined
        elif settings.COMPRESS_PRECOMPILERS:
            # or concatting it, if pre-compilation is enabled
            content = self.concat
        else:
            # or just doing nothing, when neither
            # compression nor compilation is enabled
            return self.content
        # Shortcurcuit in case the content is empty.
        if not content:
            return ''
        # Then check for the appropriate output method and call it
        output_func = getattr(self, "output_%s" % mode, None)
        if callable(output_func):
            return output_func(mode, content, forced)
        # Total failure, raise a general exception
        raise CompressorError(
            "Couldn't find output method for mode '%s'" % mode)

    def output_file(self, mode, content, forced=False):
        """
        The output method that saves the content to a file and renders
        the appropriate template with the file's URL.
        """
        new_filepath = self.filepath(content)
        if not self.storage.exists(new_filepath) or forced:
            self.storage.save(new_filepath, ContentFile(content))
        url = self.storage.url(new_filepath)
        return self.render_output(mode, {"url": url})

    def output_inline(self, mode, content, forced=False):
        """
        The output method that directly returns the content for inline
        display.
        """
        return self.render_output(mode, {"content": content})

    def render_output(self, mode, context=None):
        """
        Renders the compressor output with the appropriate template for
        the given mode and template context.
        """
        if context is None:
            context = {}
        context.update(self.extra_context)
        return render_to_string(
            "compressor/%s_%s.html" % (self.type, mode), context)
