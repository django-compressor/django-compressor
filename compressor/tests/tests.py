from __future__ import with_statement
import os
import re
import sys
from unittest2 import skipIf

from BeautifulSoup import BeautifulSoup

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

from django.core.cache.backends import dummy
from django.core.files.storage import get_storage_class
from django.template import Template, Context, TemplateSyntaxError
from django.test import TestCase

from compressor import base
from compressor.base import SOURCE_HUNK, SOURCE_FILE
from compressor.cache import get_hashed_mtime, get_hexdigest
from compressor.conf import settings
from compressor.css import CssCompressor
from compressor.js import JsCompressor
from compressor.management.commands.compress import Command as CompressCommand
from compressor.utils import find_command
from compressor.filters.base import CompilerFilter


class CompressorTestCase(TestCase):

    def setUp(self):
        self.maxDiff = None
        settings.COMPRESS_ENABLED = True
        settings.COMPRESS_PRECOMPILERS = {}
        settings.COMPRESS_DEBUG_TOGGLE = 'nocompress'
        self.css = """
        <link rel="stylesheet" href="/media/css/one.css" type="text/css" charset="utf-8">
        <style type="text/css">p { border:5px solid green;}</style>
        <link rel="stylesheet" href="/media/css/two.css" type="text/css" charset="utf-8">
        """
        self.css_node = CssCompressor(self.css)

        self.js = """
        <script src="/media/js/one.js" type="text/javascript" charset="utf-8"></script>
        <script type="text/javascript" charset="utf-8">obj.value = "value";</script>
        """
        self.js_node = JsCompressor(self.js)

    def test_css_split(self):
        out = [
            (SOURCE_FILE, os.path.join(settings.COMPRESS_ROOT, u'css/one.css'), u'css/one.css', u'<link rel="stylesheet" href="/media/css/one.css" type="text/css" charset="utf-8" />'),
            (SOURCE_HUNK, u'p { border:5px solid green;}', None, u'<style type="text/css">p { border:5px solid green;}</style>'),
            (SOURCE_FILE, os.path.join(settings.COMPRESS_ROOT, u'css/two.css'), u'css/two.css', u'<link rel="stylesheet" href="/media/css/two.css" type="text/css" charset="utf-8" />'),
        ]
        split = self.css_node.split_contents()
        split = [(x[0], x[1], x[2], self.css_node.parser.elem_str(x[3])) for x in split]
        self.assertEqual(out, split)

    def test_css_hunks(self):
        out = ['body { background:#990; }', u'p { border:5px solid green;}', 'body { color:#fff; }']
        self.assertEqual(out, list(self.css_node.hunks))

    def test_css_output(self):
        out = u'body { background:#990; }\np { border:5px solid green;}\nbody { color:#fff; }'
        self.assertEqual(out, self.css_node.combined)

    def test_css_mtimes(self):
        is_date = re.compile(r'^\d{10}[\.\d]+$')
        for date in self.css_node.mtimes:
            self.assertTrue(is_date.match(str(float(date))),
                "mtimes is returning something that doesn't look like a date: %s" % date)

    def test_css_return_if_off(self):
        settings.COMPRESS_ENABLED = False
        self.assertEqual(self.css, self.css_node.output())

    def test_cachekey(self):
        is_cachekey = re.compile(r'\w{12}')
        self.assertTrue(is_cachekey.match(self.css_node.cachekey),
            "cachekey is returning something that doesn't look like r'\w{12}'")

    def test_css_hash(self):
        self.assertEqual('c618e6846d04', get_hexdigest(self.css, 12))

    def test_css_return_if_on(self):
        output = u'<link rel="stylesheet" href="/media/CACHE/css/e41ba2cc6982.css" type="text/css">'
        self.assertEqual(output, self.css_node.output().strip())

    def test_js_split(self):
        out = [(SOURCE_FILE, os.path.join(settings.COMPRESS_ROOT, u'js/one.js'), u'js/one.js', '<script src="/media/js/one.js" type="text/javascript" charset="utf-8"></script>'),
         (SOURCE_HUNK, u'obj.value = "value";', None, '<script type="text/javascript" charset="utf-8">obj.value = "value";</script>')
         ]
        split = self.js_node.split_contents()
        split = [(x[0], x[1], x[2], self.js_node.parser.elem_str(x[3])) for x in split]
        self.assertEqual(out, split)

    def test_js_hunks(self):
        out = ['obj = {};', u'obj.value = "value";']
        self.assertEqual(out, list(self.js_node.hunks))

    def test_js_concat(self):
        out = u'obj = {};\nobj.value = "value";'
        self.assertEqual(out, self.js_node.concat)

    def test_js_output(self):
        out = u'obj={};obj.value="value";'
        self.assertEqual(out, self.js_node.combined)

    def test_js_return_if_off(self):
        try:
            enabled = settings.COMPRESS_ENABLED
            precompilers = settings.COMPRESS_PRECOMPILERS
            settings.COMPRESS_ENABLED = False
            settings.COMPRESS_PRECOMPILERS = {}
            self.assertEqual(self.js, self.js_node.output())
        finally:
            settings.COMPRESS_ENABLED = enabled
            settings.COMPRESS_PRECOMPILERS = precompilers

    def test_js_return_if_on(self):
        output = u'<script type="text/javascript" src="/media/CACHE/js/066cd253eada.js" charset="utf-8"></script>'
        self.assertEqual(output, self.js_node.output())

    def test_custom_output_dir(self):
        try:
            old_output_dir = settings.COMPRESS_OUTPUT_DIR
            settings.COMPRESS_OUTPUT_DIR = 'custom'
            output = u'<script type="text/javascript" src="/media/custom/js/066cd253eada.js" charset="utf-8"></script>'
            self.assertEqual(output, JsCompressor(self.js).output())
            settings.COMPRESS_OUTPUT_DIR = ''
            output = u'<script type="text/javascript" src="/media/js/066cd253eada.js" charset="utf-8"></script>'
            self.assertEqual(output, JsCompressor(self.js).output())
            settings.COMPRESS_OUTPUT_DIR = '/custom/nested/'
            output = u'<script type="text/javascript" src="/media/custom/nested/js/066cd253eada.js" charset="utf-8"></script>'
            self.assertEqual(output, JsCompressor(self.js).output())
        finally:
            settings.COMPRESS_OUTPUT_DIR = old_output_dir


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

    def test_css_split(self):
        out = [
            (SOURCE_FILE, os.path.join(settings.COMPRESS_ROOT, u'css/one.css'), u'css/one.css', u'<link charset="utf-8" href="/media/css/one.css" rel="stylesheet" type="text/css">'),
            (SOURCE_HUNK, u'p { border:5px solid green;}', None, u'<style type="text/css">p { border:5px solid green;}</style>'),
            (SOURCE_FILE, os.path.join(settings.COMPRESS_ROOT, u'css/two.css'), u'css/two.css', u'<link charset="utf-8" href="/media/css/two.css" rel="stylesheet" type="text/css">'),
        ]
        split = self.css_node.split_contents()
        split = [(x[0], x[1], x[2], self.css_node.parser.elem_str(x[3])) for x in split]
        self.assertEqual(out, split)

    def test_js_split(self):
        out = [(SOURCE_FILE, os.path.join(settings.COMPRESS_ROOT, u'js/one.js'), u'js/one.js', u'<script charset="utf-8" src="/media/js/one.js" type="text/javascript"></script>'),
         (SOURCE_HUNK, u'obj.value = "value";', None, u'<script charset="utf-8" type="text/javascript">obj.value = "value";</script>')
         ]
        split = self.js_node.split_contents()
        split = [(x[0], x[1], x[2], self.js_node.parser.elem_str(x[3])) for x in split]
        self.assertEqual(out, split)

