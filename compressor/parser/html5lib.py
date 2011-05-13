from __future__ import absolute_import
from django.utils.encoding import smart_unicode
from django.core.exceptions import ImproperlyConfigured

from compressor.exceptions import ParserError
from compressor.parser import ParserBase
from compressor.utils.decorators import cached_property


class Html5LibParser(ParserBase):

    def _serialize(self, elem):
        fragment = self.html5lib.treebuilders.simpletree.DocumentFragment()
        fragment.appendChild(elem)
        return self.html5lib.serialize(fragment,
            quote_attr_values=True, omit_optional_tags=False)

    def _find(self, *names):
        for node in self.html.childNodes:
            if node.type == 5 and node.name in names:
                yield node

    @cached_property
    def html(self):
        try:
            import html5lib
            self.html5lib = html5lib
            return html5lib.parseFragment(self.content)
        except ImportError, err:
            raise ImproperlyConfigured("Error while importing html5lib: %s" % err)
        except Exception, err:
            raise ParserError("Error while initializing Parser: %s" % err)

    def css_elems(self):
        return self._find('style', 'link')

    def js_elems(self):
        return self._find('script')

    def elem_attribs(self, elem):
        return elem.attributes

    def elem_content(self, elem):
        return elem.childNodes[0].value

    def elem_name(self, elem):
        return elem.name

    def elem_str(self, elem):
        # This method serializes HTML in a way that does not pass all tests.
        # However, this method is only called in tests anyway, so it doesn't
        # really matter.
        return smart_unicode(self._serialize(elem))
