from compressor.conf import settings
from compressor.base import Compressor
from compressor.exceptions import UncompressableFileError


class JsCompressor(Compressor):

    def __init__(self, content=None, output_prefix="js"):
        super(JsCompressor, self).__init__(content, output_prefix)
        self.template_name = "compressor/js.html"
        self.template_name_inline = "compressor/js_inline.html"
        self.filters = list(settings.COMPRESS_JS_FILTERS)
        self.type = 'js'

    def split_contents(self):
        if self.split_content:
            return self.split_content
        for elem in self.parser.js_elems():
            attribs = self.parser.elem_attribs(elem)
            if 'src' in attribs:
                try:
                    self.split_content.append(('file', self.get_filename(attribs['src']), elem))
                except UncompressableFileError:
                    if settings.DEBUG:
                        raise
            else:
                content = self.parser.elem_content(elem)
                self.split_content.append(('hunk', content, elem))
        return self.split_content