Html5LibParserTests = skipIf(
    html5lib is None, 'html5lib not found')(Html5LibParserTests)


class BeautifulSoupParserTests(ParserTestCase, CompressorTestCase):
    parser_cls = 'compressor.parser.BeautifulSoupParser'

BeautifulSoupParserTests = skipIf(
    BeautifulSoup is None, 'BeautifulSoup not found')(BeautifulSoupParserTests)


class HtmlParserTests(ParserTestCase, CompressorTestCase):
    parser_cls = 'compressor.parser.HtmlParser'


class CssAbsolutizingTestCase(TestCase):
    def setUp(self):
        settings.COMPRESS_ENABLED = True
        settings.COMPRESS_URL = '/media/'
        self.css = """
        <link rel="stylesheet" href="/media/css/url/url1.css" type="text/css" charset="utf-8">
        <link rel="stylesheet" href="/media/css/url/2/url2.css" type="text/css" charset="utf-8">
        """
        self.css_node = CssCompressor(self.css)

    def test_css_absolute_filter(self):
        from compressor.filters.css_default import CssAbsoluteFilter
        filename = os.path.join(settings.COMPRESS_ROOT, 'css/url/test.css')
        content = "p { background: url('../../images/image.gif') }"
        output = "p { background: url('%simages/image.gif?%s') }" % (settings.COMPRESS_URL, get_hashed_mtime(filename))
        filter = CssAbsoluteFilter(content)
        self.assertEqual(output, filter.input(filename=filename, basename='css/url/test.css'))
        settings.COMPRESS_URL = 'http://media.example.com/'
        filter = CssAbsoluteFilter(content)
        filename = os.path.join(settings.COMPRESS_ROOT, 'css/url/test.css')
        output = "p { background: url('%simages/image.gif?%s') }" % (settings.COMPRESS_URL, get_hashed_mtime(filename))
        self.assertEqual(output, filter.input(filename=filename, basename='css/url/test.css'))

    def test_css_absolute_filter_https(self):
        from compressor.filters.css_default import CssAbsoluteFilter
        filename = os.path.join(settings.COMPRESS_ROOT, 'css/url/test.css')
        content = "p { background: url('../../images/image.gif') }"
        output = "p { background: url('%simages/image.gif?%s') }" % (settings.COMPRESS_URL, get_hashed_mtime(filename))
        filter = CssAbsoluteFilter(content)
        self.assertEqual(output, filter.input(filename=filename, basename='css/url/test.css'))
        settings.COMPRESS_URL = 'https://media.example.com/'
        filter = CssAbsoluteFilter(content)
        filename = os.path.join(settings.COMPRESS_ROOT, 'css/url/test.css')
        output = "p { background: url('%simages/image.gif?%s') }" % (settings.COMPRESS_URL, get_hashed_mtime(filename))
        self.assertEqual(output, filter.input(filename=filename, basename='css/url/test.css'))

    def test_css_absolute_filter_relative_path(self):
        from compressor.filters.css_default import CssAbsoluteFilter
        filename = os.path.join(settings.TEST_DIR, 'whatever', '..', 'media', 'whatever/../css/url/test.css')
        content = "p { background: url('../../images/image.gif') }"
        output = "p { background: url('%simages/image.gif?%s') }" % (settings.COMPRESS_URL, get_hashed_mtime(filename))
        filter = CssAbsoluteFilter(content)
        self.assertEqual(output, filter.input(filename=filename, basename='css/url/test.css'))
        settings.COMPRESS_URL = 'https://media.example.com/'
        filter = CssAbsoluteFilter(content)
        output = "p { background: url('%simages/image.gif?%s') }" % (settings.COMPRESS_URL, get_hashed_mtime(filename))
        self.assertEqual(output, filter.input(filename=filename, basename='css/url/test.css'))

    def test_css_hunks(self):
        hash_dict = {
            'hash1': get_hashed_mtime(os.path.join(settings.COMPRESS_ROOT, 'css/url/url1.css')),
            'hash2': get_hashed_mtime(os.path.join(settings.COMPRESS_ROOT, 'css/url/2/url2.css')),
        }
        out = [u"p { background: url('/media/images/test.png?%(hash1)s'); }\np { background: url('/media/images/test.png?%(hash1)s'); }\np { background: url('/media/images/test.png?%(hash1)s'); }\np { background: url('/media/images/test.png?%(hash1)s'); }\n" % hash_dict,
               u"p { background: url('/media/images/test.png?%(hash2)s'); }\np { background: url('/media/images/test.png?%(hash2)s'); }\np { background: url('/media/images/test.png?%(hash2)s'); }\np { background: url('/media/images/test.png?%(hash2)s'); }\n" % hash_dict]
        self.assertEqual(out, list(self.css_node.hunks))


