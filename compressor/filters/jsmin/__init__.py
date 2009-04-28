from compressor.filters.jsmin.jsmin import jsmin
from compressor.filters import FilterBase

class JSMinFilter(FilterBase):
    def filter_js(self, js):
        return jsmin(js)