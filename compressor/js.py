from compressor.conf import settings
from compressor.base import Compressor, SOURCE_HUNK, SOURCE_FILE


class JsCompressor(Compressor):

    def __init__(self, content=None, output_prefix="js", context=None):
        filters = list(settings.COMPRESS_JS_FILTERS)
        super(JsCompressor, self).__init__(content, output_prefix, context, filters)

    def split_contents(self):
        if self.split_content:
            return self.split_content
        self.extra_nodes = []
        for elem in self.parser.js_elems():
            attribs = self.parser.elem_attribs(elem)
            if 'src' in attribs:
                basename = self.get_basename(attribs['src'])
                filename = self.get_filename(basename)
                content = (SOURCE_FILE, filename, basename, elem)
            else:
                content = (SOURCE_HUNK, self.parser.elem_content(elem), None, elem)
            self.split_content.append(content)
            if 'async' in attribs:
                extra = ' async'
            elif 'defer' in attribs:
                extra = ' defer'
            else:
                extra = ''
            # Append to the previous node if it had the same attribute
            append_to_previous = (self.extra_nodes and
                                  self.extra_nodes[-1][0] == extra)
            if append_to_previous and settings.COMPRESS_ENABLED:
                self.extra_nodes[-1][1].split_content.append(content)
            else:
                node = self.__class__(content=self.parser.elem_str(elem),
                                      context=self.context)
                node.split_content.append(content)
                self.extra_nodes.append((extra, node))
        return self.split_content

    def output(self, *args, **kwargs):
        if (settings.COMPRESS_ENABLED or settings.COMPRESS_PRECOMPILERS or
                kwargs.get('forced', False)):
            self.split_contents()
            if hasattr(self, 'extra_nodes'):
                ret = []
                for extra, subnode in self.extra_nodes:
                    subnode.extra_context.update({'extra': extra})
                    ret.append(subnode.output(*args, **kwargs))
                return '\n'.join(ret)
        return super(JsCompressor, self).output(*args, **kwargs)
