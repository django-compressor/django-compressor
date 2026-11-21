from django.test import RequestFactory, TestCase
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
        self.assertEqual(
            result.strip(),
            expected.strip(),
            "%r != %r" % (result.strip(), expected.strip()),
        )

    def setUp(self):
        import jinja2

        self.jinja2 = jinja2
        from compressor.contrib.jinja2ext import CompressorExtension

        self.env = self.jinja2.Environment(extensions=[CompressorExtension])

    def test_error_raised_if_no_arguments_given(self):
        self.assertRaises(
            self.jinja2.exceptions.TemplateSyntaxError,
            self.env.from_string,
            "{% compress %}Foobar{% endcompress %}",
        )

    def test_error_raised_if_wrong_kind_given(self):
        self.assertRaises(
            self.jinja2.exceptions.TemplateSyntaxError,
            self.env.from_string,
            "{% compress foo %}Foobar{% endcompress %}",
        )

    def test_error_raised_if_wrong_closing_kind_given(self):
        self.assertRaises(
            self.jinja2.exceptions.TemplateSyntaxError,
            self.env.from_string,
            "{% compress js %}Foobar{% endcompress css %}",
        )

    def test_error_raised_if_wrong_mode_given(self):
        self.assertRaises(
            self.jinja2.exceptions.TemplateSyntaxError,
            self.env.from_string,
            "{% compress css foo %}Foobar{% endcompress %}",
        )

    @override_settings(COMPRESS_ENABLED=False)
    def test_compress_is_disabled(self):
        tag_body = "\n".join(
            [
                '<link rel="stylesheet" href="css/one.css" type="text/css" charset="utf-8">',
                '<style type="text/css">p { border:5px solid green;}</style>',
                '<link rel="stylesheet" href="css/two.css" type="text/css" charset="utf-8">',
            ]
        )
        template_string = "{% compress css %}" + tag_body + "{% endcompress %}"
        template = self.env.from_string(template_string)
        self.assertEqual(tag_body, template.render())

        # Test with explicit kind
        template_string = "{% compress css %}" + tag_body + "{% endcompress css %}"
        template = self.env.from_string(template_string)
        self.assertEqual(tag_body, template.render())

    def test_empty_tag(self):
        template = self.env.from_string(
            """{% compress js %}{% block js %}{% endblock %}{% endcompress %}"""
        )
        context = {"STATIC_URL": settings.COMPRESS_URL}
        self.assertEqual("", template.render(context))

    def test_empty_tag_with_kind(self):
        template = self.env.from_string(
            """{% compress js %}{% block js %}
        {% endblock %}{% endcompress js %}"""
        )
        context = {"STATIC_URL": settings.COMPRESS_URL}
        self.assertEqual("", template.render(context))

    def test_css_tag(self):
        template = self.env.from_string(
            """{% compress css -%}
        <link rel="stylesheet" href="{{ STATIC_URL }}css/one.css" type="text/css" charset="utf-8">
        <style type="text/css">p { border:5px solid green;}</style>
        <link rel="stylesheet" href="{{ STATIC_URL }}css/two.css" type="text/css" charset="utf-8">
        {% endcompress %}"""
        )
        context = {"STATIC_URL": settings.COMPRESS_URL}
        out = css_tag("/static/CACHE/css/output.600674ea1d3d.css")
        self.assertEqual(out, template.render(context))

    def test_nonascii_css_tag(self):
        template = self.env.from_string(
            """{% compress css -%}
        <link rel="stylesheet" href="{{ STATIC_URL }}css/nonasc.css" type="text/css" charset="utf-8">
        <style type="text/css">p { border:5px solid green;}</style>
        {% endcompress %}"""
        )
        context = {"STATIC_URL": settings.COMPRESS_URL}
        out = css_tag("/static/CACHE/css/output.d5444a1ab4a3.css")
        self.assertEqual(out, template.render(context))

    def test_js_tag(self):
        template = self.env.from_string(
            """{% compress js -%}
        <script src="{{ STATIC_URL }}js/one.js" type="text/javascript" charset="utf-8"></script>
        <script type="text/javascript" charset="utf-8">obj.value = "value";</script>
        {% endcompress %}"""
        )
        context = {"STATIC_URL": settings.COMPRESS_URL}
        out = '<script src="/static/CACHE/js/output.8a0fed36c317.js"></script>'
        self.assertEqual(out, template.render(context))

    def test_nonascii_js_tag(self):
        template = self.env.from_string(
            """{% compress js -%}
        <script src="{{ STATIC_URL }}js/nonasc.js" type="text/javascript" charset="utf-8"></script>
        <script type="text/javascript" charset="utf-8">var test_value = "\u2014";</script>
        {% endcompress %}"""
        )
        context = {"STATIC_URL": settings.COMPRESS_URL}
        out = '<script src="/static/CACHE/js/output.8c00f1cf1e0a.js"></script>'
        self.assertEqual(out, template.render(context))

    def test_nonascii_latin1_js_tag(self):
        template = self.env.from_string(
            """{% compress js -%}
        <script src="{{ STATIC_URL }}js/nonasc-latin1.js" type="text/javascript" charset="latin-1"></script>
        <script type="text/javascript">var test_value = "\u2014";</script>
        {% endcompress %}"""
        )
        context = {"STATIC_URL": settings.COMPRESS_URL}
        out = '<script src="/static/CACHE/js/output.06a98ccfd380.js"></script>'
        self.assertEqual(out, template.render(context))

    def test_css_inline(self):
        template = self.env.from_string(
            """{% compress css, inline -%}
        <link rel="stylesheet" href="{{ STATIC_URL }}css/one.css" type="text/css" charset="utf-8">
        <style type="text/css">p { border:5px solid green;}</style>
        {% endcompress %}"""
        )
        context = {"STATIC_URL": settings.COMPRESS_URL}
        out = (
            '<style type="text/css">body{background:#990}'
            "p{border:5px solid green}</style>"
        )
        self.assertEqual(out, template.render(context))

    def test_js_inline(self):
        template = self.env.from_string(
            """{% compress js, inline -%}
        <script src="{{ STATIC_URL }}js/one.js" type="text/css" type="text/javascript" charset="utf-8"></script>
        <script type="text/javascript" charset="utf-8">obj.value = "value";</script>
        {% endcompress %}"""
        )
        context = {"STATIC_URL": settings.COMPRESS_URL}
        out = '<script>obj={};;obj.value="value";;</script>'
        self.assertEqual(out, template.render(context))

    def test_nonascii_inline_css(self):
        with self.settings(COMPRESS_ENABLED=False):
            template = self.env.from_string(
                "{% compress css %}"
                '<style type="text/css">'
                "/* русский текст */"
                "</style>{% endcompress %}"
            )
        out = '<link rel="stylesheet" href="/static/CACHE/css/output.e3b0c44298fc.css" type="text/css">'
        context = {"STATIC_URL": settings.COMPRESS_URL}
        self.assertEqual(out, template.render(context))


