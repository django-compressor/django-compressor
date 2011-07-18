from slimit import minify

from compressor.filters import FilterBase


class SlimItFilter(FilterBase):
    def output(self, **kwargs):
        return minify(self.content, mangle=True)
