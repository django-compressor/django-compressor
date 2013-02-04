from __future__ import with_statement
import os
import sys
from unittest2 import skipIf

from django.test import TestCase

from compressor.cache import get_hashed_mtime, get_hashed_content
from compressor.conf import settings
from compressor.css import CssCompressor
from compressor.utils import find_command
from compressor.filters.base import CompilerFilter
from compressor.filters.cssmin import CSSMinFilter
from compressor.filters.css_default import CssAbsoluteFilter
from compressor.filters.template import TemplateFilter
from compressor.tests.test_base import test_dir


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
    'CSStidy binary %r not found' % settings.COMPRESS_CSSTIDY_BINARY,
)(CssTidyTestCase)


class PrecompilerTestCase(TestCase):

    def setUp(self):
        self.filename = os.path.join(test_dir, 'static/css/one.css')
        with open(self.filename) as f:
            self.content = f.read()
        self.test_precompiler = os.path.join(test_dir, 'precompiler.py')

    def test_precompiler_infile_outfile(self):
        command = '%s %s -f {infile} -o {outfile}' % (sys.executable, self.test_precompiler)
        compiler = CompilerFilter(content=self.content, filename=self.filename, command=command)
        self.assertEqual(u"body { color:#990; }", compiler.input())

    def test_precompiler_infile_stdout(self):
        command = '%s %s -f {infile}' % (sys.executable, self.test_precompiler)
        compiler = CompilerFilter(content=self.content, filename=None, command=command)
        self.assertEqual(u"body { color:#990; }%s" % os.linesep, compiler.input())

    def test_precompiler_stdin_outfile(self):
        command = '%s %s -o {outfile}' % (sys.executable, self.test_precompiler)
        compiler = CompilerFilter(content=self.content, filename=None, command=command)
        self.assertEqual(u"body { color:#990; }", compiler.input())

    def test_precompiler_stdin_stdout(self):
        command = '%s %s' % (sys.executable, self.test_precompiler)
        compiler = CompilerFilter(content=self.content, filename=None, command=command)
        self.assertEqual(u"body { color:#990; }%s" % os.linesep, compiler.input())

    def test_precompiler_stdin_stdout_filename(self):
        command = '%s %s' % (sys.executable, self.test_precompiler)
        compiler = CompilerFilter(content=self.content, filename=self.filename, command=command)
        self.assertEqual(u"body { color:#990; }%s" % os.linesep, compiler.input())


class CssMinTestCase(TestCase):
    def test_cssmin_filter(self):
        content = """p {


        background: rgb(51,102,153) url('../../images/image.gif');


        }
"""
        output = "p{background:#369 url('../../images/image.gif')}"
        self.assertEqual(output, CSSMinFilter(content).output())


