import os
import re
import gzip
from BeautifulSoup import BeautifulSoup

from django.template import Template, Context, TemplateSyntaxError
from django.test import TestCase
from django.core.files.storage import get_storage_class
from django.conf import settings as django_settings
from django.core.cache.backends import dummy

from compressor import CssCompressor, JsCompressor, storage
from compressor.conf import settings
from compressor.storage import CompressorFileStorage
from compressor.utils import get_hashed_mtime


class CompressorTestCase(TestCase):

    def setUp(self):
        settings.COMPRESS = True
        self.css = """
        <link rel="stylesheet" href="/media/css/one.css" type="text/css" charset="utf-8">
        <style type="text/css">p { border:5px solid green;}</style>
        <link rel="stylesheet" href="/media/css/two.css" type="text/css" charset="utf-8">
        """
        self.cssNode = CssCompressor(self.css)

        self.js = """
        <script src="/media/js/one.js" type="text/javascript" charset="utf-8"></script>
        <script type="text/javascript" charset="utf-8">obj.value = "value";</script>
        """
        self.jsNode = JsCompressor(self.js)

    def test_css_split(self):
        out = [
            ('file', os.path.join(settings.MEDIA_ROOT, u'css/one.css'), u'<link rel="stylesheet" href="/media/css/one.css" type="text/css" charset="utf-8" />'),
            ('hunk', u'p { border:5px solid green;}', u'<style type="text/css">p { border:5px solid green;}</style>'),
            ('file', os.path.join(settings.MEDIA_ROOT, u'css/two.css'), u'<link rel="stylesheet" href="/media/css/two.css" type="text/css" charset="utf-8" />'),
        ]
        split = self.cssNode.split_contents()
        split = [(x[0], x[1], self.cssNode.parser.elem_str(x[2])) for x in split]
        self.assertEqual(out, split)

    def test_css_hunks(self):
        out = ['body { background:#990; }', u'p { border:5px solid green;}', 'body { color:#fff; }']
        self.assertEqual(out, self.cssNode.hunks)

    def test_css_output(self):
        out = u'body { background:#990; }\np { border:5px solid green;}\nbody { color:#fff; }'
        self.assertEqual(out, self.cssNode.combined)

    def test_css_mtimes(self):
        is_date = re.compile(r'^\d{10}\.\d$')
        for date in self.cssNode.mtimes:
            self.assert_(is_date.match(str(date)), "mtimes is returning something that doesn't look like a date")

    def test_css_return_if_off(self):
        settings.COMPRESS = False
        self.assertEqual(self.css, self.cssNode.output())

    def test_cachekey(self):
        is_cachekey = re.compile(r'django_compressor\.\w{12}')
        self.assert_(is_cachekey.match(self.cssNode.cachekey), "cachekey is returning something that doesn't look like r'django_compressor\.\w{12}'")

    def test_css_hash(self):
        self.assertEqual('f7c661b7a124', self.cssNode.hash)

    def test_css_return_if_on(self):
        output = u'<link rel="stylesheet" href="/media/CACHE/css/f7c661b7a124.css" type="text/css" charset="utf-8" />'
        self.assertEqual(output, self.cssNode.output().strip())

    def test_js_split(self):
        out = [('file', os.path.join(settings.MEDIA_ROOT, u'js/one.js'), '<script src="/media/js/one.js" type="text/javascript" charset="utf-8"></script>'),
         ('hunk', u'obj.value = "value";', '<script type="text/javascript" charset="utf-8">obj.value = "value";</script>')
         ]
        split = self.jsNode.split_contents()
        split = [(x[0], x[1], self.jsNode.parser.elem_str(x[2])) for x in split]
        self.assertEqual(out, split)

    def test_js_hunks(self):
        out = ['obj = {};', u'obj.value = "value";']
        self.assertEqual(out, self.jsNode.hunks)

    def test_js_concat(self):
        out = u'obj = {};\nobj.value = "value";'
        self.assertEqual(out, self.jsNode.concat())

    def test_js_output(self):
        out = u'obj={};obj.value="value";'
        self.assertEqual(out, self.jsNode.combined)

    def test_js_return_if_off(self):
        settings.COMPRESS = False
        self.assertEqual(self.js, self.jsNode.output())

    def test_js_return_if_on(self):
        output = u'<script type="text/javascript" src="/media/CACHE/js/3f33b9146e12.js" charset="utf-8"></script>'
        self.assertEqual(output, self.jsNode.output())

    def test_custom_output_dir(self):
        old_output_dir = settings.OUTPUT_DIR
        settings.OUTPUT_DIR = 'custom'
        output = u'<script type="text/javascript" src="/media/custom/js/3f33b9146e12.js" charset="utf-8"></script>'
        self.assertEqual(output, JsCompressor(self.js).output())
        settings.OUTPUT_DIR = ''
        output = u'<script type="text/javascript" src="/media/js/3f33b9146e12.js" charset="utf-8"></script>'
        self.assertEqual(output, JsCompressor(self.js).output())
        settings.OUTPUT_DIR = '/custom/nested/'
        output = u'<script type="text/javascript" src="/media/custom/nested/js/3f33b9146e12.js" charset="utf-8"></script>'
        self.assertEqual(output, JsCompressor(self.js).output())
        settings.OUTPUT_DIR = old_output_dir


