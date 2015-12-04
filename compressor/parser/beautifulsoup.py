from __future__ import absolute_import
from django.core.exceptions import ImproperlyConfigured
from django.utils.encoding import smart_text

from compressor.parser import ParserBase


class BeautifulSoupParser(ParserBase):

    def __init__(self, content):
        super(BeautifulSoupParser, self).__init__(content)
        try:
            from bs4 import BeautifulSoup
            self.soup = BeautifulSoup(self.content, "html.parser")
        except ImportError as err:
            raise ImproperlyConfigured("Error while importing BeautifulSoup: %s" % err)

    def css_elems(self):
        return self.soup.find_all({'link': True, 'style': True})

    def js_elems(self):
        return self.soup.find_all('script')

    def elem_attribs(self, elem):
        attrs = dict(elem.attrs)
        # hack around changed behaviour in bs4, it returns lists now instead of one string, see
        # http://www.crummy.com/software/BeautifulSoup/bs4/doc/#multi-valued-attributes
        for key, value in attrs.items():
            if type(value) is list:
                attrs[key] = " ".join(value)
        return attrs

    def elem_content(self, elem):
        return elem.string

    def elem_name(self, elem):
        return elem.name

    def elem_str(self, elem):
        return smart_text(elem)
