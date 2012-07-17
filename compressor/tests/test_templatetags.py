from __future__ import with_statement

import os
import sys

from mock import Mock

from django.template import Template, Context, TemplateSyntaxError
from django.test import TestCase

from compressor.conf import settings
from compressor.signals import post_compress
from compressor.tests.test_base import css_tag, test_dir


def render(template_string, context_dict=None):
    """
    A shortcut for testing template output.
    """
    if context_dict is None:
        context_dict = {}
    c = Context(context_dict)
    t = Template(template_string)
    return t.render(c).strip()


class TemplatetagTestCase(TestCase):
    def setUp(self):
        self.old_enabled = settings.COMPRESS_ENABLED
        settings.COMPRESS_ENABLED = True
        self.context = {'MEDIA_URL': settings.COMPRESS_URL}

    def tearDown(self):
        settings.COMPRESS_ENABLED = self.old_enabled

    def test_empty_tag(self):
        template = u"""{% load compress %}{% compress js %}{% block js %}
        {% endblock %}{% endcompress %}"""
        self.assertEqual(u'', render(template, self.context))

    def test_css_tag(self):
        template = u"""{% load compress %}{% compress css %}
<link rel="stylesheet" href="{{ MEDIA_URL }}css/one.css" type="text/css">
<style type="text/css">p { border:5px solid green;}</style>
<link rel="stylesheet" href="{{ MEDIA_URL }}css/two.css" type="text/css">
{% endcompress %}"""
        out = css_tag("/media/CACHE/css/e41ba2cc6982.css")
        self.assertEqual(out, render(template, self.context))

    maxDiff = None

    def test_uppercase_rel(self):
        template = u"""{% load compress %}{% compress css %}
<link rel="StyleSheet" href="{{ MEDIA_URL }}css/one.css" type="text/css">
<style type="text/css">p { border:5px solid green;}</style>
<link rel="StyleSheet" href="{{ MEDIA_URL }}css/two.css" type="text/css">
{% endcompress %}"""
        out = css_tag("/media/CACHE/css/e41ba2cc6982.css")
        self.assertEqual(out, render(template, self.context))

    def test_nonascii_css_tag(self):
        template = u"""{% load compress %}{% compress css %}
        <link rel="stylesheet" href="{{ MEDIA_URL }}css/nonasc.css" type="text/css">
        <style type="text/css">p { border:5px solid green;}</style>
        {% endcompress %}
        """
        out = css_tag("/media/CACHE/css/799f6defe43c.css")
        self.assertEqual(out, render(template, self.context))

    def test_js_tag(self):
        template = u"""{% load compress %}{% compress js %}
        <script src="{{ MEDIA_URL }}js/one.js" type="text/javascript"></script>
        <script type="text/javascript">obj.value = "value";</script>
        {% endcompress %}
        """
        out = u'<script type="text/javascript" src="/media/CACHE/js/066cd253eada.js"></script>'
        self.assertEqual(out, render(template, self.context))

    def test_nonascii_js_tag(self):
        template = u"""{% load compress %}{% compress js %}
        <script src="{{ MEDIA_URL }}js/nonasc.js" type="text/javascript"></script>
        <script type="text/javascript">var test_value = "\u2014";</script>
        {% endcompress %}
        """
        out = u'<script type="text/javascript" src="/media/CACHE/js/e214fe629b28.js"></script>'
        self.assertEqual(out, render(template, self.context))

    def test_nonascii_latin1_js_tag(self):
        template = u"""{% load compress %}{% compress js %}
        <script src="{{ MEDIA_URL }}js/nonasc-latin1.js" type="text/javascript" charset="latin-1"></script>
        <script type="text/javascript">var test_value = "\u2014";</script>
        {% endcompress %}
        """
        out = u'<script type="text/javascript" src="/media/CACHE/js/be9e078b5ca7.js"></script>'
        self.assertEqual(out, render(template, self.context))

    def test_compress_tag_with_illegal_arguments(self):
        template = u"""{% load compress %}{% compress pony %}
        <script type="pony/application">unicorn</script>
        {% endcompress %}"""
        self.assertRaises(TemplateSyntaxError, render, template, {})

    def test_debug_toggle(self):
        template = u"""{% load compress %}{% compress js %}
        <script src="{{ MEDIA_URL }}js/one.js" type="text/javascript"></script>
        <script type="text/javascript">obj.value = "value";</script>
        {% endcompress %}
        """

        class MockDebugRequest(object):
            GET = {settings.COMPRESS_DEBUG_TOGGLE: 'true'}

        context = dict(self.context, request=MockDebugRequest())
        out = u"""<script src="/media/js/one.js" type="text/javascript"></script>
        <script type="text/javascript">obj.value = "value";</script>"""
        self.assertEqual(out, render(template, context))

    def test_named_compress_tag(self):
        template = u"""{% load compress %}{% compress js inline foo %}
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


class PrecompilerTemplatetagTestCase(TestCase):
    def setUp(self):
        self.old_enabled = settings.COMPRESS_ENABLED
        self.old_precompilers = settings.COMPRESS_PRECOMPILERS

        precompiler = os.path.join(test_dir, 'precompiler.py')
        python = sys.executable

        settings.COMPRESS_ENABLED = True
        settings.COMPRESS_PRECOMPILERS = (
            ('text/coffeescript', '%s %s' % (python, precompiler)),
            ('text/less', '%s %s' % (python, precompiler)),
        )
        self.context = {'MEDIA_URL': settings.COMPRESS_URL}

    def tearDown(self):
        settings.COMPRESS_ENABLED = self.old_enabled
        settings.COMPRESS_PRECOMPILERS = self.old_precompilers

    def test_compress_coffeescript_tag(self):
        template = u"""{% load compress %}{% compress js %}
            <script type="text/coffeescript"># this is a comment.</script>
            {% endcompress %}"""
        out = script(src="/media/CACHE/js/e920d58f166d.js")
        self.assertEqual(out, render(template, self.context))

    def test_compress_coffeescript_tag_and_javascript_tag(self):
        template = u"""{% load compress %}{% compress js %}
            <script type="text/coffeescript"># this is a comment.</script>
            <script type="text/javascript"># this too is a comment.</script>
            {% endcompress %}"""
        out = script(src="/media/CACHE/js/ef6b32a54575.js")
        self.assertEqual(out, render(template, self.context))

    def test_coffeescript_and_js_tag_with_compress_enabled_equals_false(self):
        self.old_enabled = settings.COMPRESS_ENABLED
        settings.COMPRESS_ENABLED = False
        try:
            template = u"""{% load compress %}{% compress js %}
                <script type="text/coffeescript"># this is a comment.</script>
                <script type="text/javascript"># this too is a comment.</script>
                {% endcompress %}"""
            out = (script('# this is a comment.\n') + '\n' +
                   script('# this too is a comment.'))
            self.assertEqual(out, render(template, self.context))
        finally:
            settings.COMPRESS_ENABLED = self.old_enabled

    def test_compress_coffeescript_tag_compress_enabled_is_false(self):
        self.old_enabled = settings.COMPRESS_ENABLED
        settings.COMPRESS_ENABLED = False
        try:
            template = u"""{% load compress %}{% compress js %}
                <script type="text/coffeescript"># this is a comment.</script>
                {% endcompress %}"""
            out = script("# this is a comment.\n")
            self.assertEqual(out, render(template, self.context))
        finally:
            settings.COMPRESS_ENABLED = self.old_enabled

    def test_compress_coffeescript_file_tag_compress_enabled_is_false(self):
        self.old_enabled = settings.COMPRESS_ENABLED
        settings.COMPRESS_ENABLED = False
        try:
            template = u"""
            {% load compress %}{% compress js %}
            <script type="text/coffeescript" src="{{ MEDIA_URL }}js/one.coffee">
            </script>
            {% endcompress %}"""

            out = script(src="/media/CACHE/js/one.95cfb869eead.js")
            self.assertEqual(out, render(template, self.context))
        finally:
            settings.COMPRESS_ENABLED = self.old_enabled

    def test_multiple_file_order_conserved(self):
        self.old_enabled = settings.COMPRESS_ENABLED
        settings.COMPRESS_ENABLED = False
        try:
            template = u"""
            {% load compress %}{% compress js %}
            <script type="text/coffeescript" src="{{ MEDIA_URL }}js/one.coffee">
            </script>
            <script src="{{ MEDIA_URL }}js/one.js"></script>
            <script type="text/coffeescript" src="{{ MEDIA_URL }}js/one.js">
            </script>
            {% endcompress %}"""

            out = '\n'.join([script(src="/media/CACHE/js/one.95cfb869eead.js"),
                             script(scripttype="", src="/media/js/one.js"),
                             script(src="/media/CACHE/js/one.81a2cd965815.js")])

            self.assertEqual(out, render(template, self.context))
        finally:
            settings.COMPRESS_ENABLED = self.old_enabled

    def test_css_multiple_files_disabled_compression(self):
        self.old_enabled = settings.COMPRESS_ENABLED
        settings.COMPRESS_ENABLED = False
        assert(settings.COMPRESS_PRECOMPILERS)
        try:
            template = u"""
            {% load compress %}{% compress css %}
            <link rel="stylesheet" type="text/css" href="{{ MEDIA_URL }}css/one.css"></link>
            <link rel="stylesheet" type="text/css" href="{{ MEDIA_URL }}css/two.css"></link>
            {% endcompress %}"""

            out = ''.join(['<link rel="stylesheet" type="text/css" href="/media/css/one.css" />',
                           '<link rel="stylesheet" type="text/css" href="/media/css/two.css" />'])

            self.assertEqual(out, render(template, self.context))
        finally:
            settings.COMPRESS_ENABLED = self.old_enabled

    def test_css_multiple_files_mixed_precompile_disabled_compression(self):
        self.old_enabled = settings.COMPRESS_ENABLED
        settings.COMPRESS_ENABLED = False
        assert(settings.COMPRESS_PRECOMPILERS)
        try:
            template = u"""
            {% load compress %}{% compress css %}
            <link rel="stylesheet" type="text/css" href="{{ MEDIA_URL }}css/one.css"/>
            <link rel="stylesheet" type="text/css" href="{{ MEDIA_URL }}css/two.css"/>
            <link rel="stylesheet" type="text/less" href="{{ MEDIA_URL }}css/url/test.css"/>
            {% endcompress %}"""

            out = ''.join(['<link rel="stylesheet" type="text/css" href="/media/css/one.css" />',
                           '<link rel="stylesheet" type="text/css" href="/media/css/two.css" />',
                           '<link rel="stylesheet" href="/media/CACHE/css/test.c4f8a285c249.css" type="text/css" />'])
            self.assertEqual(out, render(template, self.context))
        finally:
            settings.COMPRESS_ENABLED = self.old_enabled


def script(content="", src="", scripttype="text/javascript"):
    """
    returns a unicode text html script element.

    >>> script('#this is a comment', scripttype="text/applescript")
    '<script type="text/applescript">#this is a comment</script>'
    """
    out_script = u'<script '
    if scripttype:
        out_script += u'type="%s" ' % scripttype
    if src:
        out_script += u'src="%s" ' % src
    return out_script[:-1] + u'>%s</script>' % content
