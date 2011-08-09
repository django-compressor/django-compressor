from __future__ import absolute_import
from compressor.filters import CallbackOutputFilter

class rJSMinFilter(CallbackOutputFilter):
    callback = "compressor.filters.jsmin.rjsmin.jsmin"

# This is for backwards compatibility
JSMinFilter = rJSMinFilter
