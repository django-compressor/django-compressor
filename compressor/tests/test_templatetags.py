import os
import sys
from unittest.mock import Mock

from django.conf import settings
from django.template import Context, Template, TemplateSyntaxError
from django.test import override_settings, TestCase
from sekizai.context import SekizaiContext

from compressor.signals import post_compress
from compressor.tests.test_base import css_tag, test_dir


def render(template_string, context_dict=None, context=None):
    """
    A shortcut for testing template output.
    """
    if context_dict is None:
        context_dict = {}
    if context is None:
        context = Context
    c = context(context_dict)
    t = Template(template_string)
    return t.render(c).strip()


@override_settings(COMPRESS_ENABLED=True)
class TemplatetagTestCase(TestCase):
    def setUp(self):
        self.context = {'STATIC_URL': settings.COMPRESS_URL}

    def test_empty_tag(self):
        template = """{% load compress %}{% compress js %}{% block js %}
        {% endblock %}{% endcompress %}"""
        self.assertEqual('', render(template, self.context))

    def test_css_tag(self):
        template = """{% load compress %}{% compress css %}
<link rel="stylesheet" href="{{ STATIC_URL }}css/one.css" type="text/css">
<style type="text/css">p { border:5px solid green;}</style>
<link rel="stylesheet" href="{{ STATIC_URL }}css/two.css" type="text/css">
{% endcompress %}"""
        out = css_tag("/static/CACHE/css/output.600674ea1d3d.css")
        self.assertEqual(out, render(template, self.context))

    def test_css_tag_with_block(self):
        template = """{% load compress %}{% compress css file block_name %}
<link rel="stylesheet" href="{{ STATIC_URL }}css/one.css" type="text/css">
<style type="text/css">p { border:5px solid blue;}</style>
<link rel="stylesheet" href="{{ STATIC_URL }}css/two.css" type="text/css">
{% endcompress %}"""
        out = css_tag("/static/CACHE/css/block_name.a1e074d0c4ac.css")
        self.assertEqual(out, render(template, self.context))

    def test_missing_rel_leaves_empty_result(self):
        template = """{% load compress %}{% compress css %}
<link href="{{ STATIC_URL }}css/one.css" type="text/css">
{% endcompress %}"""
        out = ""
        self.assertEqual(out, render(template, self.context))

    def test_missing_rel_only_on_one_resource(self):
        template = """{% load compress %}{% compress css %}
<link href="{{ STATIC_URL }}css/wontmatter.css" type="text/css">
<link rel="stylesheet" href="{{ STATIC_URL }}css/one.css" type="text/css">
<style type="text/css">p { border:5px solid green;}</style>
<link rel="stylesheet" href="{{ STATIC_URL }}css/two.css" type="text/css">
{% endcompress %}"""
        out = css_tag("/static/CACHE/css/output.600674ea1d3d.css")
        self.assertEqual(out, render(template, self.context))

    def test_uppercase_rel(self):
        template = """{% load compress %}{% compress css %}
<link rel="StyleSheet" href="{{ STATIC_URL }}css/one.css" type="text/css">
<style type="text/css">p { border:5px solid green;}</style>
<link rel="StyleSheet" href="{{ STATIC_URL }}css/two.css" type="text/css">
{% endcompress %}"""
        out = css_tag("/static/CACHE/css/output.600674ea1d3d.css")
        self.assertEqual(out, render(template, self.context))

    def test_nonascii_css_tag(self):
        template = """{% load compress %}{% compress css %}
        <link rel="stylesheet" href="{{ STATIC_URL }}css/nonasc.css" type="text/css">
        <style type="text/css">p { border:5px solid green;}</style>
        {% endcompress %}
        """
        out = css_tag("/static/CACHE/css/output.d5444a1ab4a3.css")
        self.assertEqual(out, render(template, self.context))

    def test_js_tag(self):
        template = """{% load compress %}{% compress js %}
        <script src="{{ STATIC_URL }}js/one.js" type="text/javascript"></script>
        <script type="text/javascript">obj.value = "value";</script>
        {% endcompress %}
        """
        out = '<script src="/static/CACHE/js/output.8a0fed36c317.js"></script>'
        self.assertEqual(out, render(template, self.context))

    def test_nonascii_js_tag(self):
        template = """{% load compress %}{% compress js %}
        <script src="{{ STATIC_URL }}js/nonasc.js" type="text/javascript"></script>
        <script type="text/javascript">var test_value = "\u2014";</script>
        {% endcompress %}
        """
        out = '<script src="/static/CACHE/js/output.8c00f1cf1e0a.js"></script>'
        self.assertEqual(out, render(template, self.context))

    def test_nonascii_latin1_js_tag(self):
        template = """{% load compress %}{% compress js %}
        <script src="{{ STATIC_URL }}js/nonasc-latin1.js" type="text/javascript" charset="latin-1"></script>
        <script type="text/javascript">var test_value = "\u2014";</script>
        {% endcompress %}
        """
        out = '<script src="/static/CACHE/js/output.06a98ccfd380.js"></script>'
        self.assertEqual(out, render(template, self.context))

    def test_compress_tag_with_illegal_arguments(self):
        template = """{% load compress %}{% compress pony %}
        <script type="pony/application">unicorn</script>
        {% endcompress %}"""
        self.assertRaises(TemplateSyntaxError, render, template, {})

    @override_settings(COMPRESS_DEBUG_TOGGLE='togglecompress')
    def test_debug_toggle(self):
        template = """{% load compress %}{% compress js %}
        <script src="{{ STATIC_URL }}js/one.js" type="text/javascript"></script>
        <script type="text/javascript">obj.value = "value";</script>
        {% endcompress %}
        """

        class MockDebugRequest:
            GET = {settings.COMPRESS_DEBUG_TOGGLE: 'true'}

        context = dict(self.context, request=MockDebugRequest())
        out = """<script src="/static/js/one.js" type="text/javascript"></script>
        <script type="text/javascript">obj.value = "value";</script>"""
        self.assertEqual(out, render(template, context))

    def test_inline(self):
        template = """{% load compress %}{% compress js inline %}
        <script src="{{ STATIC_URL }}js/one.js" type="text/javascript"></script>
        <script type="text/javascript">obj.value = "value";</script>
        {% endcompress %}{% compress css inline %}
        <link rel="stylesheet" href="{{ STATIC_URL }}css/one.css" type="text/css">
        <style type="text/css">p { border:5px solid green;}</style>
        <link rel="stylesheet" href="{{ STATIC_URL }}css/two.css" type="text/css">
        {% endcompress %}"""
        out_js = '<script>obj={};;obj.value="value";;</script>'
        out_css = ('<style type="text/css">body{background:#990}'
                   'p{border:5px solid green}'
                   'body{color:#fff}</style>')
        self.assertEqual(out_js + out_css, render(template, self.context))

    def test_named_compress_tag(self):
        template = """{% load compress %}{% compress js inline foo %}
        <script type="text/javascript">obj.value = "value";</script>
        {% endcompress %}
        """

        def listener(sender, **kwargs):
            pass
        callback = Mock(wraps=listener)
        post_compress.connect(callback)
        render(template)
        args, kwargs = callback.call_args
        context = kwargs['context']
        self.assertEqual('foo', context['compressed']['name'])

    def test_sekizai_only_once(self):
        template = """{% load sekizai_tags %}{% addtoblock "js" %}
        <script type="text/javascript">var tmpl="{% templatetag openblock %} if x == 3 %}x IS 3{% templatetag openblock %} endif %}"</script>
        {% endaddtoblock %}{% render_block "js" postprocessor "compressor.contrib.sekizai.compress" %}
        """
        out = '<script src="/static/CACHE/js/output.ffc39dec05fd.js"></script>'
        self.assertEqual(out, render(template, self.context, SekizaiContext))


