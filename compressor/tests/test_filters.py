from __future__ import with_statement, unicode_literals
from collections import defaultdict
import io
import os
import sys
import mock

from django.utils import six
from django.utils.encoding import smart_text
from django.test import TestCase
from django.test.utils import override_settings

from compressor.cache import cache, get_hashed_mtime, get_hashed_content
from compressor.conf import settings
from compressor.css import CssCompressor
from compressor.filters.base import CompilerFilter, CachedCompilerFilter
from compressor.filters.cssmin import CSSCompressorFilter, rCSSMinFilter
from compressor.filters.css_default import CssAbsoluteFilter
from compressor.filters.jsmin import JSMinFilter
from compressor.filters.template import TemplateFilter
from compressor.filters.closure import ClosureCompilerFilter
from compressor.filters.yuglify import YUglifyCSSFilter, YUglifyJSFilter
from compressor.filters.yui import YUICSSFilter, YUIJSFilter
from compressor.filters.cleancss import CleanCSSFilter
from compressor.tests.test_base import test_dir


def blankdict(*args, **kwargs):
    return defaultdict(lambda: '', *args, **kwargs)


@override_settings(COMPRESS_CACHEABLE_PRECOMPILERS=('text/css',))
class PrecompilerTestCase(TestCase):
    def setUp(self):
        self.test_precompiler = os.path.join(test_dir, 'precompiler.py')
        self.setup_infile()
        self.cached_precompiler_args = dict(
            content=self.content, charset=settings.FILE_CHARSET,
            filename=self.filename, mimetype='text/css')

    def setup_infile(self, filename='static/css/one.css'):
        self.filename = os.path.join(test_dir, filename)
        with io.open(self.filename, encoding=settings.FILE_CHARSET) as file:
            self.content = file.read()

    def test_precompiler_dict_options(self):
        command = "%s %s {option}" % (sys.executable, self.test_precompiler)
        option = ("option", "option",)
        CompilerFilter.options = dict([option])
        compiler = CompilerFilter(
            content=self.content, filename=self.filename,
            charset=settings.FILE_CHARSET, command=command)
        self.assertIn(option, compiler.options)

    def test_precompiler_infile_outfile(self):
        command = '%s %s -f {infile} -o {outfile}' % (sys.executable, self.test_precompiler)
        compiler = CompilerFilter(
            content=self.content, filename=self.filename,
            charset=settings.FILE_CHARSET, command=command)
        self.assertEqual("body { color:#990; }", compiler.input())

    def test_precompiler_infile_with_spaces(self):
        self.setup_infile('static/css/filename with spaces.css')
        command = '%s %s -f {infile} -o {outfile}' % (sys.executable, self.test_precompiler)
        compiler = CompilerFilter(
            content=self.content, filename=self.filename,
            charset=settings.FILE_CHARSET, command=command)
        self.assertEqual("body { color:#424242; }", compiler.input())

    def test_precompiler_infile_stdout(self):
        command = '%s %s -f {infile}' % (sys.executable, self.test_precompiler)
        compiler = CompilerFilter(
            content=self.content, filename=None, charset=None, command=command)
        self.assertEqual("body { color:#990; }%s" % os.linesep, compiler.input())

    def test_precompiler_stdin_outfile(self):
        command = '%s %s -o {outfile}' % (sys.executable, self.test_precompiler)
        compiler = CompilerFilter(
            content=self.content, filename=None, charset=None, command=command)
        self.assertEqual("body { color:#990; }", compiler.input())

    def test_precompiler_stdin_stdout(self):
        command = '%s %s' % (sys.executable, self.test_precompiler)
        compiler = CompilerFilter(
            content=self.content, filename=None, charset=None, command=command)
        self.assertEqual("body { color:#990; }%s" % os.linesep, compiler.input())

    def test_precompiler_stdin_stdout_filename(self):
        command = '%s %s' % (sys.executable, self.test_precompiler)
        compiler = CompilerFilter(
            content=self.content, filename=self.filename,
            charset=settings.FILE_CHARSET, command=command)
        self.assertEqual("body { color:#990; }%s" % os.linesep, compiler.input())

    def test_precompiler_output_unicode(self):
        command = '%s %s' % (sys.executable, self.test_precompiler)
        compiler = CompilerFilter(content=self.content, filename=self.filename, command=command)
        self.assertEqual(type(compiler.input()), six.text_type)

    def test_precompiler_cache(self):
        command = '%s %s -f {infile} -o {outfile}' % (sys.executable, self.test_precompiler)
        compiler = CachedCompilerFilter(command=command, **self.cached_precompiler_args)
        self.assertEqual("body { color:#990; }", compiler.input())
        # We tell whether the precompiler actually ran by inspecting compiler.infile. If not None, the compiler had to
        # write the input out to the file for the external command. If None, it was in the cache and thus skipped.
        self.assertIsNotNone(compiler.infile)  # Not cached

        compiler = CachedCompilerFilter(command=command, **self.cached_precompiler_args)
        self.assertEqual("body { color:#990; }", compiler.input())
        self.assertIsNone(compiler.infile)  # Cached

        self.cached_precompiler_args['content'] += ' '  # Invalidate cache by slightly changing content
        compiler = CachedCompilerFilter(command=command, **self.cached_precompiler_args)
        self.assertEqual("body { color:#990; }", compiler.input())
        self.assertIsNotNone(compiler.infile)  # Not cached

    @mock.patch('django.core.cache.backends.locmem.LocMemCache.get')
    def test_precompiler_cache_issue750(self, mock_cache):
        # emulate memcached and return string
        mock_cache.side_effect = (lambda key: str("body { color:#990; }"))
        command = '%s %s -f {infile} -o {outfile}' % (sys.executable, self.test_precompiler)
        compiler = CachedCompilerFilter(command=command, **self.cached_precompiler_args)
        self.assertEqual("body { color:#990; }", compiler.input())
        self.assertEqual(type(compiler.input()), type(smart_text("body { color:#990; }")))

    def test_precompiler_not_cacheable(self):
        command = '%s %s -f {infile} -o {outfile}' % (sys.executable, self.test_precompiler)
        self.cached_precompiler_args['mimetype'] = 'text/different'
        compiler = CachedCompilerFilter(command=command, **self.cached_precompiler_args)
        self.assertEqual("body { color:#990; }", compiler.input())
        self.assertIsNotNone(compiler.infile)  # Not cached

        compiler = CachedCompilerFilter(command=command, **self.cached_precompiler_args)
        self.assertEqual("body { color:#990; }", compiler.input())
        self.assertIsNotNone(compiler.infile)  # Not cached

    def test_precompiler_caches_empty_files(self):
        command = '%s %s -f {infile} -o {outfile}' % (sys.executable, self.test_precompiler)
        compiler = CachedCompilerFilter(command=command, **self.cached_precompiler_args)
        self.assertEqual("body { color:#990; }", compiler.input())

        cache.set(compiler.get_cache_key(), "")
        compiler = CachedCompilerFilter(command=command, **self.cached_precompiler_args)
        self.assertEqual("", compiler.input())


