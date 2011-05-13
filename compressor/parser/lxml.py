from __future__ import absolute_import
from django.core.exceptions import ImproperlyConfigured
from django.utils.encoding import smart_unicode

from compressor.exceptions import ParserError
from compressor.parser import ParserBase
from compressor.utils.decorators import cached_property


class LxmlParser(ParserBase):

    @cached_property
    def tree(self):
        content = '<root>%s</root>' % self.content
        try:
            from lxml.html import fromstring, soupparser
            from lxml.etree import tostring
            self.tostring = tostring
            tree = fromstring(content)
            try:
                ignore = tostring(tree, encoding=unicode)
            except UnicodeDecodeError:
                tree = soupparser.fromstring(content)
        except ImportError, err:
            raise ImproperlyConfigured("Error while importing lxml: %s" % err)
        except Exception, err:
            raise ParserError("Error while initializing Parser: %s" % err)
        else:
            return tree

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
        elem_as_string = smart_unicode(
            self.tostring(elem, method='html', encoding=unicode))
        if elem.tag == 'link':
            # This makes testcases happy
            return elem_as_string.replace('>', ' />')
        return elem_as_string