class LxmlCompressorTestCase(CompressorTestCase):

    def test_css_split(self):
        out = [
            ('file', os.path.join(settings.MEDIA_ROOT, u'css/one.css'), u'<link rel="stylesheet" href="/media/css/one.css" type="text/css" charset="utf-8">'),
            ('hunk', u'p { border:5px solid green;}', u'<style type="text/css">p { border:5px solid green;}</style>'),
            ('file', os.path.join(settings.MEDIA_ROOT, u'css/two.css'), u'<link rel="stylesheet" href="/media/css/two.css" type="text/css" charset="utf-8">'),
        ]
        split = self.cssNode.split_contents()
        split = [(x[0], x[1], self.cssNode.parser.elem_str(x[2])) for x in split]
        self.assertEqual(out, split)

    def setUp(self):
        self.old_parser = settings.PARSER
        settings.PARSER = 'compressor.parser.LxmlParser'
        super(LxmlCompressorTestCase, self).setUp()

    def tearDown(self):
        settings.PARSER = self.old_parser


class CssAbsolutizingTestCase(TestCase):
    def setUp(self):
        settings.COMPRESS = True
        settings.MEDIA_URL = '/media/'
        self.css = """
        <link rel="stylesheet" href="/media/css/url/url1.css" type="text/css" charset="utf-8">
        <link rel="stylesheet" href="/media/css/url/2/url2.css" type="text/css" charset="utf-8">
        """
        self.cssNode = CssCompressor(self.css)

    def test_css_absolute_filter(self):
        from compressor.filters.css_default import CssAbsoluteFilter
        filename = os.path.join(settings.MEDIA_ROOT, 'css/url/test.css')
        content = "p { background: url('../../images/image.gif') }"
        output = "p { background: url('%simages/image.gif?%s') }" % (settings.MEDIA_URL, get_hashed_mtime(filename))
        filter = CssAbsoluteFilter(content)
        self.assertEqual(output, filter.input(filename=filename))
        settings.MEDIA_URL = 'http://media.example.com/'
        filename = os.path.join(settings.MEDIA_ROOT, 'css/url/test.css')
        output = "p { background: url('%simages/image.gif?%s') }" % (settings.MEDIA_URL, get_hashed_mtime(filename))
        self.assertEqual(output, filter.input(filename=filename))

    def test_css_absolute_filter_https(self):
        from compressor.filters.css_default import CssAbsoluteFilter
        filename = os.path.join(settings.MEDIA_ROOT, 'css/url/test.css')
        content = "p { background: url('../../images/image.gif') }"
        output = "p { background: url('%simages/image.gif?%s') }" % (settings.MEDIA_URL, get_hashed_mtime(filename))
        filter = CssAbsoluteFilter(content)
        self.assertEqual(output, filter.input(filename=filename))
        settings.MEDIA_URL = 'https://media.example.com/'
        filename = os.path.join(settings.MEDIA_ROOT, 'css/url/test.css')
        output = "p { background: url('%simages/image.gif?%s') }" % (settings.MEDIA_URL, get_hashed_mtime(filename))
        self.assertEqual(output, filter.input(filename=filename))

    def test_css_absolute_filter_relative_path(self):
        from compressor.filters.css_default import CssAbsoluteFilter
        filename = os.path.join(django_settings.TEST_DIR, 'whatever', '..', 'media', 'whatever/../css/url/test.css')
        content = "p { background: url('../../images/image.gif') }"
        output = "p { background: url('%simages/image.gif?%s') }" % (settings.MEDIA_URL, get_hashed_mtime(filename))
        filter = CssAbsoluteFilter(content)
        self.assertEqual(output, filter.input(filename=filename))
        settings.MEDIA_URL = 'https://media.example.com/'
        output = "p { background: url('%simages/image.gif?%s') }" % (settings.MEDIA_URL, get_hashed_mtime(filename))
        self.assertEqual(output, filter.input(filename=filename))

    def test_css_hunks(self):
        hash_dict = {
            'hash1': get_hashed_mtime(os.path.join(settings.MEDIA_ROOT, 'css/url/url1.css')),
            'hash2': get_hashed_mtime(os.path.join(settings.MEDIA_ROOT, 'css/url/2/url2.css')),
        }
        out = [u"p { background: url('/media/images/test.png?%(hash1)s'); }\np { background: url('/media/images/test.png?%(hash1)s'); }\np { background: url('/media/images/test.png?%(hash1)s'); }\np { background: url('/media/images/test.png?%(hash1)s'); }\n" % hash_dict,
               u"p { background: url('/media/images/test.png?%(hash2)s'); }\np { background: url('/media/images/test.png?%(hash2)s'); }\np { background: url('/media/images/test.png?%(hash2)s'); }\np { background: url('/media/images/test.png?%(hash2)s'); }\n" % hash_dict]
        self.assertEqual(out, self.cssNode.hunks)