class CSSCompressorTestCase(TestCase):
    def test_csscompressor_filter(self):
        content = """/*!
 * django-compressor
 * Copyright (c) 2009-2014 Django Compressor authors
 */
        p {


        background: rgb(51,102,153) url('../../images/image.gif');


        }
        """
        output = """/*!
 * django-compressor
 * Copyright (c) 2009-2014 Django Compressor authors
 */p{background:#369 url('../../images/image.gif')}"""
        self.assertEqual(output, CSSCompressorFilter(content).output())


class rCssMinTestCase(TestCase):
    def test_rcssmin_filter(self):
        content = """/*!
 * django-compressor
 * Copyright (c) 2009-2014 Django Compressor authors
 */
        p {


        background: rgb(51,102,153) url('../../images/image.gif');


        }
        """
        output = """/*!
 * django-compressor
 * Copyright (c) 2009-2014 Django Compressor authors
 */p{background:rgb(51,102,153) url('../../images/image.gif')}"""
        self.assertEqual(output, rCSSMinFilter(content).output())


class JsMinTestCase(TestCase):
    def test_jsmin_filter(self):
        content = """/*!
 * django-compressor
 * Copyright (c) 2009-2014 Django Compressor authors
 */
        var foo = "bar";"""
        output = """/*!
 * django-compressor
 * Copyright (c) 2009-2014 Django Compressor authors
 */var foo="bar";"""
        self.assertEqual(output, JSMinFilter(content).output())


