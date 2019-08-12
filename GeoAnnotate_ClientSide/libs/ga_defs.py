import sys, traceback
import os
import datetime
import logging
import numpy as np

C1 = 1.19104e-5 # mWm−2 sr−1 (cm−1)4
C2 = 1.43877 # K (cm−1)−1

'''
from Jean-Claude Thelen and John M. Edwards, "Short-wave radiances: comparison between SEVIRI and the Unified Model"
Q. J. R. Meteorol. Soc. 139: 1665–1679, July 2013 B
DOI:10.1002/qj.2034

| Channel | Band    |    A    |   B   |
--------------------------------------
4         | IR 3.9  | 0.9959  | 3.471 |
5         | WV 6.2  | 0.9963  | 2.219 |
6         | WV 7.3  | 0.9991  | 0.485 |
7         | IR 8.7  | 0.9996  | 0.181 |
8         | IR 9.7  | 0.9999  | 0.060 |
9         | IR 10.8 | 0.9983  | 0.627 |
10        | IR 12.0 | 0.9988  | 0.397 |
11        | IR 13.4 | 0.9981  | 0.576 |



Channel | Band     | λcen   | λmin  | λmax  |
---------------------------------------------
1       | VIS 0.6  | 0.635  | 0.56  | 0.71  |
2       | VIS 0.8  | 0.810  | 0.74  | 0.88  |
3       | NIR 1.6  | 1.640  | 1.50  | 1.78  |
4       | IR 3.9   | 3.900  | 3.48  | 4.36  |
5       | WV 6.2   | 6.250  | 5.35  | 7.15  |
6       | WV 7.3   | 7.350  | 6.85  | 7.85  |
7       | IR 8.7   | 8.700  | 8.30  | 9.10  |
8       | IR 9.7   | 9.660  | 9.38  | 9.94  |
9       | IR 10.8  | 10.800 | 9.80  | 11.80 |
10      | IR 12.0  | 12.000 | 11.00 | 12.00 |
11      | IR 13.4  | 13.400 | 12.40 | 14.40 |
12      | HRV      | —     | 0.40  | 1.10  |

'''
A_values = {'ch4': 0.9915,
            'ch5': 0.9960,
            'ch6': 0.9991,
            'ch7': 0.9996,
            'ch8': 0.9999,
            'ch9': 0.9983,
            'ch10':0.9988,
            'ch11':0.9982}

B_values = {'ch4': 2.9002,
            'ch5': 2.0337,
            'ch6': 0.4340,
            'ch7': 0.1714,
            'ch8': 0.0527,
            'ch9': 0.6084,
            'ch10':0.3882,
            'ch11':0.5390}

nu_central = {'ch4': 2547.771 ,
             'ch5':  1595.621 ,
             'ch6':  1360.377 ,
             'ch7':  1148.130 ,
             'ch8':  1034.715 ,
             'ch9':  929.842 ,
             'ch10': 838.659 ,
             'ch11': 750.653 }



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



class RequestFailedException(Exception):
    def __init__(self):
        super(RequestFailedException, self).__init__()


def ReportException(err_fname, ex):
    exc_type, exc_value, exc_traceback = sys.exc_info()
    with open(err_fname, 'a') as errf:
        errf.write('================ ' + str(datetime.datetime.now()) + ' ================\n')
        traceback.print_tb(exc_traceback, limit=None, file=errf)
        traceback.print_exception(exc_type, exc_value, exc_traceback, limit=None, file=errf)
        errf.write('\n\n\n')



def streamlines_gen(stream, encoding = 'utf-8'):
    line = ''
    for b in stream.iter_content():
        c = b.decode(encoding)
        if c == '\n':
            yield line
            line = ''
        else:
            line = line + c


def t_brightness_calculate(self, data, channelname = 'ch9'):
    if channelname == 'ch5_ch9':
        ch5_temp = t_brightness_calculate(data['ch5'], 'ch5')
        ch9_temp = t_brightness_calculate(data['ch9'], 'ch9')
        return ch5_temp-ch9_temp
    else:
        data.mask[data == data.min()] = True
        A = A_values[channelname]
        B = B_values[channelname]
        nu = nu_central[channelname]
        c = C2 * nu
        e = nu * nu * nu * C1
        logval = np.log(1. + e / data)
        bt = (c / logval - B) / A
        return bt
    return 0