class PrecompilerTemplatetagTestCase(TestCase):

    def setUp(self):
        precompiler = os.path.join(test_dir, 'precompiler.py')
        python = sys.executable

        override_settings = {
            'COMPRESS_ENABLED': True,
            'COMPRESS_PRECOMPILERS': (
                ('text/coffeescript', '%s %s' % (python, precompiler)),
                ('text/less', '%s %s' % (python, precompiler)),
            )
        }
        self.override_settings = self.settings(**override_settings)
        self.override_settings.__enter__()

        self.context = {'STATIC_URL': settings.COMPRESS_URL}

    def tearDown(self):
        self.override_settings.__exit__(None, None, None)

    def test_compress_coffeescript_tag(self):
        template = """{% load compress %}{% compress js %}
            <script type="text/coffeescript"># this is a comment.</script>
            {% endcompress %}"""
        out = script(src="/static/CACHE/js/output.ec862f0ff42c.js")
        self.assertEqual(out, render(template, self.context))

    def test_compress_coffeescript_tag_and_javascript_tag(self):
        template = """{% load compress %}{% compress js %}
            <script type="text/coffeescript"># this is a comment.</script>
            <script type="text/javascript"># this too is a comment.</script>
            {% endcompress %}"""
        out = script(src="/static/CACHE/js/output.fb4a0d84e914.js")
        self.assertEqual(out, render(template, self.context))

    @override_settings(COMPRESS_ENABLED=False)
    def test_coffeescript_and_js_tag_with_compress_enabled_equals_false(self):
        template = """{% load compress %}{% compress js %}
            <script type="text/coffeescript"># this is a comment.</script>
            <script type="text/javascript"># this too is a comment.</script>
            {% endcompress %}"""
        out = (script('# this is a comment.\n') + '\n'
               + script('# this too is a comment.', scripttype="text/javascript"))
        self.assertEqual(out, render(template, self.context))

    @override_settings(COMPRESS_ENABLED=False)
    def test_compress_coffeescript_tag_compress_enabled_is_false(self):
        template = """{% load compress %}{% compress js %}
            <script type="text/coffeescript"># this is a comment.</script>
            {% endcompress %}"""
        out = script("# this is a comment.\n")
        self.assertEqual(out, render(template, self.context))

    @override_settings(COMPRESS_ENABLED=False)
    def test_compress_coffeescript_file_tag_compress_enabled_is_false(self):
        template = """
        {% load compress %}{% compress js %}
        <script type="text/coffeescript" src="{{ STATIC_URL }}js/one.coffee">
        </script>
        {% endcompress %}"""

        out = script(src="/static/CACHE/js/one.4b3570601b8c.js")
        self.assertEqual(out, render(template, self.context))

    @override_settings(COMPRESS_ENABLED=False)
    def test_multiple_file_order_conserved(self):
        template = """
        {% load compress %}{% compress js %}
        <script type="text/coffeescript" src="{{ STATIC_URL }}js/one.coffee">
        </script>
        <script src="{{ STATIC_URL }}js/one.js"></script>
        <script type="text/coffeescript" src="{{ STATIC_URL }}js/one.js">
        </script>
        {% endcompress %}"""

        out = '\n'.join([script(src="/static/CACHE/js/one.4b3570601b8c.js"),
                         script(scripttype="", src="/static/js/one.js"),
                         script(src="/static/CACHE/js/one.8ab93aace8fa.js")])

        self.assertEqual(out, render(template, self.context))

    @override_settings(COMPRESS_ENABLED=False)
    def test_css_multiple_files_disabled_compression(self):
        assert(settings.COMPRESS_PRECOMPILERS)
        template = """
        {% load compress %}{% compress css %}
        <link rel="stylesheet" type="text/css" href="{{ STATIC_URL }}css/one.css"></link>
        <link rel="stylesheet" type="text/css" href="{{ STATIC_URL }}css/two.css"></link>
        {% endcompress %}"""

        out = ''.join(['<link rel="stylesheet" type="text/css" href="/static/css/one.css">',
                       '<link rel="stylesheet" type="text/css" href="/static/css/two.css">'])

        self.assertEqual(out, render(template, self.context))

    @override_settings(COMPRESS_ENABLED=False)
    def test_css_multiple_files_mixed_precompile_disabled_compression(self):
        assert(settings.COMPRESS_PRECOMPILERS)
        template = """
        {% load compress %}{% compress css %}
        <link rel="stylesheet" type="text/css" href="{{ STATIC_URL }}css/one.css"/>
        <link rel="stylesheet" type="text/css" href="{{ STATIC_URL }}css/two.css"/>
        <link rel="stylesheet" type="text/less" href="{{ STATIC_URL }}css/url/test.css"/>
        {% endcompress %}"""

        out = ''.join(['<link rel="stylesheet" type="text/css" href="/static/css/one.css">',
                       '<link rel="stylesheet" type="text/css" href="/static/css/two.css">',
                       '<link rel="stylesheet" href="/static/CACHE/css/test.222f958fb191.css" type="text/css">'])
        self.assertEqual(out, render(template, self.context))


def script(content="", src="", scripttype=""):
    """
    returns a unicode text html script element.

    >>> script('#this is a comment', scripttype="text/applescript")
    '<script type="text/applescript">#this is a comment</script>'
    """
    out_script = '<script '
    if scripttype:
        out_script += 'type="%s" ' % scripttype
    if src:
        out_script += 'src="%s" ' % src
    return out_script[:-1] + '>%s</script>' % content
