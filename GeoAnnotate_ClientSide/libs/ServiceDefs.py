import fnmatch, os, re
import sys, traceback, pathlib
from datetime import datetime


def enum(sequential, **named):
    enums = dict(zip(sequential, range(len(sequential))), **named)
    return type('Enum', (), enums)

def DoesPathExistAndIsDirectory(pathStr):
    if os.path.exists(pathStr) and os.path.isdir(pathStr):
        return True
    else:
        return False

def DoesPathExistAndIsFile(pathStr):
    if os.path.exists(pathStr) and os.path.isfile(pathStr):
        return True
    else:
        return False

def find_files(directory, pattern):
    flist = []
    for root, dirs, files in os.walk(directory):
        for basename in files:
            if fnmatch.fnmatch(basename, pattern):
                filename = os.path.join(root, basename)
                filename = filename.replace('\\', '/')
                flist.append(filename)
    return flist

def find_directories(directory, pattern=None, maxdepth=None):
    for root, dirs, files in os.walk(directory):
        for d in dirs:
            if pattern is None:
                retname = os.path.join(root, d, '')
                yield retname
            elif fnmatch.fnmatch(d, pattern):
                retname = os.path.join(root, d, '')
                retname = retname.replace('\\\\', os.sep)
                if maxdepth is None:
                    yield retname
                else:
                    if retname.count(os.sep)-directory.count(os.sep) <= maxdepth:
                        yield retname


def EnsureDirectoryExists(pathStr):
    if not DoesPathExistAndIsDirectory(pathStr):
        try:
            # os.mkdir(pathStr)
            pathlib.Path(pathStr).mkdir(parents=True, exist_ok=True)
        except Exception as ex:
            err_fname = './errors.log'
            exc_type, exc_value, exc_traceback = sys.exc_info()
            with open(err_fname, 'a') as errf:
                traceback.print_tb(exc_traceback, limit=None, file=errf)
                traceback.print_exception(exc_type, exc_value, exc_traceback, limit=None, file=errf)
            print(str(ex))
            print('the directory you are trying to place a file to doesn\'t exist and cannot be created:\n%s' % pathStr)
            raise FileNotFoundError('the directory you are trying to place a file to doesn\'t exist and cannot be created:')



def ReportException(err_fname, ex, **kwargs):
    exc_type, exc_value, exc_traceback = sys.exc_info()
    with open(err_fname, 'a') as errf:
        errf.write('================ ' + str(datetime.now()) + ' ================\n')
        traceback.print_tb(exc_traceback, limit=None, file=errf)
        traceback.print_exception(exc_type, exc_value, exc_traceback, limit=None, file=errf)
        if len(kwargs) > 0:
            errf.write('\n')
            for k in kwargs.keys():
                errf.write('......%s......\n' % k)
                errf.write('%s' % kwargs[k])
                errf.write('\n')
        errf.write('\n\n\n')



def SortFNamesByDateTime(fnames_list):
    fnames_dicts = [{'fname': fn, 'dt': DateTimeFromDataFName(fn)} for fn in fnames_list]
    fnames_dicts = sorted(fnames_dicts, key=lambda x: x['dt'])
    fnames_sorted = [f['fname'] for f in fnames_dicts]
    return fnames_sorted


def DateTimeFromDataFName(fname):
    import re
    basename = os.path.basename(fname)
    regex = r'.+_(\d{4})(\d{2})(\d{2})(\d{2})(\d{2})(\d{2})\.nc'
    m = re.match(regex, basename)
    year, month, day, hour, minute, second = m.groups()
    return datetime(int(year), int(month), int(day), int(hour), int(minute), int(second))