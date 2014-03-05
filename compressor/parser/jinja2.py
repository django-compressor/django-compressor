from __future__ import absolute_import

import io

from django.template.defaulttags import IfNode

import jinja2
from jinja2.nodes import CallBlock, Call, ExtensionAttribute

from compressor.contrib.jinja2ext import CompressorExtension
from compressor.exceptions import TemplateSyntaxError

# TODO:
COMPRESSOR_JINJA2_ENV = {

}
COMPRESSOR_JINJA2_GLOBALS = {}
COMPRESSOR_JINJA2_FILTERS = {}


def flatten_context(context):
    if hasattr(context, 'dicts'):
        context_dict = {}

        for d in context.dicts:
            context_dict.update(d)

        return context_dict
    else:
        return context


class Jinja2Parser(object):
    COMPRESSOR_ID = 'compressor.contrib.jinja2ext.CompressorExtension'

    def __init__(self, charset, filters, globals, options):
        self.charset = charset
        self.env = jinja2.Environment(extensions=[CompressorExtension],
                                      **options)
        self.env.globals.update(globals)
        self.env.filters.update(filters)

    def parse(self, template_name):
        with io.open(template_name, mode='rb') as file:
            try:
                template = self.env.parse(file.read().decode(self.charset))
            except jinja2.TemplateSyntaxError as e:
                raise TemplateSyntaxError(str(e))

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
        context['compress_forced'] = True
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
