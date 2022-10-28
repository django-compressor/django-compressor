class CompressorError(Exception):
    """
    A general error of the compressor
    """

    pass


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


class OfflineGenerationError(Exception):
    """
    Offline compression generation related exceptions
    """

    pass


class FilterDoesNotExist(Exception):
    """
    Raised when a filter class cannot be found.
    """

    pass


class TemplateDoesNotExist(Exception):
    """
    This exception is raised when a template does not exist.
    """

    pass


class TemplateSyntaxError(Exception):
    """
    This exception is raised when a template syntax error is encountered.
    """

    pass
