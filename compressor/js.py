from compressor.conf import settings
from compressor.base import Compressor, SOURCE_HUNK, SOURCE_FILE


class JsCompressor(Compressor):

    def __init__(self, content=None, output_prefix="js", context=None):
        super(JsCompressor, self).__init__(content, output_prefix, context)
        self.filters = list(settings.COMPRESS_JS_FILTERS)
        self.type = output_prefix
        self.supported_attribs = getattr(settings, 'JS_SCRIPT_ATTRIBS',
                                           ['async', 'defer'])

    def split_contents(self):
        if self.split_content:
            return self.split_content
        self.script_attribs = {}
        for elem in self.parser.js_elems():
            data = None
            attribs = self.parser.elem_attribs(elem)
            if 'src' in attribs:
                basename = self.get_basename(attribs['src'])
                filename = self.get_filename(basename)
                data = (SOURCE_FILE, filename, basename, elem)
            else:
                content = self.parser.elem_content(elem)
                data = (SOURCE_HUNK, content, None, elem)
            if data:
                self.split_content.append(data)
                script_attrib = None
                for attr in self.supported_attribs:
                    if attr in attribs:
                        script_attrib = attr
                        break
                script_attrib = script_attrib or ''
                # check for existing node with same script type
                append_to_existing = self.script_attribs and script_attrib in self.script_attribs
                if append_to_existing:
                    self.script_attribs[script_attrib].split_content.append(data)
                else:
                    node = self.__class__(content=self.parser.elem_str(elem),
                                          context=self.context)
                    node.split_content.append(data)
                    self.script_attribs[script_attrib] = node
        return self.split_content

    def output(self, *args, **kwargs):
        if (settings.COMPRESS_ENABLED or settings.COMPRESS_PRECOMPILERS or
                kwargs.get('forced', False)):
            self.split_contents()
            if hasattr(self, 'script_attribs'):
                ret = []
                for attr, node in self.script_attribs.iteritems():
                    # make use of an empty attrib (async, defer don't take values)
                    # may need to override as needed
                    node.extra_context.update({'tag': attr})
                    ret.append(node.output(*args, **kwargs))
                return ''.join(ret)
        return super(JsCompressor, self).output(*args, **kwargs)
