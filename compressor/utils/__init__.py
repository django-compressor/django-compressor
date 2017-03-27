# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import os

from compressor.exceptions import FilterError


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


def get_mod_func(callback):
    """
    Converts 'django.views.news.stories.story_detail' to
    ('django.views.news.stories', 'story_detail')
    """
    try:
        dot = callback.rindex('.')
    except ValueError:
        return callback, ''
    return callback[:dot], callback[dot + 1:]


def get_pathext(default_pathext=None):
    """
    Returns the path extensions from environment or a default
    """
    if default_pathext is None:
        default_pathext = os.pathsep.join(['.COM', '.EXE', '.BAT', '.CMD'])
    return os.environ.get('PATHEXT', default_pathext)