class CssDataUriTestCase(TestCase):
    def setUp(self):
        settings.COMPRESS = True
        settings.COMPRESS_CSS_FILTERS = [
            'compressor.filters.css_default.CssAbsoluteFilter',
            'compressor.filters.datauri.CssDataUriFilter',
        ]
        settings.MEDIA_URL = '/media/'
        self.css = """
        <link rel="stylesheet" href="/media/css/datauri.css" type="text/css" charset="utf-8">
        """
        self.cssNode = CssCompressor(self.css)

    def test_data_uris(self):
        datauri_hash = get_hashed_mtime(os.path.join(settings.MEDIA_ROOT, 'css/datauri.css'))
        out = [u'.add { background-image: url("data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAABGdBTUEAAK/INwWK6QAAABl0RVh0U29mdHdhcmUAQWRvYmUgSW1hZ2VSZWFkeXHJZTwAAAJvSURBVDjLpZPrS5NhGIf9W7YvBYOkhlkoqCklWChv2WyKik7blnNris72bi6dus0DLZ0TDxW1odtopDs4D8MDZuLU0kXq61CijSIIasOvv94VTUfLiB74fXngup7nvrnvJABJ/5PfLnTTdcwOj4RsdYmo5glBWP6iOtzwvIKSWstI0Wgx80SBblpKtE9KQs/We7EaWoT/8wbWP61gMmCH0lMDvokT4j25TiQU/ITFkek9Ow6+7WH2gwsmahCPdwyw75uw9HEO2gUZSkfyI9zBPCJOoJ2SMmg46N61YO/rNoa39Xi41oFuXysMfh36/Fp0b7bAfWAH6RGi0HglWNCbzYgJaFjRv6zGuy+b9It96N3SQvNKiV9HvSaDfFEIxXItnPs23BzJQd6DDEVM0OKsoVwBG/1VMzpXVWhbkUM2K4oJBDYuGmbKIJ0qxsAbHfRLzbjcnUbFBIpx/qH3vQv9b3U03IQ/HfFkERTzfFj8w8jSpR7GBE123uFEYAzaDRIqX/2JAtJbDat/COkd7CNBva2cMvq0MGxp0PRSCPF8BXjWG3FgNHc9XPT71Ojy3sMFdfJRCeKxEsVtKwFHwALZfCUk3tIfNR8XiJwc1LmL4dg141JPKtj3WUdNFJqLGFVPC4OkR4BxajTWsChY64wmCnMxsWPCHcutKBxMVp5mxA1S+aMComToaqTRUQknLTH62kHOVEE+VQnjahscNCy0cMBWsSI0TCQcZc5ALkEYckL5A5noWSBhfm2AecMAjbcRWV0pUTh0HE64TNf0mczcnnQyu/MilaFJCae1nw2fbz1DnVOxyGTlKeZft/Ff8x1BRssfACjTwQAAAABJRU5ErkJggg=="); }\n.python { background-image: url("/media/img/python.png?%s"); }\n.datauri { background-image: url("data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAoAAAAKCAYAAACNMs+9AAAABGdBTUEAALGPC/xhBQAAAAlwSFlzAAALEwAACxMBAJqcGAAAAAd0SU1FB9YGARc5KB0XV+IAAAAddEVYdENvbW1lbnQAQ3JlYXRlZCB3aXRoIFRoZSBHSU1Q72QlbgAAAF1JREFUGNO9zL0NglAAxPEfdLTs4BZM4DIO4C7OwQg2JoQ9LE1exdlYvBBeZ7jqch9//q1uH4TLzw4d6+ErXMMcXuHWxId3KOETnnXXV6MJpcq2MLaI97CER3N0 vr4MkhoXe0rZigAAAABJRU5ErkJggg=="); }\n' % datauri_hash]
        self.assertEqual(out, self.cssNode.hunks)


