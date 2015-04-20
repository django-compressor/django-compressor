from compressor.conf import settings
from compressor.filters import CompilerFilter


class CleanCSSFilter(CompilerFilter):
    command = "{binary} {args} -o {outfile} {infile}"
    options = (
        ("binary", settings.COMPRESS_CLEAN_CSS_BINARY),
        ("args", settings.COMPRESS_CLEAN_CSS_ARGUMENTS),
    )
