from __future__ import with_statement

import os
import sys

from mock import Mock

from django.template import Template, Context, TemplateSyntaxError
from django.test import TestCase

from compressor.conf import settings
from compressor.signals import post_compress
from compressor.tests.test_base import css_tag, test_dir

from sekizai.context import SekizaiContext


def render(template_string, context_dict=None):
    """
    A shortcut for testing template output.
    """
    if context_dict is None:
        context_dict = {}
    c = SekizaiContext(context_dict)
    t = Template(template_string)
    return t.render(c).strip()


class SekiaziTestCase(TestCase):
    maxDiff = None

    def setUp(self):
        self.old_enabled = settings.COMPRESS_ENABLED
        settings.COMPRESS_ENABLED = True
        self.context = {'STATIC_URL': settings.COMPRESS_URL}

    def tearDown(self):
        settings.COMPRESS_ENABLED = self.old_enabled

    def test_empty_tag(self):
        template = u"""{% load sekizai_tags %}{% addtoblock "js" %}{% endaddtoblock "js" %}{% render_block "js" postprocessor "compressor.contrib.sekizai.compress" %}"""
        self.assertEqual(u'', render(template, self.context))

    def test_css_tag(self):
        template = u"""{% load sekizai_tags %}{% addtoblock "css" %}
<link rel="stylesheet" href="{{ STATIC_URL }}css/one.css" type="text/css">
<style type="text/css">p { border:5px solid green;}</style>
<link rel="stylesheet" href="{{ STATIC_URL }}css/two.css" type="text/css">
{% endaddtoblock %}{% render_block "css" postprocessor "compressor.contrib.sekizai.compress" %}"""
        out = css_tag("/static/CACHE/css/e41ba2cc6982.css")
        self.assertEqual(out, render(template, self.context))

    def test_uppercase_rel(self):
        template = u"""{% load sekizai_tags %}{% addtoblock "css" %}
<link rel="StyleSheet" href="{{ STATIC_URL }}css/one.css" type="text/css">
<style type="text/css">p { border:5px solid green;}</style>
<link rel="StyleSheet" href="{{ STATIC_URL }}css/two.css" type="text/css">
{% endaddtoblock %}{% render_block "css" postprocessor "compressor.contrib.sekizai.compress" %}"""
        out = css_tag("/static/CACHE/css/e41ba2cc6982.css")
        self.assertEqual(out, render(template, self.context))

    def test_nonascii_css_tag(self):
        template = u"""{% load sekizai_tags %}{% addtoblock "css" %}
        <link rel="stylesheet" href="{{ STATIC_URL }}css/nonasc.css" type="text/css">
        <style type="text/css">p { border:5px solid green;}</style>
        {% endaddtoblock %}{% render_block "css" postprocessor "compressor.contrib.sekizai.compress" %}
        """
        out = css_tag("/static/CACHE/css/799f6defe43c.css")
        self.assertEqual(out, render(template, self.context))

    def test_js_tag(self):
        template = u"""{% load sekizai_tags %}{% addtoblock "js" %}
        <script src="{{ STATIC_URL }}js/one.js" type="text/javascript"></script>
        <script type="text/javascript">obj.value = "value";</script>
        {% endaddtoblock %}{% render_block "js" postprocessor "compressor.contrib.sekizai.compress" %}
        """
        out = u'<script type="text/javascript" src="/static/CACHE/js/066cd253eada.js"></script>'
        self.assertEqual(out, render(template, self.context))

    def test_nonascii_js_tag(self):
        template = u"""{% load sekizai_tags %}{% addtoblock "js" %}
        <script src="{{ STATIC_URL }}js/nonasc.js" type="text/javascript"></script>
        <script type="text/javascript">var test_value = "\u2014";</script>
        {% endaddtoblock %}{% render_block "js" postprocessor "compressor.contrib.sekizai.compress" %}
        """
        out = u'<script type="text/javascript" src="/static/CACHE/js/e214fe629b28.js"></script>'
        self.assertEqual(out, render(template, self.context))

    def test_nonascii_latin1_js_tag(self):
        template = u"""{% load sekizai_tags %}{% addtoblock "js" %}
        <script src="{{ STATIC_URL }}js/nonasc-latin1.js" type="text/javascript" charset="latin-1"></script>
        <script type="text/javascript">var test_value = "\u2014";</script>
        {% endaddtoblock %}{% render_block "js" postprocessor "compressor.contrib.sekizai.compress" %}
        """
        out = u'<script type="text/javascript" src="/static/CACHE/js/be9e078b5ca7.js"></script>'
        self.assertEqual(out, render(template, self.context))

    def test_compress_tag_with_illegal_arguments(self):
        template = u"""{% load sekizai_tags %}{% addtoblock "pony" %}
        <script type="pony/application">unicorn</script>
        {% endaddtoblock %}{% render_block "pony" postprocessor "compressor.contrib.sekizai.compress" %}"""
        self.assertRaises(TemplateSyntaxError, render, template, {})

    def test_debug_toggle(self):
        template = u"""{% load sekizai_tags %}{% addtoblock "js" %}
        <script src="{{ STATIC_URL }}js/one.js" type="text/javascript"></script>
        <script type="text/javascript">obj.value = "value";</script>
        {% endaddtoblock %}{% render_block "js" postprocessor "compressor.contrib.sekizai.compress" %}
        """

        class MockDebugRequest(object):
            GET = {settings.COMPRESS_DEBUG_TOGGLE: 'true'}

        context = dict(self.context, request=MockDebugRequest())
        out = u"""<script src="/static/js/one.js" type="text/javascript"></script>
        <script type="text/javascript">obj.value = "value";</script>"""
        self.assertEqual(out, render(template, context))

    def test_templatetag(self):
        template = u"""{% load sekizai_tags %}{% addtoblock "js" %}
        <script type="text/javascript">var tmpl="{% templatetag openblock %} if x == 3 %}x IS 3{% templatetag openblock %} endif %}"</script>
        {% endaddtoblock %}{% render_block "js" postprocessor "compressor.contrib.sekizai.compress" %}
        """
        out = u'<script type="text/javascript" src="/static/CACHE/js/e9fce10d884d.js"></script>'
        self.assertEqual(out, render(template, self.context))
