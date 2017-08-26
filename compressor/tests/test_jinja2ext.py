# -*- coding: utf-8 -*-
from __future__ import with_statement, unicode_literals

from django.test import TestCase
from django.test.utils import override_settings

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
        import jinja2
        self.jinja2 = jinja2
        from compressor.contrib.jinja2ext import CompressorExtension
        self.env = self.jinja2.Environment(extensions=[CompressorExtension])

    def test_error_raised_if_no_arguments_given(self):
        self.assertRaises(self.jinja2.exceptions.TemplateSyntaxError,
            self.env.from_string, '{% compress %}Foobar{% endcompress %}')

    def test_error_raised_if_wrong_kind_given(self):
        self.assertRaises(self.jinja2.exceptions.TemplateSyntaxError,
            self.env.from_string, '{% compress foo %}Foobar{% endcompress %}')

    def test_error_raised_if_wrong_closing_kind_given(self):
        self.assertRaises(self.jinja2.exceptions.TemplateSyntaxError,
            self.env.from_string, '{% compress js %}Foobar{% endcompress css %}')

    def test_error_raised_if_wrong_mode_given(self):
        self.assertRaises(self.jinja2.exceptions.TemplateSyntaxError,
            self.env.from_string, '{% compress css foo %}Foobar{% endcompress %}')

    @override_settings(COMPRESS_ENABLED=False)
    def test_compress_is_disabled(self):
        tag_body = '\n'.join([
            '<link rel="stylesheet" href="css/one.css" type="text/css" charset="utf-8">',
            '<style type="text/css">p { border:5px solid green;}</style>',
            '<link rel="stylesheet" href="css/two.css" type="text/css" charset="utf-8">',
        ])
        template_string = '{% compress css %}' + tag_body + '{% endcompress %}'
        template = self.env.from_string(template_string)
        self.assertEqual(tag_body, template.render())

        # Test with explicit kind
        template_string = '{% compress css %}' + tag_body + '{% endcompress css %}'
        template = self.env.from_string(template_string)
        self.assertEqual(tag_body, template.render())

    def test_empty_tag(self):
        template = self.env.from_string("""{% compress js %}{% block js %}{% endblock %}{% endcompress %}""")
        context = {'STATIC_URL': settings.COMPRESS_URL}
        self.assertEqual('', template.render(context))

    def test_empty_tag_with_kind(self):
        template = self.env.from_string("""{% compress js %}{% block js %}
        {% endblock %}{% endcompress js %}""")
        context = {'STATIC_URL': settings.COMPRESS_URL}
        self.assertEqual('', template.render(context))

    def test_css_tag(self):
        template = self.env.from_string("""{% compress css -%}
        <link rel="stylesheet" href="{{ STATIC_URL }}css/one.css" type="text/css" charset="utf-8">
        <style type="text/css">p { border:5px solid green;}</style>
        <link rel="stylesheet" href="{{ STATIC_URL }}css/two.css" type="text/css" charset="utf-8">
        {% endcompress %}""")
        context = {'STATIC_URL': settings.COMPRESS_URL}
        out = css_tag("/static/CACHE/css/output.58a8c0714e59.css")
        self.assertEqual(out, template.render(context))

    def test_nonascii_css_tag(self):
        template = self.env.from_string("""{% compress css -%}
        <link rel="stylesheet" href="{{ STATIC_URL }}css/nonasc.css" type="text/css" charset="utf-8">
        <style type="text/css">p { border:5px solid green;}</style>
        {% endcompress %}""")
        context = {'STATIC_URL': settings.COMPRESS_URL}
        out = css_tag("/static/CACHE/css/output.4263023f49d6.css")
        self.assertEqual(out, template.render(context))

    def test_js_tag(self):
        template = self.env.from_string("""{% compress js -%}
        <script src="{{ STATIC_URL }}js/one.js" type="text/javascript" charset="utf-8"></script>
        <script type="text/javascript" charset="utf-8">obj.value = "value";</script>
        {% endcompress %}""")
        context = {'STATIC_URL': settings.COMPRESS_URL}
        out = '<script type="text/javascript" src="/static/CACHE/js/output.74e158ccb432.js"></script>'
        self.assertEqual(out, template.render(context))

    def test_nonascii_js_tag(self):
        template = self.env.from_string("""{% compress js -%}
        <script src="{{ STATIC_URL }}js/nonasc.js" type="text/javascript" charset="utf-8"></script>
        <script type="text/javascript" charset="utf-8">var test_value = "\u2014";</script>
        {% endcompress %}""")
        context = {'STATIC_URL': settings.COMPRESS_URL}
        out = '<script type="text/javascript" src="/static/CACHE/js/output.a18195c6ae48.js"></script>'
        self.assertEqual(out, template.render(context))

    def test_nonascii_latin1_js_tag(self):
        template = self.env.from_string("""{% compress js -%}
        <script src="{{ STATIC_URL }}js/nonasc-latin1.js" type="text/javascript" charset="latin-1"></script>
        <script type="text/javascript">var test_value = "\u2014";</script>
        {% endcompress %}""")
        context = {'STATIC_URL': settings.COMPRESS_URL}
        out = '<script type="text/javascript" src="/static/CACHE/js/output.f64debbd8878.js"></script>'
        self.assertEqual(out, template.render(context))

    def test_css_inline(self):
        template = self.env.from_string("""{% compress css, inline -%}
        <link rel="stylesheet" href="{{ STATIC_URL }}css/one.css" type="text/css" charset="utf-8">
        <style type="text/css">p { border:5px solid green;}</style>
        {% endcompress %}""")
        context = {'STATIC_URL': settings.COMPRESS_URL}
        out = '\n'.join([
            '<style type="text/css">body { background:#990; }',
            'p { border:5px solid green;}</style>',
        ])
        self.assertEqual(out, template.render(context))

    def test_js_inline(self):
        template = self.env.from_string("""{% compress js, inline -%}
        <script src="{{ STATIC_URL }}js/one.js" type="text/css" type="text/javascript" charset="utf-8"></script>
        <script type="text/javascript" charset="utf-8">obj.value = "value";</script>
        {% endcompress %}""")
        context = {'STATIC_URL': settings.COMPRESS_URL}
        out = '<script type="text/javascript">;obj={};;obj.value="value";</script>'
        self.assertEqual(out, template.render(context))

    def test_nonascii_inline_css(self):
        with self.settings(COMPRESS_ENABLED=False):
            template = self.env.from_string('{% compress css %}'
                                            '<style type="text/css">'
                                            '/* русский текст */'
                                            '</style>{% endcompress %}')
        out = '<link rel="stylesheet" href="/static/CACHE/css/output.c836c9caed5c.css" type="text/css" />'
        context = {'STATIC_URL': settings.COMPRESS_URL}
        self.assertEqual(out, template.render(context))
