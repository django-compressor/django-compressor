from compressor.conf import settings
from compressor.base import Compressor, SOURCE_HUNK, SOURCE_FILE
from compressor.exceptions import UncompressableFileError


class JsCompressor(Compressor):
    template_name = "compressor/js.html"
    template_name_inline = "compressor/js_inline.html"

    def __init__(self, content=None, output_prefix="js"):
        super(JsCompressor, self).__init__(content, output_prefix)
        self.filters = list(settings.COMPRESS_JS_FILTERS)
        self.type = 'js'

    def split_contents(self):
        if self.split_content:
            return self.split_content
        for elem in self.parser.js_elems():
            attribs = self.parser.elem_attribs(elem)
            if 'src' in attribs:
                try:
                    basename = self.get_basename(attribs['src'])
                    filename = self.get_filename(basename)
                    self.split_content.append(
                        (SOURCE_FILE, filename, basename, elem))
                except UncompressableFileError:
                    if settings.DEBUG:
                        raise
            else:
                content = self.parser.elem_content(elem)
                self.split_content.append((SOURCE_HUNK, content, None, elem))
        return self.split_content