class CssAbsolutizingTestCase(TestCase):
    hashing_method = 'mtime'
    hashing_func = staticmethod(get_hashed_mtime)
    content = ("p { background: url('../../img/python.png') }"
               "p { filter: Alpha(src='../../img/python.png') }")

    def setUp(self):
        self.old_enabled = settings.COMPRESS_ENABLED
        self.old_url = settings.COMPRESS_URL
        self.old_hashing_method = settings.COMPRESS_CSS_HASHING_METHOD
        settings.COMPRESS_ENABLED = True
        settings.COMPRESS_URL = '/static/'
        settings.COMPRESS_CSS_HASHING_METHOD = self.hashing_method
        self.css = """
        <link rel="stylesheet" href="/static/css/url/url1.css" type="text/css">
        <link rel="stylesheet" href="/static/css/url/2/url2.css" type="text/css">
        """
        self.css_node = CssCompressor(self.css)

    def tearDown(self):
        settings.COMPRESS_ENABLED = self.old_enabled
        settings.COMPRESS_URL = self.old_url
        settings.COMPRESS_CSS_HASHING_METHOD = self.old_hashing_method

    def test_css_absolute_filter(self):
        filename = os.path.join(settings.COMPRESS_ROOT, 'css/url/test.css')
        imagefilename = os.path.join(settings.COMPRESS_ROOT, 'img/python.png')
        params = {
            'url': settings.COMPRESS_URL,
            'hash': self.hashing_func(imagefilename),
        }
        output = ("p { background: url('%(url)simg/python.png?%(hash)s') }"
                  "p { filter: Alpha(src='%(url)simg/python.png?%(hash)s') }") % params
        filter = CssAbsoluteFilter(self.content)
        self.assertEqual(output, filter.input(filename=filename, basename='css/url/test.css'))
        settings.COMPRESS_URL = params['url'] = 'http://static.example.com/'
        filter = CssAbsoluteFilter(self.content)
        filename = os.path.join(settings.COMPRESS_ROOT, 'css/url/test.css')
        output = ("p { background: url('%(url)simg/python.png?%(hash)s') }"
                  "p { filter: Alpha(src='%(url)simg/python.png?%(hash)s') }") % params
        self.assertEqual(output, filter.input(filename=filename, basename='css/url/test.css'))

    def test_css_absolute_filter_url_fragment(self):
        filename = os.path.join(settings.COMPRESS_ROOT, 'css/url/test.css')
        imagefilename = os.path.join(settings.COMPRESS_ROOT, 'img/python.png')
        params = {
            'url': settings.COMPRESS_URL,
            'hash': self.hashing_func(imagefilename),
        }
        content = "p { background: url('../../img/python.png#foo') }"

        output = "p { background: url('%(url)simg/python.png?%(hash)s#foo') }" % params
        filter = CssAbsoluteFilter(content)
        self.assertEqual(output, filter.input(filename=filename, basename='css/url/test.css'))
        settings.COMPRESS_URL = params['url'] = 'http://media.example.com/'
        filter = CssAbsoluteFilter(content)
        filename = os.path.join(settings.COMPRESS_ROOT, 'css/url/test.css')
        output = "p { background: url('%(url)simg/python.png?%(hash)s#foo') }" % params
        self.assertEqual(output, filter.input(filename=filename, basename='css/url/test.css'))

    def test_css_absolute_filter_only_url_fragment(self):
        filename = os.path.join(settings.COMPRESS_ROOT, 'css/url/test.css')
        content = "p { background: url('#foo') }"
        filter = CssAbsoluteFilter(content)
        self.assertEqual(content, filter.input(filename=filename, basename='css/url/test.css'))
        settings.COMPRESS_URL = 'http://media.example.com/'
        filter = CssAbsoluteFilter(content)
        filename = os.path.join(settings.COMPRESS_ROOT, 'css/url/test.css')
        self.assertEqual(content, filter.input(filename=filename, basename='css/url/test.css'))

    def test_css_absolute_filter_querystring(self):
        filename = os.path.join(settings.COMPRESS_ROOT, 'css/url/test.css')
        imagefilename = os.path.join(settings.COMPRESS_ROOT, 'img/python.png')
        params = {
            'url': settings.COMPRESS_URL,
            'hash': self.hashing_func(imagefilename),
        }
        content = "p { background: url('../../img/python.png?foo') }"

        output = "p { background: url('%(url)simg/python.png?foo&%(hash)s') }" % params
        filter = CssAbsoluteFilter(content)
        self.assertEqual(output, filter.input(filename=filename, basename='css/url/test.css'))
        settings.COMPRESS_URL = params['url'] = 'http://media.example.com/'
        filter = CssAbsoluteFilter(content)
        filename = os.path.join(settings.COMPRESS_ROOT, 'css/url/test.css')
        output = "p { background: url('%(url)simg/python.png?foo&%(hash)s') }" % params
        self.assertEqual(output, filter.input(filename=filename, basename='css/url/test.css'))

    def test_css_absolute_filter_https(self):
        filename = os.path.join(settings.COMPRESS_ROOT, 'css/url/test.css')
        imagefilename = os.path.join(settings.COMPRESS_ROOT, 'img/python.png')
        params = {
            'url': settings.COMPRESS_URL,
            'hash': self.hashing_func(imagefilename),
        }
        output = ("p { background: url('%(url)simg/python.png?%(hash)s') }"
                  "p { filter: Alpha(src='%(url)simg/python.png?%(hash)s') }") % params
        filter = CssAbsoluteFilter(self.content)
        self.assertEqual(output, filter.input(filename=filename, basename='css/url/test.css'))
        settings.COMPRESS_URL = params['url'] = 'https://static.example.com/'
        filter = CssAbsoluteFilter(self.content)
        filename = os.path.join(settings.COMPRESS_ROOT, 'css/url/test.css')
        output = ("p { background: url('%(url)simg/python.png?%(hash)s') }"
                  "p { filter: Alpha(src='%(url)simg/python.png?%(hash)s') }") % params
        self.assertEqual(output, filter.input(filename=filename, basename='css/url/test.css'))

    def test_css_absolute_filter_relative_path(self):
        filename = os.path.join(settings.TEST_DIR, 'whatever', '..', 'static', 'whatever/../css/url/test.css')
        imagefilename = os.path.join(settings.COMPRESS_ROOT, 'img/python.png')
        params = {
            'url': settings.COMPRESS_URL,
            'hash': self.hashing_func(imagefilename),
        }
        output = ("p { background: url('%(url)simg/python.png?%(hash)s') }"
                  "p { filter: Alpha(src='%(url)simg/python.png?%(hash)s') }") % params
        filter = CssAbsoluteFilter(self.content)
        self.assertEqual(output, filter.input(filename=filename, basename='css/url/test.css'))
        settings.COMPRESS_URL = params['url'] = 'https://static.example.com/'
        filter = CssAbsoluteFilter(self.content)
        output = ("p { background: url('%(url)simg/python.png?%(hash)s') }"
                  "p { filter: Alpha(src='%(url)simg/python.png?%(hash)s') }") % params
        self.assertEqual(output, filter.input(filename=filename, basename='css/url/test.css'))

    def test_css_hunks(self):
        hash_dict = {
            'hash1': self.hashing_func(os.path.join(settings.COMPRESS_ROOT, 'img/python.png')),
            'hash2': self.hashing_func(os.path.join(settings.COMPRESS_ROOT, 'img/add.png')),
        }
        self.assertEqual([u"""\
p { background: url('/static/img/python.png?%(hash1)s'); }
p { background: url('/static/img/python.png?%(hash1)s'); }
p { background: url('/static/img/python.png?%(hash1)s'); }
p { background: url('/static/img/python.png?%(hash1)s'); }
p { filter: progid:DXImageTransform.Microsoft.AlphaImageLoader(src='/static/img/python.png?%(hash1)s'); }
""" % hash_dict,
               u"""\
p { background: url('/static/img/add.png?%(hash2)s'); }
p { background: url('/static/img/add.png?%(hash2)s'); }
p { background: url('/static/img/add.png?%(hash2)s'); }
p { background: url('/static/img/add.png?%(hash2)s'); }
p { filter: progid:DXImageTransform.Microsoft.AlphaImageLoader(src='/static/img/add.png?%(hash2)s'); }
""" % hash_dict], list(self.css_node.hunks()))

    def test_guess_filename(self):
        for base_url in ('/static/', 'http://static.example.com/'):
            settings.COMPRESS_URL = base_url
            url = '%s/img/python.png' % settings.COMPRESS_URL.rstrip('/')
            path = os.path.join(settings.COMPRESS_ROOT, 'img/python.png')
            content = "p { background: url('%s') }" % url
            filter = CssAbsoluteFilter(content)
            self.assertEqual(path, filter.guess_filename(url))


