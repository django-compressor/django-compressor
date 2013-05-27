from __future__ import absolute_import
from django.core.exceptions import ImproperlyConfigured
from django.utils.encoding import smart_text

from compressor.exceptions import ParserError
from compressor.parser import ParserBase
from compressor.utils.decorators import cached_property


class Html5LibParser(ParserBase):

    def __init__(self, content):
        super(Html5LibParser, self).__init__(content)
        import html5lib
        self.html5lib = html5lib

    def _serialize(self, elem):
        return self.html5lib.serialize(
            elem, tree="etree", quote_attr_values=True,
            omit_optional_tags=False, use_trailing_solidus=True,
        )

    def _find(self, *names):
        for elem in self.html:
            if elem.tag in names:
                yield elem

    @cached_property
    def html(self):
        try:
            return self.html5lib.parseFragment(self.content, treebuilder="etree")
        except ImportError as err:
            raise ImproperlyConfigured("Error while importing html5lib: %s" % err)
        except Exception as err:
            raise ParserError("Error while initializing Parser: %s" % err)

    def css_elems(self):
        return self._find('{http://www.w3.org/1999/xhtml}link',
                          '{http://www.w3.org/1999/xhtml}style')

    def js_elems(self):
        return self._find('{http://www.w3.org/1999/xhtml}script')

    def elem_attribs(self, elem):
        return elem.attrib

    def elem_content(self, elem):
        return smart_text(elem.text)

    def elem_name(self, elem):
        if '}' in elem.tag:
            return elem.tag.split('}')[1]
        return elem.tag

    def elem_str(self, elem):
        # This method serializes HTML in a way that does not pass all tests.
        # However, this method is only called in tests anyway, so it doesn't
        # really matter.
        return smart_text(self._serialize(elem))
