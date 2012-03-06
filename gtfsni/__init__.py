
import os
from os.path import join as pathjoin, abspath, dirname, exists as pathexists


PACKAGE_DATA_ROOT = pathjoin(abspath(dirname(__file__)), 'data')
try:
    from django.conf import settings
    APPLICATION_DATA_ROOT = settings.DATA_ROOT
except (ImportError, AttributeError):
    APPLICATION_DATA_ROOT = None
if not APPLICATION_DATA_ROOT:
    APPLICATION_DATA_ROOT = pathjoin(abspath(os.getcwd()), 'data')

def get_pkg_data(path):
    return pathjoin(PACKAGE_DATA_ROOT, path)

def get_app_data(path, ensure_root_exists=True):
    fpath = pathjoin(APPLICATION_DATA_ROOT, path)
    if ensure_root_exists:
        if fpath.endswith('/'):
            root = fpath
        else:
            root = dirname(fpath)
        if not pathexists(root):
            os.makedirs(root)
    return fpath

def make_app_dir(path):
    dirpath = pathjoin(APPLICATION_DATA_ROOT, path)
    if not pathexists(dirpath):
        os.makedirs(dirpath)
    return dirpath

