from __future__ import with_statement
import os
from unittest2 import skipIf

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


class ParserTestCase(object):
    def setUp(self):
        self.old_parser = settings.COMPRESS_PARSER
        settings.COMPRESS_PARSER = self.parser_cls
        super(ParserTestCase, self).setUp()

    def tearDown(self):
        settings.COMPRESS_PARSER = self.old_parser


class LxmlParserTests(ParserTestCase, CompressorTestCase):
    parser_cls = 'compressor.parser.LxmlParser'
LxmlParserTests = skipIf(lxml is None, 'lxml not found')(LxmlParserTests)


class Html5LibParserTests(ParserTestCase, CompressorTestCase):
    parser_cls = 'compressor.parser.Html5LibParser'
    # Special test variants required since xml.etree holds attributes
    # as a plain dictionary, e.g. key order is unpredictable.

    def test_css_split(self):
        split = self.css_node.split_contents()
        out0 = (
            SOURCE_FILE,
            os.path.join(settings.COMPRESS_ROOT, u'css', u'one.css'),
            u'css/one.css',
            u'{http://www.w3.org/1999/xhtml}link',
            {u'rel': u'stylesheet', u'href': u'/static/css/one.css',
             u'type': u'text/css'},
        )
        self.assertEqual(out0, split[0][:3] + (split[0][3].tag,
                                               split[0][3].attrib))
        out1 = (
            SOURCE_HUNK,
            u'p { border:5px solid green;}',
            None,
            u'<style type="text/css">p { border:5px solid green;}</style>',
        )
        self.assertEqual(out1, split[1][:3] +
                         (self.css_node.parser.elem_str(split[1][3]),))
        out2 = (
            SOURCE_FILE,
            os.path.join(settings.COMPRESS_ROOT, u'css', u'two.css'),
            u'css/two.css',
            u'{http://www.w3.org/1999/xhtml}link',
            {u'rel': u'stylesheet', u'href': u'/static/css/two.css',
             u'type': u'text/css'},
        )
        self.assertEqual(out2, split[2][:3] + (split[2][3].tag,
                                               split[2][3].attrib))

    def test_js_split(self):
        split = self.js_node.split_contents()
        out0 = (
            SOURCE_FILE,
            os.path.join(settings.COMPRESS_ROOT, u'js', u'one.js'),
            u'js/one.js',
            u'{http://www.w3.org/1999/xhtml}script',
            {u'src': u'/static/js/one.js', u'type': u'text/javascript'},
            None,
        )
        self.assertEqual(out0, split[0][:3] + (split[0][3].tag,
                                               split[0][3].attrib,
                                               split[0][3].text))
        out1 = (
            SOURCE_HUNK,
            u'obj.value = "value";',
            None,
            u'{http://www.w3.org/1999/xhtml}script',
            {u'type': u'text/javascript'},
            u'obj.value = "value";',
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


Html5LibParserTests = skipIf(
    html5lib is None, 'html5lib not found')(Html5LibParserTests)


class BeautifulSoupParserTests(ParserTestCase, CompressorTestCase):
    parser_cls = 'compressor.parser.BeautifulSoupParser'

BeautifulSoupParserTests = skipIf(
    BeautifulSoup is None, 'BeautifulSoup not found')(BeautifulSoupParserTests)


class HtmlParserTests(ParserTestCase, CompressorTestCase):
    parser_cls = 'compressor.parser.HtmlParser'
