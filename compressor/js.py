from compressor.conf import settings
from compressor.base import Compressor, SOURCE_HUNK, SOURCE_FILE


class JsCompressor(Compressor):

    def __init__(self, content=None, output_prefix="js", context=None):
        super(JsCompressor, self).__init__(content, output_prefix, context)
        self.filters = list(settings.COMPRESS_JS_FILTERS)
        self.type = output_prefix

    def split_contents(self):
        if self.split_content:
            return self.split_content
        self.nodes = []
        for elem in self.parser.js_elems():
            attribs = self.parser.elem_attribs(elem)
            if 'src' in attribs:
                basename = self.get_basename(attribs['src'])
                filename = self.get_filename(basename)
                content = (SOURCE_FILE, filename, basename, elem)
            else:
                content = (SOURCE_HUNK, self.parser.elem_content(elem), None, elem)
            self.split_content.append(content)
            extra_attr = ''
            if 'async' in attribs:
                extra_attr = ' async'
            elif 'defer' in attribs:
                extra_attr = ' defer'
            # Append to the previous node if it had the same attribute
            append_to_previous = self.nodes and self.nodes[-1][0] == extra_attr
            if append_to_previous and settings.COMPRESS_ENABLED:
                self.nodes[-1][1].split_content.append(content)
            else:
                node = JsCompressor(content=self.parser.elem_str(elem),
                                    context=self.context)
                node.split_content.append(content)
                self.nodes.append((extra_attr, node))
        return self.split_content

    def output(self, *args, **kwargs):
        if (settings.COMPRESS_ENABLED or settings.COMPRESS_PRECOMPILERS or
                kwargs.get('forced', False)):
            self.split_contents()
            if hasattr(self, 'nodes'):
                ret = []
                for extra_attr, subnode in self.nodes:
                    subnode.extra_context.update({'extra_attr': extra_attr})
                    ret.append(subnode.output(*args, **kwargs))
                return '\n'.join(ret)
        return super(JsCompressor, self).output(*args, **kwargs)
