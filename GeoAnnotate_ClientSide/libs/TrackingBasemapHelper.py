import datetime
import json
import logging
import sys

import numpy as np
# from netCDF4 import Dataset
import io
import cv2
import pickle
import uuid
import threading
import requests
import re
from io import BytesIO
import pandas as pd
from libs.ga_defs import *
import binascii
from common.srvMCSlabel import srvMCSlabel
import ast
from common.BasemapFrame import *
from libs.settings import Settings
from types import SimpleNamespace



### TODO: remove if not needed
# basemaps_pickled_list_csvfile = './cache/basemaps_pickled_list.csv'

# C1 = 1.19104e-5 # mWm−2 sr−1 (cm−1)4
# C2 = 1.43877 # K (cm−1)−1

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
# A_values = {'ch4': 0.9915,
#             'ch5': 0.9960,
#             'ch6': 0.9991,
#             'ch7': 0.9996,
#             'ch8': 0.9999,
#             'ch9': 0.9983,
#             'ch10':0.9988,
#             'ch11':0.9982}
#
# B_values = {'ch4': 2.9002,
#             'ch5': 2.0337,
#             'ch6': 0.4340,
#             'ch7': 0.1714,
#             'ch8': 0.0527,
#             'ch9': 0.6084,
#             'ch10':0.3882,
#             'ch11':0.5390}
#
# nu_central = {'ch4': 2547.771 ,
#              'ch5':  1595.621 ,
#              'ch6':  1360.377 ,
#              'ch7':  1148.130 ,
#              'ch8':  1034.715 ,
#              'ch9':  929.842 ,
#              'ch10': 838.659 ,
#              'ch11': 750.653 }


