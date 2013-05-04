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

__app_paths = __get_app_paths()

def search_in_apps(file):
    try:
        file_path = AppDirectoriesFinder().find(file)
        if len(file_path) > 0:
            if isinstance(file_path, list):
                file_path = file_path[0]
            return file_path
        return None
    except:
        return None

def search_in_dirs(file):
    for dir in settings.STATICFILES_DIRS:
        path = os.path.join(dir, file)
        if os.path.isfile(path):
            return os.path.dirname(dir)
    return None

def get_filename(dir, full_path):
    file = full_path.replace(dir, '')
    if file[:1] == '/':
        file = file[1:]
    return file

def get_app_path_for_filepath(file_path):
    if file_path.startswith(settings.STATIC_ROOT):
        file = get_filename(settings.STATIC_ROOT, file_path)
        file_path = search_in_apps(file)
        if file_path is None:
            path = search_in_dirs(file)
            if path is not None:
                return path
    else:
        for dir in settings.STATICFILES_DIRS:
            if file_path.startswith(dir):
                file = get_filename(dir, file_path)
                path = search_in_apps(file)
                if path is None:
                    return search_in_dirs(file)
                else:
                    file_path = path
                break

    if file_path is not None:
        for path in __app_paths:
            if file_path.startswith(path):
                return path
    return settings.STATIC_ROOT


