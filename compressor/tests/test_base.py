from __future__ import with_statement, unicode_literals
import os
import re

try:
    from bs4 import BeautifulSoup
except ImportError:
    from BeautifulSoup import BeautifulSoup

from django.utils import six
from django.core.cache.backends import locmem
from django.test import SimpleTestCase
from django.test.utils import override_settings

from compressor.base import SOURCE_HUNK, SOURCE_FILE
from compressor.conf import settings
from compressor.css import CssCompressor
from compressor.js import JsCompressor
from compressor.exceptions import FilterDoesNotExist


def make_soup(markup):
    # we use html.parser instead of lxml because it doesn't work on python 3.3
    if six.PY3:
        return BeautifulSoup(markup, 'html.parser')
    else:
        return BeautifulSoup(markup)


def css_tag(href, **kwargs):
    rendered_attrs = ''.join(['%s="%s" ' % (k, v) for k, v in kwargs.items()])
    template = '<link rel="stylesheet" href="%s" type="text/css" %s/>'
    return template % (href, rendered_attrs)


class TestPrecompiler(object):
    """A filter whose output is always the string 'OUTPUT' """
    def __init__(self, content, attrs, filter_type=None, filename=None,
                 charset=None):
        pass

    def input(self, **kwargs):
        return 'OUTPUT'


test_dir = os.path.abspath(os.path.join(os.path.dirname(__file__)))


class CompressorTestCase(SimpleTestCase):

    def setUp(self):
        settings.COMPRESS_ENABLED = True
        settings.COMPRESS_PRECOMPILERS = ()
        settings.COMPRESS_DEBUG_TOGGLE = 'nocompress'
        self.css = """\
<link rel="stylesheet" href="/static/css/one.css" type="text/css" />
<style type="text/css">p { border:5px solid green;}</style>
<link rel="stylesheet" href="/static/css/two.css" type="text/css" />"""
        self.css_node = CssCompressor(self.css)

        self.js = """\
<script src="/static/js/one.js" type="text/javascript"></script>
<script type="text/javascript">obj.value = "value";</script>"""
        self.js_node = JsCompressor(self.js)

    def assertEqualCollapsed(self, a, b):
        """
        assertEqual with internal newlines collapsed to single, and
        trailing whitespace removed.
        """
        collapse = lambda x: re.sub(r'\n+', '\n', x).rstrip()
        self.assertEqual(collapse(a), collapse(b))

    def assertEqualSplits(self, a, b):
        """
        assertEqual for splits, particularly ignoring the presence of
        a trailing newline on the content.
        """
        mangle = lambda split: [(x[0], x[1], x[2], x[3].rstrip()) for x in split]
        self.assertEqual(mangle(a), mangle(b))

    def test_css_split(self):
        out = [
            (
                SOURCE_FILE,
                os.path.join(settings.COMPRESS_ROOT, 'css', 'one.css'),
                'css/one.css', '<link rel="stylesheet" href="/static/css/one.css" type="text/css" />',
            ),
            (
                SOURCE_HUNK,
                'p { border:5px solid green;}',
                None,
                '<style type="text/css">p { border:5px solid green;}</style>',
            ),
            (
                SOURCE_FILE,
                os.path.join(settings.COMPRESS_ROOT, 'css', 'two.css'),
                'css/two.css',
                '<link rel="stylesheet" href="/static/css/two.css" type="text/css" />',
            ),
        ]
        split = self.css_node.split_contents()
        split = [(x[0], x[1], x[2], self.css_node.parser.elem_str(x[3])) for x in split]
        self.assertEqualSplits(split, out)

    def test_css_hunks(self):
        out = ['body { background:#990; }', 'p { border:5px solid green;}', 'body { color:#fff; }']
        self.assertEqual(out, list(self.css_node.hunks()))

    def test_css_output(self):
        out = 'body { background:#990; }\np { border:5px solid green;}\nbody { color:#fff; }'
        hunks = '\n'.join([h for h in self.css_node.hunks()])
        self.assertEqual(out, hunks)

    def test_css_mtimes(self):
        is_date = re.compile(r'^\d{10}[\.\d]+$')
        for date in self.css_node.mtimes:
            self.assertTrue(is_date.match(str(float(date))),
                "mtimes is returning something that doesn't look like a date: %s" % date)

    def test_css_return_if_off(self):
        settings.COMPRESS_ENABLED = False
        self.assertEqualCollapsed(self.css, self.css_node.output())

    def test_cachekey(self):
        is_cachekey = re.compile(r'\w{12}')
        self.assertTrue(is_cachekey.match(self.css_node.cachekey),
            "cachekey is returning something that doesn't look like r'\w{12}'")

    def test_css_return_if_on(self):
        output = css_tag('/static/CACHE/css/e41ba2cc6982.css')
        self.assertEqual(output, self.css_node.output().strip())

    def test_js_split(self):
        out = [
            (
                SOURCE_FILE,
                os.path.join(settings.COMPRESS_ROOT, 'js', 'one.js'),
                'js/one.js',
                '<script src="/static/js/one.js" type="text/javascript"></script>',
            ),
            (
                SOURCE_HUNK,
                'obj.value = "value";',
                None,
                '<script type="text/javascript">obj.value = "value";</script>',
            ),
        ]
        split = self.js_node.split_contents()
        split = [(x[0], x[1], x[2], self.js_node.parser.elem_str(x[3])) for x in split]
        self.assertEqualSplits(split, out)

    def test_js_hunks(self):
        out = ['obj = {};', 'obj.value = "value";']
        self.assertEqual(out, list(self.js_node.hunks()))

    def test_js_output(self):
        out = '<script type="text/javascript" src="/static/CACHE/js/066cd253eada.js"></script>'
        self.assertEqual(out, self.js_node.output())

    def test_js_override_url(self):
        self.js_node.context.update({'url': 'This is not a url, just a text'})
        out = '<script type="text/javascript" src="/static/CACHE/js/066cd253eada.js"></script>'
        self.assertEqual(out, self.js_node.output())

    def test_css_override_url(self):
        self.css_node.context.update({'url': 'This is not a url, just a text'})
        output = css_tag('/static/CACHE/css/e41ba2cc6982.css')
        self.assertEqual(output, self.css_node.output().strip())

    @override_settings(COMPRESS_PRECOMPILERS=(), COMPRESS_ENABLED=False)
    def test_js_return_if_off(self):
        self.assertEqualCollapsed(self.js, self.js_node.output())

    def test_js_return_if_on(self):
        output = '<script type="text/javascript" src="/static/CACHE/js/066cd253eada.js"></script>'
        self.assertEqual(output, self.js_node.output())

    @override_settings(COMPRESS_OUTPUT_DIR='custom')
    def test_custom_output_dir1(self):
        output = '<script type="text/javascript" src="/static/custom/js/066cd253eada.js"></script>'
        self.assertEqual(output, JsCompressor(self.js).output())

    @override_settings(COMPRESS_OUTPUT_DIR='')
    def test_custom_output_dir2(self):
        output = '<script type="text/javascript" src="/static/js/066cd253eada.js"></script>'
        self.assertEqual(output, JsCompressor(self.js).output())

    @override_settings(COMPRESS_OUTPUT_DIR='/custom/nested/')
    def test_custom_output_dir3(self):
        output = '<script type="text/javascript" src="/static/custom/nested/js/066cd253eada.js"></script>'
        self.assertEqual(output, JsCompressor(self.js).output())

    @override_settings(COMPRESS_PRECOMPILERS=(
        ('text/foobar', 'compressor.tests.test_base.TestPrecompiler'),
    ), COMPRESS_ENABLED=True)
    def test_precompiler_class_used(self):
        css = '<style type="text/foobar">p { border:10px solid red;}</style>'
        css_node = CssCompressor(css)
        output = make_soup(css_node.output('inline'))
        self.assertEqual(output.text, 'OUTPUT')

    @override_settings(COMPRESS_PRECOMPILERS=(
        ('text/foobar', 'compressor.tests.test_base.NonexistentFilter'),
    ), COMPRESS_ENABLED=True)
    def test_nonexistent_precompiler_class_error(self):
        css = '<style type="text/foobar">p { border:10px solid red;}</style>'
        css_node = CssCompressor(css)
        self.assertRaises(FilterDoesNotExist, css_node.output, 'inline')


