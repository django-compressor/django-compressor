class ParserBase(object):
    """
    Base parser to be subclassed when creating an own parser.
    """
    def __init__(self, content):
        self.content = content

    def css_elems(self):
        """
        Return an iterable containing the css elements to handle
        """
        raise NotImplementedError

    def js_elems(self):
        """
        Return an iterable containing the js elements to handle
        """
        raise NotImplementedError

    def elem_attribs(self, elem):
        """
        Return the dictionary like attribute store of the given element
        """
        raise NotImplementedError

    def elem_content(self, elem):
        """
        Return the content of the given element
        """
        raise NotImplementedError

    def elem_name(self, elem):
        """
        Return the name of the given element
        """
        raise NotImplementedError

    def elem_str(self, elem):
        """
        Return the string representation of the given elem
        """
        raise NotImplementedError
