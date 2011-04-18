from __future__ import absolute_import
from compressor.exceptions import ParserError
from compressor.parser import ParserBase
from django.utils.encoding import smart_unicode

try:
    import html5lib
except ImortError:
    html5lib = None

def _serialize(el):
    fragment = html5lib.treebuilders.simpletree.DocumentFragment()
    fragment.appendChild(el)
    return html5lib.serialize(fragment, quote_attr_values=True,
        omit_optional_tags=False)

def _find(tree, *names):
    for node in tree.childNodes:
        if node.type == 5 and node.name in names:
            yield node

class Html5LibParser(ParserBase):
    _html = None

    @property
    def html(self):
        if self._html is None:
            try:
                import html5lib
                self._html = html5lib.parseFragment(self.content)
            except Exception, e:
                raise ParserError("Error while initializing Parser: %s" % e)
        return self._html


    def css_elems(self):
        return _find(self.html, 'style', 'link')

    def js_elems(self):
        return _find(self.html, 'script')

    def elem_attribs(self, elem):
        return elem.attributes

    def elem_content(self, elem):
        return elem.childNodes[0].value

    def elem_name(self, elem):
        return elem.name

    def elem_str(self, elem):
        return smart_unicode(_serialize(elem))
