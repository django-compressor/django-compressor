import os
from hashlib import sha1 as hash
from BeautifulSoup import BeautifulSoup

from django import template
from django.template.loader import render_to_string
    
from compressor.conf import settings
from compressor import filters

register = template.Library()


class CompressedNode(template.Node):

    def __init__(self, content, ouput_prefix="compressed"):
        self.content = content
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
            # TODO: Put a proper exception here. Maybe one that only shows up
            # if debug is on.
            raise Exception('FIX THIS EXCPETIONS@!@')
        basename = url[len(settings.MEDIA_URL):]
        filename = os.path.join(settings.MEDIA_ROOT, basename)
        return filename

    def get_hunks(self):
        if getattr(self, '_hunks', ''):
            return self._hunks
        self._hunks = []
        for k, v in self.split_contents():
            if k == 'hunk':
                self._hunks.append(v)
            if k == 'file':
                fd = open(v, 'rb')
                self._hunks.append(fd.read())
                fd.close()
        return self._hunks
    hunks = property(get_hunks)

    def concat(self):
        return "\n".join(self.get_hunks())
        
    def get_output(self):
        if getattr(self, '_output', ''):
            return self._output
        output = self.concat()
        filter_method = getattr(self, 'filter_method', None) 
        if filter_method and self.filters:
            for f in self.filters:
                filter = getattr(filters.get_class(f)(), filter_method)
                if callable(filter):
                    output = filter(output)
        self._output = output
        return self._output
    output = property(get_output)

    def get_hash(self):
        return hash(self.output).hexdigest()[:12]
    hash = property(get_hash)

    def get_new_filepath(self):
        filename = "".join([self.hash, self.extension])
        filepath = "%s/%s/%s" % (settings.OUTPUT_DIR.strip('/'), self.ouput_prefix, filename)
        return filepath
    new_filepath = property(get_new_filepath)
    
    def save_file(self):
        filename = "%s/%s" % (settings.MEDIA_ROOT.rstrip('/'), self.new_filepath)
        if os.path.exists(filename):
            return False
        dirname = os.path.dirname(filename)
        if not os.path.exists(dirname):
            os.makedirs(dirname)
        fd = open(filename, 'wb+')
        fd.write(self.output)
        fd.close()
        return True

    def render(self):
        if not settings.COMPRESS:
            return self.content
        url = "%s/%s" % (settings.MEDIA_URL.rstrip('/'), self.new_filepath)
        self.save_file()
        context = getattr(self, 'extra_context', {})
        context['url'] = url
        return render_to_string(self.template_name, context)


class CompressedCssNode(CompressedNode):

    def __init__(self, content, ouput_prefix="css", media="all"):
        self.extra_context = { 'media': media }
        self.extension = ".css"
        self.template_name = "compressor/css.html"
        self.filters = settings.COMPRESS_CSS_FILTERS
        self.filter_method = 'filter_css'
        super(CompressedCssNode, self).__init__(content, ouput_prefix)

    def split_contents(self):
        if self.split_content:
            return self.split_content
        split = self.soup.findAll({'link' : True, 'style' : True})
        for elem in split:
            if elem.name == 'link' and elem['rel'] == 'stylesheet':
                self.split_content.append(('file', self.get_filename(elem['href'])))
            if elem.name == 'style':
                self.split_content.append(('hunk', elem.string))
        return self.split_content


class CompressedJsNode(CompressedNode):

    def __init__(self, content, ouput_prefix="js"):
        self.extension = ".js"
        self.template_name = "compressor/js.html"
        self.filters = settings.COMPRESS_JS_FILTERS
        self.filter_method = 'filter_js'
        super(CompressedJsNode, self).__init__(content, ouput_prefix)

    def split_contents(self):
        if self.split_content:
            return self.split_content
        split = self.soup.findAll('script')
        for elem in split:
            if elem.has_key('src'):
                self.split_content.append(('file', self.get_filename(elem['src'])))
            else:
                self.split_content.append(('hunk', elem.string))
        return self.split_content

