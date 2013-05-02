# -*- coding: utf-8 -*-
import os
from django.conf import settings
from django.contrib.staticfiles.finders import AppDirectoriesFinder
import importlib

def __get_app_paths():
    app_paths = set()
    for app in settings.INSTALLED_APPS:
        module = importlib.import_module(app)
        app_paths.add(os.path.abspath(module.__path__[0]))

    return app_paths

def __get_root_paths():
    root_paths = set()
    root_paths.add(settings.STATIC_ROOT)
    for path in settings.STATICFILES_DIRS:
        root_paths.add(path)
    return root_paths

__app_paths = __get_app_paths()
__root_paths = __get_root_paths()

def get_app_path_for_filepath(file_path):
    for path in __root_paths:
        if file_path.startswith(path):
            file = file_path.replace(path, '')
            if file[:1] == '/':
                file = file[1:]
            try:
                file_path = AppDirectoriesFinder().find(file)
            except:
                return None
    for path in __app_paths:
        if file_path.startswith(path):
            return path
    return None


