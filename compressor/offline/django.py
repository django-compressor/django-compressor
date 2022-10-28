from copy import copy

from django import template
from django.template import Context
from django.template.base import Node, VariableNode, TextNode, NodeList
from django.template.defaulttags import IfNode
from django.template.loader import get_template
from django.template.loader_tags import (
    BLOCK_CONTEXT_KEY,
    ExtendsNode,
    BlockNode,
    BlockContext,
)


from compressor.exceptions import TemplateSyntaxError, TemplateDoesNotExist
from compressor.templatetags.compress import CompressorNode


def handle_extendsnode(extendsnode, context):
    """Create a copy of Node tree of a derived template replacing
    all blocks tags with the nodes of appropriate blocks.
    Also handles {{ block.super }} tags.
    """
    if BLOCK_CONTEXT_KEY not in context.render_context:
        context.render_context[BLOCK_CONTEXT_KEY] = BlockContext()
    block_context = context.render_context[BLOCK_CONTEXT_KEY]
    blocks = dict(
        (n.name, n) for n in extendsnode.nodelist.get_nodes_by_type(BlockNode)
    )
    block_context.add_blocks(blocks)

    compiled_parent = extendsnode.get_parent(context)
    parent_nodelist = compiled_parent.nodelist
    # If the parent template has an ExtendsNode it is not the root.
    for node in parent_nodelist:
        # The ExtendsNode has to be the first non-text node.
        if not isinstance(node, TextNode):
            if isinstance(node, ExtendsNode):
                return handle_extendsnode(node, context)
            break
    # Add blocks of the root template to block context.
    blocks = dict((n.name, n) for n in parent_nodelist.get_nodes_by_type(BlockNode))
    block_context.add_blocks(blocks)

    block_stack = []
    new_nodelist = remove_block_nodes(parent_nodelist, block_stack, block_context)
    return new_nodelist


def remove_block_nodes(nodelist, block_stack, block_context):
    new_nodelist = NodeList()
    for node in nodelist:
        if isinstance(node, VariableNode):
            var_name = node.filter_expression.token.strip()
            if var_name == "block.super":
                if not block_stack:
                    continue
                node = block_context.get_block(block_stack[-1].name)
                if not node:
                    continue
        if isinstance(node, BlockNode):
            expanded_block = expand_blocknode(node, block_stack, block_context)
            new_nodelist.extend(expanded_block)
        else:
            # IfNode has nodelist as a @property so we can not modify it
            if isinstance(node, IfNode):
                node = copy(node)
                for i, (condition, sub_nodelist) in enumerate(
                    node.conditions_nodelists
                ):
                    sub_nodelist = remove_block_nodes(
                        sub_nodelist, block_stack, block_context
                    )
                    node.conditions_nodelists[i] = (condition, sub_nodelist)
            else:
                for attr in node.child_nodelists:
                    sub_nodelist = getattr(node, attr, None)
                    if sub_nodelist:
                        sub_nodelist = remove_block_nodes(
                            sub_nodelist, block_stack, block_context
                        )
                        node = copy(node)
                        setattr(node, attr, sub_nodelist)
            new_nodelist.append(node)
    return new_nodelist


def expand_blocknode(node, block_stack, block_context):
    popped_block = block = block_context.pop(node.name)
    if block is None:
        block = node
    block_stack.append(block)
    expanded_nodelist = remove_block_nodes(block.nodelist, block_stack, block_context)
    block_stack.pop()
    if popped_block is not None:
        block_context.push(node.name, popped_block)
    return expanded_nodelist


class DjangoParser:
    def __init__(self, charset):
        self.charset = charset

    def parse(self, template_name):
        try:
            return get_template(template_name).template
        except template.TemplateSyntaxError as e:
            raise TemplateSyntaxError(str(e))
        except template.TemplateDoesNotExist as e:
            raise TemplateDoesNotExist(str(e))

    def process_template(self, template, context):
        return True

    def get_init_context(self, offline_context):
        return offline_context

    def process_node(self, template, context, node):
        pass

    def render_nodelist(self, template, context, node):
        context.template = template
        return node.nodelist.render(context)

    def render_node(self, template, context, node):
        return node.render(context, forced=True)

    def get_nodelist(self, node, original, context=None):
        if isinstance(node, ExtendsNode):
            try:
                if context is None:
                    context = Context()
                context.template = original
                return handle_extendsnode(node, context)
            except template.TemplateSyntaxError as e:
                raise TemplateSyntaxError(str(e))
            except template.TemplateDoesNotExist as e:
                raise TemplateDoesNotExist(str(e))

        # Check if node is an ```if``` switch with true and false branches
        nodelist = []
        if isinstance(node, Node):
            for attr in node.child_nodelists:
                # see https://github.com/django-compressor/django-compressor/pull/825
                # and linked issues/PRs for a discussion on the `None) or []` part
                nodelist += getattr(node, attr, None) or []
        else:
            nodelist = getattr(node, "nodelist", [])
        return nodelist

    def walk_nodes(self, node, original=None, context=None):
        if original is None:
            original = node
        for node in self.get_nodelist(node, original, context):
            if isinstance(node, CompressorNode) and node.is_offline_compression_enabled(
                forced=True
            ):
                yield node
            else:
                for node in self.walk_nodes(node, original, context):
                    yield node