class TrackingBasemapHelperClass:
    def __init__(self, app_args):
        self.app_args = app_args
        self.srvSourceDataList = None
        self.dataSourceServersideUUID = ''
        self.dataSourceServersideDatetime = datetime.datetime(1970,1,1,0,0,0)
        self.zoom = 1.0
        self.cLat = None
        self.cLon = None
        self.LathalfRange = None
        self.LonHalfRange = None
        self.llcrnrlon = None
        self.llcrnrlat = None
        self.urcrnrlon = None
        self.urcrnrlat = None
        self.BasemapLayerImage = None
        self.CVimageCombined = None
        self.dataToPlot = 'ch9'
        self.webapi_client_id = binascii.hexlify(os.urandom(24)).decode("utf-8")

        self.remotehost = 'localhost'

        self.channelsDescriptions = {'ch9': 'ch9: 10.8 micron',
                                     'ch5': 'ch5: 6.2 micron',
                                     'ch5_ch9': 'ch5 - ch9',
                                     'lat': 'latitudes',
                                     'lon': 'longitudes'}
        self.channelNames = ['ch9', 'ch5', 'ch5_ch9']


    def ComputeCenterAndRange(self):
        self.cLat = (self.urcrnrlat + self.llcrnrlat) * 0.5
        self.LathalfRange = (self.urcrnrlat - self.llcrnrlat) * 0.5
        self.cLon = (self.urcrnrlon + self.llcrnrlon) * 0.5
        self.LonHalfRange = (self.lons_re.max() - self.lons_re.min()) * 0.5
        self.llcrnrlon = self.cLon - self.LonHalfRange * 1.05
        self.llcrnrlat = self.cLat - self.LathalfRange * 1.05
        self.urcrnrlon = self.cLon + self.LonHalfRange * 1.05
        self.urcrnrlat = self.cLat + self.LathalfRange * 1.05


    def deflate_recieved_dict(self, rec_dict):
        self.BasemapLayerImage = np.copy(rec_dict['BasemapLayerImage'])
        self.CVimageCombined = np.copy(rec_dict['CVimageCombined'])
        for dataname in self.channelNames:
            self.__dict__['DataLayerImage_%s' % dataname] = np.copy(rec_dict['DataLayerImage_%s' % dataname])
        self.llcrnrlon = rec_dict['llcrnrlon']
        self.llcrnrlat = rec_dict['llcrnrlat']
        self.urcrnrlon = rec_dict['urcrnrlon']
        self.urcrnrlat = rec_dict['urcrnrlat']
        self.cLat = rec_dict['cLat']
        self.cLon = rec_dict['cLon']
        self.LathalfRange = rec_dict['LathalfRange']
        self.LonHalfRange = rec_dict['LonHalfRange']
        self.dataToPlot = rec_dict['dataToPlot']



    def send_close_signal(self):
        url1 = 'http://%s:1999/imdone?webapi_client_id=%s' % (self.remotehost, self.webapi_client_id)
        try:
            if self.app_args.http_logging:
                logging.info(url1)
            req1 = requests.get(url1)
        except Exception as ex:
            print('Request failed. Please check the connection.')
            ReportException('./logs/errors.log', ex)
            raise RequestFailedException()
        print(req1.headers)
        ctype = req1.headers['Content-Type']
        m = re.match(r'.+charset=(.+)', ctype)
        enc = 'utf-8'
        if m is not None:
            enc = m.groups()[0]
            print('encoding detected: %s' % enc)
        print(req1.status_code)



    def initiate(self, basemap_args: SimpleNamespace = None):
        url = 'http://%s:1999/exec?command=createbmhelper&webapi_client_id=%s' % (self.remotehost,
                                                                                  self.webapi_client_id)
        try:
            req = requests.get(url, json=json.dumps(basemap_args.__dict__))
            # req = requests.get(url, stream=True)
            if self.app_args.http_logging:
                logging.info(url)
        except Exception as ex:
            print('Request failed. Please check the connection.')
            ReportException('./logs/errors.log', ex)
            raise RequestFailedException()


        print(req.headers)
        ctype = req.headers['Content-Type']
        m = re.match(r'.+charset=(.+)', ctype)
        enc = 'utf-8'
        if m is not None:
            enc = m.groups()[0]
            print('encoding detected: %s' % enc)
        print(req.status_code)

        for line in streamlines_gen(req):
            print(line)
            if line == 'READY':
                print('Got READY response. Serverside client-server comm.agent is ready.')


    def RequestDataSnapshotsList(self,
                                 dt_start: datetime.datetime = datetime.datetime(1970, 1, 1, 0, 0, 0),
                                 dt_end: datetime.datetime = datetime.datetime(2101, 1, 1, 0, 0, 0)):

        url1 = 'http://%s:1999/exec?command=listData&webapi_client_id=%s&dt_start=%s&dt_end=%s' % (self.remotehost,
                                                                                                   self.webapi_client_id,
                                                                                                   datetime.datetime.strftime(dt_start, '%Y-%m-%d-%H-%M-%S'),
                                                                                                   datetime.datetime.strftime(dt_end, '%Y-%m-%d-%H-%M-%S'))
        url2 = 'http://%s:1999/datalist?webapi_client_id=%s' % (self.remotehost, self.webapi_client_id)

        try:
            req1 = requests.get(url1, stream=True)
            if self.app_args.http_logging:
                logging.info(url1)
        except Exception as ex:
            print('Request failed. Please check the connection.')
            ReportException('./logs/errors.log', ex)
            raise RequestFailedException()


        print(req1.headers)
        ctype = req1.headers['Content-Type']
        m = re.match(r'.+charset=(.+)', ctype)
        enc = 'utf-8'
        if m is not None:
            enc = m.groups()[0]
            print('encoding detected: %s' % enc)
        print(req1.status_code)

        for line in streamlines_gen(req1):
            print(line)
            if line == 'READY':
                print('Got READY response. Serverside source data list is ready. Requesting it.')
                try:
                    req = requests.get(url2)
                    if self.app_args.http_logging:
                        logging.info(url2)
                except Exception as ex:
                    print('Request failed. Please check the connection.')
                    ReportException('./logs/errors.log', ex)
                    raise RequestFailedException()

                print(req.status_code)
                print(req.headers)
                enc = 'utf-8'
                if m is not None:
                    enc = m.groups()[0]
                    print('encoding detected: %s' % enc)

                req_json = req.content.decode(enc)

                rec_dict = ast.literal_eval(req_json)
                rec_dict = [rec_dict[k] for k in rec_dict.keys()]
                def convert_datetime(dct):
                    dct['dt'] = datetime.datetime.strptime(dct['dt_str'], '%Y-%m-%d-%H-%M-%S')
                    return dct
                rec_dict = [convert_datetime(d) for d in rec_dict]
                rec_dict.sort(key = lambda s: s['dt'])
                src_data_df = pd.DataFrame(rec_dict)

                self.srvSourceDataList = src_data_df



    def RequestPreparedImages(self, resolution = 'c', calculateLatLonLimits=True):
        url = 'http://%s:1999/images?webapi_client_id=%s' % (self.remotehost, self.webapi_client_id)
        try:
            req = requests.get(url)
            if self.app_args.http_logging:
                logging.info(url)
        except Exception as ex:
            print('Request failed. Please check the connection.')
            ReportException('./logs/errors.log', ex)
            raise RequestFailedException()

        print(req.status_code)
        print(req.headers)

        self.srvUUID2DataDesc = req.content

        rec_dict = None
        with BytesIO() as bytesf:
            bytesf.write(req.content)
            bytesf.seek(0)
            rec_dict = pickle.load(bytesf)

        if rec_dict is not None:
            self.deflate_recieved_dict(rec_dict)
        else:
            raise Exception('Generated images transfer failed.')


    def FuseBasemapWithData(self, alpha = 0.3, beta = 0.7):
        BasemapImageCV = cv2.imdecode(self.BasemapLayerImage, cv2.IMREAD_COLOR)
        DataLayerImageCV = cv2.imdecode(self.__dict__['DataLayerImage_%s' % self.dataToPlot], cv2.IMREAD_COLOR)
        self.CVimageCombined = cv2.addWeighted(BasemapImageCV, alpha, DataLayerImageCV, beta, 0.0)



    def SetNewLatLonLimits(self, llcrnrlon, llcrnrlat, urcrnrlon, urcrnrlat, resolution='c'):
        url1 = 'http://%s:1999/exec?command=SetNewLatLonLimits&llcrnrlon=%.5f&llcrnrlat=%.5f&urcrnrlon=%.5f&urcrnrlat=%.5f&resolution=%s&webapi_client_id=%s' % (self.remotehost, llcrnrlon, llcrnrlat, urcrnrlon, urcrnrlat, resolution, self.webapi_client_id)
        url2 = 'http://%s:1999/images?webapi_client_id=%s' % (self.remotehost, self.webapi_client_id)
        try:
            req1 = requests.get(url1, stream=True)
            if self.app_args.http_logging:
                logging.info(url1)
        except Exception as ex:
            print('Request failed. Please check the connection.')
            ReportException('./logs/errors.log', ex)
            raise RequestFailedException()

        print(req1.headers)
        ctype = req1.headers['Content-Type']
        m = re.match(r'.+charset=(.+)', ctype)
        enc = 'utf-8'
        if m is not None:
            enc = m.groups()[0]
            print('encoding detected: %s' % enc)
        print(req1.status_code)

        for line in streamlines_gen(req1):
            print(line)
            if line == 'READY':
                print('got READY response')
                print('requesting image')

                try:
                    req2 = requests.get(url2)
                    if self.app_args.http_logging:
                        logging.info(url2)
                except Exception as ex:
                    print('Request failed. Please check the connection.')
                    ReportException('./logs/errors.log', ex)
                    raise RequestFailedException()

                print(req2.status_code)
                print(req2.headers)

                rec_dict = None
                with BytesIO() as bytesf:
                    bytesf.write(req2.content)
                    bytesf.seek(0)
                    rec_dict = pickle.load(bytesf)


                if rec_dict is not None:
                    self.deflate_recieved_dict(rec_dict)
                else:
                    raise Exception('Generated images transfer failed.')



    def SwitchSourceData(self, uuid):
        self.dataSourceUUID = uuid

        url1 = 'http://%s:1999/exec?command=SwitchSourceData&uuid=%s&webapi_client_id=%s' % (self.remotehost, uuid, self.webapi_client_id)
        url2 = 'http://%s:1999/images?webapi_client_id=%s' % (self.remotehost, self.webapi_client_id)
        try:
            req1 = requests.get(url1, stream=True)
            if self.app_args.http_logging:
                logging.info(url1)
        except Exception as ex:
            print('Request failed. Please check the connection.')
            ReportException('./logs/errors.log', ex)
            raise RequestFailedException()

        print(req1.headers)
        ctype = req1.headers['Content-Type']
        m = re.match(r'.+charset=(.+)', ctype)
        enc = 'utf-8'
        if m is not None:
            enc = m.groups()[0]
            print('encoding detected: %s' % enc)
        print(req1.status_code)

        for line in streamlines_gen(req1):
            print(line)
            if line == 'READY':
                print('got READY response')
                print('requesting image')

                try:
                    req2 = requests.get(url2)
                    if self.app_args.http_logging:
                        logging.info(url2)
                except Exception as ex:
                    print('Request failed. Please check the connection.')
                    ReportException('./logs/errors.log', ex)
                    raise RequestFailedException()
                print(req2.status_code)
                print(req2.headers)

                rec_dict = None
                with BytesIO() as bytesf:
                    bytesf.write(req2.content)
                    bytesf.seek(0)
                    rec_dict = pickle.load(bytesf)

                if rec_dict is not None:
                    self.deflate_recieved_dict(rec_dict)
                else:
                    raise Exception('Generated images transfer failed.')


    # def SwitchSourceData(self, filename):
    #     self.dataSourceFile = filename
    #     # self.ReadSourceData()
    #
    #     url1 = 'http://%s:1999/exec?command=SwitchSourceData&src_fname=%s&webapi_client_id=%s' % (self.remotehost, os.path.basename(self.dataSourceFile), self.webapi_client_id)
    #     url2 = 'http://%s:1999/images?webapi_client_id=%s' % (self.remotehost, self.webapi_client_id)
    #     try:
    #         req1 = requests.get(url1, stream=True)
    #         if self.app_args.http_logging:
    #             logging.info(url1)
    #     except Exception as ex:
    #         print('Request failed. Please check the connection.')
    #         ReportException('./logs/errors.log', ex)
    #         raise RequestFailedException()
    #
    #     print(req1.headers)
    #     ctype = req1.headers['Content-Type']
    #     m = re.match(r'.+charset=(.+)', ctype)
    #     enc = 'utf-8'
    #     if m is not None:
    #         enc = m.groups()[0]
    #         print('encoding detected: %s' % enc)
    #     print(req1.status_code)
    #
    #     for line in streamlines_gen(req1):
    #         print(line)
    #         if line == 'READY':
    #             print('got READY response')
    #             print('requesting image')
    #
    #             try:
    #                 req2 = requests.get(url2)
    #                 if self.app_args.http_logging:
    #                     logging.info(url2)
    #             except Exception as ex:
    #                 print('Request failed. Please check the connection.')
    #                 ReportException('./logs/errors.log', ex)
    #                 raise RequestFailedException()
    #             print(req2.status_code)
    #             print(req2.headers)
    #
    #             rec_dict = None
    #             with BytesIO() as bytesf:
    #                 bytesf.write(req2.content)
    #                 bytesf.seek(0)
    #                 rec_dict = pickle.load(bytesf)
    #
    #             if rec_dict is not None:
    #                 self.deflate_recieved_dict(rec_dict)
    #             else:
    #                 raise Exception('Generated images transfer failed.')



    def RequestPredictedMCSlabels(self):
        url1 = 'http://%s:1999/exec?command=PredictMCScurrentData&webapi_client_id=%s' % (self.remotehost, self.webapi_client_id)
        url2 = 'http://%s:1999/predictions?webapi_client_id=%s' % (self.remotehost, self.webapi_client_id)
        try:
            req1 = requests.get(url1, stream=True)
            if self.app_args.http_logging:
                logging.info(url1)
        except Exception as ex:
            print('Request failed. Please check the connection.')
            ReportException('./logs/errors.log', ex)
            raise RequestFailedException()

        print(req1.headers)
        ctype = req1.headers['Content-Type']
        m = re.match(r'.+charset=(.+)', ctype)
        enc = 'utf-8'
        if m is not None:
            enc = m.groups()[0]
            print('encoding detected: %s' % enc)
        print(req1.status_code)

        for line in streamlines_gen(req1):
            print(line)
            if line == 'READY':
                print('got READY response')
                print('requesting labels')

                try:
                    req2 = requests.get(url2)
                    if self.app_args.http_logging:
                        logging.info(url2)
                except Exception as ex:
                    print('Request failed. Please check the connection.')
                    ReportException('./logs/errors.log', ex)
                    raise RequestFailedException()
                print(req2.status_code)
                print(req2.headers)

                rec_dict = None
                with BytesIO() as bytesf:
                    bytesf.write(req2.content)
                    bytesf.seek(0)
                    rec_dict = pickle.load(bytesf)

                if rec_dict is not None:
                    print(rec_dict)
                else:
                    logging.info('Received empty detected labels.')
                    rec_dict = None
        return rec_dict



    def cycleChannel(self, perform = True):
        newChannel = ''
        if self.dataToPlot == 'ch9':
            newChannel = 'ch5'
        elif self.dataToPlot == 'ch5':
            newChannel = 'ch5_ch9'
        elif self.dataToPlot == 'ch5_ch9':
            newChannel = 'ch9'

        if perform:
            self.dataToPlot = newChannel
            self.FuseBasemapWithData()
            return newChannel
        else:
            return newChannel


    def getValueStr_AtCoordinates(self, posLon, posLat):
        currData = self.__dict__['data_%s' % self.dataToPlot]
        dlat = self.lats - posLat
        dlon = self.lons - posLon
        dsqr = np.square(dlat) + np.square(dlon)
        nearest_value = currData[np.unravel_index(np.argmin(dsqr), dsqr.shape)]
        return '%f' % nearest_value



def create_basemaphelper(args, settings: Settings):
    try:
        helper = TrackingBasemapHelperClass(args)
        helper.initiate(basemap_args=settings.basemap_args)
    except:
        helper = None
        EnsureDirectoryExists('./logs/')
        ReportException('./logs/error.log', None)
        logging.warning('Unable to create client-server communication agent. The app functionality will be limited.')
    return helper