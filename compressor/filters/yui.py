from compressor.conf import settings
from compressor.filters import CompilerFilter


class YUICompressorFilter(CompilerFilter):
    command = "{binary} {args}"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.command += " --type=%s" % self.type
        if self.verbose:
            self.command += " --verbose"


class YUICSSFilter(YUICompressorFilter):
    type = "css"
    options = (
        ("binary", settings.COMPRESS_YUI_BINARY),
        ("args", settings.COMPRESS_YUI_CSS_ARGUMENTS),
    )


class YUIJSFilter(YUICompressorFilter):
    type = "js"
    options = (
        ("binary", settings.COMPRESS_YUI_BINARY),
        ("args", settings.COMPRESS_YUI_JS_ARGUMENTS),
    )
