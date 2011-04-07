import fnmatch
import os
import socket
from itertools import chain

from django.core.files.base import ContentFile
from django.core.exceptions import ImproperlyConfigured
from django.template.loader import render_to_string

from compressor.cache import get_hexdigest, get_mtime
from compressor.conf import settings
from compressor.exceptions import CompressorError, UncompressableFileError
from compressor.filters import CompilerFilter
from compressor.storage import default_storage
from compressor.utils import get_class, cached_property


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
        self.precompilers = settings.COMPRESS_PRECOMPILERS
        self.storage = default_storage
        self.split_content = []
        self.extra_context = {}

    def split_contents(self):
        """
        To be implemented in a subclass, should return an
        iterable with three values: kind, value, element
        """
        raise NotImplementedError

    def get_filename(self, url):
        try:
            base_url = self.storage.base_url
        except AttributeError:
            base_url = settings.COMPRESS_URL
        if not url.startswith(base_url):
            raise UncompressableFileError(
                "'%s' isn't accesible via COMPRESS_URL ('%s') and can't be"
                " compressed" % (url, base_url))
        basename = url.replace(base_url, "", 1)
        filename = os.path.join(settings.COMPRESS_ROOT, basename)
        if not os.path.exists(filename):
            raise UncompressableFileError("'%s' does not exist" % filename)
        return filename

    @cached_property
    def parser(self):
        return get_class(settings.COMPRESS_PARSER)(self.content)

    @cached_property
    def cached_filters(self):
        return [get_class(filter_cls) for filter_cls in self.filters]

    @cached_property
    def mtimes(self):
        for kind, value, elem in self.split_contents():
            if kind == 'file':
                yield str(get_mtime(value))

    @cached_property
    def cachekey(self):
        cachestr = "".join(
            chain([self.content], self.mtimes)).encode(self.charset)
        return "django_compressor.%s.%s" % (socket.gethostname(),
                                            get_hexdigest(cachestr)[:12])

    @cached_property
    def hunks(self):
        for kind, value, elem in self.split_contents():
            if kind == "hunk":
                # Let's cast BeautifulSoup element to unicode here since
                # it will try to encode using ascii internally later
                yield unicode(
                    self.filter(value, method="input", elem=elem, kind=kind))
            elif kind == "file":
                content = ""
                try:
                    fd = open(value, 'rb')
                    try:
                        content = fd.read()
                    finally:
                        fd.close()
                except IOError, e:
                    raise UncompressableFileError(
                        "IOError while processing '%s': %s" % (value, e))
                content = self.filter(content,
                    method="input", filename=value, elem=elem, kind=kind)
                attribs = self.parser.elem_attribs(elem)
                charset = attribs.get("charset", self.charset)
                yield unicode(content, charset)

    @cached_property
    def concat(self):
        return '\n'.join((hunk.encode(self.charset) for hunk in self.hunks))

    def matches_patterns(self, path, patterns=[]):
        """
        Return True or False depending on whether the ``path`` matches the
        list of give the given patterns.
        """
        if not isinstance(patterns, (list, tuple)):
            patterns = (patterns,)
        for pattern in patterns:
            if fnmatch.fnmatchcase(path, pattern):
                return True
        return False

    def compiler_options(self, kind, filename, elem):
        if kind == "file" and filename:
            for patterns, options in self.precompilers.items():
                if self.matches_patterns(filename, patterns):
                    yield options
        elif kind == "hunk" and elem is not None:
            # get the mimetype of the file and handle "text/<type>" cases
            attrs = self.parser.elem_attribs(elem)
            mimetype = attrs.get("type", "").split("/")[-1]
            for options in self.precompilers.values():
                if (mimetype and
                        mimetype == options.get("mimetype", "").split("/")[-1]):
                    yield options

    def precompile(self, content, kind=None, elem=None, filename=None, **kwargs):
        if not kind:
            return content
        for options in self.compiler_options(kind, filename, elem):
            command = options.get("command")
            if command is None:
                continue
            content = CompilerFilter(content,
                filter_type=self.type, command=command).output(**kwargs)
        return content

    def filter(self, content, method, **kwargs):
        # run compiler
        if method == "input":
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
        return self.filter(self.concat, method="output")

    def hash(self, content):
        return get_hexdigest(content)[:12]

    def filepath(self, content):
        return os.path.join(settings.COMPRESS_OUTPUT_DIR.strip(os.sep),
            self.output_prefix, "%s.%s" % (self.hash(content), self.type))

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
        elif self.precompilers:
            # or concatting it, if pre-compilation is enabled
            content = self.concat
        else:
            # or just doing nothing, when neither
            # compression nor compilation is enabled
            return self.content
        # Then check for the appropriate output method and call it
        output_func = getattr(self, "output_%s" % mode, None)
        if callable(output_func):
            return output_func(mode, content)
        # Total failure, raise a general exception
        raise CompressorError(
            "Couldn't find output method for mode '%s'" % mode)

    def output_file(self, mode, content):
        """
        The output method that saves the content to a file and renders
        the appropriate template with the file's URL.
        """
        new_filepath = self.filepath(content)
        if not self.storage.exists(new_filepath):
            self.storage.save(new_filepath, ContentFile(content))
        url = self.storage.url(new_filepath)
        return self.render_output(mode, {"url": url})

    def output_inline(self, mode, content):
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
