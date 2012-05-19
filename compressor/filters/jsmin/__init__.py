from __future__ import absolute_import
from compressor.filters import CallbackOutputFilter
from compressor.filters.jsmin.slimit import SlimItFilter  # noqa


class rJSMinFilter(CallbackOutputFilter):
    callback = "compressor.filters.jsmin.rjsmin.jsmin"

# This is for backwards compatibility
JSMinFilter = rJSMinFilter
