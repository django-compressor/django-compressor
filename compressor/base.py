from __future__ import with_statement
import os
import codecs
import urllib

from django.core.files.base import ContentFile
from django.template import Context
from django.template.loader import render_to_string
from django.utils.encoding import smart_unicode
from django.utils.safestring import mark_safe

from compressor.cache import get_hexdigest, get_mtime

from compressor.conf import settings
from compressor.exceptions import CompressorError, UncompressableFileError
from compressor.filters import CompilerFilter
from compressor.storage import default_storage, compressor_file_storage
from compressor.signals import post_compress
from compressor.utils import get_class, staticfiles
from compressor.utils.decorators import cached_property

# Some constants for nicer handling.
SOURCE_HUNK, SOURCE_FILE = 'inline', 'file'
METHOD_INPUT, METHOD_OUTPUT = 'input', 'output'


class Compressor(object):
    """
    Base compressor object to be subclassed for content type
    depending implementations details.
    """
    type = None

    def __init__(self, content=None, output_prefix=None, context=None, *args, **kwargs):
        self.content = content or ""
        self.output_prefix = output_prefix or "compressed"
        self.output_dir = settings.COMPRESS_OUTPUT_DIR.strip('/')
        self.charset = settings.DEFAULT_CHARSET
        self.storage = default_storage
        self.split_content = []
        self.context = context or {}
        self.extra_context = {}
        self.all_mimetypes = dict(settings.COMPRESS_PRECOMPILERS)
        self.finders = staticfiles.finders

    def split_contents(self):
        """
        To be implemented in a subclass, should return an
        iterable with four values: kind, value, basename, element
        """
        raise NotImplementedError

    def get_template_name(self, mode):
        """
        Returns the template path for the given mode.
        """
        try:
            template = getattr(self, "template_name_%s" % mode)
            if template:
                return template
        except AttributeError:
            pass
        return "compressor/%s_%s.html" % (self.type, mode)

    def get_basename(self, url):
        try:
            base_url = self.storage.base_url
        except AttributeError:
            base_url = settings.COMPRESS_URL
        if not url.startswith(base_url):
            raise UncompressableFileError("'%s' isn't accessible via "
                                          "COMPRESS_URL ('%s') and can't be "
                                          "compressed" % (url, base_url))
        basename = url.replace(base_url, "", 1)
        # drop the querystring, which is used for non-compressed cache-busting.
        return basename.split("?", 1)[0]

    def get_filepath(self, content, basename=None):
        parts = []
        if basename:
            filename = os.path.split(basename)[1]
            parts.append(os.path.splitext(filename)[0])
        parts.extend([get_hexdigest(content, 12), self.type])
        return os.path.join(self.output_dir, self.output_prefix, '.'.join(parts))

    def get_filename(self, basename):
        filename = None
        # first try finding the file in the root
        try:
            # call path first so remote storages don't make it to exists,
            # which would cause network I/O
            filename = self.storage.path(basename)
            if not self.storage.exists(basename):
                filename = None
        except NotImplementedError:
            # remote storages don't implement path, access the file locally
            if compressor_file_storage.exists(basename):
                filename = compressor_file_storage.path(basename)
        # secondly try to find it with staticfiles (in debug mode)
        if not filename and self.finders:
            filename = self.finders.find(urllib.url2pathname(basename))
        if filename:
            return filename
        # or just raise an exception as the last resort
        raise UncompressableFileError(
            "'%s' could not be found in the COMPRESS_ROOT '%s'%s" %
            (basename, settings.COMPRESS_ROOT,
             self.finders and " or with staticfiles." or "."))

    def get_filecontent(self, filename, charset):
        with codecs.open(filename, 'rb', charset) as fd:
            try:
                return fd.read()
            except IOError, e:
                raise UncompressableFileError("IOError while processing "
                                              "'%s': %s" % (filename, e))
            except UnicodeDecodeError, e:
                raise UncompressableFileError("UnicodeDecodeError while "
                                              "processing '%s' with "
                                              "charset %s: %s" %
                                              (filename, charset, e))

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

    def hunks(self, forced=False):
        """
        The heart of content parsing, iterates of the
        list of split contents and looks at its kind
        to decide what to do with it. Should yield a
        bunch of precompiled and/or rendered hunks.
        """
        enabled = settings.COMPRESS_ENABLED or forced

        for kind, value, basename, elem in self.split_contents():
            precompiled = False
            attribs = self.parser.elem_attribs(elem)
            charset = attribs.get("charset", self.charset)
            options = {
                'method': METHOD_INPUT,
                'elem': elem,
                'kind': kind,
                'basename': basename,
            }

            if kind == SOURCE_FILE:
                options = dict(options, filename=value)
                value = self.get_filecontent(value, charset)

            if self.all_mimetypes:
                precompiled, value = self.precompile(value, **options)

            if enabled:
                value = self.filter(value, **options)
                yield smart_unicode(value, charset.lower())
            else:
                if precompiled:
                    value = self.handle_output(kind, value, forced=True, basename=basename)
                    yield smart_unicode(value, charset.lower())
                else:
                    yield self.parser.elem_str(elem)

    def filter_output(self, content):
        """
        Passes the concatenated content to the 'output' methods
        of the compressor filters.
        """
        return self.filter(content, method=METHOD_OUTPUT)

    def filter_input(self, forced=False):
        """
        Passes each hunk (file or code) to the 'input' methods
        of the compressor filters.
        """
        content = []
        for hunk in self.hunks(forced):
            content.append(hunk)
        return content

    def precompile(self, content, kind=None, elem=None, filename=None, **kwargs):
        if not kind:
            return False, content
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
                return True, CompilerFilter(content, filter_type=self.type,
                    command=command, filename=filename).input(**kwargs)
        return False, content

    def filter(self, content, method, **kwargs):
        for filter_cls in self.cached_filters:
            filter_func = getattr(
                filter_cls(content, filter_type=self.type), method)
            try:
                if callable(filter_func):
                    content = filter_func(**kwargs)
            except NotImplementedError:
                pass
        return content

    def output(self, mode='file', forced=False):
        """
        The general output method, override in subclass if you need to do
        any custom modification. Calls other mode specific methods or simply
        returns the content directly.
        """
        content = self.filter_input(forced)
        if not content:
            return ''

        output = '\n'.join(c.encode(self.charset) for c in content)

        if settings.COMPRESS_ENABLED or forced:
            filtered_output = self.filter_output(output)
            return self.handle_output(mode, filtered_output, forced)

        return output

    def handle_output(self, mode, content, forced, basename=None):
        # Then check for the appropriate output method and call it
        output_func = getattr(self, "output_%s" % mode, None)
        if callable(output_func):
            return output_func(mode, content, forced, basename)
        # Total failure, raise a general exception
        raise CompressorError(
            "Couldn't find output method for mode '%s'" % mode)

    def output_file(self, mode, content, forced=False, basename=None):
        """
        The output method that saves the content to a file and renders
        the appropriate template with the file's URL.
        """
        new_filepath = self.get_filepath(content, basename=basename)
        if not self.storage.exists(new_filepath) or forced:
            self.storage.save(new_filepath, ContentFile(content))
        url = mark_safe(self.storage.url(new_filepath))
        return self.render_output(mode, {"url": url})

    def output_inline(self, mode, content, forced=False, basename=None):
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
        # Just in case someone renders the compressor outside
        # the usual template rendering cycle
        if 'compressed' not in self.context:
            self.context['compressed'] = {}

        self.context['compressed'].update(context or {})
        self.context['compressed'].update(self.extra_context)
        final_context = Context(self.context)
        post_compress.send(sender=self.__class__, type=self.type,
                           mode=mode, context=final_context)
        template_name = self.get_template_name(mode)
        return render_to_string(template_name, context_instance=final_context)
