from __future__ import absolute_import
from django.core.exceptions import ImproperlyConfigured
from django.utils import six
from django.utils.encoding import smart_text

from compressor.exceptions import ParserError
from compressor.parser import ParserBase
from compressor.utils.decorators import cached_property


class BeautifulSoupParser(ParserBase):

    @cached_property
    def soup(self):
        try:
            if six.PY3:
                from bs4 import BeautifulSoup
            else:
                from BeautifulSoup import BeautifulSoup
            return BeautifulSoup(self.content)
        except ImportError as err:
            raise ImproperlyConfigured("Error while importing BeautifulSoup: %s" % err)
        except Exception as err:
            raise ParserError("Error while initializing Parser: %s" % err)

    def css_elems(self):
        if six.PY3:
            return self.soup.find_all({'link': True, 'style': True})
        else:
            return self.soup.findAll({'link': True, 'style': True})

    def js_elems(self):
        if six.PY3:
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