class CssDataUriTestCase(TestCase):
    def setUp(self):
        settings.COMPRESS_ENABLED = True
        settings.COMPRESS_CSS_FILTERS = [
            'compressor.filters.css_default.CssAbsoluteFilter',
            'compressor.filters.datauri.CssDataUriFilter',
        ]
        settings.COMPRESS_URL = '/media/'
        self.css = """
        <link rel="stylesheet" href="/media/css/datauri.css" type="text/css" charset="utf-8">
        """
        self.css_node = CssCompressor(self.css)

    def test_data_uris(self):
        datauri_hash = get_hashed_mtime(os.path.join(settings.COMPRESS_ROOT, 'css/datauri.css'))
        out = [u'.add { background-image: url("data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAABGdBTUEAAK/INwWK6QAAABl0RVh0U29mdHdhcmUAQWRvYmUgSW1hZ2VSZWFkeXHJZTwAAAJvSURBVDjLpZPrS5NhGIf9W7YvBYOkhlkoqCklWChv2WyKik7blnNris72bi6dus0DLZ0TDxW1odtopDs4D8MDZuLU0kXq61CijSIIasOvv94VTUfLiB74fXngup7nvrnvJABJ/5PfLnTTdcwOj4RsdYmo5glBWP6iOtzwvIKSWstI0Wgx80SBblpKtE9KQs/We7EaWoT/8wbWP61gMmCH0lMDvokT4j25TiQU/ITFkek9Ow6+7WH2gwsmahCPdwyw75uw9HEO2gUZSkfyI9zBPCJOoJ2SMmg46N61YO/rNoa39Xi41oFuXysMfh36/Fp0b7bAfWAH6RGi0HglWNCbzYgJaFjRv6zGuy+b9It96N3SQvNKiV9HvSaDfFEIxXItnPs23BzJQd6DDEVM0OKsoVwBG/1VMzpXVWhbkUM2K4oJBDYuGmbKIJ0qxsAbHfRLzbjcnUbFBIpx/qH3vQv9b3U03IQ/HfFkERTzfFj8w8jSpR7GBE123uFEYAzaDRIqX/2JAtJbDat/COkd7CNBva2cMvq0MGxp0PRSCPF8BXjWG3FgNHc9XPT71Ojy3sMFdfJRCeKxEsVtKwFHwALZfCUk3tIfNR8XiJwc1LmL4dg141JPKtj3WUdNFJqLGFVPC4OkR4BxajTWsChY64wmCnMxsWPCHcutKBxMVp5mxA1S+aMComToaqTRUQknLTH62kHOVEE+VQnjahscNCy0cMBWsSI0TCQcZc5ALkEYckL5A5noWSBhfm2AecMAjbcRWV0pUTh0HE64TNf0mczcnnQyu/MilaFJCae1nw2fbz1DnVOxyGTlKeZft/Ff8x1BRssfACjTwQAAAABJRU5ErkJggg=="); }\n.python { background-image: url("/media/img/python.png?%s"); }\n.datauri { background-image: url("data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAoAAAAKCAYAAACNMs+9AAAABGdBTUEAALGPC/xhBQAAAAlwSFlzAAALEwAACxMBAJqcGAAAAAd0SU1FB9YGARc5KB0XV+IAAAAddEVYdENvbW1lbnQAQ3JlYXRlZCB3aXRoIFRoZSBHSU1Q72QlbgAAAF1JREFUGNO9zL0NglAAxPEfdLTs4BZM4DIO4C7OwQg2JoQ9LE1exdlYvBBeZ7jqch9//q1uH4TLzw4d6+ErXMMcXuHWxId3KOETnnXXV6MJpcq2MLaI97CER3N0 vr4MkhoXe0rZigAAAABJRU5ErkJggg=="); }\n' % datauri_hash]
        self.assertEqual(out, list(self.css_node.hunks))


