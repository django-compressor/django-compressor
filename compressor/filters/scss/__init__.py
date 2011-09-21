from compressor.filters import CallbackOutputFilter


class PyScssFilter(CallbackOutputFilter):
    """
    A filter that compiles .scss files into css with PyScss
    https://github.com/Kronuz/pyScss
    """
    callback = "compressor.filters.scss.scss_filter.run"
