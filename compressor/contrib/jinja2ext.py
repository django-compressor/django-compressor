from jinja2 import nodes
from jinja2.ext import Extension
from jinja2.exceptions import TemplateSyntaxError

from compressor.templatetags.compress import OUTPUT_FILE, CompressorMixin


class CompressorExtension(CompressorMixin, Extension):

    tags = set(['compress'])

    def parse(self, parser):
        lineno = next(parser.stream).lineno
        kindarg = parser.parse_expression()
        # Allow kind to be defined as jinja2 name node
        if isinstance(kindarg, nodes.Name):
            kindarg = nodes.Const(kindarg.name)
        args = [kindarg]
        if args[0].value not in self.compressors:
            raise TemplateSyntaxError('compress kind may be one of: %s' %
                                      (', '.join(self.compressors.keys())),
                                      lineno)
        if parser.stream.skip_if('comma'):
            modearg = parser.parse_expression()
            # Allow mode to be defined as jinja2 name node
            if isinstance(modearg, nodes.Name):
                modearg = nodes.Const(modearg.name)
                args.append(modearg)
        else:
            args.append(nodes.Const('file'))

        body = parser.parse_statements(['name:endcompress'], drop_needle=True)

        # Skip the kind if used in the endblock, by using the kind in the
        # endblock the templates are slightly more readable.
        parser.stream.skip_if('name:' + kindarg.value)
        return nodes.CallBlock(self.call_method('_compress_normal', args), [], [],
            body).set_lineno(lineno)

    def _compress_forced(self, kind, mode, caller):
        return self._compress(kind, mode, caller, True)

    def _compress_normal(self, kind, mode, caller):
        return self._compress(kind, mode, caller, False)

    def _compress(self, kind, mode, caller, forced):
        mode = mode or OUTPUT_FILE
        original_content = caller()
        context = {
            'original_content': original_content
        }
        return self.render_compressed(context, kind, mode, forced=forced)

    def get_original_content(self, context):
        return context['original_content']
