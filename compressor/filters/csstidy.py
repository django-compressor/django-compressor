from compressor.conf import settings
from compressor.filters import CompilerFilter


class CSSTidyFilter(CompilerFilter):
    command = "{binary} {infile} {args} {outfile}"
    options = {
        "binary": settings.COMPRESS_CSSTIDY_BINARY,
        "args": settings.COMPRESS_CSSTIDY_ARGUMENTS,
    }