class CssMediaTestCase(TestCase):
    def setUp(self):
        self.css = """
        <link rel="stylesheet" href="/media/css/one.css" type="text/css" media="screen" charset="utf-8">
        <style type="text/css" media="print">p { border:5px solid green;}</style>
        <link rel="stylesheet" href="/media/css/two.css" type="text/css" charset="utf-8" media="all">
        <style type="text/css">h1 { border:5px solid green;}</style>
        """
        self.css_node = CssCompressor(self.css)

    def test_css_output(self):
        links = BeautifulSoup(self.css_node.output()).findAll('link')
        media = [u'screen', u'print', u'all', None]
        self.assertEqual(len(links), 4)
        self.assertEqual(media, [l.get('media', None) for l in links])

    def test_avoid_reordering_css(self):
        css = self.css + '<style type="text/css" media="print">p { border:10px solid red;}</style>'
        node = CssCompressor(css)
        media = [u'screen', u'print', u'all', None, u'print']
        links = BeautifulSoup(node.output()).findAll('link')
        self.assertEqual(media, [l.get('media', None) for l in links])


class CssMinTestCase(TestCase):
    def test_cssmin_filter(self):
        from compressor.filters.cssmin import CSSMinFilter
        content = """p {


        background: rgb(51,102,153) url('../../images/image.gif');


        }
"""
        output =  "p{background:#369 url('../../images/image.gif')}"
        self.assertEqual(output, CSSMinFilter(content).output())

