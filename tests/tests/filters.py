from __future__ import with_statement
import os
import sys
from unittest2 import skipIf

from django.test import TestCase

from compressor.cache import get_hashed_mtime
from compressor.conf import settings
from compressor.css import CssCompressor
from compressor.utils import find_command
from compressor.filters.base import CompilerFilter

from .templatetags import render
from .base import css_tag, test_dir


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
            "font,th,td,p{color:#000;}", CSSTidyFilter(content).input())

CssTidyTestCase = skipIf(
    find_command(settings.COMPRESS_CSSTIDY_BINARY) is None,
    'CSStidy binary %r not found' % settings.COMPRESS_CSSTIDY_BINARY
)(CssTidyTestCase)


class PrecompilerTestCase(TestCase):

    def setUp(self):
        self.filename = os.path.join(test_dir, 'media/css/one.css')
        with open(self.filename) as f:
            self.content = f.read()
        self.test_precompiler =  os.path.join(test_dir, 'precompiler.py')

    def test_precompiler_infile_outfile(self):
        command = '%s %s -f {infile} -o {outfile}' % (sys.executable, self.test_precompiler)
        compiler = CompilerFilter(content=self.content, filename=self.filename, command=command)
        self.assertEqual(u"body { color:#990; }", compiler.input())

    def test_precompiler_infile_stdout(self):
        command = '%s %s -f {infile}' %  (sys.executable, self.test_precompiler)
        compiler = CompilerFilter(content=self.content, filename=None, command=command)
        self.assertEqual(u"body { color:#990; }%s" % os.linesep, compiler.input())

    def test_precompiler_stdin_outfile(self):
        command = '%s %s -o {outfile}' %  (sys.executable, self.test_precompiler)
        compiler = CompilerFilter(content=self.content, filename=None, command=command)
        self.assertEqual(u"body { color:#990; }", compiler.input())

    def test_precompiler_stdin_stdout(self):
        command = '%s %s' %  (sys.executable, self.test_precompiler)
        compiler = CompilerFilter(content=self.content, filename=None, command=command)
        self.assertEqual(u"body { color:#990; }%s" % os.linesep, compiler.input())

    def test_precompiler_stdin_stdout_filename(self):
        command = '%s %s' %  (sys.executable, self.test_precompiler)
        compiler = CompilerFilter(content=self.content, filename=self.filename, command=command)
        self.assertEqual(u"body { color:#990; }%s" % os.linesep, compiler.input())


class CssMinTestCase(TestCase):
    def test_cssmin_filter(self):
        from compressor.filters.cssmin import CSSMinFilter
        content = """p {


        background: rgb(51,102,153) url('../../images/image.gif');


        }
"""
        output =  "p{background:#369 url('../../images/image.gif')}"
        self.assertEqual(output, CSSMinFilter(content).output())


