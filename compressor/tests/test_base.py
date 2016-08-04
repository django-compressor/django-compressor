from __future__ import with_statement, unicode_literals
import os
import re
from tempfile import mkdtemp
from shutil import rmtree, copytree

from bs4 import BeautifulSoup

from django.core.cache.backends import locmem
from django.test import SimpleTestCase
from django.test.utils import override_settings

from compressor import cache as cachemod
from compressor.base import SOURCE_FILE, SOURCE_HUNK
from compressor.cache import get_cachekey, get_precompiler_cachekey, get_hexdigest
from compressor.conf import settings
from compressor.css import CssCompressor
from compressor.exceptions import FilterDoesNotExist, FilterError
from compressor.js import JsCompressor
from compressor.storage import DefaultStorage


def make_soup(markup):
    return BeautifulSoup(markup, "html.parser")


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


class PassthroughPrecompiler(object):
    """A filter whose outputs the input unmodified """
    def __init__(self, content, attrs, filter_type=None, filename=None,
                 charset=None):
        self.content = content

    def input(self, **kwargs):
        return self.content


test_dir = os.path.abspath(os.path.join(os.path.dirname(__file__)))


class PrecompilerAndAbsoluteFilterTestCase(SimpleTestCase):

    def setUp(self):
        self.html_orig = '<link rel="stylesheet" href="/static/css/relative_url.css" type="text/css" />'
        self.html_link_to_precompiled_css = '<link rel="stylesheet" href="/static/CACHE/css/relative_url.41a74f6d5864.css" type="text/css" />'
        self.html_link_to_absolutized_css = '<link rel="stylesheet" href="/static/CACHE/css/relative_url.9b8fd415e521.css" type="text/css" />'
        self.css_orig = "p { background: url('../img/python.png'); }" # content of relative_url.css
        self.css_absolutized = "p { background: url('/static/img/python.png?c2281c83670e'); }"

    def helper(self, enabled, use_precompiler, use_absolute_filter, expected_output):
        precompiler = (('text/css', 'compressor.tests.test_base.PassthroughPrecompiler'),) if use_precompiler else ()
        filters = ('compressor.filters.css_default.CssAbsoluteFilter',) if use_absolute_filter else ()

        with self.settings(COMPRESS_ENABLED=enabled, COMPRESS_PRECOMPILERS=precompiler, COMPRESS_CSS_FILTERS=filters):
            css_node = CssCompressor(self.html_orig)
            output = list(css_node.hunks())[0]
            self.assertEqual(output, expected_output)

    @override_settings(COMPRESS_CSS_HASHING_METHOD="content")
    def test_precompiler_enables_absolute(self):
        """
        Tests whether specifying a precompiler also runs the CssAbsoluteFilter even if
        compression is disabled, but only if the CssAbsoluteFilter is actually contained
        in the filters setting.
        While at it, ensure that everything runs as expected when compression is enabled.
        """
        self.helper(enabled=False, use_precompiler=False, use_absolute_filter=False, expected_output=self.html_orig)
        self.helper(enabled=False, use_precompiler=False, use_absolute_filter=True, expected_output=self.html_orig)
        self.helper(enabled=False, use_precompiler=True, use_absolute_filter=False, expected_output=self.html_link_to_precompiled_css)
        self.helper(enabled=False, use_precompiler=True, use_absolute_filter=True, expected_output=self.html_link_to_absolutized_css)
        self.helper(enabled=True, use_precompiler=False, use_absolute_filter=False, expected_output=self.css_orig)
        self.helper(enabled=True, use_precompiler=False, use_absolute_filter=True, expected_output=self.css_absolutized)
        self.helper(enabled=True, use_precompiler=True, use_absolute_filter=False, expected_output=self.css_orig)
        self.helper(enabled=True, use_precompiler=True, use_absolute_filter=True, expected_output=self.css_absolutized)


@override_settings(
    COMPRESS_ENABLED=True,
    COMPRESS_PRECOMPILERS=(),
    COMPRESS_DEBUG_TOGGLE='nocompress',
)
class CompressorTestCase(SimpleTestCase):

    def setUp(self):
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

    def test_css_output_with_bom_input(self):
        out = 'body { background:#990; }\n.compress-test {color: red;}'
        css = ("""<link rel="stylesheet" href="/static/css/one.css" type="text/css" />
        <link rel="stylesheet" href="/static/css/utf-8_with-BOM.css" type="text/css" />""")
        css_node_with_bom = CssCompressor(css)
        hunks = '\n'.join([h for h in css_node_with_bom.hunks()])
        self.assertEqual(out, hunks)

    def test_css_mtimes(self):
        is_date = re.compile(r'^\d{10}[\.\d]+$')
        for date in self.css_node.mtimes:
            self.assertTrue(is_date.match(str(float(date))),
                "mtimes is returning something that doesn't look like a date: %s" % date)

    @override_settings(COMPRESS_ENABLED=False)
    def test_css_return_if_off(self):
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

    @override_settings(COMPRESS_PRECOMPILERS=(
        ('text/foobar', './foo -I ./bar/baz'),
    ), COMPRESS_ENABLED=True)
    def test_command_with_dot_precompiler(self):
        css = '<style type="text/foobar">p { border:10px solid red;}</style>'
        css_node = CssCompressor(css)
        self.assertRaises(FilterError, css_node.output, 'inline')

    @override_settings(COMPRESS_PRECOMPILERS=(
        ('text/django', 'compressor.filters.template.TemplateFilter'),
    ), COMPRESS_ENABLED=True)
    def test_template_precompiler(self):
        css = '<style type="text/django">p { border:10px solid {% if 1 %}green{% else %}red{% endif %};}</style>'
        css_node = CssCompressor(css)
        output = make_soup(css_node.output('inline'))
        self.assertEqual(output.text, 'p { border:10px solid green;}')


