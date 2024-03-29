import sys, traceback
import os
import datetime

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


def EnsureDirectoryExists(pathStr):
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


def ReportException(err_fname):
    exc_type, exc_value, exc_traceback = sys.exc_info()
    with open(err_fname, 'a') as errf:
        errf.write('================ ' + str(datetime.datetime.now()) + ' ================\n')
        traceback.print_tb(exc_traceback, limit=None, file=errf)
        traceback.print_exception(exc_type, exc_value, exc_traceback, limit=None, file=errf)
        errf.write('\n\n\n')


def ReportError(err_fname, webapi_client_id, error_description, error_additional_data):
    with open(err_fname, 'a') as errf:
        errf.write('================ ' + str(datetime.datetime.now()) + ' ================\n')
        errf.writelines('webapi_client_id: \t%s' % webapi_client_id)
        errf.writelines('error_description: \t%s' % error_description)
        errf.writelines('error_data: \t%s' % error_additional_data)
        errf.write('\n\n\n')