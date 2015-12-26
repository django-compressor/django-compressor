from __future__ import with_statement
import os
import unittest

try:
    import lxml
except ImportError:
    lxml = None

try:
    import html5lib
except ImportError:
    html5lib = None

from django.test.utils import override_settings

from compressor.base import SOURCE_HUNK, SOURCE_FILE
from compressor.conf import settings
from compressor.tests.test_base import CompressorTestCase


class ParserTestCase(object):
    def setUp(self):
        self.override_settings = self.settings(COMPRESS_PARSER=self.parser_cls)
        self.override_settings.__enter__()
        super(ParserTestCase, self).setUp()

    def tearDown(self):
        self.override_settings.__exit__(None, None, None)


@unittest.skipIf(lxml is None, 'lxml not found')
class LxmlParserTests(ParserTestCase, CompressorTestCase):
    parser_cls = 'compressor.parser.LxmlParser'


@unittest.skipIf(html5lib is None, 'html5lib not found')
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

    @override_settings(COMPRESS_ENABLED=False)
    def test_css_return_if_off(self):
        # Yes, they are semantically equal but attributes might be
        # scrambled in unpredictable order. A more elaborate check
        # would require parsing both arguments with a different parser
        # and then evaluating the result, which no longer is
        # a meaningful unit test.
        self.assertEqual(len(self.css), len(self.css_node.output()))

    @override_settings(COMPRESS_PRECOMPILERS=(), COMPRESS_ENABLED=False)
    def test_js_return_if_off(self):
        # As above.
        self.assertEqual(len(self.js), len(self.js_node.output()))


class BeautifulSoupParserTests(ParserTestCase, CompressorTestCase):
    parser_cls = 'compressor.parser.BeautifulSoupParser'
    # just like in the Html5LibParserTests, provide special tests because
    # in bs4 attributes are held in dictionaries

    def test_css_split(self):
        split = self.css_node.split_contents()
        out0 = (
            SOURCE_FILE,
            os.path.join(settings.COMPRESS_ROOT, 'css', 'one.css'),
            'css/one.css',
            None,
            None,
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
            None,
            None,
        )
        self.assertEqual(out2, split[2][:3] + (split[2][3].tag,
                                               split[2][3].attrib))

    @override_settings(COMPRESS_ENABLED=False)
    def test_css_return_if_off(self):
        # in addition to unspecified attribute order,
        # bs4 output doesn't have the extra space, so we add that here
        fixed_output = self.css_node.output().replace('"/>', '" />')
        self.assertEqual(len(self.css), len(fixed_output))


class HtmlParserTests(ParserTestCase, CompressorTestCase):
    parser_cls = 'compressor.parser.HtmlParser'