class CssMediaTestCase(TestCase):
    def setUp(self):
        self.css = """
        <link rel="stylesheet" href="/media/css/one.css" type="text/css" media="screen" charset="utf-8">
        <style type="text/css" media="print">p { border:5px solid green;}</style>
        <link rel="stylesheet" href="/media/css/two.css" type="text/css" charset="utf-8" media="all">
        <style type="text/css">h1 { border:5px solid green;}</style>
        """
        self.cssNode = CssCompressor(self.css)

    def test_css_output(self):
        links = BeautifulSoup(self.cssNode.output()).findAll('link')
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
        settings.COMPRESS = True

    def test_empty_tag(self):
        template = u"""{% load compress %}{% compress js %}{% block js %}
        {% endblock %}{% endcompress %}"""
        context = { 'MEDIA_URL': settings.MEDIA_URL }
        self.assertEqual(u'', render(template, context))

    def test_css_tag(self):
        template = u"""{% load compress %}{% compress css %}
        <link rel="stylesheet" href="{{ MEDIA_URL }}css/one.css" type="text/css" charset="utf-8">
        <style type="text/css">p { border:5px solid green;}</style>
        <link rel="stylesheet" href="{{ MEDIA_URL }}css/two.css" type="text/css" charset="utf-8">
        {% endcompress %}
        """
        context = { 'MEDIA_URL': settings.MEDIA_URL }
        out = u'<link rel="stylesheet" href="/media/CACHE/css/f7c661b7a124.css" type="text/css" charset="utf-8" />'
        self.assertEqual(out, render(template, context))

    def test_nonascii_css_tag(self):
        template = u"""{% load compress %}{% compress css %}
        <link rel="stylesheet" href="{{ MEDIA_URL }}css/nonasc.css" type="text/css" charset="utf-8">
        <style type="text/css">p { border:5px solid green;}</style>
        {% endcompress %}
        """
        context = { 'MEDIA_URL': settings.MEDIA_URL }
        out = '<link rel="stylesheet" href="/media/CACHE/css/1c1c0855907b.css" type="text/css" charset="utf-8" />'
        self.assertEqual(out, render(template, context))

    def test_js_tag(self):
        template = u"""{% load compress %}{% compress js %}
        <script src="{{ MEDIA_URL }}js/one.js" type="text/javascript" charset="utf-8"></script>
        <script type="text/javascript" charset="utf-8">obj.value = "value";</script>
        {% endcompress %}
        """
        context = { 'MEDIA_URL': settings.MEDIA_URL }
        out = u'<script type="text/javascript" src="/media/CACHE/js/3f33b9146e12.js" charset="utf-8"></script>'
        self.assertEqual(out, render(template, context))

    def test_nonascii_js_tag(self):
        template = u"""{% load compress %}{% compress js %}
        <script src="{{ MEDIA_URL }}js/nonasc.js" type="text/javascript" charset="utf-8"></script>
        <script type="text/javascript" charset="utf-8">var test_value = "\u2014";</script>
        {% endcompress %}
        """
        context = { 'MEDIA_URL': settings.MEDIA_URL }
        out = u'<script type="text/javascript" src="/media/CACHE/js/5d5c0e1cb25f.js" charset="utf-8"></script>'
        self.assertEqual(out, render(template, context))

    def test_nonascii_latin1_js_tag(self):
        template = u"""{% load compress %}{% compress js %}
        <script src="{{ MEDIA_URL }}js/nonasc_latin1.js" type="text/javascript" charset="utf-8"></script>
        <script type="text/javascript" charset="utf-8">var test_value = "\u2014";</script>
        {% endcompress %}
        """
        context = { 'MEDIA_URL': settings.MEDIA_URL }
        out = u'<script type="text/javascript" src="/media/CACHE/js/40a8e9ffb476.js" charset="utf-8"></script>'
        self.assertEqual(out, render(template, context))

    def test_compress_tag_with_illegal_arguments(self):
        template = u"""{% load compress %}{% compress pony %}
        <script type="pony/application">unicorn</script>
        {% endcompress %}"""
        self.assertRaises(TemplateSyntaxError, render, template, {})


