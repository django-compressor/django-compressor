from compressor.conf import settings
from compressor.filters import CompilerFilter


class ClosureCompilerFilter(CompilerFilter):
    command = "{binary} {args}"
    options = (
        ("binary", settings.COMPRESS_CLOSURE_COMPILER_BINARY),
        ("args", settings.COMPRESS_CLOSURE_COMPILER_ARGUMENTS),
    )
