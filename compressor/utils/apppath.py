# -*- coding: utf-8 -*-
import os
from django.conf import settings

def __get_app_paths():
    app_paths = set()
    for app in settings.INSTALLED_APPS:
        module = __import__(app)
        app_paths.add(module.__path__[0])
    return app_paths

__app_paths = __get_app_paths()

def get_app_path_for_filepath(file_path):
    for path in __app_paths:
        if file_path.startswith(path):
            return path
    return None