@override_settings(COMPRESS_ENABLED=True, COMPRESS_DEBUG_TOGGLE="nocompress")
class TestJinja2DebugToggle(TestCase):
    def setUp(self):
        from jinja2 import Environment

        from compressor.contrib.jinja2ext import CompressorExtension

        self.env = Environment(extensions=[CompressorExtension])
        self.context = {"STATIC_URL": settings.COMPRESS_URL}
        self.tag_body = (
            '<script src="{{ STATIC_URL }}js/one.js"></script>\n'
            '<script>obj.value = "value";</script>'
        )
        self.original_content = self.tag_body.replace("{{ STATIC_URL }}", "/static/")
        self.template_string = "{% compress js %}" + self.tag_body + "{% endcompress %}"
        self.template = self.env.from_string(self.template_string)
        self.compressed_content = (
            '<script src="/static/CACHE/js/output.8a0fed36c317.js"></script>'
        )

    def test_debug_toggle(self):
        # Populate the cache before bypassing it for a debug request.
        self.assertEqual(self.compressed_content, self.template.render(self.context))
        request = RequestFactory().get("/", {"unrelated": "true"})
        context = dict(self.context, request=request)
        self.assertEqual(self.compressed_content, self.template.render(context))

        for value in ("", "false"):
            with self.subTest(value=value):
                context["request"] = RequestFactory().get("/", {"nocompress": value})
                self.assertEqual(self.original_content, self.template.render(context))

        self.assertEqual(self.compressed_content, self.template.render(self.context))

    @override_settings(COMPRESS_DEBUG_TOGGLE=None)
    def test_debug_toggle_disabled(self):
        request = RequestFactory().get("/", {"nocompress": "true"})
        context = dict(self.context, request=request)
        self.assertEqual(self.compressed_content, self.template.render(context))

    @override_settings(COMPRESS_OFFLINE=True)
    def test_debug_toggle_bypasses_offline_manifest(self):
        request = RequestFactory().get("/", {"nocompress": "true"})
        context = dict(self.context, request=request)
        self.assertEqual(self.original_content, self.template.render(context))

    @override_settings(COMPRESS_OFFLINE=True)
    def test_offline_generation_ignores_debug_toggle(self):
        from compressor.offline.jinja2 import Jinja2Parser

        parser = Jinja2Parser("utf-8", self.env)
        template = self.env.parse(self.template_string)
        node = next(parser.walk_nodes(template))
        request = RequestFactory().get("/", {"nocompress": "true"})
        context = dict(self.context, request=request)
        self.assertEqual(
            self.compressed_content, parser.render_node(template, context, node)
        )
