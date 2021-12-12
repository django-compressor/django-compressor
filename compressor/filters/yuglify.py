from compressor.conf import settings
from compressor.filters import CompilerFilter


class YUglifyFilter(CompilerFilter):
    command = "{binary} {args}"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.command += ' --type=%s' % self.type


class YUglifyCSSFilter(YUglifyFilter):
    type = 'css'
    options = (
        ("binary", settings.COMPRESS_YUGLIFY_BINARY),
        ("args", settings.COMPRESS_YUGLIFY_CSS_ARGUMENTS),
    )


class YUglifyJSFilter(YUglifyFilter):
    type = 'js'
    options = (
        ("binary", settings.COMPRESS_YUGLIFY_BINARY),
        ("args", settings.COMPRESS_YUGLIFY_JS_ARGUMENTS),
    )
