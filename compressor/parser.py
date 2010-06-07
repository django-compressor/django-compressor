from django.conf import settings as django_settings
from django.utils.encoding import smart_unicode

from compressor.conf import settings
from compressor.exceptions import ParserError
from compressor.utils import get_class

class ParserBase(object):

    def __init__(self, content):
        self.content = content

    def css_elems(self):
        """
        Return an iterable containing the css elements to handle
        """
        raise NotImplementedError

    def js_elems(self):
        """
        Return an iterable containing the js elements to handle
        """
        raise NotImplementedError

    def elem_attribs(self, elem):
        """
        Return the dictionary like attribute store of the given element
        """
        raise NotImplementedError

    def elem_content(self, elem):
        """
        Return the content of the given element
        """
        raise NotImplementedError

    def elem_name(self, elem):
        """
        Return the name of the given element
        """
        raise NotImplementedError

    def elem_str(self, elem):
        """
        Return the string representation of the given elem
        """
        raise NotImplementedError

class BeautifulSoupParser(ParserBase):
    _soup = None

    @property
    def soup(self):
        try:
            from BeautifulSoup import BeautifulSoup
        except ImportError, e:
            raise ParserError("Error while initializing Parser: %s" % e)
        if self._soup is None:
            self._soup = BeautifulSoup(self.content)
        return self._soup

    def css_elems(self):
        return self.soup.findAll({'link' : True, 'style' : True})

    def js_elems(self):
        return self.soup.findAll('script')

    def elem_attribs(self, elem):
        return dict(elem.attrs)

    def elem_content(self, elem):
        return elem.string

    def elem_name(self, elem):
        return elem.name

    def elem_str(self, elem):
        return smart_unicode(elem)

class LxmlParser(ParserBase):
    _tree = None

    @property
    def tree(self):
        try:
            from lxml import html
            from lxml.etree import tostring
        except ImportError, e:
            raise ParserError("Error while initializing Parser: %s" % e)
        if self._tree is None:
            content = '<root>%s</root>' % self.content
            self._tree = html.fromstring(content)
            try:
                ignore = tostring(self._tree, encoding=unicode)
            except UnicodeDecodeError:
                self._tree = html.soupparser.fromstring(content)
        return self._tree

    def css_elems(self):
        return self.tree.xpath('link[@rel="stylesheet"]|style')

    def js_elems(self):
        return self.tree.findall('script')

    def elem_attribs(self, elem):
        return elem.attrib

    def elem_content(self, elem):
        return smart_unicode(elem.text)

    def elem_name(self, elem):
        return elem.tag

    def elem_str(self, elem):
        from lxml import etree
        return smart_unicode(etree.tostring(elem, method='html', encoding=unicode))
