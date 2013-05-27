from __future__ import with_statement
import os

try:
    import lxml
except ImportError:
    lxml = None

try:
    import html5lib
except ImportError:
    html5lib = None

try:
    from BeautifulSoup import BeautifulSoup
except ImportError:
    BeautifulSoup = None


from compressor.base import SOURCE_HUNK, SOURCE_FILE
from compressor.conf import settings
from compressor.tests.test_base import CompressorTestCase

try:
    from django.utils import unittest as ut2
except ImportError:
    import unittest2 as ut2


class ParserTestCase(object):
    def setUp(self):
        self.old_parser = settings.COMPRESS_PARSER
        settings.COMPRESS_PARSER = self.parser_cls
        super(ParserTestCase, self).setUp()

    def tearDown(self):
        settings.COMPRESS_PARSER = self.old_parser


@ut2.skipIf(lxml is None, 'lxml not found')
class LxmlParserTests(ParserTestCase, CompressorTestCase):
    parser_cls = 'compressor.parser.LxmlParser'


@ut2.skipIf(html5lib is None, 'html5lib not found')
class Html5LibParserTests(ParserTestCase, CompressorTestCase):
    parser_cls = 'compressor.parser.Html5LibParser'
    # Special test variants required since xml.etree holds attributes
    # as a plain dictionary, e.g. key order is unpredictable.

    def test_css_split(self):
        split = self.css_node.split_contents()
        out0 = (
            SOURCE_FILE,
            os.path.join(settings.COMPRESS_ROOT, 'css', 'one.css'),
            'css/one.css',
            '{http://www.w3.org/1999/xhtml}link',
            {'rel': 'stylesheet', 'href': '/static/css/one.css',
             'type': 'text/css'},
        )
        self.assertEqual(out0, split[0][:3] + (split[0][3].tag,
                                               split[0][3].attrib))
        out1 = (
            SOURCE_HUNK,
            'p { border:5px solid green;}',
            None,
            '<style type="text/css">p { border:5px solid green;}</style>',
        )
        self.assertEqual(out1, split[1][:3] +
                         (self.css_node.parser.elem_str(split[1][3]),))
        out2 = (
            SOURCE_FILE,
            os.path.join(settings.COMPRESS_ROOT, 'css', 'two.css'),
            'css/two.css',
            '{http://www.w3.org/1999/xhtml}link',
            {'rel': 'stylesheet', 'href': '/static/css/two.css',
             'type': 'text/css'},
        )
        self.assertEqual(out2, split[2][:3] + (split[2][3].tag,
                                               split[2][3].attrib))

    def test_js_split(self):
        split = self.js_node.split_contents()
        out0 = (
            SOURCE_FILE,
            os.path.join(settings.COMPRESS_ROOT, 'js', 'one.js'),
            'js/one.js',
            '{http://www.w3.org/1999/xhtml}script',
            {'src': '/static/js/one.js', 'type': 'text/javascript'},
            None,
        )
        self.assertEqual(out0, split[0][:3] + (split[0][3].tag,
                                               split[0][3].attrib,
                                               split[0][3].text))
        out1 = (
            SOURCE_HUNK,
            'obj.value = "value";',
            None,
            '{http://www.w3.org/1999/xhtml}script',
            {'type': 'text/javascript'},
            'obj.value = "value";',
        )
        self.assertEqual(out1, split[1][:3] + (split[1][3].tag,
                                               split[1][3].attrib,
                                               split[1][3].text))

    def test_css_return_if_off(self):
        settings.COMPRESS_ENABLED = False
        # Yes, they are semantically equal but attributes might be
        # scrambled in unpredictable order. A more elaborate check
        # would require parsing both arguments with a different parser
        # and then evaluating the result, which no longer is
        # a meaningful unit test.
        self.assertEqual(len(self.css), len(self.css_node.output()))

    def test_js_return_if_off(self):
        try:
            enabled = settings.COMPRESS_ENABLED
            precompilers = settings.COMPRESS_PRECOMPILERS
            settings.COMPRESS_ENABLED = False
            settings.COMPRESS_PRECOMPILERS = {}
            # As above.
            self.assertEqual(len(self.js), len(self.js_node.output()))
        finally:
            settings.COMPRESS_ENABLED = enabled
            settings.COMPRESS_PRECOMPILERS = precompilers


@ut2.skipIf(BeautifulSoup is None, 'BeautifulSoup not found')
class BeautifulSoupParserTests(ParserTestCase, CompressorTestCase):
    parser_cls = 'compressor.parser.BeautifulSoupParser'


class HtmlParserTests(ParserTestCase, CompressorTestCase):
    parser_cls = 'compressor.parser.HtmlParser'
