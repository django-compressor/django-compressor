import os
import re
import socket
from BeautifulSoup import BeautifulSoup

try:
    import lxml
except ImportError:
    lxml = None

from django.core.cache.backends import dummy
from django.core.files.storage import get_storage_class
from django.template import Template, Context, TemplateSyntaxError
from django.test import TestCase

from compressor import base
from compressor.cache import get_hashed_mtime
from compressor.conf import settings
from compressor.css import CssCompressor
from compressor.js import JsCompressor
from compressor.management.commands.compress import Command as CompressCommand


class CompressorTestCase(TestCase):

    def setUp(self):
        settings.COMPRESS_ENABLED = True
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
            ('file', os.path.join(settings.COMPRESS_ROOT, u'css/one.css'), u'<link rel="stylesheet" href="/media/css/one.css" type="text/css" charset="utf-8" />'),
            ('hunk', u'p { border:5px solid green;}', u'<style type="text/css">p { border:5px solid green;}</style>'),
            ('file', os.path.join(settings.COMPRESS_ROOT, u'css/two.css'), u'<link rel="stylesheet" href="/media/css/two.css" type="text/css" charset="utf-8" />'),
        ]
        split = self.css_node.split_contents()
        split = [(x[0], x[1], self.css_node.parser.elem_str(x[2])) for x in split]
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
            self.assert_(is_date.match(str(float(date))), "mtimes is returning something that doesn't look like a date: %s" % date)

    def test_css_return_if_off(self):
        settings.COMPRESS_ENABLED = False
        self.assertEqual(self.css, self.css_node.output())

    def test_cachekey(self):
        host_name = socket.gethostname()
        is_cachekey = re.compile(r'django_compressor\.%s\.\w{12}' % host_name)
        self.assert_(is_cachekey.match(self.css_node.cachekey), "cachekey is returning something that doesn't look like r'django_compressor\.%s\.\w{12}'" % host_name)

    def test_css_hash(self):
        self.assertEqual('f7c661b7a124', self.css_node.hash)

    def test_css_return_if_on(self):
        output = u'<link rel="stylesheet" href="/media/CACHE/css/f7c661b7a124.css" type="text/css">'
        self.assertEqual(output, self.css_node.output().strip())

    def test_js_split(self):
        out = [('file', os.path.join(settings.COMPRESS_ROOT, u'js/one.js'), '<script src="/media/js/one.js" type="text/javascript" charset="utf-8"></script>'),
         ('hunk', u'obj.value = "value";', '<script type="text/javascript" charset="utf-8">obj.value = "value";</script>')
         ]
        split = self.js_node.split_contents()
        split = [(x[0], x[1], self.js_node.parser.elem_str(x[2])) for x in split]
        self.assertEqual(out, split)

    def test_js_hunks(self):
        out = ['obj = {};', u'obj.value = "value";']
        self.assertEqual(out, list(self.js_node.hunks))

    def test_js_concat(self):
        out = u'obj = {};\nobj.value = "value";'
        self.assertEqual(out, self.js_node.concat())

    def test_js_output(self):
        out = u'obj={};obj.value="value";'
        self.assertEqual(out, self.js_node.combined)

    def test_js_return_if_off(self):
        try:
            enabled = settings.COMPRESS_ENABLED
            settings.COMPRESS_ENABLED = False
            self.assertEqual(self.js, self.js_node.output())
        finally:
            settings.COMPRESS_ENABLED = enabled

    def test_js_return_if_on(self):
        output = u'<script type="text/javascript" src="/media/CACHE/js/3f33b9146e12.js" charset="utf-8"></script>'
        self.assertEqual(output, self.js_node.output())

    def test_custom_output_dir(self):
        try:
            old_output_dir = settings.COMPRESS_OUTPUT_DIR
            settings.COMPRESS_OUTPUT_DIR = 'custom'
            output = u'<script type="text/javascript" src="/media/custom/js/3f33b9146e12.js" charset="utf-8"></script>'
            self.assertEqual(output, JsCompressor(self.js).output())
            settings.COMPRESS_OUTPUT_DIR = ''
            output = u'<script type="text/javascript" src="/media/js/3f33b9146e12.js" charset="utf-8"></script>'
            self.assertEqual(output, JsCompressor(self.js).output())
            settings.COMPRESS_OUTPUT_DIR = '/custom/nested/'
            output = u'<script type="text/javascript" src="/media/custom/nested/js/3f33b9146e12.js" charset="utf-8"></script>'
            self.assertEqual(output, JsCompressor(self.js).output())
        finally:
            settings.COMPRESS_OUTPUT_DIR = old_output_dir

