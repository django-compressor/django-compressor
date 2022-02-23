import warnings

from django.core.exceptions import ImproperlyConfigured

from compressor.filters import FilterBase, CallbackOutputFilter


class rJSMinFilter(CallbackOutputFilter):
    callback = "rjsmin.jsmin"
    dependencies = ["rjsmin"]
    kwargs = {"keep_bang_comments": True}


# This is for backwards compatibility
JSMinFilter = rJSMinFilter


class SlimItFilter(CallbackOutputFilter):
    dependencies = ["slimit"]
    callback = "slimit.minify"
    kwargs = {
        "mangle": True,
    }

    def __init__(self, *args, **kwargs):
        warnings.warn(
            "SlimItFilter is broken in Python 3.6+ and will be removed in "
            "django-compressor 3.3.",
            DeprecationWarning,
        )
        super().__init__(*args, **kwargs)


class CalmjsFilter(FilterBase):
    def __init__(self, *args, **kwargs):
        try:
            self._parser = kwargs.pop('parser')
        except KeyError:
            self._parser = None
        try:
            self._unparser = kwargs.pop('unparser')
        except KeyError:
            self._unparser = None
        super().__init__(*args, **kwargs)
        try:
            import calmjs.parse
        except ImportError:
            raise ImproperlyConfigured(
                "The module calmjs.parse couldn't be imported. "
                "Make sure it is correctly installed."
            )
        if self._parser is None:
            self._parser = calmjs.parse.es5
        if self._unparser is None:
            self._unparser = calmjs.parse.unparsers.es5.minify_printer(obfuscate=True)

    def output(self, **kwargs):
        program = self._parser(self.content)
        minified = u''.join(part.text for part in self._unparser(program))
        assert isinstance(minified, str)
        return minified
