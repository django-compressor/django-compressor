from compressor.exceptions import FilterError
from django.urls import get_mod_func


def get_class(class_string, exception=FilterError):
    """
    Convert a string version of a function name to the callable object.
    """
    if not hasattr(class_string, '__bases__'):
        try:
            class_string = str(class_string)
            mod_name, class_name = get_mod_func(class_string)
            if class_name:
                return getattr(__import__(mod_name, {}, {}, [str('')]), class_name)
        except AttributeError as e:
            raise exception('Failed to import %s. AttributeError is: %s' % (class_string, e))
        except ImportError as e:
            raise exception('Failed to import %s. ImportError is: %s' % (class_string, e))

        raise exception("Invalid class path '%s'" % class_string)
