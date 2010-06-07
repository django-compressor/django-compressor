class UncompressableFileError(Exception):
    """
    This exception is raised when a file cannot be compressed
    """
    pass

class FilterError(Exception):
    """
    This exception is raised when a filter fails
    """
    pass

class ParserError(Exception):
    """
    This exception is raised when the parser fails
    """
    pass
