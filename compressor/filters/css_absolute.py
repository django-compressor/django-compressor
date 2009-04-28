from compressor.filters import FilterBase, FilterError
from compressor.conf import settings

# steal bits from http://github.com/cjohansen/juicer/blob/35fe866c82d3f5e7804a6f2f4491c1e81da08820/lib/juicer/merger/stylesheet_merger.rb
class CssAbsoluteFilter(FilterBase):
    def input(self, filename=None, **kwargs):
        if not filename or not filename.startswith(settings.MEDIA_ROOT):
            return self.content
        filename = filename[len(settings.MEDIA_ROOT):]
        return "\n".join([filename, self.content])