class CssAbsolutizingTestCase(TestCase):
    def setUp(self):
        settings.COMPRESS_ENABLED = True
        settings.COMPRESS_URL = '/media/'
        settings.COMPRESS_CSS_HASHING_METHOD = 'mtime'
        self.css = """
        <link rel="stylesheet" href="/media/css/url/url1.css" type="text/css">
        <link rel="stylesheet" href="/media/css/url/2/url2.css" type="text/css">
        """
        self.css_node = CssCompressor(self.css)

    def suffix_method(self, filename):
        return get_hashed_mtime(filename)

    def test_css_absolute_filter(self):
        from compressor.filters.css_default import CssAbsoluteFilter
        filename = os.path.join(settings.COMPRESS_ROOT, 'css/url/test.css')
        imagefilename = os.path.join(settings.COMPRESS_ROOT, 'img/python.png')
        content = "p { background: url('../../img/python.png') }"
        output = "p { background: url('%simg/python.png?%s') }" % (settings.COMPRESS_URL, self.suffix_method(imagefilename))
        filter = CssAbsoluteFilter(content)
        self.assertEqual(output, filter.input(filename=filename, basename='css/url/test.css'))
        settings.COMPRESS_URL = 'http://media.example.com/'
        filter = CssAbsoluteFilter(content)
        filename = os.path.join(settings.COMPRESS_ROOT, 'css/url/test.css')
        output = "p { background: url('%simg/python.png?%s') }" % (settings.COMPRESS_URL, self.suffix_method(imagefilename))
        self.assertEqual(output, filter.input(filename=filename, basename='css/url/test.css'))

    def test_css_absolute_filter_https(self):
        from compressor.filters.css_default import CssAbsoluteFilter
        filename = os.path.join(settings.COMPRESS_ROOT, 'css/url/test.css')
        imagefilename = os.path.join(settings.COMPRESS_ROOT, 'img/python.png')
        content = "p { background: url('../../img/python.png') }"
        output = "p { background: url('%simg/python.png?%s') }" % (settings.COMPRESS_URL, self.suffix_method(imagefilename))
        filter = CssAbsoluteFilter(content)
        self.assertEqual(output, filter.input(filename=filename, basename='css/url/test.css'))
        settings.COMPRESS_URL = 'https://media.example.com/'
        filter = CssAbsoluteFilter(content)
        filename = os.path.join(settings.COMPRESS_ROOT, 'css/url/test.css')
        output = "p { background: url('%simg/python.png?%s') }" % (settings.COMPRESS_URL, self.suffix_method(imagefilename))
        self.assertEqual(output, filter.input(filename=filename, basename='css/url/test.css'))

    def test_css_absolute_filter_relative_path(self):
        from compressor.filters.css_default import CssAbsoluteFilter
        filename = os.path.join(settings.TEST_DIR, 'whatever', '..', 'media', 'whatever/../css/url/test.css')
        imagefilename = os.path.join(settings.COMPRESS_ROOT, 'img/python.png')
        content = "p { background: url('../../img/python.png') }"
        output = "p { background: url('%simg/python.png?%s') }" % (settings.COMPRESS_URL, self.suffix_method(imagefilename))
        filter = CssAbsoluteFilter(content)
        self.assertEqual(output, filter.input(filename=filename, basename='css/url/test.css'))
        settings.COMPRESS_URL = 'https://media.example.com/'
        filter = CssAbsoluteFilter(content)
        output = "p { background: url('%simg/python.png?%s') }" % (settings.COMPRESS_URL, self.suffix_method(imagefilename))
        self.assertEqual(output, filter.input(filename=filename, basename='css/url/test.css'))

    def test_css_hunks(self):
        hash_dict = {
            'hash1': self.suffix_method(os.path.join(settings.COMPRESS_ROOT, 'img/python.png')),
            'hash2': self.suffix_method(os.path.join(settings.COMPRESS_ROOT, 'img/add.png')),
        }
        out = [u"p { background: url('/media/img/python.png?%(hash1)s'); }\np { background: url('/media/img/python.png?%(hash1)s'); }\np { background: url('/media/img/python.png?%(hash1)s'); }\np { background: url('/media/img/python.png?%(hash1)s'); }\n" % hash_dict,
               u"p { background: url('/media/img/add.png?%(hash2)s'); }\np { background: url('/media/img/add.png?%(hash2)s'); }\np { background: url('/media/img/add.png?%(hash2)s'); }\np { background: url('/media/img/add.png?%(hash2)s'); }\n" % hash_dict]
        hunks = [h for m, h in self.css_node.hunks()]
        self.assertEqual(out, hunks)

    def test_guess_filename(self):
        import urllib
        from compressor.filters.css_default import CssAbsoluteFilter
        for base_url in ('/media/', 'http://media.example.com/'):
            settings.COMPRESS_URL = base_url
            url = '%s/img/python.png' % settings.COMPRESS_URL.rstrip('/')
            path = os.path.join(settings.COMPRESS_ROOT, 'img/python.png')
            content = "p { background: url('%s') }" % url
            filter = CssAbsoluteFilter(content)
            self.assertEqual(path, filter.guess_filename(url))

class CssAbsolutizingTestCaseWithHash(CssAbsolutizingTestCase):

    def setUp(self):
        settings.COMPRESS_ENABLED = True
        settings.COMPRESS_URL = '/media/'
        settings.COMPRESS_CSS_HASHING_METHOD = 'hash'
        self.css = """
        <link rel="stylesheet" href="/media/css/url/url1.css" type="text/css" charset="utf-8">
        <link rel="stylesheet" href="/media/css/url/2/url2.css" type="text/css" charset="utf-8">
        """
        self.css_node = CssCompressor(self.css)

    def suffix_method(self, filename):
        f = open(filename)
        suffix = "H%s" % (get_hexdigest(f.read(), 12), )
        f.close()
        return suffix


