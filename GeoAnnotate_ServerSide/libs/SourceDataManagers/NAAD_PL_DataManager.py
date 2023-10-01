from libs.SourceDataManagers.BaseDataManager import BaseDataManager
import datetime
import re
from Support_defs import find_files
from netCDF4 import Dataset
import numpy as np
import pandas as pd
from hashlib import md5
from uuid import uuid4
import os





class NAAD_PL_DataManager(BaseDataManager):
    def __init__(self, parent, baseDataDirectory='./'):
        super().__init__(parent, baseDataDirectory)

    @classmethod
    def dt(cls, nc_basename):
        assert len(nc_basename) > 3
        expr = r'.+(\d{4})m(\d{2})d(\d{2})h(\d{2})\.nc'
        m = re.match(expr, nc_basename)
        yr, mnth, day, hr = m.groups()
        mn, sc = 0, 0
        yr, mnth, day, hr, mn, sc = [int(s) for s in [yr, mnth, day, hr, mn, sc]]
        dt = datetime.datetime(yr, mnth, day, hr, mn, sc)
        return dt

    def ListAvailableData(self, dt_start: datetime.datetime, dt_end: datetime.datetime):
        assert type(dt_start) is datetime.datetime
        assert type(dt_end) is datetime.datetime

        found_fnames = [f for f in find_files(self.baseDataDirectory, '*.nc')]

        fnames_df = pd.DataFrame(found_fnames, columns=['full_fname'])
        fnames_df['dt'] = fnames_df['full_fname'].apply(self.dt)
        fnames_df['dt_str'] = fnames_df['dt'].apply(lambda x: datetime.datetime.strftime(x, '%Y-%m-%d-%H-%M-%S'))
        fnames_df_filtered = fnames_df[((fnames_df['dt'] >= dt_start) & (fnames_df['dt'] <= dt_end))]
        fnames_df_filtered = fnames_df_filtered.sort_values('dt')
        fnames_df_filtered['uuid'] = fnames_df_filtered['full_fname'].apply(lambda x: str(uuid4()))
        self.uids2DataDesc = dict([(s['uuid'],dict(s)) for idx,s in fnames_df_filtered.iterrows()])
        self.uids2datetime = dict([(s['uuid'],s['dt']) for idx,s in fnames_df_filtered.iterrows()])

        return fnames_df_filtered.shape[0]


    def ReadSourceData(self, dataItemIdentifier):
        dataSourceFile = dataItemIdentifier['full_fname']
        ds1 = Dataset(dataSourceFile, 'r')
        self.lats = ds1.variables['XLAT'][:]
        self.lons = ds1.variables['XLONG'][:]

        curr_dt = self.dt(os.path.basename(dataSourceFile))

        # if self.parent.interpolation_constants is None:
            #try to load pre-calculated interp. constants
        lons_md5 = md5(self.lons.data).hexdigest()
        lats_md5 = md5(self.lats.data).hexdigest()
        lons_proj_md5 = md5(self.parent.projection_grid['lons_proj']).hexdigest()
        lats_proj_md5 = md5(self.parent.projection_grid['lats_proj']).hexdigest()
        new_interp_sources_md5 = md5((lons_md5+lats_md5+lons_proj_md5+lats_proj_md5).encode()).hexdigest()
        self.parent.SwitchInterpolationConstants(new_interp_sources_md5)

        for dataname in self.parent.channelNames:
            if dataname == 'wvp':
                self.data[dataname] = np.array(ds1.variables['iwv'][:])[0]
            elif dataname == 'wsp':
                u10 = np.array(ds1.variables['u10'][:])[0]
                v10 = np.array(ds1.variables['v10'][:])[0]
                self.data[dataname] = np.sqrt(np.square(u10) + np.square(v10))
        self.data['msl'] = np.array(ds1.variables['msl'][:])[0]/100.0 # hPa

        ds1.close()
