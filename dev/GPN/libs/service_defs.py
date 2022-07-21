import os, sys, fnmatch
import numpy as np
from lxml import etree
import hashlib, json
import re


def find_files(directory, pattern):
    import os, fnmatch
    flist = []
    for root, dirs, files in os.walk(directory):
        for basename in files:
            if fnmatch.fnmatch(basename, pattern):
                filename = os.path.join(root, basename)
                filename = filename.replace('\\', '/')
                flist.append(filename)
    return flist




def orthodrome(pt1, pt2):
    return np.sqrt(np.sum(((pt2-pt1)*(np.asarray([np.cos(np.pi*pt1[1]/180), 1.])) * 111.3)**2))




def DoesPathExistAndIsDirectory(pathStr):
    if os.path.exists(pathStr) and os.path.isdir(pathStr):
        return True
    else:
        return False


def EnsureDirectoryExists(pathStr):
    import traceback
    if not DoesPathExistAndIsDirectory(pathStr):
        try:
            os.mkdir(pathStr)
        except Exception as ex:
            err_fname = './errors.log'
            exc_type, exc_value, exc_traceback = sys.exc_info()
            with open(err_fname, 'a') as errf:
                traceback.print_tb(exc_traceback, limit=None, file=errf)
                traceback.print_exception(exc_type, exc_value, exc_traceback, limit=None, file=errf)
            print(str(ex))
            print('the directory you are trying to place a file to doesn\'t exist and cannot be created:\n%s' % pathStr)
            raise FileNotFoundError('the directory you are trying to place a file to doesn\'t exist and cannot be created:')

