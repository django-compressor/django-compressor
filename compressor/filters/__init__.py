class FilterBase(object):
    def __init__(self, content, filter_type=None, verbose=0):
        self.type = filter_type
        self.content = content
        self.verbose = verbose

    def input(self, **kwargs):
        raise NotImplementedError
    def output(self, **kwargs):
        raise NotImplementedError
        
class FilterError(Exception):
    """
    This exception is raised when a filter fails
    """
    pass

def get_class(class_string):
    """
    Convert a string version of a function name to the callable object.
    """

    if not hasattr(class_string, '__bases__'):

        try:
            class_string = class_string.encode('ascii')
            mod_name, class_name = get_mod_func(class_string)
            if class_name != '':
                cls = getattr(__import__(mod_name, {}, {}, ['']), class_name)
        except (ImportError, AttributeError):
            raise FilterError('Failed to import filter %s' % class_string)

    return cls

def get_mod_func(callback):
    """
    Converts 'django.views.news.stories.story_detail' to
    ('django.views.news.stories', 'story_detail')
    """

    try:
        dot = callback.rindex('.')
    except ValueError:
        return callback, ''
    return callback[:dot], callback[dot+1:]
