from compressor.filters import CallbackOutputFilter


class CSSCompressorFilter(CallbackOutputFilter):
    """
    A filter that utilizes Yury Selivanov's Python port of the YUI CSS
    compression algorithm: https://pypi.python.org/pypi/csscompressor
    """

    callback = "csscompressor.compress"
    dependencies = ["csscompressor"]


class rCSSMinFilter(CallbackOutputFilter):
    callback = "rcssmin.cssmin"
    dependencies = ["rcssmin"]
    kwargs = {"keep_bang_comments": True}


# This is for backwards compatibility.
CSSMinFilter = rCSSMinFilter
