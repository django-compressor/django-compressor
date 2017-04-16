from compressor.conf import settings
from compressor.filters import CompilerFilter


class CSSOFilter(CompilerFilter):
    command = "{binary} {args} --input {infile} --output {outfile}"
    options = (
        ("binary", settings.COMPRESS_CSSO_BINARY),
        ("args", settings.COMPRESS_CSSO_ARGUMENTS),
    )
