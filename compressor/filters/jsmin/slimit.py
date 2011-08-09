from __future__ import absolute_import
from django.core.exceptions import ImproperlyConfigured
from compressor.filters import CallbackOutputFilter

class SlimItFilter(CallbackOutputFilter):
    dependencies = ["slimit"]
    callback = "slimit.minify"
    kwargs = {
        "mangle": True,
    }