class CssAbsolutizingTestCaseWithHash(CssAbsolutizingTestCase):
    hashing_method = 'content'
    hashing_func = staticmethod(get_hashed_content)

    def setUp(self):
        super(CssAbsolutizingTestCaseWithHash, self).setUp()
        self.css = """
        <link rel="stylesheet" href="/static/css/url/url1.css" type="text/css" charset="utf-8">
        <link rel="stylesheet" href="/static/css/url/2/url2.css" type="text/css" charset="utf-8">
        """
        self.css_node = CssCompressor(self.css)


class CssDataUriTestCase(TestCase):
    def setUp(self):
        settings.COMPRESS_ENABLED = True
        settings.COMPRESS_CSS_FILTERS = [
            'compressor.filters.css_default.CssAbsoluteFilter',
            'compressor.filters.datauri.CssDataUriFilter',
        ]
        settings.COMPRESS_URL = '/static/'
        settings.COMPRESS_CSS_HASHING_METHOD = 'mtime'
        self.css = """
        <link rel="stylesheet" href="/static/css/datauri.css" type="text/css">
        """
        self.css_node = CssCompressor(self.css)

    def test_data_uris(self):
        datauri_hash = get_hashed_mtime(os.path.join(settings.COMPRESS_ROOT, 'img/python.png'))
        out = [u'''.add { background-image: url("data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAABGdBTUEAAK/INwWK6QAAABl0RVh0U29mdHdhcmUAQWRvYmUgSW1hZ2VSZWFkeXHJZTwAAAJvSURBVDjLpZPrS5NhGIf9W7YvBYOkhlkoqCklWChv2WyKik7blnNris72bi6dus0DLZ0TDxW1odtopDs4D8MDZuLU0kXq61CijSIIasOvv94VTUfLiB74fXngup7nvrnvJABJ/5PfLnTTdcwOj4RsdYmo5glBWP6iOtzwvIKSWstI0Wgx80SBblpKtE9KQs/We7EaWoT/8wbWP61gMmCH0lMDvokT4j25TiQU/ITFkek9Ow6+7WH2gwsmahCPdwyw75uw9HEO2gUZSkfyI9zBPCJOoJ2SMmg46N61YO/rNoa39Xi41oFuXysMfh36/Fp0b7bAfWAH6RGi0HglWNCbzYgJaFjRv6zGuy+b9It96N3SQvNKiV9HvSaDfFEIxXItnPs23BzJQd6DDEVM0OKsoVwBG/1VMzpXVWhbkUM2K4oJBDYuGmbKIJ0qxsAbHfRLzbjcnUbFBIpx/qH3vQv9b3U03IQ/HfFkERTzfFj8w8jSpR7GBE123uFEYAzaDRIqX/2JAtJbDat/COkd7CNBva2cMvq0MGxp0PRSCPF8BXjWG3FgNHc9XPT71Ojy3sMFdfJRCeKxEsVtKwFHwALZfCUk3tIfNR8XiJwc1LmL4dg141JPKtj3WUdNFJqLGFVPC4OkR4BxajTWsChY64wmCnMxsWPCHcutKBxMVp5mxA1S+aMComToaqTRUQknLTH62kHOVEE+VQnjahscNCy0cMBWsSI0TCQcZc5ALkEYckL5A5noWSBhfm2AecMAjbcRWV0pUTh0HE64TNf0mczcnnQyu/MilaFJCae1nw2fbz1DnVOxyGTlKeZft/Ff8x1BRssfACjTwQAAAABJRU5ErkJggg=="); }
.add-with-hash { background-image: url("data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAABGdBTUEAAK/INwWK6QAAABl0RVh0U29mdHdhcmUAQWRvYmUgSW1hZ2VSZWFkeXHJZTwAAAJvSURBVDjLpZPrS5NhGIf9W7YvBYOkhlkoqCklWChv2WyKik7blnNris72bi6dus0DLZ0TDxW1odtopDs4D8MDZuLU0kXq61CijSIIasOvv94VTUfLiB74fXngup7nvrnvJABJ/5PfLnTTdcwOj4RsdYmo5glBWP6iOtzwvIKSWstI0Wgx80SBblpKtE9KQs/We7EaWoT/8wbWP61gMmCH0lMDvokT4j25TiQU/ITFkek9Ow6+7WH2gwsmahCPdwyw75uw9HEO2gUZSkfyI9zBPCJOoJ2SMmg46N61YO/rNoa39Xi41oFuXysMfh36/Fp0b7bAfWAH6RGi0HglWNCbzYgJaFjRv6zGuy+b9It96N3SQvNKiV9HvSaDfFEIxXItnPs23BzJQd6DDEVM0OKsoVwBG/1VMzpXVWhbkUM2K4oJBDYuGmbKIJ0qxsAbHfRLzbjcnUbFBIpx/qH3vQv9b3U03IQ/HfFkERTzfFj8w8jSpR7GBE123uFEYAzaDRIqX/2JAtJbDat/COkd7CNBva2cMvq0MGxp0PRSCPF8BXjWG3FgNHc9XPT71Ojy3sMFdfJRCeKxEsVtKwFHwALZfCUk3tIfNR8XiJwc1LmL4dg141JPKtj3WUdNFJqLGFVPC4OkR4BxajTWsChY64wmCnMxsWPCHcutKBxMVp5mxA1S+aMComToaqTRUQknLTH62kHOVEE+VQnjahscNCy0cMBWsSI0TCQcZc5ALkEYckL5A5noWSBhfm2AecMAjbcRWV0pUTh0HE64TNf0mczcnnQyu/MilaFJCae1nw2fbz1DnVOxyGTlKeZft/Ff8x1BRssfACjTwQAAAABJRU5ErkJggg=="); }
.python { background-image: url("/static/img/python.png?%s"); }
.datauri { background-image: url("data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAoAAAAKCAYAAACNMs+9AAAABGdBTUEAALGPC/xhBQAAAAlwSFlzAAALEwAACxMBAJqcGAAAAAd0SU1FB9YGARc5KB0XV+IAAAAddEVYdENvbW1lbnQAQ3JlYXRlZCB3aXRoIFRoZSBHSU1Q72QlbgAAAF1JREFUGNO9zL0NglAAxPEfdLTs4BZM4DIO4C7OwQg2JoQ9LE1exdlYvBBeZ7jqch9//q1uH4TLzw4d6+ErXMMcXuHWxId3KOETnnXXV6MJpcq2MLaI97CER3N0 vr4MkhoXe0rZigAAAABJRU5ErkJggg=="); }
''' % datauri_hash]
        self.assertEqual(out, list(self.css_node.hunks()))


class TemplateTestCase(TestCase):
    def setUp(self):
        self.old_context = settings.COMPRESS_TEMPLATE_FILTER_CONTEXT

    def tearDown(self):
        settings.COMPRESS_TEMPLATE_FILTER_CONTEXT = self.old_context

    def test_template_filter(self):
        settings.COMPRESS_TEMPLATE_FILTER_CONTEXT = {
            'stuff': 'thing',
            'gimmick': 'bold'
        }
        content = """
        #content {background-image: url("{{ STATIC_URL|default:stuff }}/images/bg.png");}
        #footer {font-weight: {{ gimmick }};}
        """
        input = """
        #content {background-image: url("thing/images/bg.png");}
        #footer {font-weight: bold;}
        """
        self.assertEqual(input, TemplateFilter(content).input())
