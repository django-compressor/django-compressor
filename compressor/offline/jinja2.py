import io

import jinja2
import jinja2.ext
from jinja2 import nodes
from jinja2.ext import Extension
from jinja2.nodes import CallBlock, Call, ExtensionAttribute

from compressor.exceptions import TemplateSyntaxError, TemplateDoesNotExist


def flatten_context(context):
    if hasattr(context, "dicts"):
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

    tags = set(["spaceless"])

    def parse(self, parser):
        lineno = next(parser.stream).lineno
        body = parser.parse_statements(["name:endspaceless"], drop_needle=True)

        return nodes.CallBlock(
            self.call_method("_spaceless", []), [], [], body
        ).set_lineno(lineno)

    def _spaceless(self, caller):
        from django.utils.html import strip_spaces_between_tags

        return strip_spaces_between_tags(caller().strip())


def url_for(mod, filename):
    """
    Incomplete emulation of Flask's url_for.
    """
    try:
        from django.contrib.staticfiles.templatetags import staticfiles
    except ImportError:
        # Django 3.0+
        import django.templatetags.static as staticfiles

    if mod == "static":
        return staticfiles.static(filename)

    return ""


class Jinja2Parser:
    COMPRESSOR_ID = "compressor.contrib.jinja2ext.CompressorExtension"

    def __init__(self, charset, env):
        self.charset = charset
        self.env = env

    def parse(self, template_name):
        with io.open(template_name, mode="rb") as file:
            try:
                template = self.env.parse(file.read().decode(self.charset))
            except jinja2.TemplateSyntaxError as e:
                raise TemplateSyntaxError(str(e))
            except jinja2.TemplateNotFound as e:
                raise TemplateDoesNotExist(str(e))

        return template

    def process_template(self, template, context):
        return True

    def get_init_context(self, offline_context):
        # Don't need to add filters and tests to the context, as Jinja2 will
        # automatically look for them in self.env.filters and self.env.tests.
        # This is tested by test_complex and test_templatetag.

        # Allow offline context to override the globals.
        context = self.env.globals.copy()
        context.update(flatten_context(offline_context))

        return context

    def process_node(self, template, context, node):
        pass

    def _render_nodes(self, template, context, nodes):
        compiled_node = self.env.compile(jinja2.nodes.Template(nodes))
        template = jinja2.Template.from_code(self.env, compiled_node, {})
        flat_context = flatten_context(context)

        return template.render(flat_context)

    def render_nodelist(self, template, context, node):
        return self._render_nodes(template, context, node.body)

    def render_node(self, template, context, node):
        return self._render_nodes(template, context, [node])

    def get_nodelist(self, node):
        body = getattr(node, "body", getattr(node, "nodes", []))

        if isinstance(node, jinja2.nodes.If):
            return body + node.else_

        return body

    def walk_nodes(self, node, block_name=None, context=None):
        for node in self.get_nodelist(node):
            if (
                isinstance(node, CallBlock)
                and isinstance(node.call, Call)
                and isinstance(node.call.node, ExtensionAttribute)
                and node.call.node.identifier == self.COMPRESSOR_ID
            ):
                node.call.node.name = "_compress_forced"
                yield node
            else:
                for node in self.walk_nodes(node, block_name=block_name):
                    yield node
