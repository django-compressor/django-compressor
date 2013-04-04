# -*- coding: utf-8 -*-
import os
from django.conf import settings

__app_paths = None

def __get_app_paths():
    if __app_paths is None:
	app_paths = []
        for app in settings.INSTALLED_APPS:
            module = __import__(app)
            app_paths.append(dir(module))
	__app_paths = app_paths
    return __app_paths

__get_app_paths()

def get_app_path_for_filepath(file_path):
    app_paths = __get_app_paths()
    for path in app_paths:
        if file_path.startswith(path):
            return path
    return None

