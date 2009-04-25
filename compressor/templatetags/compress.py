import os
from BeautifulSoup import BeautifulSoup

from django import template
from compressor.conf import settings

register = template.Library()


class CompressedNode(template.Node):

    def __init__(self, content, ouput_prefix="compressed"):
        self.content = content
        self.ouput_prefix = ouput_prefix
        self.hunks = []
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
        if self.hunks:
            return self.hunks
        for k, v in self.split_contents():
            if k == 'hunk':
                self.hunks.append(v)
            if k == 'file':
                fd = open(v, 'rb')
                self.hunks.append(fd.read())
                fd.close()
        return self.hunks

    def concat(self):
        return "\n".join(self.get_hunks())

    def render(self):
        if not settings.COMPRESS:
            return self.content
        return "fail"


class CompressedCssNode(CompressedNode):

    def __init__(self, content, ouput_prefix="css", media="all"):
        self.media = media
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