if lxml:
    class LxmlCompressorTestCase(CompressorTestCase):

        def test_css_split(self):
            out = [
                ('file', os.path.join(settings.COMPRESS_ROOT, u'css/one.css'), u'<link rel="stylesheet" href="/media/css/one.css" type="text/css" charset="utf-8">'),
                ('hunk', u'p { border:5px solid green;}', u'<style type="text/css">p { border:5px solid green;}</style>'),
                ('file', os.path.join(settings.COMPRESS_ROOT, u'css/two.css'), u'<link rel="stylesheet" href="/media/css/two.css" type="text/css" charset="utf-8">'),
            ]
            split = self.css_node.split_contents()
            split = [(x[0], x[1], self.css_node.parser.elem_str(x[2])) for x in split]
            self.assertEqual(out, split)

        def setUp(self):
            self.old_parser = settings.COMPRESS_PARSER
            settings.COMPRESS_PARSER = 'compressor.parser.LxmlParser'
            super(LxmlCompressorTestCase, self).setUp()

        def tearDown(self):
            settings.COMPRESS_PARSER = self.old_parser


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
        self.assertEqual(output, filter.input(filename=filename))
        settings.COMPRESS_URL = 'http://media.example.com/'
        filename = os.path.join(settings.COMPRESS_ROOT, 'css/url/test.css')
        output = "p { background: url('%simages/image.gif?%s') }" % (settings.COMPRESS_URL, get_hashed_mtime(filename))
        self.assertEqual(output, filter.input(filename=filename))

    def test_css_absolute_filter_https(self):
        from compressor.filters.css_default import CssAbsoluteFilter
        filename = os.path.join(settings.COMPRESS_ROOT, 'css/url/test.css')
        content = "p { background: url('../../images/image.gif') }"
        output = "p { background: url('%simages/image.gif?%s') }" % (settings.COMPRESS_URL, get_hashed_mtime(filename))
        filter = CssAbsoluteFilter(content)
        self.assertEqual(output, filter.input(filename=filename))
        settings.COMPRESS_URL = 'https://media.example.com/'
        filename = os.path.join(settings.COMPRESS_ROOT, 'css/url/test.css')
        output = "p { background: url('%simages/image.gif?%s') }" % (settings.COMPRESS_URL, get_hashed_mtime(filename))
        self.assertEqual(output, filter.input(filename=filename))

    def test_css_absolute_filter_relative_path(self):
        from compressor.filters.css_default import CssAbsoluteFilter
        filename = os.path.join(settings.TEST_DIR, 'whatever', '..', 'media', 'whatever/../css/url/test.css')
        content = "p { background: url('../../images/image.gif') }"
        output = "p { background: url('%simages/image.gif?%s') }" % (settings.COMPRESS_URL, get_hashed_mtime(filename))
        filter = CssAbsoluteFilter(content)
        self.assertEqual(output, filter.input(filename=filename))
        settings.COMPRESS_URL = 'https://media.example.com/'
        output = "p { background: url('%simages/image.gif?%s') }" % (settings.COMPRESS_URL, get_hashed_mtime(filename))
        self.assertEqual(output, filter.input(filename=filename))

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
        out = u'<link rel="stylesheet" href="/media/CACHE/css/f7c661b7a124.css" type="text/css">'
        self.assertEqual(out, render(template, context))

    def test_nonascii_css_tag(self):
        template = u"""{% load compress %}{% compress css %}
        <link rel="stylesheet" href="{{ MEDIA_URL }}css/nonasc.css" type="text/css" charset="utf-8">
        <style type="text/css">p { border:5px solid green;}</style>
        {% endcompress %}
        """
        context = { 'MEDIA_URL': settings.COMPRESS_URL }
        out = '<link rel="stylesheet" href="/media/CACHE/css/1c1c0855907b.css" type="text/css">'
        self.assertEqual(out, render(template, context))

    def test_js_tag(self):
        template = u"""{% load compress %}{% compress js %}
        <script src="{{ MEDIA_URL }}js/one.js" type="text/javascript" charset="utf-8"></script>
        <script type="text/javascript" charset="utf-8">obj.value = "value";</script>
        {% endcompress %}
        """
        context = { 'MEDIA_URL': settings.COMPRESS_URL }
        out = u'<script type="text/javascript" src="/media/CACHE/js/3f33b9146e12.js" charset="utf-8"></script>'
        self.assertEqual(out, render(template, context))

    def test_nonascii_js_tag(self):
        template = u"""{% load compress %}{% compress js %}
        <script src="{{ MEDIA_URL }}js/nonasc.js" type="text/javascript" charset="utf-8"></script>
        <script type="text/javascript" charset="utf-8">var test_value = "\u2014";</script>
        {% endcompress %}
        """
        context = { 'MEDIA_URL': settings.COMPRESS_URL }
        out = u'<script type="text/javascript" src="/media/CACHE/js/5d5c0e1cb25f.js" charset="utf-8"></script>'
        self.assertEqual(out, render(template, context))

    def test_nonascii_latin1_js_tag(self):
        template = u"""{% load compress %}{% compress js %}
        <script src="{{ MEDIA_URL }}js/nonasc_latin1.js" type="text/javascript" charset="utf-8"></script>
        <script type="text/javascript" charset="utf-8">var test_value = "\u2014";</script>
        {% endcompress %}
        """
        context = { 'MEDIA_URL': settings.COMPRESS_URL }
        out = u'<script type="text/javascript" src="/media/CACHE/js/40a8e9ffb476.js" charset="utf-8"></script>'
        self.assertEqual(out, render(template, context))

    def test_compress_tag_with_illegal_arguments(self):
        template = u"""{% load compress %}{% compress pony %}
        <script type="pony/application">unicorn</script>
        {% endcompress %}"""
        self.assertRaises(TemplateSyntaxError, render, template, {})


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
        out = u'<link rel="stylesheet" href="/media/CACHE/css/5b231a62e9a6.css.gz" type="text/css">'
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

    def setUp(self):
        self._old_compress = settings.COMPRESS_ENABLED
        settings.COMPRESS_ENABLED = True

    def tearDown(self):
        settings.COMPRESS_ENABLED = self._old_compress

    def test_offline(self):
        count, result = CompressCommand().compress()
        self.assertEqual(2, count)
        self.assertEqual(result, [
            u'<link rel="stylesheet" href="/media/CACHE/css/a55e1cf95000.css" type="text/css">\n',
            u'<script type="text/javascript" src="/media/CACHE/js/bf53fa5b13e2.js" charset="utf-8"></script>',
        ])

    def test_offline_with_context(self):
        self._old_offline_context = settings.COMPRESS_OFFLINE_CONTEXT
        settings.COMPRESS_OFFLINE_CONTEXT = {
            'color': 'blue',
        }
        count, result = CompressCommand().compress()
        self.assertEqual(2, count)
        self.assertEqual(result, [
            u'<link rel="stylesheet" href="/media/CACHE/css/8a2405e029de.css" type="text/css">\n',
            u'<script type="text/javascript" src="/media/CACHE/js/bf53fa5b13e2.js" charset="utf-8"></script>',
        ])
        settings.COMPRESS_OFFLINE_CONTEXT = self._old_offline_context
