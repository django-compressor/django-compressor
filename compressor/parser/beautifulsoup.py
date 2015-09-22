from __future__ import absolute_import
from django.core.exceptions import ImproperlyConfigured
from django.utils.encoding import smart_text

from compressor.parser import ParserBase


class BeautifulSoupParser(ParserBase):

    def __init__(self, content):
        super(BeautifulSoupParser, self).__init__(content)
        try:
            from bs4 import BeautifulSoup
            self.use_bs4 = True
            self.soup = BeautifulSoup(self.content, "html.parser")
        except ImportError:
            try:
                from BeautifulSoup import BeautifulSoup
                self.use_bs4 = False
                self.soup = BeautifulSoup(self.content)
            except ImportError as err:
                raise ImproperlyConfigured("Error while importing BeautifulSoup: %s" % err)

    def css_elems(self):
        if self.use_bs4:
            return self.soup.find_all({'link': True, 'style': True})
        else:
            return self.soup.findAll({'link': True, 'style': True})

    def js_elems(self):
        if self.use_bs4:
            return self.soup.find_all('script')
        else:
            return self.soup.findAll('script')

    def elem_attribs(self, elem):
        return dict(elem.attrs)

    def elem_content(self, elem):
        return elem.string

    def elem_name(self, elem):
        return elem.name

    def elem_str(self, elem):
        return smart_text(elem)
