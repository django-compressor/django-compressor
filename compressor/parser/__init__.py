from django.utils.functional import LazyObject
from django.utils.importlib import import_module

# support legacy parser module usage
from compressor.parser.base import ParserBase
from compressor.parser.lxml import LxmlParser
from compressor.parser.htmlparser import HtmlParser
from compressor.parser.beautifulsoup import BeautifulSoupParser
from compressor.parser.html5lib import Html5LibParser


class AutoSelectParser(LazyObject):
    options = (
        ('lxml.html', LxmlParser),  # lxml, extremely fast
        ('HTMLParser', HtmlParser), # fast and part of the Python stdlib
    )
    def __init__(self, content):
        self._wrapped = None
        self._setup(content)

    def __getattr__(self, name):
        return getattr(self._wrapped, name)

    def _setup(self, content):
        for dependency, parser in self.options:
            try:
                import_module(dependency)
                self._wrapped = parser(content)
                break
            except ImportError:
                continue
