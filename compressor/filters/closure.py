from compressor.conf import settings
from compressor.filters import CompilerFilter


class ClosureCompilerFilter(CompilerFilter):
    command = "%(binary)s %(args)s"
    options = {
        "binary": settings.COMPRESS_CLOSURE_COMPILER_ARGUMENTS,
        "args": settings.COMPRESS_CLOSURE_COMPILER_ARGUMENTS,
    }