@override_settings(
        COMPRESS_ENABLED=True,
        COMPRESS_URL='/static/',
)
class CssAbsolutizingTestCase(TestCase):
    hashing_method = 'mtime'
    hashing_func = staticmethod(get_hashed_mtime)
    template = ("p { background: url('%(url)simg/python.png%(query)s%(hash)s%(frag)s') }"
                "p { filter: Alpha(src='%(url)simg/python.png%(query)s%(hash)s%(frag)s') }")

    def setUp(self):
        self.override_settings = self.settings(COMPRESS_CSS_HASHING_METHOD=self.hashing_method)
        self.override_settings.__enter__()

        self.css = """
        <link rel="stylesheet" href="/static/css/url/url1.css" type="text/css">
        <link rel="stylesheet" href="/static/css/url/2/url2.css" type="text/css">
        """
        self.css_node = CssCompressor(self.css)

    def tearDown(self):
        self.override_settings.__exit__(None, None, None)

    @override_settings(COMPRESS_CSS_HASHING_METHOD=None)
    def test_css_no_hash(self):
        filename = os.path.join(settings.COMPRESS_ROOT, 'css/url/test.css')
        content = self.template % blankdict(url='../../')
        params = blankdict({
            'url': settings.COMPRESS_URL,
        })
        output = self.template % params
        filter = CssAbsoluteFilter(content)
        self.assertEqual(output, filter.input(filename=filename, basename='css/url/test.css'))

        with self.settings(COMPRESS_URL='http://static.example.com/'):
            params['url'] = settings.COMPRESS_URL
            output = self.template % params
            filter = CssAbsoluteFilter(content)
            self.assertEqual(output, filter.input(filename=filename, basename='css/url/test.css'))

    def test_css_absolute_filter(self):
        filename = os.path.join(settings.COMPRESS_ROOT, 'css/url/test.css')
        imagefilename = os.path.join(settings.COMPRESS_ROOT, 'img/python.png')
        content = self.template % blankdict(url='../../')
        params = blankdict({
            'url': settings.COMPRESS_URL,
            'hash': '?' + self.hashing_func(imagefilename),
        })
        output = self.template % params
        filter = CssAbsoluteFilter(content)
        self.assertEqual(output, filter.input(filename=filename, basename='css/url/test.css'))

        with self.settings(COMPRESS_URL='http://static.example.com/'):
            params['url'] = settings.COMPRESS_URL
            output = self.template % params
            filter = CssAbsoluteFilter(content)
            self.assertEqual(output, filter.input(filename=filename, basename='css/url/test.css'))

    def test_css_absolute_filter_url_fragment(self):
        filename = os.path.join(settings.COMPRESS_ROOT, 'css/url/test.css')
        imagefilename = os.path.join(settings.COMPRESS_ROOT, 'img/python.png')
        content = self.template % blankdict(url='../../', frag='#foo')
        params = blankdict({
            'url': settings.COMPRESS_URL,
            'hash': '?' + self.hashing_func(imagefilename),
            'frag': '#foo',
        })
        output = self.template % params
        filter = CssAbsoluteFilter(content)
        self.assertEqual(output, filter.input(filename=filename, basename='css/url/test.css'))

        with self.settings(COMPRESS_URL='http://media.example.com/'):
            params['url'] = settings.COMPRESS_URL
            output = self.template % params
            filter = CssAbsoluteFilter(content)
            self.assertEqual(output, filter.input(filename=filename, basename='css/url/test.css'))

    def test_css_absolute_filter_only_url_fragment(self):
        filename = os.path.join(settings.COMPRESS_ROOT, 'css/url/test.css')
        content = "p { background: url('#foo') }"
        filter = CssAbsoluteFilter(content)
        self.assertEqual(content, filter.input(filename=filename, basename='css/url/test.css'))

        with self.settings(COMPRESS_URL='http://media.example.com/'):
            filter = CssAbsoluteFilter(content)
            self.assertEqual(content, filter.input(filename=filename, basename='css/url/test.css'))

    def test_css_absolute_filter_only_url_fragment_wrap_double_quotes(self):
        filename = os.path.join(settings.COMPRESS_ROOT, 'css/url/test.css')
        content = 'p { background: url("#foo") }'
        filter = CssAbsoluteFilter(content)
        self.assertEqual(content, filter.input(filename=filename, basename='css/url/test.css'))

        with self.settings(COMPRESS_URL='http://media.example.com/'):
            filter = CssAbsoluteFilter(content)
            self.assertEqual(content, filter.input(filename=filename, basename='css/url/test.css'))

    def test_css_absolute_filter_querystring(self):
        filename = os.path.join(settings.COMPRESS_ROOT, 'css/url/test.css')
        imagefilename = os.path.join(settings.COMPRESS_ROOT, 'img/python.png')
        content = self.template % blankdict(url='../../', query='?foo')
        params = blankdict({
            'url': settings.COMPRESS_URL,
            'query': '?foo',
            'hash': '&' + self.hashing_func(imagefilename),
        })
        output = self.template % params
        filter = CssAbsoluteFilter(content)
        self.assertEqual(output, filter.input(filename=filename, basename='css/url/test.css'))

        with self.settings(COMPRESS_URL='http://media.example.com/'):
            params['url'] = settings.COMPRESS_URL
            output = self.template % params
            filter = CssAbsoluteFilter(content)
            self.assertEqual(output, filter.input(filename=filename, basename='css/url/test.css'))

    def test_css_absolute_filter_https(self):
        filename = os.path.join(settings.COMPRESS_ROOT, 'css/url/test.css')
        imagefilename = os.path.join(settings.COMPRESS_ROOT, 'img/python.png')
        content = self.template % blankdict(url='../../')
        params = blankdict({
            'url': settings.COMPRESS_URL,
            'hash': '?' + self.hashing_func(imagefilename),
        })
        output = self.template % params
        filter = CssAbsoluteFilter(content)
        self.assertEqual(output, filter.input(filename=filename, basename='css/url/test.css'))

        with self.settings(COMPRESS_URL='https://static.example.com/'):
            params['url'] = settings.COMPRESS_URL
            output = self.template % params
            filter = CssAbsoluteFilter(content)
            self.assertEqual(output, filter.input(filename=filename, basename='css/url/test.css'))

    def test_css_absolute_filter_relative_path(self):
        filename = os.path.join(settings.TEST_DIR, 'whatever', '..', 'static', 'whatever/../css/url/test.css')
        imagefilename = os.path.join(settings.COMPRESS_ROOT, 'img/python.png')
        content = self.template % blankdict(url='../../')
        params = blankdict({
            'url': settings.COMPRESS_URL,
            'hash': '?' + self.hashing_func(imagefilename),
        })
        output = self.template % params
        filter = CssAbsoluteFilter(content)
        self.assertEqual(output, filter.input(filename=filename, basename='css/url/test.css'))

        with self.settings(COMPRESS_URL='https://static.example.com/'):
            params['url'] = settings.COMPRESS_URL
            output = self.template % params
            filter = CssAbsoluteFilter(content)
            self.assertEqual(output, filter.input(filename=filename, basename='css/url/test.css'))

    def test_css_absolute_filter_filename_outside_compress_root(self):
        filename = '/foo/bar/baz/test.css'
        content = self.template % blankdict(url='../qux/')
        params = blankdict({
            'url': settings.COMPRESS_URL + 'bar/qux/',
        })
        output = self.template % params
        filter = CssAbsoluteFilter(content)
        self.assertEqual(output, filter.input(filename=filename, basename='bar/baz/test.css'))

        with self.settings(COMPRESS_URL='https://static.example.com/'):
            params['url'] = settings.COMPRESS_URL + 'bar/qux/'
            output = self.template % params
            filter = CssAbsoluteFilter(content)
            self.assertEqual(output, filter.input(filename=filename, basename='bar/baz/test.css'))

    def test_css_hunks(self):
        hash_dict = {
            'hash1': self.hashing_func(os.path.join(settings.COMPRESS_ROOT, 'img/python.png')),
            'hash2': self.hashing_func(os.path.join(settings.COMPRESS_ROOT, 'img/add.png')),
        }
        self.assertEqual(["""\
p { background: url('/static/img/python.png?%(hash1)s'); }
p { background: url('/static/img/python.png?%(hash1)s'); }
p { background: url('/static/img/python.png?%(hash1)s'); }
p { background: url('/static/img/python.png?%(hash1)s'); }
p { filter: progid:DXImageTransform.Microsoft.AlphaImageLoader(src='/static/img/python.png?%(hash1)s'); }
""" % hash_dict,
               """\
p { background: url('/static/img/add.png?%(hash2)s'); }
p { background: url('/static/img/add.png?%(hash2)s'); }
p { background: url('/static/img/add.png?%(hash2)s'); }
p { background: url('/static/img/add.png?%(hash2)s'); }
p { filter: progid:DXImageTransform.Microsoft.AlphaImageLoader(src='/static/img/add.png?%(hash2)s'); }
""" % hash_dict], list(self.css_node.hunks()))

    def test_guess_filename(self):
        for base_url in ('/static/', 'http://static.example.com/'):
            with self.settings(COMPRESS_URL=base_url):
                url = '%s/img/python.png' % settings.COMPRESS_URL.rstrip('/')
                path = os.path.join(settings.COMPRESS_ROOT, 'img/python.png')
                content = "p { background: url('%s') }" % url
                filter = CssAbsoluteFilter(content)
                self.assertEqual(path, filter.guess_filename(url))


