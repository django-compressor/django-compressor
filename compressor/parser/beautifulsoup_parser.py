from compressor.exceptions import ParserError
from compressor.parser import ParserBase
from django.utils.encoding import smart_unicode

class BeautifulSoupParser(ParserBase):
    _soup = None

    @property
    def soup(self):
        if self._soup is None:
            try:
                from BeautifulSoup import BeautifulSoup
            except ImportError, e:
                raise ParserError("Error while initializing Parser: %s" % e)
            self._soup = BeautifulSoup(self.content)
        return self._soup

    def css_elems(self):
        return self.soup.findAll({'link': True, 'style': True})

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
