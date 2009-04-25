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
        self.css_output = '<link rel="stylesheet" href="/media/compressed/cssHASH.css" type="text/css" media="all" charset="utf-8">'
        self.cssNode = CompressedCssNode(self.css)

        self.js = """
        <script src="/media/js/one.js" type="text/javascript" charset="utf-8"></script>
        <script type="text/javascript" charset="utf-8">obj.value = "value";</script>
        """
        self.js_output = '<script src="/media/compressed/jsHASH.js" charset="utf-8"></script>'
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
        self.assertEqual(out, self.cssNode.get_hunks())

    def test_css_concat(self):
        out = u'body { background:#990; }\np { border:5px solid green;}\nbody { color:#fff; }'
        self.assertEqual(out, self.cssNode.concat())

    def test_css_return_if_off(self):
        settings.COMPRESS = False
        self.assertEqual(self.css, self.cssNode.render())

    def test_css_return_if_on(self):
        self.assertEqual(self.css_output, self.cssNode.render())


    def test_js_split(self):
        out = [
            ('file', os.path.join(settings.MEDIA_ROOT, u'js/one.js')),
            ('hunk', u'obj.value = "value";'),
        ]
        self.assertEqual(out, self.jsNode.split_contents())

    def test_js_hunks(self):
        out = ['obj = {};', u'obj.value = "value";']
        self.assertEqual(out, self.jsNode.get_hunks())

    def test_js_concat(self):
        out = u'obj = {};\nobj.value = "value";'
        self.assertEqual(out, self.jsNode.concat())

    def test_js_return_if_off(self):
        settings.COMPRESS = False
        self.assertEqual(self.js, self.jsNode.render())

    def test_js_return_if_on(self):
        self.assertEqual(self.js_output, self.jsNode.render())
