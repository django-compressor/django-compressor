from __future__ import absolute_import
from django.core.exceptions import ImproperlyConfigured

from compressor.exceptions import ParserError
from compressor.parser import ParserBase
from compressor.utils.decorators import cached_property
from compressor.utils.compat import smart_text


class LxmlParser(ParserBase):

    def __init__(self, content):
        try:
            from lxml.html import fromstring, soupparser
            from lxml.etree import tostring
            self.fromstring = fromstring
            self.soupparser = soupparser
            self.tostring = tostring
        except ImportError as err:
            raise ImproperlyConfigured("Error while importing lxml: %s" % err)
        except Exception as err:
            raise ParserError("Error while initializing Parser: %s" % err)
        super(LxmlParser, self).__init__(content)

    @cached_property
    def tree(self):
        content = '<root>%s</root>' % self.content
        tree = self.fromstring(content)
        try:
            self.tostring(tree, encoding=unicode)
        except UnicodeDecodeError:
            tree = self.soupparser.fromstring(content)
        return tree

    def css_elems(self):
        return self.tree.xpath('//link[re:test(@rel, "^stylesheet$", "i")]|style',
            namespaces={"re": "http://exslt.org/regular-expressions"})

    def js_elems(self):
        return self.tree.findall('script')

    def elem_attribs(self, elem):
        return elem.attrib

    def elem_content(self, elem):
        return smart_text(elem.text)

    def elem_name(self, elem):
        return elem.tag

    def elem_str(self, elem):
        elem_as_string = smart_text(
            self.tostring(elem, method='html', encoding=unicode))
        if elem.tag == 'link':
            # This makes testcases happy
            return elem_as_string.replace('>', ' />')
        return elem_as_string
