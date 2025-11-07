from django.core.exceptions import ImproperlyConfigured
from django.utils.encoding import smart_str

from compressor.parser import ParserBase


class BeautifulSoupParser(ParserBase):
    def __init__(self, content):
        super().__init__(content)
        try:
            from bs4 import BeautifulSoup

            # Disable multi_valued_attributes
            # http://www.crummy.com/software/BeautifulSoup/bs4/doc/#multi-valued-attributes
            self.soup = BeautifulSoup(self.content, "html.parser", multi_valued_attributes=None)
        except ImportError as err:
            raise ImproperlyConfigured("Error while importing BeautifulSoup: %s" % err)

    def css_elems(self):
        return self.soup.find_all({"link": True, "style": True})

    def js_elems(self):
        return self.soup.find_all("script")

    def elem_attribs(self, elem):
        return elem.attrs

    def elem_content(self, elem):
        return elem.string

    def elem_name(self, elem):
        return elem.name

    def elem_str(self, elem):
        elem_as_string = smart_str(elem)
        if elem.name == "link":
            # This makes testcases happy
            elem_as_string = elem_as_string.replace("/>", ">")
        return elem_as_string
