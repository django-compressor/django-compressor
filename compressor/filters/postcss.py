from compressor.conf import settings
from compressor.filters import CompilerFilter


DEFAULT_BINARY = "postcss"
DEFAULT_ARGS = " "
DEFAULT_PLUGINS = ()


def fetch_options():
    def plugins_as_args(plugins):
        return ''.join(map(lambda plugin: '--use %s ' % plugin, plugins))
    return (
        ("binary", getattr(settings, "COMPRESS_POSTCSS_BINARY", DEFAULT_BINARY)),
        ("args", getattr(settings, "COMPRESS_POSTCSS_ARGS", DEFAULT_ARGS)),
        ("plugins", plugins_as_args(getattr(settings, "COMPRESS_POSTCSS_PLUGINS", DEFAULT_PLUGINS))),
    )


class PostCSSFilter(CompilerFilter):
    command = "{binary} {args} {plugins} -o {outfile} {infile}"
    options = fetch_options()


class PostCSSFilterTestable(PostCSSFilter):
    def __init__(self, *args, **kwargs):
        super(PostCSSFilter, self).__init__(*args, **kwargs)
        self.options = fetch_options()
