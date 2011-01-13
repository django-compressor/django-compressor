import os

from django.conf import settings as django_settings
from django.template.loader import render_to_string
from django.core.files.base import ContentFile

from compressor.conf import settings
from compressor import filters
from compressor.exceptions import UncompressableFileError
from compressor.utils import get_hexdigest, get_mtime, get_class

class Compressor(object):

    def __init__(self, content, output_prefix="compressed"):
        self.content = content
        self.type = None
        self.output_prefix = output_prefix
        self.split_content = []
        self._parser = None

    def split_contents(self):
        raise NotImplementedError('split_contents must be defined in a subclass')

    def get_filename(self, url):
        try:
            base_url = self.storage.base_url
        except AttributeError:
            base_url = settings.MEDIA_URL

        if not url.startswith(base_url):
            raise UncompressableFileError('"%s" is not in COMPRESS_URL ("%s") and can not be compressed' % (url, base_url))
        basename = url.replace(base_url, "", 1)
        filename = os.path.join(settings.MEDIA_ROOT, basename)
        if not os.path.exists(filename):
            raise UncompressableFileError('"%s" does not exist' % filename)
        return filename

    def _get_parser(self):
        if self._parser:
            return self._parser
        parser_cls = get_class(settings.PARSER)
        self._parser = parser_cls(self.content)
        return self._parser

    def _set_parser(self, parser):
        self._parser = parser
    parser = property(_get_parser, _set_parser)

    @property
    def mtimes(self):
        return [get_mtime(h[1]) for h in self.split_contents() if h[0] == 'file']

    @property
    def cachekey(self):
        cachebits = [self.content]
        cachebits.extend([str(m) for m in self.mtimes])
        cachestr = "".join(cachebits).encode(django_settings.DEFAULT_CHARSET)
        return "django_compressor.%s" % get_hexdigest(cachestr)[:12]

    @property
    def storage(self):
        from compressor.storage import default_storage
        return default_storage

    @property
    def hunks(self):
        if getattr(self, '_hunks', ''):
            return self._hunks
        self._hunks = []
        for kind, v, elem in self.split_contents():
            attribs = self.parser.elem_attribs(elem)
            if kind == 'hunk':
                input = v
                if self.filters:
                    input = self.filter(input, 'input', elem=elem)
                # Let's cast BeautifulSoup element to unicode here since
                # it will try to encode using ascii internally later
                self._hunks.append(unicode(input))
            if kind == 'file':
                # TODO: wrap this in a try/except for IoErrors(?)
                fd = open(v, 'rb')
                input = fd.read()
                if self.filters:
                    input = self.filter(input, 'input', filename=v, elem=elem)
                charset = attribs.get('charset', django_settings.DEFAULT_CHARSET)
                self._hunks.append(unicode(input, charset))
                fd.close()
        return self._hunks

    def concat(self):
        # Design decision needed: either everything should be unicode up to
        # here or we encode strings as soon as we acquire them. Currently
        # concat() expects all hunks to be unicode and does the encoding
        return "\n".join([hunk.encode(django_settings.DEFAULT_CHARSET) for hunk in self.hunks])

    def filter(self, content, method, **kwargs):
        for f in self.filters:
            filter = getattr(filters.get_class(f)(content, filter_type=self.type), method)
            try:
                if callable(filter):
                    content = filter(**kwargs)
            except NotImplementedError:
                pass
        return content

    @property
    def combined(self):
        if getattr(self, '_output', ''):
            return self._output
        output = self.concat()
        if self.filters:
            output = self.filter(output, 'output')
        self._output = output
        return self._output

    @property
    def hash(self):
        return get_hexdigest(self.combined)[:12]

    @property
    def new_filepath(self):
        filename = "".join([self.hash, self.extension])
        return os.path.join(
            settings.OUTPUT_DIR.strip(os.sep), self.output_prefix, filename)

    def save_file(self):
        if self.storage.exists(self.new_filepath):
            return False
        self.storage.save(self.new_filepath, ContentFile(self.combined))
        return True

    def output(self):
        if not settings.COMPRESS:
            return self.content
        self.save_file()
        context = getattr(self, 'extra_context', {})
        context['url'] = self.storage.url(self.new_filepath)
        return render_to_string(self.template_name, context)

    def output_inline(self):
        context = {'content': settings.COMPRESS and self.combined or self.concat()}
        if hasattr(self, 'extra_context'):
            context.update(self.extra_context)
        return render_to_string(self.template_name_inline, context)
