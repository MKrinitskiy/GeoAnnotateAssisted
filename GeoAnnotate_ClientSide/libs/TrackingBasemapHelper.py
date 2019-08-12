# import matplotlib
# # matplotlib.use('Qt5Agg')
# # matplotlib.use('TkAgg')
# matplotlib.use('ps')

# from matplotlib import pyplot as plt
# from mpl_toolkits.basemap import Basemap
import numpy as np
from netCDF4 import Dataset
import io, cv2, pickle, uuid, threading, requests, re
from io import BytesIO
import pandas as pd
from libs.ga_defs import *
import binascii



# basemaps_pickled_list_csvfile = './cache/basemaps_pickled_list.csv'

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


class TrackingBasemapHelperClass(object):
    def __init__(self, dataSourceFile):
        self.dataSourceFile = dataSourceFile
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
        # self.channelColormaps = ['jet', self.create_ch5_cmap(), 'spring']



    # def create_ch5_cmap(self):
    #     from matplotlib import cm
    #     from matplotlib.colors import ListedColormap
    #
    #     ch5_vmin = 200.
    #     ch5_vmax = 320.
    #     ch5_vm1 = 237.
    #     jet_cnt = int(512 * (ch5_vm1 - ch5_vmin) / (ch5_vmax - ch5_vmin))
    #     gray_cnt = 512 - jet_cnt
    #     jet = cm.get_cmap('jet', jet_cnt)
    #     gray = cm.get_cmap('gray', gray_cnt)
    #     jetcolors = jet(np.linspace(0, 1, jet_cnt))
    #     graycolors = gray(np.linspace(0, 1, gray_cnt))
    #     newcolors = np.concatenate([jetcolors[::-1], graycolors[::-1]], axis=0)
    #     newcm = ListedColormap(newcolors)
    #     return newcm


    @classmethod
    def t_brightness_calculate(self, data, channelname = 'ch9'):
        if channelname == 'ch5_ch9':
            ch5_temp = TrackingBasemapHelperClass.t_brightness_calculate(data['ch5'], 'ch5')
            ch9_temp = TrackingBasemapHelperClass.t_brightness_calculate(data['ch9'], 'ch9')
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


    def ReadSourceData(self, calculateLatLonLimits = True):
        ds1 = Dataset(self.dataSourceFile, 'r')

        self.lats = ds1.variables['lat'][:]
        self.lons = ds1.variables['lon'][:]

        for dataname in self.channelNames:
            if dataname == 'ch5_ch9':
                ch5_data = ds1.variables['ch5'][:]
                ch5_data.mask = self.lats.mask
                ch9_data = ds1.variables['ch5'][:]
                ch9_data.mask = self.lats.mask
                curr_data = {'ch5': ch5_data, 'ch9': ch9_data}
                self.__dict__['data_%s' % dataname] = TrackingBasemapHelperClass.t_brightness_calculate(curr_data, dataname)
            else:
                curr_data = ds1.variables[dataname][:]
                curr_data.mask = self.lats.mask
                self.__dict__['data_%s' % dataname] = TrackingBasemapHelperClass.t_brightness_calculate(curr_data, dataname)



        ds1.close()

        while self.lats.min() < 0.0:
            self.lats[self.lats < 0.0] = self.lats[self.lats < 0.0] + 360.
        while self.lons.min() < 0.0:
            self.lons[self.lons < 0.0] = self.lons[self.lons < 0.0] + 360.

        self.lats_re = np.reshape(self.lats, (-1,))
        self.lons_re = np.reshape(self.lons, (-1,))

        # if calculateLatLonLimits:
        #     self.llcrnrlon = self.lons_re.min()
        #     self.llcrnrlat = self.lats_re.min()
        #     self.urcrnrlon = self.lons_re.max()
        #     self.urcrnrlat = self.lats_re.max()
        #     self.ComputeCenterAndRange()


    def ComputeCenterAndRange(self):
        self.cLat = (self.urcrnrlat + self.llcrnrlat) * 0.5
        self.LathalfRange = (self.urcrnrlat - self.llcrnrlat) * 0.5
        self.cLon = (self.urcrnrlon + self.llcrnrlon) * 0.5
        self.LonHalfRange = (self.lons_re.max() - self.lons_re.min()) * 0.5
        self.llcrnrlon = self.cLon - self.LonHalfRange * 1.05
        self.llcrnrlat = self.cLat - self.LathalfRange * 1.05
        self.urcrnrlon = self.cLon + self.LonHalfRange * 1.05
        self.urcrnrlat = self.cLat + self.LathalfRange * 1.05


    # def listAvailablePickledBasemapObjects(self):
    #     EnsureDirectoryExists('./logs/')
    #     EnsureDirectoryExists(os.path.dirname(basemaps_pickled_list_csvfile))
    #     if os.path.exists(basemaps_pickled_list_csvfile) and os.path.isfile(basemaps_pickled_list_csvfile):
    #         self.df_pickled_basemaps_list = pd.read_csv(basemaps_pickled_list_csvfile, sep=';')
    #         self.df_pickled_basemaps_list['FileNotPresent'] = [(not DoesPathExistAndIsFile(s)) for s in self.df_pickled_basemaps_list.bm_fname]
    #         self.df_pickled_basemaps_list = self.df_pickled_basemaps_list.drop(self.df_pickled_basemaps_list[self.df_pickled_basemaps_list.FileNotPresent].index)
    #     else:
    #         columns = [('llcrnrlon', float),
    #                    ('llcrnrlat', float),
    #                    ('urcrnrlon', float),
    #                    ('urcrnrlat', float),
    #                    ('resolution', str),
    #                    ('bm_fname', str)]
    #         self.df_pickled_basemaps_list = pd.DataFrame({k: pd.Series(dtype=t) for k, t in columns})


    # def loadPickledBasemapObj(self, resolution, eps=1.e-4):
    #     self.listAvailablePickledBasemapObjects()
    #
    #     df_filtered = self.df_pickled_basemaps_list[(np.abs(self.df_pickled_basemaps_list.llcrnrlon-self.llcrnrlon)<=eps) &
    #                                                 (np.abs(self.df_pickled_basemaps_list.llcrnrlat-self.llcrnrlat)<=eps) &
    #                                                 (np.abs(self.df_pickled_basemaps_list.urcrnrlon-self.urcrnrlon)<=eps) &
    #                                                 (np.abs(self.df_pickled_basemaps_list.urcrnrlat-self.urcrnrlat)<=eps) &
    #                                                 (self.df_pickled_basemaps_list.resolution == resolution)]
    #     if df_filtered.shape[0] > 0:
    #         try:
    #             bm = pickle.load(open(df_filtered.bm_fname.iloc[0], 'rb'))
    #             return bm
    #         except Exception as ex:
    #             ReportException('./logs/errors.log', ex)
    #             print('An exception was thrown. Take a look into the ./logs/errors.log file')
    #             return None
    #     else:
    #         return None



    # def savePickledBasemapObj(self, resolution):
    #     fname = './cache/' + str(uuid.uuid4()) + '.pickle'
    #     pickle.dump(self.bm, open(fname, 'wb'), -1)
    #     self.df_pickled_basemaps_list = self.df_pickled_basemaps_list.append({'llcrnrlon': self.llcrnrlon,
    #                                                                           'llcrnrlat': self.llcrnrlat,
    #                                                                           'urcrnrlon': self.urcrnrlon,
    #                                                                           'urcrnrlat': self.urcrnrlat,
    #                                                                           'resolution': resolution,
    #                                                                           'bm_fname': fname},
    #                                                                          ignore_index=True)
    #     self.df_pickled_basemaps_list.to_csv(basemaps_pickled_list_csvfile, sep=';', index=False)



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


    def initiate(self, resolution = 'c', calculateLatLonLimits=True):
        self.ReadSourceData()
        url1 = 'http://%s:1999/exec?command=createbmhelper&src_fname=%s&resolution=%s&calculateLatLonLimits=%s&webapi_client_id=%s' % (self.remotehost, os.path.basename(self.dataSourceFile), resolution, str(calculateLatLonLimits), self.webapi_client_id)
        url2 = 'http://%s:1999/images?webapi_client_id=%s' % (self.remotehost, self.webapi_client_id)
        try:
            req1 = requests.get(url1, stream=True)
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
                except Exception as ex:
                    print('Request failed. Please check the connection.')
                    ReportException('./logs/errors.log', ex)
                    raise RequestFailedException()

                print(req2.status_code)
                print(req2.headers)
                # with open(os.path.join(os.getcwd(), 'demo', r2.headers['fileName']), 'wb') as f:
                #     f.write(r2.content)

                rec_dict = None
                with BytesIO() as bytesf:
                    bytesf.write(req2.content)
                    bytesf.seek(0)
                    # pilImage = Image.open(bytesf, 'r')
                    # cv2Image = np.copy(np.array(pilImage))
                    rec_dict = pickle.load(bytesf)

                if rec_dict is not None:
                    self.deflate_recieved_dict(rec_dict)
                else:
                    raise Exception('Generated images transfer failed.')


    # def createBasemapObj(self, resolution='c'):
    #
    #     self.bm = self.loadPickledBasemapObj(resolution)
    #     if self.bm == None:
    #         self.bm = Basemap(resolution=resolution, projection='cyl',
    #                           llcrnrlon = self.llcrnrlon,
    #                           llcrnrlat = self.llcrnrlat,
    #                           urcrnrlon = self.urcrnrlon,
    #                           urcrnrlat = self.urcrnrlat,
    #                           area_thresh=20000)
    #         self.savePickledBasemapObj(resolution)



    # def PlotBasemapBackground(self):
    #     self.BasemapFigure = plt.figure(figsize=(8, 8), dpi=300)
    #     # self.bm.drawcounties()
    #     self.bm.drawcoastlines()
    #     # self.bm.drawrivers(linewidth=0.5, color='blue')
    #     m = self.bm.drawmeridians([self.lons_re.min() + i * (self.lons_re.max() - self.lons_re.min()) / 5. for i in range(6)])
    #     p = self.bm.drawparallels([self.lats_re.min() + i * (self.lats_re.max() - self.lats_re.min()) / 5. for i in range(6)])
    #     plt.axis("off")
    #
    #     buf = io.BytesIO()
    #     self.BasemapFigure.savefig(buf, dpi=300, format='png', pad_inches=0, bbox_inches='tight')
    #     plt.close()
    #     buf.seek(0)
    #     self.BasemapLayerImage = np.copy(np.asarray(bytearray(buf.read()), dtype=np.uint8))


    # def PlotDataLayer(self):
    #     # coords_condition = ((self.lats <= self.urcrnrlat) & (self.lats >= self.llcrnrlat) & (self.lons <= self.urcrnrlon) & (self.lons >= self.llcrnrlon))
    #
    #     for dataname,cmap in zip(self.channelNames, self.channelColormaps):
    #         DataFigure = plt.figure(figsize=(8, 8), dpi=300)
    #         data = self.__dict__['data_%s' % dataname]
    #         vmin = data[data.mask==False].min()
    #         vmax = data[data.mask==False].max()
    #         # self.bm.pcolormesh(self.lons.data, self.lats.data, data,
    #         #                    latlon=True, alpha=1.0,
    #         #                    vmin = vmin, vmax = vmax, cmap=cmap)
    #         self.bm.pcolor(self.lons.data, self.lats.data, data,
    #                            latlon=True, alpha=1.0,
    #                            vmin=vmin, vmax=vmax, cmap=cmap)
    #         plt.axis("off")
    #         buf = io.BytesIO()
    #         DataFigure.savefig(buf, dpi=300, format='png', pad_inches=0, bbox_inches='tight')
    #         plt.close()
    #         buf.seek(0)
    #         self.__dict__['DataLayerImage_%s'%dataname] = np.copy(np.asarray(bytearray(buf.read()), dtype=np.uint8))


    def FuseBasemapWithData(self, alpha = 0.3, beta = 0.7):
        BasemapImageCV = cv2.imdecode(self.BasemapLayerImage, cv2.IMREAD_COLOR)
        DataLayerImageCV = cv2.imdecode(self.__dict__['DataLayerImage_%s' % self.dataToPlot], cv2.IMREAD_COLOR)
        self.CVimageCombined = cv2.addWeighted(BasemapImageCV, alpha, DataLayerImageCV, beta, 0.0)



    def SetNewLatLonLimits(self, llcrnrlon, llcrnrlat, urcrnrlon, urcrnrlat, resolution='c'):
        url1 = 'http://%s:1999/exec?command=SetNewLatLonLimits&llcrnrlon=%.5f&llcrnrlat=%.5f&urcrnrlon=%.5f&urcrnrlat=%.5f&resolution=%s&webapi_client_id=%s' % (self.remotehost, llcrnrlon, llcrnrlat, urcrnrlon, urcrnrlat, resolution, self.webapi_client_id)
        url2 = 'http://%s:1999/images?webapi_client_id=%s' % (self.remotehost, self.webapi_client_id)
        try:
            req1 = requests.get(url1, stream=True)
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



    def SwitchSourceData(self, filename):
        self.dataSourceFile = filename
        self.ReadSourceData()

        url1 = 'http://%s:1999/exec?command=SwitchSourceData&src_fname=%s&webapi_client_id=%s' % (self.remotehost, os.path.basename(self.dataSourceFile), self.webapi_client_id)
        url2 = 'http://%s:1999/images?webapi_client_id=%s' % (self.remotehost, self.webapi_client_id)
        try:
            req1 = requests.get(url1, stream=True)
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



