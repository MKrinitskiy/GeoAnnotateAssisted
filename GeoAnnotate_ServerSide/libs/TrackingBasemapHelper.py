import matplotlib
matplotlib.use('ps')
from .scaling import *


from matplotlib import pyplot as plt
from mpl_toolkits.basemap import Basemap
import numpy as np
from netCDF4 import Dataset
import io
import cv2
import pandas as pd
from libs.ga_defs import *
import pickle
import uuid
import threading
from .colormaps import *
from libs.SourceDataManagers import *
from libs.SourceDataRenderers import *
from libs.SourceDataRenderers import *
from hashlib import sha512
import json
from tempfile import NamedTemporaryFile
from libs.u_interpolate import interpolation_weights, interpolate_data
from hashlib import md5
from matplotlib import cm



basemaps_pickled_list_csvfile = './cache/basemaps_pickled_list.csv'

class TrackingBasemapHelperClass(object):
    def __init__(self, app = None):
        self.zoom = 1.0
        self.app = app

        self.BasemapLayerImage = None
        self.CVimageCombined = None
        self.dpi = 300
        self.interpolation_constants_cache = {}
        self.interpolation_constants = None

        self.DataLayerImage = {}
        self.DataInterpolated = {}


        if ((self.app.args.data_type == 'METEOSAT-MCS') or (self.app.args.data_type == "METEOSAT-QLL")):
            self.currentChannel = 'ch9'
            self.channelNames = ['ch9', 'ch5', 'ch5_ch9']
            self.channelColormaps = [create_ch9_cmap(),
                                     create_ch5_cmap(),
                                     create_btd_cmap()]
            self.channelVmin = [norm_constants.ch9_vmin, norm_constants.ch5_vmin, norm_constants.btd_vmin]
            self.channelVmax = [norm_constants.ch9_vmax, norm_constants.ch5_vmax, norm_constants.btd_vmax]

            self.sourceDataManager = METEOSAT_MCS_DataManager(self, baseDataDirectory = self.app.args.source_data_dir)
            self.sourceDataPlotter = METEOSAT_MCS_Renderer(self)
        elif self.app.args.data_type == 'NAAD-PL':
            self.currentChannel = 'wvp'
            # self.channelNames = ['wvp', 'wsp', 'msl']
            self.channelNames = ['wvp', 'wsp']
            self.channelColormaps = [cm.get_cmap('Blues'), cm.get_cmap('Reds'), cm.get_cmap('spring')]
            self.channelVmin = [norm_constants.wvp_vmin, norm_constants.wsp_vmin, norm_constants.msl_vmin]
            self.channelVmax = [norm_constants.wvp_vmax, norm_constants.wsp_vmax, norm_constants.msl_vmax]

            self.sourceDataManager = NAAD_PL_DataManager(self, baseDataDirectory = self.app.args.source_data_dir)
            self.sourceDataPlotter = NAAD_PL_Renderer(self)
        elif self.app.args.data_type == 'AMRC-MC':
            self.currentChannel = 'IR'
            # self.channelNames = ['IR', 'WV', 'SLP']
            self.channelNames = ['IR', 'WV']
            self.channelColormaps = [cm.get_cmap('Greys'), cm.get_cmap('Blues')]
            self.channelVmin = [norm_constants.IR_vmin, norm_constants.WV_vmin]
            self.channelVmax = [norm_constants.IR_vmax, norm_constants.WV_vmax]

            self.sourceDataManager = AMRC_MC_DataManager(self, baseDataDirectory=self.app.args.source_data_dir)
            self.sourceDataPlotter = AMRC_MC_Renderer(self)
        elif self.app.args.data_type == 'NAAD-CS':
            self.currentChannel = 'lambda2'
            # self.channelNames = ['wvp', 'wsp', 'msl']
            self.channelNames = ['lambda2']
            self.channelColormaps = [cm.get_cmap('spring')]
            self.channelVmin = [norm_constants.lambda2_vmin]
            self.channelVmax = [norm_constants.lambda2_vmax]

            self.sourceDataManager = NAAD_CS_DataManager(self, source_data_file=self.app.args.source_data_file)
            self.sourceDataPlotter = NAAD_CS_Renderer(self)


    def ReadSourceData(self):
        self.sourceDataManager.ReadSourceData(self.dataSourceFile)


    def listAvailablePickledBasemapObjects(self):
        EnsureDirectoryExists('./logs/')
        EnsureDirectoryExists(os.path.dirname(basemaps_pickled_list_csvfile))
        if os.path.exists(basemaps_pickled_list_csvfile) and os.path.isfile(basemaps_pickled_list_csvfile):
            self.df_pickled_basemaps_list = pd.read_csv(basemaps_pickled_list_csvfile, sep=';')
            self.df_pickled_basemaps_list['FileNotPresent'] = [(not DoesPathExistAndIsFile(s)) for s in self.df_pickled_basemaps_list.bm_fname]
            self.df_pickled_basemaps_list = self.df_pickled_basemaps_list.drop(self.df_pickled_basemaps_list[self.df_pickled_basemaps_list.FileNotPresent].index)
        else:
            columns = [('bm_args_sha512', str),
                       ('bm_fname', str)]
            self.df_pickled_basemaps_list = pd.DataFrame({k: pd.Series(dtype=t) for k, t in columns})



    def loadPickledBasemapObj(self, basemap_args_sha512: str):
        self.listAvailablePickledBasemapObjects()

        df_filtered = self.df_pickled_basemaps_list[self.df_pickled_basemaps_list['bm_args_sha512'] == basemap_args_sha512]
        if df_filtered.shape[0] > 0:
            try:
                bm = pickle.load(open(df_filtered.bm_fname.iloc[0], 'rb'))
                return bm
            except Exception as ex:
                ReportException('./logs/errors.log')
                print('An exception was thrown. Take a look into the ./logs/errors.log file')
                return None
        else:
            return None



    def savePickledBasemapObj(self, bm_args_sha512: str):
        fname = './cache/' + str(uuid.uuid4()) + '.pickle'
        pickle.dump(self.bm, open(fname, 'wb'), -1)
        self.df_pickled_basemaps_list = self.df_pickled_basemaps_list.append({'bm_args_sha512': sha512(bm_args_sha512.encode()).hexdigest(),
                                                                              'bm_fname': fname},
                                                                             ignore_index=True)
        self.df_pickled_basemaps_list.to_csv(basemaps_pickled_list_csvfile, sep=';', index=False)


    def SwitchInterpolationConstants(self, new_proj_sources_md5:str):
        if new_proj_sources_md5 in self.interpolation_constants_cache:
            self.interpolation_constants = self.interpolation_constants_cache[new_proj_sources_md5]
        else:
            curr_interpolation_constants = self.loadInterpolationConstants(new_proj_sources_md5)
            if curr_interpolation_constants is not None:
                self.interpolation_constants_cache[new_proj_sources_md5] = curr_interpolation_constants
                self.interpolation_constants = curr_interpolation_constants
            else:
                interpolation_inds, interpolation_wghts, interpolation_shape = interpolation_weights(np.array(self.sourceDataManager.lons.data),
                                                                                                     np.array(self.sourceDataManager.lats.data),
                                                                                                     self.projection_grid['lons_proj'],
                                                                                                     self.projection_grid['lats_proj'])
                curr_interpolation_constants = {'interpolation_inds': interpolation_inds,
                                                'interpolation_wghts': interpolation_wghts,
                                                'interpolation_shape': interpolation_shape,
                                                'zoom_applied': False,
                                                'interp_sources_md5': new_proj_sources_md5}
                self.interpolation_constants_cache[new_proj_sources_md5] = curr_interpolation_constants
                self.interpolation_constants = curr_interpolation_constants
                self.saveCurrentInterpolationConstants()


    def loadInterpolationConstants(self, interp_sources_md5: str):
        try:
            EnsureDirectoryExists('./cache/interpolation/')
        except:
            ReportException('./logs/error.log')
            return None

        try:
            with open('./cache/interpolation/%s.pkl' % interp_sources_md5, 'rb') as f:
                interpolation_constants = pickle.load(f)
                return interpolation_constants
        except:
            ReportException('./logs/error.log')
            return None


    def saveCurrentInterpolationConstants(self):
        try:
            EnsureDirectoryExists('./cache/interpolation/')
        except:
            ReportException('./logs/error.log')
            return

        try:
            with open('./cache/interpolation/%s.pkl' % self.interpolation_constants['interp_sources_md5'], 'wb') as f:
                pickle.dump(self.interpolation_constants, f)
        except:
            ReportException('./logs/error.log')


    def createBasemapObj(self, basemap_args_json: str = None):
        try:
            self.bm = self.loadPickledBasemapObj(sha512(basemap_args_json.encode()).hexdigest())
        except:
            ReportException('./logs/error.log')
            self.bm = None

        if self.bm == None:
            self.bm = Basemap(**(json.loads(basemap_args_json)))
            self.savePickledBasemapObj(basemap_args_json)

        #region plot one basemap figure just to get image shape
        fig = plt.figure(figsize=(4, 4), dpi=300)
        ax = plt.Axes(fig, [0., 0., 1., 1.])
        ax.set_axis_off()
        fig.add_axes(ax)
        _ = self.bm.drawcoastlines()
        _ = self.bm.fillcontinents()
        _ = self.bm.plot(55, 55, 'bo', latlon=True)

        with io.BytesIO() as buf:
            fig.savefig(buf, dpi=self.dpi, format='png', pad_inches=0, bbox_inches='tight')
            buf.seek(0)
            basemapImg = cv2.imdecode(np.copy(np.asarray(bytearray(buf.read()), dtype=np.uint8)), cv2.IMREAD_COLOR)
            basemapImg = cv2.cvtColor(basemapImg, cv2.COLOR_BGR2RGB)
            h, w, c = basemapImg.shape
        plt.close(fig)
        #endregion

        lons_proj, lats_proj, x_proj, y_proj = self.bm.makegrid(*(basemapImg.shape[:-1][::-1]), returnxy=True)

        self.projection_grid = {'lons_proj': lons_proj,
                                'lats_proj': lats_proj,
                                'x_proj': x_proj,
                                'y_proj': y_proj}


    def PlotBasemapBackground(self):
        self.sourceDataPlotter.PlotBasemapBackground()


    def PlotDataLayer(self):
        self.sourceDataPlotter.PlotDataLayer()


    def FuseBasemapWithData(self, alpha = 0.4, beta = 0.6):
        self.CVimageCombined = cv2.addWeighted(self.BasemapLayerImage, alpha, self.DataLayerImage[self.currentChannel], beta, 0.0)


    def ChangeProjection(self, new_proj_args_json):
        self.createBasemapObj(new_proj_args_json)


    def SwitchSourceData(self, curr_data_info):
        self.dataSourceFile = curr_data_info
        self.CVimageCombined = None
