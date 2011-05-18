from __future__ import absolute_import
from django.core.exceptions import ImproperlyConfigured
from django.utils.encoding import smart_unicode

from compressor.exceptions import ParserError
from compressor.parser import ParserBase
from compressor.utils.decorators import cached_property


class BeautifulSoupParser(ParserBase):

    @cached_property
    def soup(self):
        try:
            from BeautifulSoup import BeautifulSoup
            return BeautifulSoup(self.content)
        except ImportError, err:
            raise ImproperlyConfigured("Error while importing BeautifulSoup: %s" % err)
        except Exception, err:
            raise ParserError("Error while initializing Parser: %s" % err)

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
