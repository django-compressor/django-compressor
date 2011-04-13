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
from compressor.utils import get_class, cached_property, get_staticfiles_finders


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
        self.finders = get_staticfiles_finders()

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
        # drop the querystring, which is used for non-compressed cache-busting.
        basename = basename.split("?", 1)[0]
        # first try finding the file in the root
        filename = os.path.join(settings.COMPRESS_ROOT, basename)
        if not os.path.exists(filename):
            # if not found and staticfiles is installed, use it
            if self.finders:
                filename = self.finders.find(basename)
                if filename:
                    return filename
            # or just raise an exception as the last resort
            raise UncompressableFileError(
                "'%s' could not be found in the COMPRESS_ROOT '%s'%s" % (
                    basename, settings.COMPRESS_ROOT,
                    self.finders and " or with staticfiles." or "."))
        return filename

    @cached_property
    def parser(self):
        return get_class(settings.COMPRESS_PARSER)(self.content)

    @cached_property
    def cached_filters(self):
        return [get_class(filter_cls) for filter_cls in self.filters]

    @cached_property
    def mtimes(self):
        return [str(get_mtime(value))
                for kind, value, _ in self.split_contents() if kind == 'file']

    @cached_property
    def cachekey(self):
        key = get_hexdigest(''.join(
            [self.content] + self.mtimes).encode(self.charset), 12)
        return "django_compressor.%s.%s" % (socket.gethostname(), key)

    @cached_property
    def hunks(self):
        for kind, value, elem in self.split_contents():
            if kind == "hunk":
                # Let's cast BeautifulSoup element to unicode here since
                # it will try to encode using ascii internally later
                yield unicode(self.filter(
                    value, method="input", elem=elem, kind=kind))
            elif kind == "file":
                content = ""
                fd = open(value, 'rb')
                try:
                    content = fd.read()
                except IOError, e:
                    raise UncompressableFileError(
                        "IOError while processing '%s': %s" % (value, e))
                finally:
                    fd.close()
                content = self.filter(content,
                    method="input", filename=value, elem=elem, kind=kind)
                attribs = self.parser.elem_attribs(elem)
                charset = attribs.get("charset", self.charset)
                yield unicode(content, charset)

    @cached_property
    def concat(self):
        return '\n'.join((hunk.encode(self.charset) for hunk in self.hunks))

    def precompile(self, content, kind=None, elem=None, filename=None, **kwargs):
        if not kind:
            return content
        attrs = self.parser.elem_attribs(elem)
        mimetype = attrs.get("type", None)
        if mimetype is not None:
            command = self.all_mimetypes.get(mimetype)
            if command is None:
                if mimetype not in ("text/css", "text/javascript"):
                    error = ("Couldn't find any precompiler in "
                             "COMPRESS_PRECOMPILERS setting for "
                             "mimetype '%s'." % mimetype)
                    raise CompressorError(error)
            else:
                content = CompilerFilter(content, filter_type=self.type,
                                         command=command).output(**kwargs)
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
        elif settings.COMPRESS_PRECOMPILERS:
            # or concatting it, if pre-compilation is enabled
            content = self.concat
        else:
            # or just doing nothing, when neither
            # compression nor compilation is enabled
            content = self.concat
        # Shortcurcuit in case the content is empty.
        if not content:
            return ''
        # Then check for the appropriate output method and call it
        output_func = getattr(self, "output_%s" % mode, None)
        if not settings.COMPRESS_ENABLED:
            # In order to raise errors about uncompressable files we still
            # need to fake output.
            output_func = self.output_original
        if callable(output_func):
            return output_func(mode, content, forced)
        # Total failure, raise a general exception
        raise CompressorError(
            "Couldn't find output method for mode '%s'" % mode)

    def output_original(self, mode, content, forced=False):
        '''
        Essentially a do nothing output method.
        '''
        return self.content.strip()

    def output_file(self, mode, content, forced=False):
        """
        The output method that saves the content to a file and renders
        the appropriate template with the file's URL.
        """
        new_filepath = self.filepath(self.content)
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