class CssAbsolutizingTestCaseWithHash(CssAbsolutizingTestCase):
    hashing_method = 'content'
    hashing_func = staticmethod(get_hashed_content)


@override_settings(
    COMPRESS_ENABLED=True,
    COMPRESS_CSS_FILTERS=[
        'compressor.filters.css_default.CssAbsoluteFilter',
        'compressor.filters.datauri.CssDataUriFilter',
    ],
    COMPRESS_URL='/static/',
    COMPRESS_CSS_HASHING_METHOD='mtime'
)
class CssDataUriTestCase(TestCase):
    def setUp(self):
        self.css = """
        <link rel="stylesheet" href="/static/css/datauri.css" type="text/css">
        """
        self.css_node = CssCompressor(self.css)

    def test_data_uris(self):
        datauri_hash = get_hashed_mtime(os.path.join(settings.COMPRESS_ROOT, 'img/python.png'))
        out = ['''.add { background-image: url("data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAABGdBTUEAAK/INwWK6QAAABl0RVh0U29mdHdhcmUAQWRvYmUgSW1hZ2VSZWFkeXHJZTwAAAJvSURBVDjLpZPrS5NhGIf9W7YvBYOkhlkoqCklWChv2WyKik7blnNris72bi6dus0DLZ0TDxW1odtopDs4D8MDZuLU0kXq61CijSIIasOvv94VTUfLiB74fXngup7nvrnvJABJ/5PfLnTTdcwOj4RsdYmo5glBWP6iOtzwvIKSWstI0Wgx80SBblpKtE9KQs/We7EaWoT/8wbWP61gMmCH0lMDvokT4j25TiQU/ITFkek9Ow6+7WH2gwsmahCPdwyw75uw9HEO2gUZSkfyI9zBPCJOoJ2SMmg46N61YO/rNoa39Xi41oFuXysMfh36/Fp0b7bAfWAH6RGi0HglWNCbzYgJaFjRv6zGuy+b9It96N3SQvNKiV9HvSaDfFEIxXItnPs23BzJQd6DDEVM0OKsoVwBG/1VMzpXVWhbkUM2K4oJBDYuGmbKIJ0qxsAbHfRLzbjcnUbFBIpx/qH3vQv9b3U03IQ/HfFkERTzfFj8w8jSpR7GBE123uFEYAzaDRIqX/2JAtJbDat/COkd7CNBva2cMvq0MGxp0PRSCPF8BXjWG3FgNHc9XPT71Ojy3sMFdfJRCeKxEsVtKwFHwALZfCUk3tIfNR8XiJwc1LmL4dg141JPKtj3WUdNFJqLGFVPC4OkR4BxajTWsChY64wmCnMxsWPCHcutKBxMVp5mxA1S+aMComToaqTRUQknLTH62kHOVEE+VQnjahscNCy0cMBWsSI0TCQcZc5ALkEYckL5A5noWSBhfm2AecMAjbcRWV0pUTh0HE64TNf0mczcnnQyu/MilaFJCae1nw2fbz1DnVOxyGTlKeZft/Ff8x1BRssfACjTwQAAAABJRU5ErkJggg=="); }
.add-with-hash { background-image: url("data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAABGdBTUEAAK/INwWK6QAAABl0RVh0U29mdHdhcmUAQWRvYmUgSW1hZ2VSZWFkeXHJZTwAAAJvSURBVDjLpZPrS5NhGIf9W7YvBYOkhlkoqCklWChv2WyKik7blnNris72bi6dus0DLZ0TDxW1odtopDs4D8MDZuLU0kXq61CijSIIasOvv94VTUfLiB74fXngup7nvrnvJABJ/5PfLnTTdcwOj4RsdYmo5glBWP6iOtzwvIKSWstI0Wgx80SBblpKtE9KQs/We7EaWoT/8wbWP61gMmCH0lMDvokT4j25TiQU/ITFkek9Ow6+7WH2gwsmahCPdwyw75uw9HEO2gUZSkfyI9zBPCJOoJ2SMmg46N61YO/rNoa39Xi41oFuXysMfh36/Fp0b7bAfWAH6RGi0HglWNCbzYgJaFjRv6zGuy+b9It96N3SQvNKiV9HvSaDfFEIxXItnPs23BzJQd6DDEVM0OKsoVwBG/1VMzpXVWhbkUM2K4oJBDYuGmbKIJ0qxsAbHfRLzbjcnUbFBIpx/qH3vQv9b3U03IQ/HfFkERTzfFj8w8jSpR7GBE123uFEYAzaDRIqX/2JAtJbDat/COkd7CNBva2cMvq0MGxp0PRSCPF8BXjWG3FgNHc9XPT71Ojy3sMFdfJRCeKxEsVtKwFHwALZfCUk3tIfNR8XiJwc1LmL4dg141JPKtj3WUdNFJqLGFVPC4OkR4BxajTWsChY64wmCnMxsWPCHcutKBxMVp5mxA1S+aMComToaqTRUQknLTH62kHOVEE+VQnjahscNCy0cMBWsSI0TCQcZc5ALkEYckL5A5noWSBhfm2AecMAjbcRWV0pUTh0HE64TNf0mczcnnQyu/MilaFJCae1nw2fbz1DnVOxyGTlKeZft/Ff8x1BRssfACjTwQAAAABJRU5ErkJggg=="); }
.python { background-image: url("/static/img/python.png?%s"); }
.datauri { background-image: url("data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAoAAAAKCAYAAACNMs+9AAAABGdBTUEAALGPC/xhBQAAAAlwSFlzAAALEwAACxMBAJqcGAAAAAd0SU1FB9YGARc5KB0XV+IAAAAddEVYdENvbW1lbnQAQ3JlYXRlZCB3aXRoIFRoZSBHSU1Q72QlbgAAAF1JREFUGNO9zL0NglAAxPEfdLTs4BZM4DIO4C7OwQg2JoQ9LE1exdlYvBBeZ7jqch9//q1uH4TLzw4d6+ErXMMcXuHWxId3KOETnnXXV6MJpcq2MLaI97CER3N0 vr4MkhoXe0rZigAAAABJRU5ErkJggg=="); }
''' % datauri_hash]
        self.assertEqual(out, list(self.css_node.hunks()))


