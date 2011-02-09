from compressor.filters import FilterBase
from compressor.filters.cssmin.cssmin import cssmin

class CSSMinFilter(FilterBase):
    """
    A filter that utilizes Zachary Voase's Python port of
    the YUI CSS compression algorithm: http://pypi.python.org/pypi/cssmin/
    """
    def output(self, **kwargs):
        return cssmin(self.content)