class TestStorage(CompressorFileStorage):
    """
    Test compressor storage that gzips storage files
    """
    def url(self, name):
        return u'%s.gz' % super(TestStorage, self).url(name)

    def save(self, filename, content):
        filename = super(TestStorage, self).save(filename, content)
        out = gzip.open(u'%s.gz' % self.path(filename), 'wb')
        out.writelines(open(self.path(filename), 'rb'))
        out.close()


class StorageTestCase(TestCase):
    def setUp(self):
        self._storage = storage.default_storage
        storage.default_storage = get_storage_class('core.tests.TestStorage')()
        settings.COMPRESS = True

    def tearDown(self):
        storage.default_storage = self._storage

    def test_css_tag_with_storage(self):
        template = u"""{% load compress %}{% compress css %}
        <link rel="stylesheet" href="{{ MEDIA_URL }}css/one.css" type="text/css" charset="utf-8">
        <style type="text/css">p { border:5px solid white;}</style>
        <link rel="stylesheet" href="{{ MEDIA_URL }}css/two.css" type="text/css" charset="utf-8">
        {% endcompress %}
        """
        context = { 'MEDIA_URL': settings.MEDIA_URL }
        out = u'<link rel="stylesheet" href="/media/CACHE/css/5b231a62e9a6.css.gz" type="text/css" charset="utf-8" />'
        self.assertEqual(out, render(template, context))


class VerboseTestCase(CompressorTestCase):

    def setUp(self):
        super(VerboseTestCase, self).setUp()
        setattr(settings, "COMPRESS_VERBOSE", True)


class CacheBackendTestCase(CompressorTestCase):

    def test_correct_backend(self):
        from compressor.cache import cache
        self.assertEqual(cache.__class__, dummy.CacheClass)
