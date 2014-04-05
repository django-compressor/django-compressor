from __future__ import absolute_import
import io
from types import MethodType

from django import template
from django.template import Template
from django.template.loader_tags import (ExtendsNode, BlockNode,
                                         BLOCK_CONTEXT_KEY)


from compressor.exceptions import TemplateSyntaxError, TemplateDoesNotExist
from compressor.templatetags.compress import CompressorNode


def patched_render(self, context):
    # 'Fake' _render method that just returns the context instead of
    # rendering. It also checks whether the first node is an extend node or
    # not, to be able to handle complex inheritance chain.
    self._render_firstnode = MethodType(patched_render_firstnode, self)
    self._render_firstnode(context)

    # Cleanup, uninstall our _render monkeypatch now that it has been called
    self._render = self._old_render
    return context


def patched_render_firstnode(self, context):
    # If this template has a ExtendsNode, we want to find out what
    # should be put in render_context to make the {% block ... %}
    # tags work.
    #
    # We can't fully render the base template(s) (we don't have the
    # full context vars - only what's necessary to render the compress
    # nodes!), therefore we hack the ExtendsNode we found, patching
    # its get_parent method so that rendering the ExtendsNode only
    # gives us the blocks content without doing any actual rendering.
    extra_context = {}
    try:
        firstnode = self.nodelist[0]
    except IndexError:
        firstnode = None
    if isinstance(firstnode, ExtendsNode):
        firstnode._log = self._log
        firstnode._log_verbosity = self._log_verbosity
        firstnode._old_get_parent = firstnode.get_parent
        firstnode.get_parent = MethodType(patched_get_parent, firstnode)
        try:
            extra_context = firstnode.render(context)
            context.render_context = extra_context.render_context
            # We aren't rendering {% block %} tags, but we want
            # {{ block.super }} inside {% compress %} inside {% block %}s to
            # work. Therefore, we need to pop() the last block context for
            # each block name, to emulate what would have been done if the
            # {% block %} had been fully rendered.
            for blockname in firstnode.blocks.keys():
                context.render_context[BLOCK_CONTEXT_KEY].pop(blockname)
        except (IOError, template.TemplateSyntaxError,
                template.TemplateDoesNotExist):
            # That first node we are trying to render might cause more errors
            # that we didn't catch when simply creating a Template instance
            # above, so we need to catch that (and ignore it, just like above)
            # as well.
            if self._log_verbosity > 0:
                self._log.write("Caught error when rendering extend node from "
                                "template %s\n" % getattr(self, 'name', self))
            return None
        finally:
            # Cleanup, uninstall our get_parent monkeypatch now that it has been called
            firstnode.get_parent = firstnode._old_get_parent
    return extra_context


def patched_get_parent(self, context):
    # Patch template returned by extendsnode's get_parent to make sure their
    # _render method is just returning the context instead of actually
    # rendering stuff.
    # In addition, this follows the inheritance chain by looking if the first
    # node of the template is an extend node itself.
    compiled_template = self._old_get_parent(context)
    compiled_template._log = self._log
    compiled_template._log_verbosity = self._log_verbosity
    compiled_template._old_render = compiled_template._render
    compiled_template._render = MethodType(patched_render, compiled_template)
    return compiled_template


class DjangoParser(object):
    def __init__(self, charset):
        self.charset = charset

    def parse(self, template_name):
        with io.open(template_name, mode='rb') as file:
            try:
                return Template(file.read().decode(self.charset))
            except template.TemplateSyntaxError as e:
                raise TemplateSyntaxError(str(e))
            except template.TemplateDoesNotExist as e:
                raise TemplateDoesNotExist(str(e))

    def process_template(self, template, context):
        template._render_firstnode = MethodType(patched_render_firstnode, template)
        template._extra_context = template._render_firstnode(context)

        if template._extra_context is None:
            # Something is wrong - ignore this template
            return False

        return True

    def get_init_context(self, offline_context):
        return offline_context

    def process_node(self, template, context, node):
        if template._extra_context and node._block_name:
            # Give a block context to the node if it was found inside
            # a {% block %}.
            context['block'] = context.render_context[BLOCK_CONTEXT_KEY].get_block(node._block_name)

            if context['block']:
                context['block'].context = context

    def render_nodelist(self, template, context, node):
        return node.nodelist.render(context)

    def render_node(self, template, context, node):
        return node.render(context, forced=True)

    def get_nodelist(self, node):
        # Check if node is an ```if``` switch with true and false branches
        if hasattr(node, 'nodelist_true') and hasattr(node, 'nodelist_false'):
            return node.nodelist_true + node.nodelist_false
        return getattr(node, "nodelist", [])

    def walk_nodes(self, node, block_name=None):
        for node in self.get_nodelist(node):
            if isinstance(node, BlockNode):
                block_name = node.name
            if isinstance(node, CompressorNode) and node.is_offline_compression_enabled(forced=True):
                node._block_name = block_name
                yield node
            else:
                for node in self.walk_nodes(node, block_name=block_name):
                    yield node