def render(template_string, context_dict=None):
    """A shortcut for testing template output."""
    if context_dict is None:
        context_dict = {}

    c = Context(context_dict)
    t = Template(template_string)
    return t.render(c).strip()


class TemplatetagTestCase(TestCase):
    def setUp(self):
        settings.COMPRESS_ENABLED = True

    def test_empty_tag(self):
        template = u"""{% load compress %}{% compress js %}{% block js %}
        {% endblock %}{% endcompress %}"""
        context = { 'MEDIA_URL': settings.COMPRESS_URL }
        self.assertEqual(u'', render(template, context))

    def test_css_tag(self):
        template = u"""{% load compress %}{% compress css %}
        <link rel="stylesheet" href="{{ MEDIA_URL }}css/one.css" type="text/css" charset="utf-8">
        <style type="text/css">p { border:5px solid green;}</style>
        <link rel="stylesheet" href="{{ MEDIA_URL }}css/two.css" type="text/css" charset="utf-8">
        {% endcompress %}
        """
        context = { 'MEDIA_URL': settings.COMPRESS_URL }
        out = u'<link rel="stylesheet" href="/media/CACHE/css/e41ba2cc6982.css" type="text/css">'
        self.assertEqual(out, render(template, context))

    def test_nonascii_css_tag(self):
        template = u"""{% load compress %}{% compress css %}
        <link rel="stylesheet" href="{{ MEDIA_URL }}css/nonasc.css" type="text/css" charset="utf-8">
        <style type="text/css">p { border:5px solid green;}</style>
        {% endcompress %}
        """
        context = { 'MEDIA_URL': settings.COMPRESS_URL }
        out = '<link rel="stylesheet" href="/media/CACHE/css/799f6defe43c.css" type="text/css">'
        self.assertEqual(out, render(template, context))

    def test_js_tag(self):
        template = u"""{% load compress %}{% compress js %}
        <script src="{{ MEDIA_URL }}js/one.js" type="text/javascript" charset="utf-8"></script>
        <script type="text/javascript" charset="utf-8">obj.value = "value";</script>
        {% endcompress %}
        """
        context = { 'MEDIA_URL': settings.COMPRESS_URL }
        out = u'<script type="text/javascript" src="/media/CACHE/js/066cd253eada.js" charset="utf-8"></script>'
        self.assertEqual(out, render(template, context))

    def test_nonascii_js_tag(self):
        template = u"""{% load compress %}{% compress js %}
        <script src="{{ MEDIA_URL }}js/nonasc.js" type="text/javascript" charset="utf-8"></script>
        <script type="text/javascript" charset="utf-8">var test_value = "\u2014";</script>
        {% endcompress %}
        """
        context = { 'MEDIA_URL': settings.COMPRESS_URL }
        out = u'<script type="text/javascript" src="/media/CACHE/js/e214fe629b28.js" charset="utf-8"></script>'
        self.assertEqual(out, render(template, context))

    def test_nonascii_latin1_js_tag(self):
        template = u"""{% load compress %}{% compress js %}
        <script src="{{ MEDIA_URL }}js/nonasc_latin1.js" type="text/javascript" charset="utf-8"></script>
        <script type="text/javascript" charset="utf-8">var test_value = "\u2014";</script>
        {% endcompress %}
        """
        context = { 'MEDIA_URL': settings.COMPRESS_URL }
        out = u'<script type="text/javascript" src="/media/CACHE/js/f1be5a5de243.js" charset="utf-8"></script>'
        self.assertEqual(out, render(template, context))

    def test_compress_tag_with_illegal_arguments(self):
        template = u"""{% load compress %}{% compress pony %}
        <script type="pony/application">unicorn</script>
        {% endcompress %}"""
        self.assertRaises(TemplateSyntaxError, render, template, {})

    def test_debug_toggle(self):
        template = u"""{% load compress %}{% compress js %}
        <script src="{{ MEDIA_URL }}js/one.js" type="text/javascript" charset="utf-8"></script>
        <script type="text/javascript" charset="utf-8">obj.value = "value";</script>
        {% endcompress %}
        """
        class MockDebugRequest(object):
            GET = {settings.COMPRESS_DEBUG_TOGGLE: 'true'}
        context = { 'MEDIA_URL': settings.COMPRESS_URL, 'request':  MockDebugRequest()}
        out = u"""<script src="/media/js/one.js" type="text/javascript" charset="utf-8"></script>
        <script type="text/javascript" charset="utf-8">obj.value = "value";</script>"""
        self.assertEqual(out, render(template, context))