class CssDataUriTestCase(TestCase):
    def setUp(self):
        settings.COMPRESS_ENABLED = True
        settings.COMPRESS_CSS_FILTERS = [
            'compressor.filters.css_default.CssAbsoluteFilter',
            'compressor.filters.datauri.CssDataUriFilter',
        ]
        settings.COMPRESS_URL = '/media/'
        settings.COMPRESS_CSS_HASHING_METHOD = 'mtime'
        self.css = """
        <link rel="stylesheet" href="/media/css/datauri.css" type="text/css">
        """
        self.css_node = CssCompressor(self.css)

    def test_data_uris(self):
        datauri_hash = get_hashed_mtime(os.path.join(settings.COMPRESS_ROOT, 'css/datauri.css'))
        out = [u'.add { background-image: url("data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAABGdBTUEAAK/INwWK6QAAABl0RVh0U29mdHdhcmUAQWRvYmUgSW1hZ2VSZWFkeXHJZTwAAAJvSURBVDjLpZPrS5NhGIf9W7YvBYOkhlkoqCklWChv2WyKik7blnNris72bi6dus0DLZ0TDxW1odtopDs4D8MDZuLU0kXq61CijSIIasOvv94VTUfLiB74fXngup7nvrnvJABJ/5PfLnTTdcwOj4RsdYmo5glBWP6iOtzwvIKSWstI0Wgx80SBblpKtE9KQs/We7EaWoT/8wbWP61gMmCH0lMDvokT4j25TiQU/ITFkek9Ow6+7WH2gwsmahCPdwyw75uw9HEO2gUZSkfyI9zBPCJOoJ2SMmg46N61YO/rNoa39Xi41oFuXysMfh36/Fp0b7bAfWAH6RGi0HglWNCbzYgJaFjRv6zGuy+b9It96N3SQvNKiV9HvSaDfFEIxXItnPs23BzJQd6DDEVM0OKsoVwBG/1VMzpXVWhbkUM2K4oJBDYuGmbKIJ0qxsAbHfRLzbjcnUbFBIpx/qH3vQv9b3U03IQ/HfFkERTzfFj8w8jSpR7GBE123uFEYAzaDRIqX/2JAtJbDat/COkd7CNBva2cMvq0MGxp0PRSCPF8BXjWG3FgNHc9XPT71Ojy3sMFdfJRCeKxEsVtKwFHwALZfCUk3tIfNR8XiJwc1LmL4dg141JPKtj3WUdNFJqLGFVPC4OkR4BxajTWsChY64wmCnMxsWPCHcutKBxMVp5mxA1S+aMComToaqTRUQknLTH62kHOVEE+VQnjahscNCy0cMBWsSI0TCQcZc5ALkEYckL5A5noWSBhfm2AecMAjbcRWV0pUTh0HE64TNf0mczcnnQyu/MilaFJCae1nw2fbz1DnVOxyGTlKeZft/Ff8x1BRssfACjTwQAAAABJRU5ErkJggg=="); }\n.python { background-image: url("/media/img/python.png?%s"); }\n.datauri { background-image: url("data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAoAAAAKCAYAAACNMs+9AAAABGdBTUEAALGPC/xhBQAAAAlwSFlzAAALEwAACxMBAJqcGAAAAAd0SU1FB9YGARc5KB0XV+IAAAAddEVYdENvbW1lbnQAQ3JlYXRlZCB3aXRoIFRoZSBHSU1Q72QlbgAAAF1JREFUGNO9zL0NglAAxPEfdLTs4BZM4DIO4C7OwQg2JoQ9LE1exdlYvBBeZ7jqch9//q1uH4TLzw4d6+ErXMMcXuHWxId3KOETnnXXV6MJpcq2MLaI97CER3N0 vr4MkhoXe0rZigAAAABJRU5ErkJggg=="); }\n' % datauri_hash]
        hunks = [h for m, h in self.css_node.hunks()]
        self.assertEqual(out, hunks)