class TemplateTestCase(TestCase):
    @override_settings(COMPRESS_TEMPLATE_FILTER_CONTEXT={
        'stuff': 'thing',
        'gimmick': 'bold'
    })
    def test_template_filter(self):
        content = """
        #content {background-image: url("{{ STATIC_URL|default:stuff }}/images/bg.png");}
        #footer {font-weight: {{ gimmick }};}
        """
        input = """
        #content {background-image: url("thing/images/bg.png");}
        #footer {font-weight: bold;}
        """
        self.assertEqual(input, TemplateFilter(content).input())


class SpecializedFiltersTest(TestCase):
    """
    Test to check the Specializations of filters.
    """
    def test_closure_filter(self):
        filter = ClosureCompilerFilter('')
        self.assertEqual(filter.options, (('binary', six.text_type('java -jar compiler.jar')), ('args', six.text_type(''))))

    def test_yuglify_filters(self):
        filter = YUglifyCSSFilter('')
        self.assertEqual(filter.command, '{binary} {args} --type=css')
        self.assertEqual(filter.options, (('binary', six.text_type('yuglify')), ('args', six.text_type('--terminal'))))

        filter = YUglifyJSFilter('')
        self.assertEqual(filter.command, '{binary} {args} --type=js')
        self.assertEqual(filter.options, (('binary', six.text_type('yuglify')), ('args', six.text_type('--terminal'))))

    def test_yui_filters(self):
        filter = YUICSSFilter('')
        self.assertEqual(filter.command, '{binary} {args} --type=css')
        self.assertEqual(filter.options, (('binary', six.text_type('java -jar yuicompressor.jar')), ('args', six.text_type(''))))

        filter = YUIJSFilter('', verbose=1)
        self.assertEqual(filter.command, '{binary} {args} --type=js --verbose')
        self.assertEqual(filter.options, (('binary', six.text_type('java -jar yuicompressor.jar')), ('args', six.text_type('')), ('verbose', 1)))

    def test_clean_css_filter(self):
        filter = CleanCSSFilter('')
        self.assertEqual(filter.options, (('binary', six.text_type('cleancss')), ('args', six.text_type(''))))