class CssMediaTestCase(SimpleTestCase):
    def setUp(self):
        self.css = """\
<link rel="stylesheet" href="/static/css/one.css" type="text/css" media="screen">
<style type="text/css" media="print">p { border:5px solid green;}</style>
<link rel="stylesheet" href="/static/css/two.css" type="text/css" media="all">
<style type="text/css">h1 { border:5px solid green;}</style>"""

    def test_css_output(self):
        css_node = CssCompressor(self.css)
        links = make_soup(css_node.output()).find_all('link')
        media = ['screen', 'print', 'all', None]
        self.assertEqual(len(links), 4)
        self.assertEqual(media, [l.get('media', None) for l in links])

    def test_avoid_reordering_css(self):
        css = self.css + '<style type="text/css" media="print">p { border:10px solid red;}</style>'
        css_node = CssCompressor(css)
        media = ['screen', 'print', 'all', None, 'print']
        links = make_soup(css_node.output()).find_all('link')
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
        output = make_soup(css_node.output()).find_all(['link', 'style'])
        self.assertEqual(['/static/css/one.css', '/static/css/two.css', None],
                         [l.get('href', None) for l in output])
        self.assertEqual(['screen', 'screen', 'screen'],
                         [l.get('media', None) for l in output])


@override_settings(COMPRESS_VERBOSE=True)
class VerboseTestCase(CompressorTestCase):
    pass


class CacheBackendTestCase(CompressorTestCase):

    def test_correct_backend(self):
        from compressor.cache import cache
        self.assertEqual(cache.__class__, locmem.LocMemCache)


class JsAsyncDeferTestCase(SimpleTestCase):
    def setUp(self):
        self.js = """\
            <script src="/static/js/one.js" type="text/javascript"></script>
            <script src="/static/js/two.js" type="text/javascript" async></script>
            <script src="/static/js/three.js" type="text/javascript" defer></script>
            <script type="text/javascript">obj.value = "value";</script>
            <script src="/static/js/one.js" type="text/javascript" async></script>
            <script src="/static/js/two.js" type="text/javascript" async></script>
            <script src="/static/js/three.js" type="text/javascript"></script>"""

    def test_js_output(self):
        def extract_attr(tag):
            if tag.has_attr('async'):
                return 'async'
            if tag.has_attr('defer'):
                return 'defer'
        js_node = JsCompressor(self.js)
        output = [None, 'async', 'defer', None, 'async', None]
        scripts = make_soup(js_node.output()).find_all('script')
        attrs = [extract_attr(s) for s in scripts]
        self.assertEqual(output, attrs)


class CacheTestCase(SimpleTestCase):

    def setUp(self):
        cachemod._cachekey_func = None

    def test_get_cachekey_basic(self):
        self.assertEqual(get_cachekey("foo"), "django_compressor.foo")

    @override_settings(COMPRESS_CACHE_KEY_FUNCTION='.leading.dot')
    def test_get_cachekey_leading_dot(self):
        self.assertRaises(ImportError, lambda: get_cachekey("foo"))

    @override_settings(COMPRESS_CACHE_KEY_FUNCTION='invalid.module')
    def test_get_cachekey_invalid_mod(self):
        self.assertRaises(ImportError, lambda: get_cachekey("foo"))

    def test_get_precompiler_cachekey(self):
        try:
            get_precompiler_cachekey("asdf", "asdf")
        except TypeError:
            self.fail("get_precompiler_cachekey raised TypeError unexpectedly")


class CompressorInDebugModeTestCase(SimpleTestCase):

    def setUp(self):
        self.css = '<link rel="stylesheet" href="/static/css/one.css" type="text/css" />'
        self.tmpdir = mkdtemp()
        new_static_root = os.path.join(self.tmpdir, "static")
        copytree(settings.STATIC_ROOT, new_static_root)

        self.override_settings = self.settings(
            COMPRESS_ENABLED=True,
            COMPRESS_PRECOMPILERS=(),
            COMPRESS_DEBUG_TOGGLE='nocompress',
            DEBUG=True,
            STATIC_ROOT=new_static_root,
            COMPRESS_ROOT=new_static_root,
            STATICFILES_DIRS=[settings.COMPRESS_ROOT]
        )
        self.override_settings.__enter__()

    def tearDown(self):
        rmtree(self.tmpdir)
        self.override_settings.__exit__(None, None, None)

    def test_filename_in_debug_mode(self):
        # In debug mode, compressor should look for files using staticfiles
        # finders only, and not look into the global static directory, where
        # files can be outdated
        css_filename = os.path.join(settings.COMPRESS_ROOT, "css", "one.css")
        # Store the hash of the original file's content
        with open(css_filename) as f:
            css_content = f.read()
        hashed = get_hexdigest(css_content, 12)
        # Now modify the file in the STATIC_ROOT
        test_css_content = "p { font-family: 'test' }"
        with open(css_filename, "a") as css:
            css.write("\n")
            css.write(test_css_content)
        # We should generate a link with the hash of the original content, not
        # the modified one
        expected = '<link rel="stylesheet" href="/static/CACHE/css/%s.css" type="text/css" />' % hashed
        compressor = CssCompressor(self.css)
        compressor.storage = DefaultStorage()
        output = compressor.output()
        self.assertEqual(expected, output)
        with open(os.path.join(settings.COMPRESS_ROOT, "CACHE", "css",
                               "%s.css" % hashed), "r") as f:
            result = f.read()
        self.assertTrue(test_css_content not in result)
