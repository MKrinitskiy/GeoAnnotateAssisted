import datetime

import numpy as np
from netCDF4 import Dataset
import io
import pandas as pd
from libs.ga_defs import *
from Support_defs import find_files
import pickle
from uuid import uuid4
import threading
from typing import OrderedDict
import re


def dt(nc_basename):
    expr = r'.+(\d{4})(\d{2})(\d{2})(\d{2})(\d{2})(\d{2})\.nc'
    m = re.match(expr, nc_basename)
    yr,mnth,day,hr,mn,sc = m.groups()
    yr,mnth,day,hr,mn,sc = [int(s) for s in [yr,mnth,day,hr,mn,sc]]
    dt = datetime.datetime(yr,mnth,day,hr,mn,sc)
    return dt

def MSG_label(nc_basename):
    pattern = r'.+(MSG\d).+'
    match = re.match(pattern, nc_basename)
    return match[1]

class SourceDataManager_METEOSAT:
    def __init__(self, baseDataDirectory = './'):
        self.baseDataDirectory = baseDataDirectory
        # self.dataSnapshots = {}
        self.uids2DataDesc = {}
        self.uids2datetime = {}


    def ListAvailableData(self, dt_start: datetime.datetime, dt_end: datetime.datetime):
        assert type(dt_start) is datetime.datetime
        assert type(dt_end) is datetime.datetime

        found_fnames = [f for f in find_files(self.baseDataDirectory, '*.nc')]

        fnames_df = pd.DataFrame(found_fnames, columns=['full_fname'])
        fnames_df['dt'] = fnames_df['full_fname'].apply(dt)
        fnames_df['dt_str'] = fnames_df['dt'].apply(lambda x: datetime.datetime.strftime(x, '%Y-%m-%d-%H-%M-%S'))
        fnames_df['MSG_label'] = fnames_df['full_fname'].apply(MSG_label)
        fnames_df_filtered = fnames_df[((fnames_df['dt'] >= dt_start) & (fnames_df['dt'] <= dt_end))]
        fnames_df_filtered = fnames_df_filtered.sort_values('dt')
        fnames_df_filtered['uuid'] = fnames_df_filtered['full_fname'].apply(lambda x: str(uuid4()))
        self.uids2DataDesc = dict([(s['uuid'],dict(s)) for idx,s in fnames_df_filtered.iterrows()])
        self.uids2datetime = dict([(s['uuid'],s['dt']) for idx,s in fnames_df_filtered.iterrows()])

        return fnames_df_filtered.shape[0]
