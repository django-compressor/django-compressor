import os, re
import gzip

from django.template import Template, Context
from django.test import TestCase
from compressor import CssCompressor, JsCompressor
from compressor.conf import settings
from compressor.storage import CompressorFileStorage

from django.conf import settings as django_settings

from BeautifulSoup import BeautifulSoup


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
            ('file', os.path.join(settings.MEDIA_ROOT, u'css/one.css'), '<link rel="stylesheet" href="/media/css/one.css" type="text/css" charset="utf-8" />'),
            ('hunk', u'p { border:5px solid green;}', '<style type="text/css">p { border:5px solid green;}</style>'),
            ('file', os.path.join(settings.MEDIA_ROOT, u'css/two.css'), '<link rel="stylesheet" href="/media/css/two.css" type="text/css" charset="utf-8" />'),
        ]
        split = self.cssNode.split_contents()
        split = [(x[0], x[1], str(x[2])) for x in split]
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
        split = [(x[0], x[1], str(x[2])) for x in split]
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
        output = "p { background: url('%simages/image.gif') }" % settings.MEDIA_URL
        filter = CssAbsoluteFilter(content)
        self.assertEqual(output, filter.input(filename=filename))
        settings.MEDIA_URL = 'http://media.example.com/'
        filename = os.path.join(settings.MEDIA_ROOT, 'css/url/test.css')
        output = "p { background: url('%simages/image.gif') }" % settings.MEDIA_URL
        self.assertEqual(output, filter.input(filename=filename))

    def test_css_absolute_filter_https(self):
        from compressor.filters.css_default import CssAbsoluteFilter
        filename = os.path.join(settings.MEDIA_ROOT, 'css/url/test.css')
        content = "p { background: url('../../images/image.gif') }"
        output = "p { background: url('%simages/image.gif') }" % settings.MEDIA_URL
        filter = CssAbsoluteFilter(content)
        self.assertEqual(output, filter.input(filename=filename))
        settings.MEDIA_URL = 'https://media.example.com/'
        filename = os.path.join(settings.MEDIA_ROOT, 'css/url/test.css')
        output = "p { background: url('%simages/image.gif') }" % settings.MEDIA_URL
        self.assertEqual(output, filter.input(filename=filename))

    def test_css_hunks(self):
        out = [u"p { background: url('/media/images/test.png'); }\np { background: url('/media/images/test.png'); }\np { background: url('/media/images/test.png'); }\np { background: url('/media/images/test.png'); }\n",
               u"p { background: url('/media/images/test.png'); }\np { background: url('/media/images/test.png'); }\np { background: url('/media/images/test.png'); }\np { background: url('/media/images/test.png'); }\n",
               ]
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
        self._storage = settings.STORAGE
        settings.STORAGE = 'core.tests.TestStorage'
        settings.COMPRESS = True

    def tearDown(self):
        settings.STORAGE = self._storage

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