class StorageTestCase(TestCase):
    def setUp(self):
        self._storage = base.default_storage
        base.default_storage = get_storage_class('compressor.storage.GzipCompressorFileStorage')()
        settings.COMPRESS_ENABLED = True

    def tearDown(self):
        base.default_storage = self._storage

    def test_css_tag_with_storage(self):
        template = u"""{% load compress %}{% compress css %}
        <link rel="stylesheet" href="{{ MEDIA_URL }}css/one.css" type="text/css" charset="utf-8">
        <style type="text/css">p { border:5px solid white;}</style>
        <link rel="stylesheet" href="{{ MEDIA_URL }}css/two.css" type="text/css" charset="utf-8">
        {% endcompress %}
        """
        context = { 'MEDIA_URL': settings.COMPRESS_URL }
        out = u'<link rel="stylesheet" href="/media/CACHE/css/1d4424458f88.css.gz" type="text/css">'
        self.assertEqual(out, render(template, context))


class VerboseTestCase(CompressorTestCase):

    def setUp(self):
        super(VerboseTestCase, self).setUp()
        settings.COMPRESS_VERBOSE = True


class CacheBackendTestCase(CompressorTestCase):

    def test_correct_backend(self):
        from compressor.cache import cache
        self.assertEqual(cache.__class__, dummy.CacheClass)


