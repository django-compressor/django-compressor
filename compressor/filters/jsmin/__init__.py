from compressor.filters.jsmin.jsmin import jsmin
from compressor.filters import FilterBase

class JSMinFilter(FilterBase):
    def output(self, **kwargs):
        return jsmin(self.content)