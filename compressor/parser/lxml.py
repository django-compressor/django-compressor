from __future__ import absolute_import
from compressor.exceptions import ParserError
from compressor.parser import ParserBase

from django.utils.encoding import smart_unicode

class LxmlParser(ParserBase):
    _tree = None

    @property
    def tree(self):
        if self._tree is None:
            try:
                from lxml import html
                from lxml.etree import tostring
            except ImportError, e:
                raise ParserError("Error while initializing Parser: %s" % e)
            else:
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
        return smart_unicode(
            etree.tostring(elem, method='html', encoding=unicode))
