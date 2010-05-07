from compressor.filters import FilterBase, FilterError

class CSSMinFilter(FilterBase):
    """
    A filter that utilizes Zachary Voase's Python port of
    the YUI CSS compression algorithm: http://pypi.python.org/pypi/cssmin/
    """
    def output(self, **kwargs):
        try:
            import cssmin
        except ImportError, e:
            if self.verbose:
                raise FilterError('Failed to import cssmin: %s' % e)
            return self.content
        return cssmin.cssmin(self.content)
