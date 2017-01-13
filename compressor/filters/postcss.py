from compressor.conf import settings
from compressor.filters import CompilerFilter


COMPRESS_POSTCSS_BINARY  = "postcss"
COMPRESS_POSTCSS_ARGS    = " "
COMPRESS_POSTCSS_PLUGINS = ()


class PostCSSFilter(CompilerFilter):

    def plugins_as_args(plugins):
        return ''.join(map(lambda plugin: '--use %s ' % plugin, plugins))

    command = "{binary} {args} {plugins} -o {outfile} {infile}"
    options = (
        ("binary", getattr(settings, "COMPRESS_POSTCSS_BINARY", COMPRESS_POSTCSS_BINARY)),
        ("args", getattr(settings, "COMPRESS_POSTCSS_ARGS", COMPRESS_POSTCSS_ARGS)),
        ("plugins", plugins_as_args(getattr(settings, "COMPRESS_POSTCSS_PLUGINS", COMPRESS_POSTCSS_PLUGINS))),
    )
