from django.test import TestCase

from mock import Mock

from compressor.conf import settings
from compressor.css import CssCompressor
from compressor.js import JsCompressor
from compressor.signals import post_compress


class PostCompressSignalTestCase(TestCase):
    def setUp(self):
        settings.COMPRESS_ENABLED = True
        settings.COMPRESS_PRECOMPILERS = {}
        settings.COMPRESS_DEBUG_TOGGLE = 'nocompress'
        self.css = """\
<link rel="stylesheet" href="/media/css/one.css" type="text/css" />
<style type="text/css">p { border:5px solid green;}</style>
<link rel="stylesheet" href="/media/css/two.css" type="text/css" />"""
        self.css_node = CssCompressor(self.css)

        self.js = """\
<script src="/media/js/one.js" type="text/javascript"></script>
<script type="text/javascript">obj.value = "value";</script>"""
        self.js_node = JsCompressor(self.js)

    def tearDown(self):
        post_compress.disconnect()

    def test_js_signal_sent(self):
        def listener(sender, **kwargs):
            pass
        callback = Mock(wraps=listener)
        post_compress.connect(callback)
        self.js_node.output()
        args, kwargs = callback.call_args
        self.assertEquals('django-compressor', kwargs['sender'])
        self.assertEquals('js', kwargs['type'])
        self.assertEquals('file', kwargs['mode'])
        context = kwargs['context']
        assert 'url' in context

    def test_css_signal_sent(self):
        def listener(sender, **kwargs):
            pass
        callback = Mock(wraps=listener)
        post_compress.connect(callback)
        self.css_node.output()
        args, kwargs = callback.call_args
        self.assertEquals('django-compressor', kwargs['sender'])
        self.assertEquals('css', kwargs['type'])
        self.assertEquals('file', kwargs['mode'])
        context = kwargs['context']
        assert 'url' in context

    def test_css_signal_multiple_media_attributes(self):
        css = """\
<link rel="stylesheet" href="/media/css/one.css" media="handheld" type="text/css" />
<style type="text/css" media="print">p { border:5px solid green;}</style>
<link rel="stylesheet" href="/media/css/two.css" type="text/css" />"""
        css_node = CssCompressor(css)
        def listener(sender, **kwargs):
            pass
        callback = Mock(wraps=listener)
        post_compress.connect(callback)
        css_node.output()
        self.assertEquals(3, callback.call_count)
