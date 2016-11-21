# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from contextlib import contextmanager
import os

from django.apps import apps

from compressor.conf import settings
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
        except (ImportError, AttributeError):
            raise exception('Failed to import %s' % class_string)

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


@contextmanager
def url_placeholders():
    if settings.COMPRESS_OFFLINE_URL_PLACEHOLDERS:
        # Backup settings.STATIC_URL and settings.COMPRESS_URL
        settings.STATIC_URL_ORIGIN = settings.STATIC_URL
        settings.COMPRESS_URL_ORIGIN = settings.COMPRESS_URL

        # Replace settings.STATIC_URL and settings.COMPRESS_URL with placeholders
        settings.STATIC_URL = settings.COMPRESS_STATIC_URL_PLACEHOLDER
        settings.COMPRESS_URL = settings.COMPRESS_URL_PLACEHOLDER

        # Needed to reset ``storage.base_url`` in {% static %} tag
        if apps.is_installed('django.contrib.staticfiles'):
            from django.contrib.staticfiles.storage import staticfiles_storage
            staticfiles_storage.base_url = settings.STATIC_URL
        else:
            staticfiles_storage = None

        yield

        # Restore original settings.STATIC_URL and settings.COMPRESS_URL
        settings.STATIC_URL = settings.STATIC_URL_ORIGIN
        settings.COMPRESS_URL = settings.COMPRESS_URL_ORIGIN

        # Needed to reset ``storage.base_url`` in {% static %} tag
        if staticfiles_storage:
            staticfiles_storage.base_url = settings.STATIC_URL
    else:
        yield
