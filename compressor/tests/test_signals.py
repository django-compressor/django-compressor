from django.test import TestCase
from django.test.utils import override_settings

from mock import Mock

from compressor.css import CssCompressor
from compressor.js import JsCompressor
from compressor.signals import post_compress


@override_settings(
    COMPRESS_ENABLED=True,
    COMPRESS_PRECOMPILERS=(),
    COMPRESS_DEBUG_TOGGLE='nocompress'
)
class PostCompressSignalTestCase(TestCase):
    def setUp(self):
        self.css = """\
<link rel="stylesheet" href="/static/css/one.css" type="text/css" />
<style type="text/css">p { border:5px solid green;}</style>
<link rel="stylesheet" href="/static/css/two.css" type="text/css" />"""
        self.css_node = CssCompressor('css', self.css)

        self.js = """\
<script src="/static/js/one.js" type="text/javascript"></script>
<script type="text/javascript">obj.value = "value";</script>"""
        self.js_node = JsCompressor('js', self.js)

    def tearDown(self):
        post_compress.disconnect()

    def test_js_signal_sent(self):
        def listener(sender, **kwargs):
            pass
        callback = Mock(wraps=listener)
        post_compress.connect(callback)
        self.js_node.output()
        args, kwargs = callback.call_args
        self.assertEqual(JsCompressor, kwargs['sender'])
        self.assertEqual('js', kwargs['type'])
        self.assertEqual('file', kwargs['mode'])
        context = kwargs['context']
        assert 'url' in context['compressed']

    def test_css_signal_sent(self):
        def listener(sender, **kwargs):
            pass
        callback = Mock(wraps=listener)
        post_compress.connect(callback)
        self.css_node.output()
        args, kwargs = callback.call_args
        self.assertEqual(CssCompressor, kwargs['sender'])
        self.assertEqual('css', kwargs['type'])
        self.assertEqual('file', kwargs['mode'])
        context = kwargs['context']
        assert 'url' in context['compressed']

    def test_css_signal_multiple_media_attributes(self):
        css = """\
<link rel="stylesheet" href="/static/css/one.css" media="handheld" type="text/css" />
<style type="text/css" media="print">p { border:5px solid green;}</style>
<link rel="stylesheet" href="/static/css/two.css" type="text/css" />"""
        css_node = CssCompressor('css', css)

        def listener(sender, **kwargs):
            pass
        callback = Mock(wraps=listener)
        post_compress.connect(callback)
        css_node.output()
        self.assertEqual(3, callback.call_count)
