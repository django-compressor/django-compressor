from __future__ import absolute_import, unicode_literals

from django.core.exceptions import ImproperlyConfigured
from django.utils import six
from django.utils.encoding import smart_text

from compressor.exceptions import ParserError
from compressor.parser import ParserBase
from compressor.utils.decorators import cached_property


class LxmlParser(ParserBase):
    """
    LxmlParser will use `lxml.html` parser to parse rendered contents of
    {% compress %} tag. Under python 2 it will also try to use beautiful
    soup parser in case of any problems with encoding.
    """
    def __init__(self, content):
        try:
            from lxml.html import fromstring
            from lxml.etree import tostring
        except ImportError as err:
            raise ImproperlyConfigured("Error while importing lxml: %s" % err)
        except Exception as err:
            raise ParserError("Error while initializing parser: %s" % err)

        if not six.PY3:
            # soupparser uses Beautiful Soup 3 which does not run on python 3.x
            try:
                from lxml.html import soupparser
            except ImportError as err:
                soupparser = None
            except Exception as err:
                raise ParserError("Error while initializing parser: %s" % err)
        else:
            soupparser = None

        self.soupparser = soupparser
        self.fromstring = fromstring
        self.tostring = tostring
        super(LxmlParser, self).__init__(content)

    @cached_property
    def tree(self):
        """
        Document tree.
        """
        content = '<root>%s</root>' % self.content
        tree = self.fromstring(content)
        try:
            self.tostring(tree, encoding=six.text_type)
        except UnicodeDecodeError:
            if self.soupparser:  # use soup parser on python 2
                tree = self.soupparser.fromstring(content)
            else:  # raise an error on python 3
                raise
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
            self.tostring(elem, method='html', encoding=six.text_type))
        if elem.tag == 'link':
            # This makes testcases happy
            return elem_as_string.replace('>', ' />')
        return elem_as_string
