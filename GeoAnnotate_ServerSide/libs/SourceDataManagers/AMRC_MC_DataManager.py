from libs.SourceDataManagers.BaseDataManager import BaseDataManager
import datetime
from datetime import timedelta
import re
from Support_defs import find_files
from netCDF4 import Dataset
import numpy as np
import pandas as pd
from hashlib import md5
from uuid import uuid4
from libs.service_defs import *




class AMRC_MC_DataManager(BaseDataManager):
    def __init__(self, parent, baseDataDirectory='./'):
        super().__init__(parent, baseDataDirectory)
        self.current_channel = 'IR'

    @classmethod
    def dt(cls, nc_basename):
        assert len(nc_basename) > 3
        ir_regex = r'.+Antarctic\.Composite\..+\.Infrared\.(\d{4})\.(\d{2})\.(\d{2})\.(\d{2})Z\.nc'
        wv_regex = r'.+Antarctic\.Composite\..+\.WaterVapor\.(\d{4})\.(\d{2})\.(\d{2})\.(\d{2})Z\.nc'
        ir_match = re.match(ir_regex, nc_basename)
        wv_match = re.match(wv_regex, nc_basename)

        ir_regex2 = r'.+Antarctic\.Composite\..+\.Infrared\.(\d{4}\.\d{2}\.\d{2}\.\d{2})Z\.nc'
        wv_regex2 = r'.+Antarctic\.Composite\..+\.WaterVapor\.(\d{4}\.\d{2}\.\d{2}\.\d{2})Z\.nc'

        dt = None

        if ir_match is not None:
            ir_match2 = re.match(ir_regex2, nc_basename)
            dt_str = ir_match2.groups()[0]
            dt = datetime.datetime.strptime(dt_str, '%Y.%m.%d.%H')
        if wv_match is not None:
            wv_match2 = re.match(wv_regex2, nc_basename)
            dt_str = wv_match2.groups()[0]
            dt = datetime.datetime.strptime(dt_str, '%Y.%m.%d.%H')

        return dt


    def ListAvailableData(self, dt_start: datetime.datetime, dt_end: datetime.datetime):
        assert type(dt_start) is datetime.datetime
        assert type(dt_end) is datetime.datetime

        found_fnames_IR = [f for f in find_files(os.path.join(self.baseDataDirectory, 'IR'), 'Antarctic.Composite.*.nc')]
        found_fnames_WV = [f for f in find_files(os.path.join(self.baseDataDirectory, 'WV'), 'Antarctic.Composite.*.nc')]


        fnames_df_IR = pd.DataFrame(found_fnames_IR, columns=['full_fname_IR'])
        fnames_df_WV = pd.DataFrame(found_fnames_WV, columns=['full_fname_WV'])


        fnames_df_IR['dtIR'] = fnames_df_IR['full_fname_IR'].apply(self.dt)
        fnames_df_IR['dtIR_str'] = fnames_df_IR['dtIR'].apply(lambda x: datetime.datetime.strftime(x, '%Y-%m-%d-%H-%M-%S'))
        fnames_df_WV['dtWV'] = fnames_df_WV['full_fname_WV'].apply(self.dt)
        fnames_df_WV['dtWV_str'] = fnames_df_WV['dtWV'].apply(lambda x: datetime.datetime.strftime(x, '%Y-%m-%d-%H-%M-%S'))
        fnames_df_IR.sort_values('dtIR', inplace=True)
        fnames_df_WV.sort_values('dtWV', inplace=True)
        fnames_df = pd.merge_asof(fnames_df_IR, fnames_df_WV,
                                  left_on="dtIR",
                                  right_on='dtWV',
                                  direction="nearest",
                                  tolerance=timedelta(hours=3))
        fnames_df['dt'] = fnames_df['dtIR']
        fnames_df['dt_str'] = fnames_df['dtIR_str']
        fnames_df['full_fname'] = fnames_df['full_fname_IR']

        fnames_df_filtered = fnames_df[((fnames_df['dt'] >= dt_start) & (fnames_df['dt'] <= dt_end))]
        fnames_df_filtered = fnames_df_filtered.sort_values('dt')
        fnames_df_filtered['uuid'] = fnames_df_filtered['full_fname'].apply(lambda x: str(uuid4()))
        self.uids2DataDesc = dict([(s['uuid'],dict(s)) for idx,s in fnames_df_filtered.iterrows()])
        self.uids2datetime = dict([(s['uuid'],s['dt']) for idx,s in fnames_df_filtered.iterrows()])

        return fnames_df_filtered.shape[0]

    @property
    def lons(self):
        if self.current_channel == 'IR':
            return self.lonsIR
        elif self.current_channel == 'WV':
            return self.lonsWV

    @property
    def lats(self):
        if self.current_channel == 'IR':
            return self.latsIR
        elif self.current_channel == 'WV':
            return self.latsWV

    def ReadSourceData(self, dataItemIdentifier):
        dataSourceInfo = dataItemIdentifier
        ir_fname = dataSourceInfo['full_fname_IR']
        wv_fname = dataSourceInfo['full_fname_WV']

        for dataname in self.parent.channelNames:
            if dataname == 'IR':
                with Dataset(ir_fname, 'r') as dsIR:
                    self.latsIR = np.array(dsIR.variables['lat'][:])
                    self.lonsIR = np.array(dsIR.variables['lon'][:])
                    self.data[dataname] = np.array(dsIR.variables['data'][:])
                lons_md5 = md5(self.lonsIR.data).hexdigest()
                lats_md5 = md5(self.latsIR.data).hexdigest()
                lons_proj_md5 = md5(self.parent.projection_grid['lons_proj']).hexdigest()
                lats_proj_md5 = md5(self.parent.projection_grid['lats_proj']).hexdigest()
                new_interp_sources_md5 = md5((lons_md5 + lats_md5 + lons_proj_md5 + lats_proj_md5).encode()).hexdigest()
                self.current_channel = 'IR'
                self.parent.SwitchInterpolationConstants(new_interp_sources_md5)
            elif dataname == 'WV':
                with Dataset(wv_fname, 'r') as dsWV:
                    self.latsWV = np.array(dsWV.variables['lat'][:])
                    self.lonsWV = np.array(dsWV.variables['lon'][:])
                    self.data[dataname] = np.array(dsWV.variables['data'][:])
                lons_md5 = md5(self.lonsWV.data).hexdigest()
                lats_md5 = md5(self.latsWV.data).hexdigest()
                lons_proj_md5 = md5(self.parent.projection_grid['lons_proj']).hexdigest()
                lats_proj_md5 = md5(self.parent.projection_grid['lats_proj']).hexdigest()
                new_interp_sources_md5 = md5((lons_md5 + lats_md5 + lons_proj_md5 + lats_proj_md5).encode()).hexdigest()
                self.current_channel = 'WV'
                self.parent.SwitchInterpolationConstants(new_interp_sources_md5)
