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
from itertools import cycle



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

        self.webapi_client_id = binascii.hexlify(os.urandom(24)).decode("utf-8")

        self.remotehost = 'localhost'

        if self.app_args.labels_type == 'MCS':
            self.channelsDescriptions = {'ch9': 'ch9: 10.8 micron',
                                         'ch5': 'ch5: 6.2 micron',
                                         'ch5_ch9': 'ch5 - ch9',
                                         'lat': 'latitudes',
                                         'lon': 'longitudes'}
            self.channelNames = ['ch9', 'ch5', 'ch5_ch9']
            self.channelNamesCycle = cycle(self.channelNames)
            self.currentChannel = next(self.channelNamesCycle)
        elif ((self.app_args.labels_type == 'PL') | (self.app_args.labels_type == 'MC')):
            self.channelsDescriptions = {'wvp': 'wvp: integrated water vapor',
                                         'wsp': 'wsp: 10m. wind speed',
                                         'lat': 'latitudes',
                                         'lon': 'longitudes'}
            self.channelNames = ['wvp', 'wsp']
            self.channelNamesCycle = cycle(self.channelNames)
            self.currentChannel = next(self.channelNamesCycle)
        elif (self.app_args.labels_type == 'AMRC'):
            self.channelsDescriptions = {'IR': 'IR: infrared',
                                         'WV': 'WV: integrated water vapor',
                                         'lat': 'latitudes',
                                         'lon': 'longitudes'}
            self.channelNames = ['IR', 'WV']
            self.channelNamesCycle = cycle(self.channelNames)
            self.currentChannel = next(self.channelNamesCycle)
        self.lons_proj = None
        self.lats_proj = None



    def deflate_recieved_dict(self, rec_dict):
        self.BasemapLayerImage = np.copy(rec_dict['BasemapLayerImage'])
        # self.CVimageCombined = np.copy(rec_dict['CVimageCombined'])
        for dataname in self.channelNames:
            self.__dict__['DataLayerImage_%s' % dataname] = np.copy(rec_dict['DataLayerImage_%s' % dataname])
            self.__dict__['DataInterpolated_%s' % dataname] = np.copy(rec_dict['DataInterpolated_%s' % dataname])
        # self.currentChannel = rec_dict['currentChannel']
        self.lons_proj = rec_dict['lons_proj']
        self.lats_proj = rec_dict['lats_proj']



    def xy2value(self, posx: int = 0, posy: int = 0):
        dataname = self.currentChannel

        try:
            retVal = self.__dict__['DataInterpolated_%s' % dataname][int(np.round(self.lons_proj.shape[0]-posy)), int(np.round(posx))]
        except:
            retVal = 0

        return retVal


    def xy2latlon(self, posx: int = 0, posy: int = 0):
        retLat, retLon = 0.0, 0.0
        try:
            retLon = self.lons_proj[int(np.round(self.lons_proj.shape[0] - posy)), int(np.round(posx))]
            retLat = self.lats_proj[int(np.round(self.lats_proj.shape[0] - posy)), int(np.round(posx))]
        except:
            ReportException('./logs/error.log', None)

        return retLon, retLat


    def latlon2xy(self, poslat: float = 45, poslon: float = 45):
        # top-left corner based;
        # xy in terms of data arrays indices
        retx, rety = 0,0
        try:
            latlon_dist = np.sqrt(((self.lats_proj-poslat)**2 + (self.lons_proj - poslon)**2))
            ind = np.argmin(latlon_dist)
            ind = np.unravel_index(ind, self.lats_proj.shape)
            retx = ind[1]
            rety = self.lats_proj.shape[0]-ind[0]
            if rety < 0:
                rety = 0
            elif rety > self.lats_proj.shape[0]-1:
                rety = self.lats_proj.shape[0]-1
        except:
            ReportException('./logs/error.log', None)
        return retx, rety



    def send_close_signal(self):
        url1 = 'http://%s:%d/imdone?webapi_client_id=%s' % (self.remotehost, self.app_args.port, self.webapi_client_id)
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



    def initiate(self, basemap_args: dict = None):
        url = 'http://%s:%d/exec?command=createbmhelper&webapi_client_id=%s' % (self.remotehost,
                                                                                self.app_args.port,
                                                                                self.webapi_client_id)
        try:
            req = requests.get(url, json=json.dumps(basemap_args))
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

        url1 = 'http://%s:%d/exec?command=listData&webapi_client_id=%s&dt_start=%s&dt_end=%s' % (self.remotehost,
                                                                                                 self.app_args.port,
                                                                                                 self.webapi_client_id,
                                                                                                 datetime.datetime.strftime(dt_start, '%Y-%m-%d-%H-%M-%S'),
                                                                                                 datetime.datetime.strftime(dt_end, '%Y-%m-%d-%H-%M-%S'))
        url2 = 'http://%s:%d/datalist?webapi_client_id=%s' % (self.remotehost, self.app_args.port, self.webapi_client_id)

        try:
            req1 = requests.get(url1, stream=True)
            if self.app_args.http_logging:
                logging.info(url1)
        except Exception as ex:
            print('Request failed. You may want to check your connection.')
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
                if req_json == 'There is no data in this date/time range':
                    rec_dict = {}
                    src_data_df = None
                else:
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
        url = 'http://%s:%d/images?webapi_client_id=%s' % (self.remotehost, self.app_args.port, self.webapi_client_id)
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
        BasemapImageCV = self.BasemapLayerImage
        DataLayerImageCV = self.__dict__['DataLayerImage_%s' % self.currentChannel]
        self.CVimageCombined = cv2.addWeighted(BasemapImageCV, alpha, DataLayerImageCV, beta, 0.0)



    def SetNewLatLonLimits(self, llcrnrlon, llcrnrlat, urcrnrlon, urcrnrlat, resolution='c'):
        url1 = 'http://%s:%d/exec?command=SetNewLatLonLimits&llcrnrlon=%.5f&llcrnrlat=%.5f&urcrnrlon=%.5f&urcrnrlat=%.5f&resolution=%s&webapi_client_id=%s' % (self.remotehost, self.app_args.port, llcrnrlon, llcrnrlat, urcrnrlon, urcrnrlat, resolution, self.webapi_client_id)
        url2 = 'http://%s:%d/images?webapi_client_id=%s' % (self.remotehost, self.app_args.port, self.webapi_client_id)
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

        url1 = 'http://%s:%d/exec?command=SwitchSourceData&uuid=%s&webapi_client_id=%s' % (self.remotehost, self.app_args.port, uuid, self.webapi_client_id)
        url2 = 'http://%s:%d/images?webapi_client_id=%s' % (self.remotehost, self.app_args.port, self.webapi_client_id)
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

    def RequestPredictedMCSlabels(self):
        url1 = 'http://%s:%d/exec?command=PredictMCScurrentData&webapi_client_id=%s' % (self.remotehost, self.app_args.port, self.webapi_client_id)
        url2 = 'http://%s:%d/predictions?webapi_client_id=%s' % (self.remotehost, self.app_args.port, self.webapi_client_id)
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
        newChannel = next(self.channelNamesCycle)
        # if self.currentChannel == 'ch9':
        #     newChannel = 'ch5'
        # elif self.currentChannel == 'ch5':
        #     newChannel = 'ch5_ch9'
        # elif self.currentChannel == 'ch5_ch9':
        #     newChannel = 'ch9'

        if perform:
            self.currentChannel = newChannel
            self.FuseBasemapWithData()
            return newChannel
        else:
            return newChannel


    def getValueStr_AtCoordinates(self, posLon, posLat):
        currData = self.__dict__['data_%s' % self.currentChannel]
        dlat = self.lats - posLat
        dlon = self.lons - posLon
        dsqr = np.square(dlat) + np.square(dlon)
        nearest_value = currData[np.unravel_index(np.argmin(dsqr), dsqr.shape)]
        return '%f' % nearest_value



def create_basemaphelper(args, basemap_args: dict):
    try:
        helper = TrackingBasemapHelperClass(args)
        helper.initiate(basemap_args=basemap_args)
    except:
        helper = None
        EnsureDirectoryExists('./logs/')
        ReportException('./logs/error.log', None)
        logging.warning('Unable to create client-server communication agent. The app functionality will be limited.')
    return helper