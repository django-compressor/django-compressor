from compressor.filters import CallbackOutputFilter


class CSSMinFilter(CallbackOutputFilter):
    """
    A filter that utilizes Zachary Voase's Python port of
    the YUI CSS compression algorithm: http://pypi.python.org/pypi/cssmin/
    """
    callback = "compressor.filters.cssmin.cssmin.cssmin"


class rCSSMinFilter(CallbackOutputFilter):
    callback = "compressor.filters.cssmin.rcssmin.cssmin"
