from compressor.conf import settings
from compressor.filters import CompilerFilter


class CSSTidyFilter(CompilerFilter):
    command = "%(binary)s %(infile)s %(args)s %(outfile)s"
    options = {
        "binary": settings.COMPRESS_CSSTIDY_BINARY,
        "args": settings.COMPRESS_CSSTIDY_ARGUMENTS,
    }
