# -*- coding: utf-8 -*-
import os
import sys

from compressor.exceptions import FilterError

if sys.version_info < (2, 5):
    # Add any http://docs.python.org/library/functions.html?#any to Python < 2.5
    def any(seq):
        for item in seq:
            if item:
                return True
        return False

else:
    any = any


if sys.version_info < (2, 6):
    def walk(root, topdown=True, onerror=None, followlinks=False):
        """
        A version of os.walk that can follow symlinks for Python < 2.6
        """
        for dirpath, dirnames, filenames in os.walk(root, topdown, onerror):
            yield (dirpath, dirnames, filenames)
            if followlinks:
                for d in dirnames:
                    p = os.path.join(dirpath, d)
                    if os.path.islink(p):
                        for link_dirpath, link_dirnames, link_filenames in walk(p):
                            yield (link_dirpath, link_dirnames, link_filenames)
else:
    from os import walk


def get_class(class_string, exception=FilterError):
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
            pass
        else:
            return cls
    raise exception('Failed to import %s' % class_string)


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


def find_command(cmd, paths=None, pathext=None):
    """
    Searches the PATH for the given command and returns its path
    """
    if paths is None:
        paths = os.environ.get('PATH', '').split(os.pathsep)
    if isinstance(paths, basestring):
        paths = [paths]
    # check if there are funny path extensions for executables, e.g. Windows
    if pathext is None:
        pathext = get_pathext()
    pathext = [ext for ext in pathext.lower().split(os.pathsep)]
    # don't use extensions if the command ends with one of them
    if os.path.splitext(cmd)[1].lower() in pathext:
        pathext = ['']
    # check if we find the command on PATH
    for path in paths:
        # try without extension first
        cmd_path = os.path.join(path, cmd)
        for ext in pathext:
            # then including the extension
            cmd_path_ext = cmd_path + ext
            if os.path.isfile(cmd_path_ext):
                return cmd_path_ext
        if os.path.isfile(cmd_path):
            return cmd_path
    return None
