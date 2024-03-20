from compressor.conf import settings
from compressor.filters import CompilerFilter


class LightningCSSFilter(CompilerFilter):
    command = "{binary} {args} {infile} -o {outfile}"
    options = (
        ("binary", settings.COMPRESS_LIGHTNING_CSS_BINARY),
        ("args", settings.COMPRESS_LIGHTNING_CSS_ARGUMENTS),
    )