class CssMediaTestCase(SimpleTestCase):
    def setUp(self):
        self.css = """\
<link rel="stylesheet" href="/static/css/one.css" type="text/css" media="screen">
<style type="text/css" media="print">p { border:5px solid green;}</style>
<link rel="stylesheet" href="/static/css/two.css" type="text/css" media="all">
<style type="text/css">h1 { border:5px solid green;}</style>"""

    def test_css_output(self):
        css_node = CssCompressor(self.css)
        if six.PY3:
            links = make_soup(css_node.output()).find_all('link')
        else:
            links = make_soup(css_node.output()).findAll('link')
        media = ['screen', 'print', 'all', None]
        self.assertEqual(len(links), 4)
        self.assertEqual(media, [l.get('media', None) for l in links])

    def test_avoid_reordering_css(self):
        css = self.css + '<style type="text/css" media="print">p { border:10px solid red;}</style>'
        css_node = CssCompressor(css)
        media = ['screen', 'print', 'all', None, 'print']
        if six.PY3:
            links = make_soup(css_node.output()).find_all('link')
        else:
            links = make_soup(css_node.output()).findAll('link')
        self.assertEqual(media, [l.get('media', None) for l in links])

    @override_settings(COMPRESS_PRECOMPILERS=(
        ('text/foobar', 'python %s {infile} {outfile}' % os.path.join(test_dir, 'precompiler.py')),
    ), COMPRESS_ENABLED=False)
    def test_passthough_when_compress_disabled(self):
        css = """\
<link rel="stylesheet" href="/static/css/one.css" type="text/css" media="screen">
<link rel="stylesheet" href="/static/css/two.css" type="text/css" media="screen">
<style type="text/foobar" media="screen">h1 { border:5px solid green;}</style>"""
        css_node = CssCompressor(css)
        if six.PY3:
            output = make_soup(css_node.output()).find_all(['link', 'style'])
        else:
            output = make_soup(css_node.output()).findAll(['link', 'style'])
        self.assertEqual(['/static/css/one.css', '/static/css/two.css', None],
                         [l.get('href', None) for l in output])
        self.assertEqual(['screen', 'screen', 'screen'],
                         [l.get('media', None) for l in output])


class VerboseTestCase(CompressorTestCase):

    def setUp(self):
        super(VerboseTestCase, self).setUp()
        settings.COMPRESS_VERBOSE = True


class CacheBackendTestCase(CompressorTestCase):

    def test_correct_backend(self):
        from compressor.cache import cache
        self.assertEqual(cache.__class__, locmem.CacheClass)
