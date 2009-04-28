import os

from django.test import TestCase
from compressor.templatetags.compress import CompressedCssNode, CompressedJsNode
from compressor.conf import settings


class CompressedNodeTestCase(TestCase):
    
    def setUp(self):
        settings.COMPRESS = True
        self.css = """
        <link rel="stylesheet" href="/media/css/one.css" type="text/css" media="screen" charset="utf-8">
        <style type="text/css" media="screen">p { border:5px solid green;}</style>
        <link rel="stylesheet" href="/media/css/two.css" type="text/css" media="screen" charset="utf-8">
        """
        self.cssNode = CompressedCssNode(self.css)

        self.js = """
        <script src="/media/js/one.js" type="text/javascript" charset="utf-8"></script>
        <script type="text/javascript" charset="utf-8">obj.value = "value";</script>
        """
        self.jsNode = CompressedJsNode(self.js)
        
    def test_css_split(self):
        out = [
            ('file', os.path.join(settings.MEDIA_ROOT, u'css/one.css')),
            ('hunk', u'p { border:5px solid green;}'),
            ('file', os.path.join(settings.MEDIA_ROOT, u'css/two.css')),
        ]
        self.assertEqual(out, self.cssNode.split_contents())

    def test_css_hunks(self):
        out = ['body { background:#990; }', u'p { border:5px solid green;}', 'body { color:#fff; }']
        self.assertEqual(out, self.cssNode.hunks)

    def test_css_output(self):
        out = u'body { background:#990; }\np { border:5px solid green;}\nbody { color:#fff; }'
        self.assertEqual(out, self.cssNode.output)

    def test_css_return_if_off(self):
        settings.COMPRESS = False
        self.assertEqual(self.css, self.cssNode.render())

    def test_css_hash(self):
        self.assertEqual('f7c661b7a124', self.cssNode.hash)

    def test_css_return_if_on(self):
        output = u'<link rel="stylesheet" href="/media/COMPRESSOR_CACHE/css/f7c661b7a124.css" type="text/css" media="all" charset="utf-8">'
        self.assertEqual(output, self.cssNode.render())


    def test_js_split(self):
        out = [
            ('file', os.path.join(settings.MEDIA_ROOT, u'js/one.js')),
            ('hunk', u'obj.value = "value";'),
        ]
        self.assertEqual(out, self.jsNode.split_contents())

    def test_js_hunks(self):
        out = ['obj = {};', u'obj.value = "value";']
        self.assertEqual(out, self.jsNode.hunks)

    def test_js_concat(self):
        out = u'obj = {};\nobj.value = "value";'
        self.assertEqual(out, self.jsNode.concat())

    def test_js_output(self):
        out = u'obj={};obj.value="value";'
        self.assertEqual(out, self.jsNode.output)

    def test_js_return_if_off(self):
        settings.COMPRESS = False
        self.assertEqual(self.js, self.jsNode.render())

    def test_js_return_if_on(self):
        output = u'<script type="text/javascript" src="/media/COMPRESSOR_CACHE/js/3f33b9146e12.js" charset="utf-8"></script>'
        self.assertEqual(output, self.jsNode.render())
        

class CssAbsolutizingTestCase(TestCase):
    def setUp(self):
        settings.COMPRESS = True
        self.css = """
        <link rel="stylesheet" href="/media/css/backgrounded.css" type="text/css" media="screen" charset="utf-8">
        """
        self.cssNode = CompressedCssNode(self.css)

    def test_fail(self):
        settings.COMPRESS = False
        self.assertEqual(self.js, self.jsNode.render())
