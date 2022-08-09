from libs.SourceDataManagers.BaseDataManager import BaseDataManager
import datetime
import re
from Support_defs import find_files
from netCDF4 import Dataset
import numpy as np
from libs.sat_service_defs import infer_ncfile_info_from_fname
import pandas as pd
from hashlib import md5
from uuid import uuid4




class METEOSAT_MCS_DataManager(BaseDataManager):
    # region sat data constants
    C1 = 1.19104e-5  # mWm−2 sr−1 (cm−1)4
    C2 = 1.43877  # K (cm−1)−1

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
                'ch10': 0.9988,
                'ch11': 0.9982}

    B_values = {'ch4': 2.9002,
                'ch5': 2.0337,
                'ch6': 0.4340,
                'ch7': 0.1714,
                'ch8': 0.0527,
                'ch9': 0.6084,
                'ch10': 0.3882,
                'ch11': 0.5390}

    nu_central = {'ch4': 2547.771,
                  'ch5': 1595.621,
                  'ch6': 1360.377,
                  'ch7': 1148.130,
                  'ch8': 1034.715,
                  'ch9': 929.842,
                  'ch10': 838.659,
                  'ch11': 750.653}

    # endregion

    def __init__(self, parent, baseDataDirectory='./'):
        super().__init__(parent, baseDataDirectory)
        self.curr_sat_label = 'None'

    @classmethod
    def dt(cls, nc_basename):
        assert len(nc_basename) > 3
        expr = r'.+(\d{4})(\d{2})(\d{2})(\d{2})(\d{2})(\d{2})\.nc'
        m = re.match(expr, nc_basename)
        yr, mnth, day, hr, mn, sc = m.groups()
        yr, mnth, day, hr, mn, sc = [int(s) for s in [yr, mnth, day, hr, mn, sc]]
        dt = datetime.datetime(yr, mnth, day, hr, mn, sc)
        return dt


    @classmethod
    def MSG_label(cls, nc_basename):
        pattern = r'.+(MSG\d).+'
        match = re.match(pattern, nc_basename)
        return match[1]


    def ListAvailableData(self, dt_start: datetime.datetime, dt_end: datetime.datetime):
        assert type(dt_start) is datetime.datetime
        assert type(dt_end) is datetime.datetime

        found_fnames = [f for f in find_files(self.baseDataDirectory, '*.nc')]

        fnames_df = pd.DataFrame(found_fnames, columns=['full_fname'])
        fnames_df['dt'] = fnames_df['full_fname'].apply(self.dt)
        fnames_df['dt_str'] = fnames_df['dt'].apply(lambda x: datetime.datetime.strftime(x, '%Y-%m-%d-%H-%M-%S'))
        fnames_df['MSG_label'] = fnames_df['full_fname'].apply(self.MSG_label)
        fnames_df_filtered = fnames_df[((fnames_df['dt'] >= dt_start) & (fnames_df['dt'] <= dt_end))]
        fnames_df_filtered = fnames_df_filtered.sort_values('dt')
        fnames_df_filtered['uuid'] = fnames_df_filtered['full_fname'].apply(lambda x: str(uuid4()))
        self.uids2DataDesc = dict([(s['uuid'],dict(s)) for idx,s in fnames_df_filtered.iterrows()])
        self.uids2datetime = dict([(s['uuid'],s['dt']) for idx,s in fnames_df_filtered.iterrows()])

        return fnames_df_filtered.shape[0]


    def ReadSourceData(self, dataSourceFile):
        ds1 = Dataset(dataSourceFile, 'r')
        self.lats = ds1.variables['lat'][:]
        self.lons = ds1.variables['lon'][:]

        sat_label, _ = infer_ncfile_info_from_fname(dataSourceFile)

        if sat_label != self.curr_sat_label:
            #try to load pre-calculated interp. constants
            lons_md5 = md5(self.lons.data).hexdigest()
            lats_md5 = md5(self.lats.data).hexdigest()
            lons_proj_md5 = md5(self.parent.projection_grid['lons_proj']).hexdigest()
            lats_proj_md5 = md5(self.parent.projection_grid['lats_proj']).hexdigest()
            new_interp_sources_md5 = md5((lons_md5+lats_md5+lons_proj_md5+lats_proj_md5).encode()).hexdigest()
            self.parent.SwitchInterpolationConstants(new_interp_sources_md5)

        self.curr_sat_label = sat_label

        for dataname in self.parent.channelNames:
            if dataname == 'ch5_ch9':
                ch5_data = ds1.variables['ch5'][:]
                ch5_data.mask = self.lats.mask
                ch5_data = self.t_brightness_calculate(ch5_data, 'ch5')
                ch9_data = ds1.variables['ch9'][:]
                ch9_data.mask = self.lats.mask
                ch9_data = self.t_brightness_calculate(ch9_data, 'ch9')

                btd = ch5_data - ch9_data
                btd.mask = self.lats.mask
                btd.mask[btd > 50.] = True
                self.data[dataname] = btd
            else:
                curr_data = ds1.variables[dataname][:]
                curr_data.mask = self.lats.mask
                self.data[dataname] = self.t_brightness_calculate(curr_data, dataname)



        ds1.close()
        while self.lats.min() < 0.0:
            self.lats[self.lats < 0.0] = self.lats[self.lats < 0.0] + 360.
        while self.lons.min() < 0.0:
            self.lons[self.lons < 0.0] = self.lons[self.lons < 0.0] + 360.


    @classmethod
    def t_brightness_calculate(cls, data, channelname = 'ch9'):
        data.mask[data == data.min()] = True
        A = cls.A_values[channelname]
        B = cls.B_values[channelname]
        nu = cls.nu_central[channelname]
        c = cls.C2 * nu
        e = nu * nu * nu * cls.C1
        logval = np.log(1. + e / data)
        bt = (c / logval - B) / A
        return bt

