from compressor.filters import FilterBase
from compressor.filters.jsmin.rjsmin import _make_jsmin

jsmin = _make_jsmin(python_only=True)

class JSMinFilter(FilterBase):
    def output(self, **kwargs):
        return jsmin(self.content)
