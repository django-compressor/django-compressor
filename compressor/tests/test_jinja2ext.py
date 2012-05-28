# -*- coding: utf-8 -*-
from __future__ import with_statement

from django.test import TestCase

import jinja2

from compressor.conf import settings
from compressor.tests.test_base import css_tag


class TestJinja2CompressorExtension(TestCase):
    """
    Test case for jinja2 extension.

    .. note::
       At tests we need to make some extra care about whitespace. Please note
       that we use jinja2 specific controls (*minus* character at block's
       beginning or end). For more information see jinja2 documentation.
    """

    def assertStrippedEqual(self, result, expected):
        self.assertEqual(result.strip(), expected.strip(), "%r != %r" % (
            result.strip(), expected.strip()))

    def setUp(self):
        from compressor.contrib.jinja2ext import CompressorExtension
        self.env = jinja2.Environment(extensions=[CompressorExtension])

    def test_error_raised_if_no_arguments_given(self):
        self.assertRaises(jinja2.exceptions.TemplateSyntaxError,
            self.env.from_string, '{% compress %}Foobar{% endcompress %}')

    def test_error_raised_if_wrong_kind_given(self):
        self.assertRaises(jinja2.exceptions.TemplateSyntaxError,
            self.env.from_string, '{% compress foo %}Foobar{% endcompress %}')

    def test_error_raised_if_wrong_mode_given(self):
        self.assertRaises(jinja2.exceptions.TemplateSyntaxError,
            self.env.from_string, '{% compress css foo %}Foobar{% endcompress %}')

    def test_compress_is_disabled(self):
        org_COMPRESS_ENABLED = settings.COMPRESS_ENABLED
        settings.COMPRESS_ENABLED = False
        tag_body = '\n'.join([
            '<link rel="stylesheet" href="css/one.css" type="text/css" charset="utf-8">',
            '<style type="text/css">p { border:5px solid green;}</style>',
            '<link rel="stylesheet" href="css/two.css" type="text/css" charset="utf-8">',
        ])
        template_string = '{% compress css %}' + tag_body + '{% endcompress %}'
        template = self.env.from_string(template_string)
        self.assertEqual(tag_body, template.render())
        settings.COMPRESS_ENABLED = org_COMPRESS_ENABLED

    def test_empty_tag(self):
        template = self.env.from_string(u"""{% compress js %}{% block js %}
        {% endblock %}{% endcompress %}""")
        context = {'MEDIA_URL': settings.COMPRESS_URL}
        self.assertEqual(u'', template.render(context))

    def test_css_tag(self):
        template = self.env.from_string(u"""{% compress css -%}
        <link rel="stylesheet" href="{{ MEDIA_URL }}css/one.css" type="text/css" charset="utf-8">
        <style type="text/css">p { border:5px solid green;}</style>
        <link rel="stylesheet" href="{{ MEDIA_URL }}css/two.css" type="text/css" charset="utf-8">
        {% endcompress %}""")
        context = {'MEDIA_URL': settings.COMPRESS_URL}
        out = css_tag("/media/CACHE/css/e41ba2cc6982.css")
        self.assertEqual(out, template.render(context))

    def test_nonascii_css_tag(self):
        template = self.env.from_string(u"""{% compress css -%}
        <link rel="stylesheet" href="{{ MEDIA_URL }}css/nonasc.css" type="text/css" charset="utf-8">
        <style type="text/css">p { border:5px solid green;}</style>
        {% endcompress %}""")
        context = {'MEDIA_URL': settings.COMPRESS_URL}
        out = css_tag("/media/CACHE/css/799f6defe43c.css")
        self.assertEqual(out, template.render(context))

    def test_js_tag(self):
        template = self.env.from_string(u"""{% compress js -%}
        <script src="{{ MEDIA_URL }}js/one.js" type="text/javascript" charset="utf-8"></script>
        <script type="text/javascript" charset="utf-8">obj.value = "value";</script>
        {% endcompress %}""")
        context = {'MEDIA_URL': settings.COMPRESS_URL}
        out = u'<script type="text/javascript" src="/media/CACHE/js/066cd253eada.js"></script>'
        self.assertEqual(out, template.render(context))

    def test_nonascii_js_tag(self):
        template = self.env.from_string(u"""{% compress js -%}
        <script src="{{ MEDIA_URL }}js/nonasc.js" type="text/javascript" charset="utf-8"></script>
        <script type="text/javascript" charset="utf-8">var test_value = "\u2014";</script>
        {% endcompress %}""")
        context = {'MEDIA_URL': settings.COMPRESS_URL}
        out = u'<script type="text/javascript" src="/media/CACHE/js/e214fe629b28.js"></script>'
        self.assertEqual(out, template.render(context))

    def test_nonascii_latin1_js_tag(self):
        template = self.env.from_string(u"""{% compress js -%}
        <script src="{{ MEDIA_URL }}js/nonasc-latin1.js" type="text/javascript" charset="latin-1"></script>
        <script type="text/javascript">var test_value = "\u2014";</script>
        {% endcompress %}""")
        context = {'MEDIA_URL': settings.COMPRESS_URL}
        out = u'<script type="text/javascript" src="/media/CACHE/js/be9e078b5ca7.js"></script>'
        self.assertEqual(out, template.render(context))

    def test_css_inline(self):
        template = self.env.from_string(u"""{% compress css, inline -%}
        <link rel="stylesheet" href="{{ MEDIA_URL }}css/one.css" type="text/css" charset="utf-8">
        <style type="text/css">p { border:5px solid green;}</style>
        {% endcompress %}""")
        context = {'MEDIA_URL': settings.COMPRESS_URL}
        out = '\n'.join([
            '<style type="text/css">body { background:#990; }',
            'p { border:5px solid green;}</style>',
        ])
        self.assertEqual(out, template.render(context))

    def test_js_inline(self):
        template = self.env.from_string(u"""{% compress js, inline -%}
        <script src="{{ MEDIA_URL }}js/one.js" type="text/css" type="text/javascript" charset="utf-8"></script>
        <script type="text/javascript" charset="utf-8">obj.value = "value";</script>
        {% endcompress %}""")
        context = {'MEDIA_URL': settings.COMPRESS_URL}
        out = '<script type="text/javascript">obj={};obj.value="value";</script>'
        self.assertEqual(out, template.render(context))

    def test_nonascii_inline_css(self):
        org_COMPRESS_ENABLED = settings.COMPRESS_ENABLED
        settings.COMPRESS_ENABLED = False
        template = self.env.from_string(u'{% compress css %}'
                                        u'<style type="text/css">'
                                        u'/* русский текст */'
                                        u'</style>{% endcompress %}')
        out = u'<link rel="stylesheet" href="/media/CACHE/css/b2cec0f8cb24.css" type="text/css" />'
        settings.COMPRESS_ENABLED = org_COMPRESS_ENABLED
        context = {'MEDIA_URL': settings.COMPRESS_URL}
        self.assertEqual(out, template.render(context))
