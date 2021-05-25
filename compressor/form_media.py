import codecs
import os
from importlib import import_module
from urllib.request import url2pathname

from compressor.base import METHOD_INPUT, METHOD_OUTPUT
from compressor.cache import cache_get, cache_set, get_cachekey, get_hexdigest, get_mtime
from compressor.exceptions import FilterDoesNotExist, UncompressableFileError
from compressor.filters import CachedCompilerFilter
from compressor.storage import default_storage
from compressor.utils import get_class, staticfiles
from django.conf import settings
from django.core.files.base import ContentFile
from django.templatetags.static import static
from django.urls import get_mod_func
from django.utils.functional import cached_property
from django.utils.safestring import mark_safe


class FormMedia:
    charset = settings.DEFAULT_CHARSET
    filters = None
    mimetype = None
    output_dir = settings.COMPRESS_OUTPUT_DIR.strip('/')
    precompiler_mimetypes = dict(settings.COMPRESS_PRECOMPILERS)
    resource_kind = None
    storage = default_storage

    def __init__(self, path):
        self.path = path

    def __html__(self):
        return self.render_compressed()

    @cached_property
    def cached_filters(self):
        return [get_class(filter_cls) for filter_cls in self.filters]

    @cached_property
    def cachekey(self):
        filename = self.get_filename(self.path)
        return get_hexdigest(''.join([filename, str(get_mtime(filename))]), 12)

    def filter(self, content, filters, method, **kwargs):
        for filter_cls in filters:
            filter_func = getattr(filter_cls(content, filter_type=self.resource_kind), method)
            try:
                if callable(filter_func):
                    content = filter_func(**kwargs)
            except NotImplementedError:
                pass
        return content

    def filter_input(self, forced=False):
        """
        Passes each hunk (file or code) to the 'input' methods
        of the compressor filters.
        """
        content = []
        for hunk in self.hunks(forced):
            content.append(hunk)
        return content

    def filter_output(self, content):
        """
        Passes the concatenated content to the 'output' methods
        of the compressor filters.
        """
        return self.filter(content, self.cached_filters, method=METHOD_OUTPUT)

    def get_filecontent(self, filename):
        """
        Reads file contents and returns it as text.
        """
        charset = 'utf-8-sig' if self.charset == 'utf-8' else self.charset
        with codecs.open(filename, 'r', charset) as fd:
            try:
                return fd.read()
            except IOError as e:
                raise UncompressableFileError("IOError while processing "
                                              "'%s': %s" % (filename, e))
            except UnicodeDecodeError as e:
                raise UncompressableFileError("UnicodeDecodeError while "
                                              "processing '%s' with "
                                              "charset %s: %s" %
                                              (filename, charset, e))

    def get_filename(self, path):
        """
        Returns full path to a file, for example:

        get_filename('css/one.css') -> '/full/path/to/static/css/one.css'
        """
        filename = None
        # First try finding the file using the storage class.
        # This is skipped in DEBUG mode as files might be outdated in
        # compressor's final destination (COMPRESS_ROOT) during development
        if not settings.DEBUG:
            filename = self.storage.path(path) if self.storage.exists(path) else None
        # secondly try to find it with staticfiles
        if not filename and staticfiles.finders:
            filename = staticfiles.finders.find(url2pathname(path))
        if filename:
            return filename
        # or just raise an exception as the last resort
        raise UncompressableFileError(
            "'%s' could not be found in the COMPRESS_ROOT '%s'%s" %
            (path, settings.COMPRESS_ROOT,
             staticfiles.finders and " or with staticfiles." or "."))

    def get_filepath(self, content, basename=None):
        """
        Returns file path for an output file based on contents.

        Returned path is relative to compressor storage's base url, for
        example "CACHE/css/58a8c0714e59.css".

        When `basename` argument is provided then file name (without extension)
        will be used as a part of returned file name, for example:

        get_filepath(content, "my_file.css") -> 'CACHE/css/my_file.58a8c0714e59.css'
        """
        parts = []
        if basename:
            filename = os.path.split(basename)[1]
            parts.append(os.path.splitext(filename)[0])
        parts.extend([get_hexdigest(content, 12), self.resource_kind])
        return os.path.join(self.output_dir, self.resource_kind, '.'.join(parts))

    def hunks(self, forced=False):
        """
        The heart of content parsing, iterates over the
        list of split contents and looks at its kind
        to decide what to do with it. Should yield a
        bunch of precompiled and/or rendered hunks.
        """
        precompiled = False
        options = {
            'method': METHOD_INPUT,
            'basename': self.path,
            'filename': self.get_filename(self.path),
        }

        value = self.get_filecontent(options['filename'])

        if self.precompiler_mimetypes:
            precompiled, value = self.precompile(value, **options)

        if settings.COMPRESS_ENABLED or forced:
            yield self.filter(value, self.cached_filters, **options)
        elif precompiled:
            for filter_cls in self.cached_filters:
                if filter_cls.run_with_compression_disabled:
                    value = self.filter(value, [filter_cls], **options)
            yield self.output_file(value, forced=True)
        else:
            yield static(self.path)

    def output(self, forced=False, basename=None):
        """
        The general output method, override in subclass if you need to do
        any custom modification. Calls 'output_file' method or simply
        returns the content directly.
        """
        output = '\n'.join(self.filter_input(forced))

        if not output:
            return ''

        if settings.COMPRESS_ENABLED or forced:
            filtered_output = self.filter_output(output)
            return self.output_file(filtered_output, forced, basename)

        return output

    def output_file(self, content, forced=False, basename=None):
        """
        The output method that saves the content to a file and renders
        the appropriate template with the file's URL.
        """
        new_filepath = self.get_filepath(content, basename=basename)
        if not self.storage.exists(new_filepath) or forced:
            self.storage.save(new_filepath, ContentFile(content.encode(self.charset)))
        return mark_safe(self.storage.url(new_filepath))

    def precompile(self, content, filename=None, **kwargs):
        """
        Processes file using a pre compiler.

        This is the place where files like coffee script are processed.
        """
        filter_or_command = self.precompiler_mimetypes.get(self.mimetype)
        if filter_or_command is None:
            return False, content

        mod_name, cls_name = get_mod_func(filter_or_command)
        try:
            mod = import_module(mod_name)
        except (ImportError, TypeError):
            precompiler = CachedCompilerFilter(
                content=content, filter_type=self.resource_kind, filename=filename,
                charset=self.charset, command=filter_or_command, mimetype=self.mimetype)
            return True, precompiler.input(**kwargs)
        try:
            precompiler_class = getattr(mod, cls_name)
        except AttributeError:
            raise FilterDoesNotExist('Could not find "%s".' % filter_or_command)
        precompiler = precompiler_class(
            content, filter_type=self.resource_kind, charset=self.charset,
            filename=filename)
        return True, precompiler.input(**kwargs)

    def render_cached(self):
        """
        If enabled checks the cache for the given compressor's cache key
        and return a tuple of cache key and output
        """
        cache_key = get_cachekey("form_media.%s.file.%s" % (self.cachekey, self.resource_kind))
        cache_content = cache_get(cache_key)
        return cache_key, cache_content

    def render_compressed(self, name=None):
        # Check cache
        cache_key = None
        if settings.COMPRESS_ENABLED:
            cache_key, cache_content = self.render_cached()
            if cache_content is not None:
                return cache_content

        file_basename = name or getattr(self, 'basename', 'output')

        rendered_output = self.output(basename=file_basename)
        if cache_key:
            cache_set(cache_key, rendered_output)
        return rendered_output

    def startswith(self, _):
        # Masquerade as absolute path so that we are returned as-is.
        return True


class CSS(FormMedia):
    """
    Example:

    class CallbackFrom(forms.Form):
        class Media:
            css = {
                'all': (
                    CSS('css/callback.css'),
                )
            }
    """
    filters = settings.COMPRESS_FILTERS['css']
    mimetype = 'text/css'
    resource_kind = 'css'


class JS(FormMedia):
    """
    Example:

    class CallbackFrom(forms.Form):
        class Media:
            js = (
                JS('js/callback.js'),
            )
    """
    filters = settings.COMPRESS_FILTERS['js']
    mimetype = 'text/javascript'
    resource_kind = 'js'