class OfflineGenerationTestCase(TestCase):
    """Uses templates/test_compressor_offline.html"""
    maxDiff = None

    def setUp(self):
        self._old_compress = settings.COMPRESS_ENABLED
        settings.COMPRESS_ENABLED = True

    def tearDown(self):
        settings.COMPRESS_ENABLED = self._old_compress

    def test_offline(self):
        count, result = CompressCommand().compress()
        self.assertEqual(2, count)
        self.assertEqual([
            u'<link rel="stylesheet" href="/media/CACHE/css/cd579b7deb7d.css" type="text/css">\n',
            u'<script type="text/javascript" src="/media/CACHE/js/0a2bb9a287c0.js" charset="utf-8"></script>',
        ], result)

    def test_offline_with_context(self):
        self._old_offline_context = settings.COMPRESS_OFFLINE_CONTEXT
        settings.COMPRESS_OFFLINE_CONTEXT = {
            'color': 'blue',
        }
        count, result = CompressCommand().compress()
        self.assertEqual(2, count)
        self.assertEqual([
            u'<link rel="stylesheet" href="/media/CACHE/css/ee62fbfd116a.css" type="text/css">\n',
            u'<script type="text/javascript" src="/media/CACHE/js/0a2bb9a287c0.js" charset="utf-8"></script>',
        ], result)
        settings.COMPRESS_OFFLINE_CONTEXT = self._old_offline_context


class CssTidyTestCase(TestCase):
    def test_tidy(self):
        content = """
/* Some comment */
font,th,td,p{
color: black;
}
"""
        from compressor.filters.csstidy import CSSTidyFilter
        self.assertEqual(
            "font,th,td,p{color:#000;}", CSSTidyFilter(content).output())

CssTidyTestCase = skipIf(
    find_command(settings.COMPRESS_CSSTIDY_BINARY) is None,
    'CSStidy binary %r not found' % settings.COMPRESS_CSSTIDY_BINARY
)(CssTidyTestCase)

class PrecompilerTestCase(TestCase):

    def setUp(self):
        self.this_dir = os.path.dirname(__file__)
        self.filename = os.path.join(self.this_dir, 'media/css/one.css')
        self.test_precompiler =  os.path.join(self.this_dir, 'precompiler.py')
        with open(self.filename) as f:
            self.content = f.read()

    def test_precompiler_infile_outfile(self):
        command = '%s %s -f {infile} -o {outfile}' % (sys.executable, self.test_precompiler)
        compiler = CompilerFilter(content=self.content, filename=self.filename, command=command)
        self.assertEqual(u"body { color:#990; }", compiler.output())

    def test_precompiler_stdin_outfile(self):
        command = '%s %s -o {outfile}' %  (sys.executable, self.test_precompiler)
        compiler = CompilerFilter(content=self.content, filename=None, command=command)
        self.assertEqual(u"body { color:#990; }", compiler.output())

    def test_precompiler_stdin_stdout(self):
        command = '%s %s' %  (sys.executable, self.test_precompiler)
        compiler = CompilerFilter(content=self.content, filename=None, command=command)
        self.assertEqual(u"body { color:#990; }\n", compiler.output())

    def test_precompiler_stdin_stdout_filename(self):
        command = '%s %s' %  (sys.executable, self.test_precompiler)
        compiler = CompilerFilter(content=self.content, filename=self.filename, command=command)
        self.assertEqual(u"body { color:#990; }\n", compiler.output())

    def test_precompiler_infile_stdout(self):
        command = '%s %s -f {infile}' %  (sys.executable, self.test_precompiler)
        compiler = CompilerFilter(content=self.content, filename=None, command=command)
        self.assertEqual(u"body { color:#990; }\n", compiler.output())
