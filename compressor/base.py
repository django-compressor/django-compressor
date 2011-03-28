import os
import re
import socket
from itertools import chain
import tempfile
from subprocess import Popen, PIPE

from django.template.loader import render_to_string
from django.core.files.base import ContentFile

from compressor.cache import get_hexdigest, get_mtime
from compressor.conf import settings
from compressor.exceptions import UncompressableFileError, PrecompilerError
from compressor.storage import default_storage
from compressor.utils import get_class, cached_property, cmd_split

class Compressor(object):

    def __init__(self, content=None, output_prefix="compressed"):
        self.content = content or ""
        self.extra_context = {}
        self.type = None
        self.output_prefix = output_prefix
        self.split_content = []
        self.charset = settings.DEFAULT_CHARSET
        self.precompilers = settings.COMPRESS_PRECOMPILERS

    def split_contents(self):
        raise NotImplementedError(
            "split_contents must be defined in a subclass")

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
    def storage(self):
        return default_storage

    @cached_property
    def hunks(self):
        for kind, value, elem in self.split_contents():
            attribs = self.parser.elem_attribs(elem)
            if kind == "hunk":
                # Let's cast BeautifulSoup element to unicode here since
                # it will try to encode using ascii internally later
                yield unicode(self.filter(value, "input", elem=elem, kind=kind))
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
                content = self.filter(content, "input", filename=value, elem=elem, kind=kind)
                yield unicode(content, attribs.get("charset", self.charset))

    def concat(self):
        return "\n".join((hunk.encode(self.charset) for hunk in self.hunks))

    def precompile(self, content, **kwargs):
        type = None
        compiler = None
        elem = kwargs['elem']
        kind = kwargs['kind']
        if kind == "file":
            type = os.path.splitext(kwargs['filename'])[1][1:]
            for pc in self.precompilers:
                if pc.get('extension', None) == type:
                    compiler = pc
                    break
        elif kind == "hunk":
            type = self.parser.elem_attribs(elem).get('type', None)
            slash = type.rindex('/')
            if slash >= 0:
                type = type[slash + 1:]
            for pc in self.precompilers:
                if pc.get('type', None) == type:
                    compiler = pc
                    break
        if not compiler:
            return content
        
        source_file = tempfile.NamedTemporaryFile(mode='w+b', suffix='.' + compiler['extension'])
        dest_file_name = source_file.name[:-len(compiler['extension'])] + compiler['dest_extension']
        dest_dir_name = os.path.split(dest_file_name)[0]
        command = compiler['command'].format(source=source_file.name, dest=dest_file_name, dest_dir=dest_dir_name)
        source_file.write(content)
        source_file.flush()
        try:
            p = Popen(cmd_split(command), stdout=PIPE, stdin=PIPE, stderr=PIPE)
            output, err = p.communicate(self.content)
        except IOError, e:
            raise PrecompilerError(e)
        if p.wait() != 0:
            if not err:
                err = 'Error running pre-compiler with command "{0}"'.format(command)
            raise PrecompilerError(err)
        if compiler.get('stdout', False):
            content = output
        else:
            output_file = open(dest_file_name)
            content = output_file.read()
            output_file.close()
            os.remove(dest_file_name)
        source_file.close()
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
        return self.filter(self.concat(), 'output')

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
