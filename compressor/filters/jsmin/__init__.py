from __future__ import absolute_import
from compressor.filters import CallbackOutputFilter
from compressor.filters.jsmin.slimit import SlimItFilter  # noqa


class rJSMinFilter(CallbackOutputFilter):
    callback = "rjsmin.jsmin"
    dependencies = ["rjsmin"]
    kwargs = {
        "keep_bang_comments": True
    }

# This is for backwards compatibility
JSMinFilter = rJSMinFilter
