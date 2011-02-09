from compressor.conf import settings
from compressor.exceptions import FilterError

class FilterBase(object):
    def __init__(self, content, filter_type=None, verbose=0):
        self.type = filter_type
        self.content = content
        self.verbose = verbose or settings.COMPRESS_VERBOSE

    def input(self, **kwargs):
        raise NotImplementedError

    def output(self, **kwargs):
        raise NotImplementedError
