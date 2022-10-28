from jinja2 import nodes
from jinja2.ext import Extension
from jinja2.exceptions import TemplateSyntaxError

from compressor.templatetags import compress


# Allow django like definitions which assume constants instead of variables
def const(node):
    if isinstance(node, nodes.Name):
        return nodes.Const(node.name)
    else:
        return node


class CompressorExtension(compress.CompressorMixin, Extension):

    tags = set(["compress"])

    def parse(self, parser):
        # Store the first lineno for the actual function call
        lineno = parser.stream.current.lineno
        next(parser.stream)
        args = []

        kindarg = const(parser.parse_expression())

        if kindarg.value in self.compressors:
            args.append(kindarg)
        else:
            raise TemplateSyntaxError(
                "Compress kind may be one of: %r, got: %r"
                % (self.compressors.keys(), kindarg.value),
                parser.stream.current.lineno,
            )

        # For legacy support, allow for a commma but simply ignore it
        parser.stream.skip_if("comma")

        # Some sane defaults for file output
        namearg = nodes.Const(None)
        modearg = nodes.Const("file")

        # If we're not at the "%}" part yet we must have a output mode argument
        if parser.stream.current.type != "block_end":
            modearg = const(parser.parse_expression())
            args.append(modearg)

            if modearg.value == compress.OUTPUT_FILE:
                # The file mode optionally accepts a name
                if parser.stream.current.type != "block_end":
                    namearg = const(parser.parse_expression())
            elif (
                modearg.value == compress.OUTPUT_INLINE
                or modearg.value == compress.OUTPUT_PRELOAD
            ):
                pass
            else:
                raise TemplateSyntaxError(
                    "Compress mode may be one of: %r, got %r"
                    % (compress.OUTPUT_MODES, modearg.value),
                    parser.stream.current.lineno,
                )

        # Parse everything between the compress and endcompress tags
        body = parser.parse_statements(["name:endcompress"], drop_needle=True)

        # Skip the kind if used in the endblock, by using the kind in the
        # endblock the templates are slightly more readable.
        parser.stream.skip_if("name:" + kindarg.value)

        return nodes.CallBlock(
            self.call_method("_compress_normal", [kindarg, modearg, namearg]),
            [],
            [],
            body,
        ).set_lineno(lineno)

    def _compress_forced(self, kind, mode, name, caller):
        return self._compress(kind, mode, name, caller, True)

    def _compress_normal(self, kind, mode, name, caller):
        return self._compress(kind, mode, name, caller, False)

    def _compress(self, kind, mode, name, caller, forced):
        mode = mode or compress.OUTPUT_FILE
        original_content = caller()
        context = {"original_content": original_content}
        return self.render_compressed(context, kind, mode, name, forced=forced)

    def get_original_content(self, context):
        return context["original_content"]
