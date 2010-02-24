import os
from BeautifulSoup import BeautifulSoup

from django import template
from django.conf import settings as django_settings
from django.template.loader import render_to_string
from django.utils.functional import curry

from django.core.files.base import ContentFile
from django.core.files.storage import get_storage_class

from compressor.conf import settings
from compressor import filters


register = template.Library()


class UncompressableFileError(Exception):
    pass


def get_hexdigest(plaintext):
    try:
        import hashlib
        return hashlib.sha1(plaintext).hexdigest()
    except ImportError:
        import sha
        return sha.new(plaintext).hexdigest()


class Compressor(object):

    def __init__(self, content, output_prefix="compressed"):
        self.content = content
        self.type = None
        self.output_prefix = output_prefix
        self.split_content = []
        self.soup = BeautifulSoup(self.content)

    def split_contents(self):
        raise NotImplementedError('split_contents must be defined in a subclass')

    def get_filename(self, url):
        if not url.startswith(self.storage.base_url):
            raise UncompressableFileError('"%s" is not in COMPRESS_URL ("%s") and can not be compressed' % (url, self.storage.base_url))
        basename = url.replace(self.storage.base_url, "", 1)
        if not self.storage.exists(basename):
            raise UncompressableFileError('"%s" does not exist' % self.storage.path(basename))
        return self.storage.path(basename)

    @property
    def mtimes(self):
        return [os.path.getmtime(h[1]) for h in self.split_contents() if h[0] == 'file']

    @property
    def cachekey(self):
        cachebits = [self.content]
        cachebits.extend([str(m) for m in self.mtimes])
        cachestr = "".join(cachebits).encode(django_settings.DEFAULT_CHARSET)
        return "django_compressor.%s" % get_hexdigest(cachestr)[:12]

    @property
    def storage(self):
        return get_storage_class(settings.STORAGE)()

    @property
    def hunks(self):
        if getattr(self, '_hunks', ''):
            return self._hunks
        self._hunks = []
        for kind, v, elem in self.split_contents():
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
                charset = elem.get('charset', django_settings.DEFAULT_CHARSET)
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
        return "/".join((settings.OUTPUT_DIR.strip('/'), self.output_prefix, filename))

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


class CssCompressor(Compressor):

    def __init__(self, content, output_prefix="css"):
        self.extension = ".css"
        self.template_name = "compressor/css.html"
        self.filters = ['compressor.filters.css_default.CssAbsoluteFilter']
        self.filters.extend(settings.COMPRESS_CSS_FILTERS)
        self.type = 'css'
        super(CssCompressor, self).__init__(content, output_prefix)

    def split_contents(self):
        if self.split_content:
            return self.split_content
        split = self.soup.findAll({'link' : True, 'style' : True})
        self.by_media = {}
        for elem in split:
            data = None
            if elem.name == 'link' and elem['rel'] == 'stylesheet':
                try:
                    data = ('file', self.get_filename(elem['href']), elem)
                except UncompressableFileError:
                    if django_settings.DEBUG:
                        raise
            elif elem.name == 'style':
                data = ('hunk', elem.string, elem)
            if data:
                self.split_content.append(data)
                self.by_media.setdefault(elem.get('media', None),
                    CssCompressor(content='')).split_content.append(data)
        return self.split_content

    def output(self):
        self.split_contents()
        if not hasattr(self, 'by_media'):
            return super(CssCompressor, self).output()
        if not settings.COMPRESS:
            return self.content
        ret = []
        for media, subnode in self.by_media.items():
            subnode.extra_context = {'media': media}
            ret.append(subnode.output())
        return ''.join(ret)


class JsCompressor(Compressor):

    def __init__(self, content, output_prefix="js"):
        self.extension = ".js"
        self.template_name = "compressor/js.html"
        self.filters = settings.COMPRESS_JS_FILTERS
        self.type = 'js'
        super(JsCompressor, self).__init__(content, output_prefix)

    def split_contents(self):
        if self.split_content:
            return self.split_content
        split = self.soup.findAll('script')
        for elem in split:
            if elem.has_key('src'):
                try:
                    self.split_content.append(('file', self.get_filename(elem['src']), elem))
                except UncompressableFileError:
                    if django_settings.DEBUG:
                        raise
            else:
                self.split_content.append(('hunk', elem.string, elem))
        return self.split_content
