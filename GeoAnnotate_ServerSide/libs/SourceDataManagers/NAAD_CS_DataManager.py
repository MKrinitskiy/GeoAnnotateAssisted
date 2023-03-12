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
from numbers import Number
from decimal import Decimal
from fractions import Fraction





class NAAD_CS_DataManager(BaseDataManager):
    def __init__(self, parent, source_data_file='./src_data/source_data_file.nc'):
        super().__init__(parent, source_data_file = source_data_file)

    @classmethod
    def dt(cls, xtime):
        assert isinstance(xtime, Number), 'xtime values supposed to be the number of minutes since 1979-01-01 00:00:00'
        dt_start = datetime.datetime(1979, 1, 1, 0, 0, 0)
        dt = dt_start + datetime.timedelta(minutes=int(xtime))
        return dt

    def ListAvailableData(self, dt_start: datetime.datetime, dt_end: datetime.datetime):
        assert type(dt_start) is datetime.datetime
        assert type(dt_end) is datetime.datetime

        with Dataset(self.source_data_file, 'r') as ds:
            datetimes_minutes = ds.variables['XTIME'][:]

        xtime_indices_df = pd.DataFrame(np.concatenate([datetimes_minutes[:,np.newaxis],
                                                        np.arange(len(datetimes_minutes))[:,np.newaxis]], axis=1),
                                        columns=['xtime_minutes', 'xtime_indices'])
        xtime_indices_df['dt'] = xtime_indices_df['xtime_minutes'].apply(self.dt)
        xtime_indices_df['dt_str'] = xtime_indices_df['dt'].apply(lambda x: datetime.datetime.strftime(x, '%Y-%m-%d-%H-%M-%S'))
        xtime_indices_df_filtered = xtime_indices_df[((xtime_indices_df['dt'] >= dt_start) & (xtime_indices_df['dt'] <= dt_end))]
        xtime_indices_df_filtered = xtime_indices_df_filtered.sort_values('dt')
        xtime_indices_df_filtered['uuid'] = xtime_indices_df_filtered['dt_str'].apply(lambda x: str(uuid4()))
        self.uids2DataDesc = dict([(s['uuid'],dict(s)) for idx,s in xtime_indices_df_filtered.iterrows()])
        self.uids2datetime = dict([(s['uuid'],s['dt']) for idx,s in xtime_indices_df_filtered.iterrows()])

        return xtime_indices_df_filtered.shape[0]


    def ReadSourceData(self, dataItemIdentifier):
        with Dataset(self.source_data_file, 'r') as ds1:
            self.lats = ds1.variables['XLAT'][:]
            self.lons = ds1.variables['XLONG'][:]
            xtime = ds1.variables['XTIME'][:]
            curr_datetime_minutes = xtime[dataItemIdentifier]
            curr_dt = self.dt(curr_datetime_minutes)

            # if self.parent.interpolation_constants is None:
                #try to load pre-calculated interp. constants
            lons_md5 = md5(self.lons.data).hexdigest()
            lats_md5 = md5(self.lats.data).hexdigest()
            lons_proj_md5 = md5(self.parent.projection_grid['lons_proj']).hexdigest()
            lats_proj_md5 = md5(self.parent.projection_grid['lats_proj']).hexdigest()
            new_interp_sources_md5 = md5((lons_md5+lats_md5+lons_proj_md5+lats_proj_md5).encode()).hexdigest()
            self.parent.SwitchInterpolationConstants(new_interp_sources_md5)

            for dataname in self.parent.channelNames:
                if dataname == 'lambda2':
                    self.data[dataname] = np.array(ds1.variables['lambda2'][dataItemIdentifier, 0, :, :])
