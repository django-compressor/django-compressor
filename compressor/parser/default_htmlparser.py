import sys

from django.utils import six
from django.utils.encoding import smart_text

from compressor.exceptions import ParserError
from compressor.parser import ParserBase


# Starting in Python 3.2, the HTMLParser constructor takes a 'strict'
# argument which default to True (which we don't want).
# In Python 3.3, it defaults to False.
# In Python 3.4, passing it at all raises a deprecation warning.
# So we only pass it for 3.2.
# In Python 3.4, it also takes a 'convert_charrefs' argument
# which raises a warning if we don't pass it.
major, minor, release = sys.version_info[:3]
CONSTRUCTOR_TAKES_STRICT = major == 3 and minor == 2
CONSTRUCTOR_TAKES_CONVERT_CHARREFS = major == 3 and minor >= 4
HTML_PARSER_ARGS = {}
if CONSTRUCTOR_TAKES_STRICT:
    HTML_PARSER_ARGS['strict'] = False
if CONSTRUCTOR_TAKES_CONVERT_CHARREFS:
    HTML_PARSER_ARGS['convert_charrefs'] = False


class DefaultHtmlParser(ParserBase, six.moves.html_parser.HTMLParser):
    def __init__(self, content):
        six.moves.html_parser.HTMLParser.__init__(self, **HTML_PARSER_ARGS)
        self.content = content
        self._css_elems = []
        self._js_elems = []
        self._current_tag = None
        try:
            self.feed(self.content)
            self.close()
        except Exception as err:
            lineno = err.lineno
            line = self.content.splitlines()[lineno]
            raise ParserError("Error while initializing HtmlParser: %s (line: %s)" % (err, repr(line)))

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        if tag in ('style', 'script'):
            if tag == 'style':
                tags = self._css_elems
            elif tag == 'script':
                tags = self._js_elems
            tags.append({
                'tag': tag,
                'attrs': attrs,
                'attrs_dict': dict(attrs),
                'text': ''
            })
            self._current_tag = tag
        elif tag == 'link':
            self._css_elems.append({
                'tag': tag,
                'attrs': attrs,
                'attrs_dict': dict(attrs),
                'text': None
            })

    def handle_endtag(self, tag):
        if self._current_tag and self._current_tag == tag.lower():
            self._current_tag = None

    def handle_data(self, data):
        if self._current_tag == 'style':
            self._css_elems[-1]['text'] = data
        elif self._current_tag == 'script':
            self._js_elems[-1]['text'] = data

    def css_elems(self):
        return self._css_elems

    def js_elems(self):
        return self._js_elems

    def elem_name(self, elem):
        return elem['tag']

    def elem_attribs(self, elem):
        return elem['attrs_dict']

    def elem_content(self, elem):
        return smart_text(elem['text'])

    def elem_str(self, elem):
        tag = {}
        tag.update(elem)
        tag['attrs'] = ''
        if len(elem['attrs']):
            tag['attrs'] = ' %s' % ' '.join(['%s="%s"' % (name, value) for name, value in elem['attrs']])
        if elem['tag'] == 'link':
            return '<%(tag)s%(attrs)s />' % tag
        else:
            return '<%(tag)s%(attrs)s>%(text)s</%(tag)s>' % tag
