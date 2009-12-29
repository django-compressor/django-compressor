import os
from BeautifulSoup import BeautifulSoup

from django import template
from django.conf import settings as django_settings
from django.template.loader import render_to_string

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

    def __init__(self, content, ouput_prefix="compressed"):
        self.content = content
        self.type = None
        self.ouput_prefix = ouput_prefix
        self.split_content = []
        self.soup = BeautifulSoup(self.content)

    def content_hash(self):
        """docstring for content_hash"""
        pass

    def split_contents(self):
        raise NotImplementedError('split_contents must be defined in a subclass')

    def get_filename(self, url):
        if not url.startswith(settings.MEDIA_URL):
            raise UncompressableFileError('"%s" is not in COMPRESS_URL ("%s") and can not be compressed' % (url, settings.MEDIA_URL))
        # .lstrip used to remove leading slashes because os.path.join
        # counterintuitively takes "/foo/bar" and "/baaz" to produce "/baaz",
        # not the "/foo/bar/baaz" which you might expect:
        basename = url.replace(settings.MEDIA_URL, "", 1).lstrip("/")
        filename = os.path.join(settings.MEDIA_ROOT, basename)
        if not os.path.exists(filename):
            raise UncompressableFileError('"%s" does not exist' % (filename,))
        return filename

    @property
    def mtimes(self):
        return [os.path.getmtime(h[1]) for h in self.split_contents() if h[0] == 'file']

    @property
    def cachekey(self):
        cachebits = [self.content]
        cachebits.extend([str(m) for m in self.mtimes])
        cachestr = "".join(cachebits)
        return "django_compressor.%s" % get_hexdigest(cachestr)[:12]

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
                self._hunks.append(input)
            if kind == 'file':
                # TODO: wrap this in a try/except for IoErrors(?)
                fd = open(v, 'rb')
                input = fd.read()
                if self.filters:
                    input = self.filter(input, 'input', filename=v, elem=elem)
                self._hunks.append(input)
                fd.close()
        return self._hunks

    def concat(self):
        # if any of the hunks are unicode, all of them will be coerced
        # this breaks any hunks with non-ASCII data in them
        return "\n".join([str(hunk) for hunk in self.hunks])

    def filter(self, content, method, **kwargs):
        content = content
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
        filter_method = getattr(self, 'filter_method', None)
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
        filepath = "%s/%s/%s" % (settings.OUTPUT_DIR.strip('/'), self.ouput_prefix, filename)
        return filepath

    def save_file(self):
        filename = "%s/%s" % (settings.MEDIA_ROOT.rstrip('/'), self.new_filepath)
        if os.path.exists(filename):
            return False
        dirname = os.path.dirname(filename)
        if not os.path.exists(dirname):
            os.makedirs(dirname)
        fd = open(filename, 'wb+')
        fd.write(self.combined)
        fd.close()
        return True

    def output(self):
        if not settings.COMPRESS:
            return self.content
        url = "%s/%s" % (settings.MEDIA_URL.rstrip('/'), self.new_filepath)
        self.save_file()
        context = getattr(self, 'extra_context', {})
        context['url'] = url
        return render_to_string(self.template_name, context)


class CssCompressor(Compressor):

    def __init__(self, content, ouput_prefix="css"):
        self.extension = ".css"
        self.template_name = "compressor/css.html"
        self.filters = ['compressor.filters.css_default.CssAbsoluteFilter', 'compressor.filters.css_default.CssMediaFilter']
        self.filters.extend(settings.COMPRESS_CSS_FILTERS)
        self.type = 'css'
        super(CssCompressor, self).__init__(content, ouput_prefix)

    def split_contents(self):
        if self.split_content:
            return self.split_content
        split = self.soup.findAll({'link' : True, 'style' : True})
        for elem in split:
            if elem.name == 'link' and elem['rel'] == 'stylesheet':
                # TODO: Make sure this doesn't break when debug is off. I was thinking it would just skip over but it 500's :(
                try:
                    self.split_content.append(('file', self.get_filename(elem['href']), elem))
                except UncompressableFileError:
                    if django_settings.DEBUG:
                        raise
            if elem.name == 'style':
                self.split_content.append(('hunk', elem.string, elem))
        return self.split_content


class JsCompressor(Compressor):

    def __init__(self, content, ouput_prefix="js"):
        self.extension = ".js"
        self.template_name = "compressor/js.html"
        self.filters = settings.COMPRESS_JS_FILTERS
        self.type = 'js'
        super(JsCompressor, self).__init__(content, ouput_prefix)

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
