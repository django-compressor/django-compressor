from compressor.conf import settings
from compressor.base import Compressor, SOURCE_HUNK, SOURCE_FILE
from compressor.js import JsCompressor

class LdjsonCompressor(JsCompressor):

    def __init__(self, content=None, output_prefix="ldjson", context=None):
        super(LdjsonCompressor, self).__init__(content, output_prefix, context)