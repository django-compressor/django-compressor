from __future__ import absolute_import

import io

from django.template.defaulttags import IfNode

import jinja2
import jinja2.ext
from jinja2 import nodes
from jinja2.ext import Extension
from jinja2.nodes import CallBlock, Call, ExtensionAttribute

from compressor.exceptions import TemplateSyntaxError, TemplateDoesNotExist


def flatten_context(context):
    if hasattr(context, 'dicts'):
        context_dict = {}

        for d in context.dicts:
            context_dict.update(d)

        return context_dict

    return context


class SpacelessExtension(Extension):
    """
    Functional "spaceless" extension equivalent to Django's.

    See: https://github.com/django/django/blob/master/django/template/defaulttags.py
    """

    tags = set(['spaceless'])

    def parse(self, parser):
        lineno = parser.stream.next().lineno
        body = parser.parse_statements(['name:endspaceless'], drop_needle=True)

        return nodes.CallBlock(self.call_method('_spaceless', []),
                               [], [], body).set_lineno(lineno)

    def _spaceless(self, caller):
        from django.utils.html import strip_spaces_between_tags

        return strip_spaces_between_tags(caller().strip())


def url_for(mod, filename):
    """
    Incomplete emulation of Flask's url_for.
    """

    from django.contrib.staticfiles.templatetags import staticfiles

    if mod == "static":
        return staticfiles.static(filename)

    return ""


class Jinja2Parser(object):
    COMPRESSOR_ID = 'compressor.contrib.jinja2ext.CompressorExtension'

    def __init__(self, charset, extensions, loader, filters, globals, options):
        self.env = jinja2.Environment(
            extensions=extensions,
            loader=loader,
            **options
        )
        self.env.globals.update(globals)
        self.env.filters.update(filters)
        self.charset = charset

    def parse(self, template_name):
        with io.open(template_name, mode='rb') as file:
            try:
                template = self.env.parse(file.read().decode(self.charset))
            except jinja2.TemplateSyntaxError as e:
                raise TemplateSyntaxError(str(e))
            except jinja2.TemplateNotFound as e:
                raise TemplateDoesNotExist(str(e))

        return template

    def process_template(self, template, context):
        return True

    def process_node(self, template, context, node):
        context.update(self.env.globals)
        context.update(self.env.filters)

    def render_nodelist(self, template, context, node):
        compiled_node = self.env.compile(jinja2.nodes.Template(node.body))
        template = jinja2.Template.from_code(self.env, compiled_node, {})
        flat_context = flatten_context(context)

        return template.render(flat_context)

    def render_node(self, template, context, node):
        context['__compress_forced'] = True
        compiled_node = self.env.compile(jinja2.nodes.Template([node]))
        template = jinja2.Template.from_code(self.env, compiled_node, {})
        flat_context = flatten_context(context)

        return template.render(flat_context)

    def get_nodelist(self, node):
        if (isinstance(node, IfNode) and
          hasattr(node, 'nodelist_true') and
          hasattr(node, 'nodelist_false')):
            return node.nodelist_true + node.nodelist_false
        return getattr(node, "body", getattr(node, "nodes", []))

    def walk_nodes(self, node, block_name=None):
        for node in self.get_nodelist(node):
            if (isinstance(node, CallBlock) and
              isinstance(node.call, Call) and
              isinstance(node.call.node, ExtensionAttribute) and
              node.call.node.identifier == self.COMPRESSOR_ID):
                yield node
            else:
                for node in self.walk_nodes(node, block_name=block_name):
                    yield node