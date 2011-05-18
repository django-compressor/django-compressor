from compressor.utils import staticfiles
from compressor.storage import CompressorFileStorage


class CompressorFinder(staticfiles.finders.BaseStorageFinder):
    """
    A staticfiles finder that looks in COMPRESS_ROOT
    for compressed files, to be used during development
    with staticfiles development file server or during
    deployment.
    """
    storage = CompressorFileStorage
