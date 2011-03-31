import fnmatch
import os
import socket
from itertools import chain

from django.core.files.base import ContentFile
from django.core.exceptions import ImproperlyConfigured
from django.template.loader import render_to_string

from compressor.cache import get_hexdigest, get_mtime
from compressor.conf import settings
from compressor.exceptions import UncompressableFileError
from compressor.filters import CompilerFilter
from compressor.storage import default_storage
from compressor.utils import get_class, cached_property


class StorageMixin(object):
#    from django import VERSION as DJANGO_VERSION
#    if DJANGO_VERSION[:2] >= (1, 3):
#        from django.contrib.staticfiles.finders import find as _django_find
#        def _find_file_path(self, path):
#            return self._django_find(path)
#    else:
    def _find_file_path(self, path):
        static_roots = getattr(settings, 'STATIC_ROOTS', []) + [settings.COMPRESS_ROOT]
        for root in static_roots:
            filename = os.path.join(root, path)
            if os.path.exists(filename):
                return filename
        return None
    
    def get_filename(self, file, is_url=True):
        if is_url:
            try:
                base_url = self.storage.base_url
            except AttributeError:
                base_url = settings.COMPRESS_URL
            if not file.startswith(base_url):
                raise UncompressableFileError(
                    "'%s' isn't accesible via COMPRESS_URL ('%s') and can't be"
                    " processed" % (file, base_url))
            res = self._find_file_path(file.replace(base_url, "", 1))
        else:
            res = self._find_file_path(file)
        if res is None:
            raise UncompressableFileError("'%s' does not exist" % file)
        return res

    @cached_property
    def storage(self):
        return default_storage

class PrecompilerMixin(object):
    def matches_patterns(self, path, patterns, options):
        """
        Return True or False depending on whether the ``path`` matches the
        list of give the given patterns.
        """
        if "match" in options:
            patterns = options["match"]
            if not isinstance(patterns, (list, tuple)):
                patterns = (patterns,)
        else:
            patterns = ("*." + ext for ext in ((patterns,) if not isinstance(patterns, (list, tuple)) else patterns))
        for pattern in patterns:
            if fnmatch.fnmatchcase(path, pattern):
                return True
        return False

    def compiler_options(self, kind, filename=None, elem=None, content_type=None):
        if kind == "file" and filename:
            for patterns, options in self.precompilers.items():
                if self.matches_patterns(filename, patterns, options):
                    yield options
        elif kind == "hunk" and elem is not None:
            # get the mimetype of the hunk and handle "text/<type>" or "<type>" cases
            attrs = self.parser.elem_attribs(elem)
            mimetype = attrs.get("type", "").split("/")[-1]
            for options in self.precompilers.values():
                if options.get("mimetype") == mimetype:
                    yield options
        elif kind == "preprocess":
            for patterns, options in self.precompilers.items():
                if (content_type in patterns) if isinstance(patterns, (list, tuple)) else (content_type == patterns):
                    yield options
            

    def precompile(self, content, kind=None, elem=None, filename=None, content_type=None, **kwargs):
        if not kind:
            return content
        for options in self.compiler_options(kind, filename, elem, content_type):
            command = options.get("command")
            if command is None:
                continue
            content = CompilerFilter(content,
                filter_type=self.type, command=command).output(**kwargs)
        return content

class Compressor(StorageMixin, PrecompilerMixin):
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
        self.split_content = []
        self.extra_context = {}

    def split_contents(self):
        """
        To be implemented in a subclass, should return an
        iterable with three values: kind, value, element
        """
        raise NotImplementedError


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

    def concat(self):
        return "\n".join((hunk.encode(self.charset) for hunk in self.hunks))


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
        return self.filter(self.concat(), method="output")

    @cached_property
    def hash(self):
        return get_hexdigest(self.combined)[:12]

    @cached_property
    def new_filepath(self):
        return os.path.join(settings.COMPRESS_OUTPUT_DIR.strip(os.sep),
            self.output_prefix, "%s.%s" % (self.hash, self.type))

    def save_file(self):
        if self.storage.exists(self.new_filepath):
            return False
        self.storage.save(self.new_filepath, ContentFile(self.combined))
        return True

    def output(self, forced=False):
        if not settings.COMPRESS_ENABLED and not forced:
            return self.content
        context = {
            "saved": self.save_file(),
            "url": self.storage.url(self.new_filepath),
        }
        context.update(self.extra_context)
        return render_to_string(self.template_name, context)

    def output_inline(self):
        if settings.COMPRESS_ENABLED:
            content = self.combined
        else:
            content = self.concat()
        context = dict(content=content, **self.extra_context)
        return render_to_string(self.template_name_inline, context)


class Processor(StorageMixin, PrecompilerMixin):
    """
    Base preprocessor object to be subclassed for content type
    depending implementations details.
    """
    type = None

    def __init__(self, value, kind, content_type, output_prefix="preprocessed"):
        if kind == "file":
            path = self.get_filename(value, False)
            with open(path) as f:
                self.content = f.read()
            self.file = path
        else:
            self.content = value
            self.file = None
        self.kind = kind
        self.content_type = content_type
        self.output_prefix = output_prefix
        self.charset = settings.DEFAULT_CHARSET
        self.precompilers = settings.COMPRESS_PRECOMPILERS

    @cached_property
    def mtimes(self):
        if self.kind == "file":
            yield str(get_mtime(self.file))

    @cached_property
    def cachekey(self):
        cachestr = "".join(
            chain([self.content] if self.kind != "file" else [], self.mtimes)).encode(self.charset)
        return "django_compressor.preprocess.%s.%s" % (socket.gethostname(),
                                            get_hexdigest(cachestr)[:12])

    @cached_property
    def hash(self):
        return get_hexdigest(self.content)[:12]

    @cached_property
    def new_filepath(self):
        return os.path.join(settings.COMPRESS_OUTPUT_DIR.strip(os.sep),
            self.output_prefix, "%s.%s" % (self.hash, self.type))

    def save_file(self, content):
        if self.storage.exists(self.new_filepath):
            return False
        self.storage.save(self.new_filepath, ContentFile(content))
        return True

    def output(self, mode="file"):
        content = self.precompile(self.content, kind="preprocess", content_type=self.content_type)
        template_name = self.template_name if mode == "file" else self.template_name_inline 
        context = {
            "saved": self.save_file(content),
            "url": self.storage.url(self.new_filepath),
        }
        #context.update(self.extra_context)
        return render_to_string(template_name, context)
