from datetime import datetime
import os
from .DatabaseOps import DatabaseOps
import pandas as pd
import numpy as np
from common.srvMClabel import srvMClabel
from .SQLite_queries import SQLite_Queries


class MClabel():
    def __init__(self, name, uid, dt, pts, sourcedata_identifier):
        self.name = name
        self.uid = uid
        self.dt = dt
        self.pts = pts
        self.sourcedata_identifier = sourcedata_identifier

    @classmethod
    def from_db_row_dict(cls, row_dict):
        label = MClabel(None, None, None, None, None)
        label.name = row_dict['label_name']
        label.uid = row_dict['label_uid']
        label.dt = row_dict['label_dt']
        label.sourcedata_fname = row_dict['sourcedata_fname']

        lon0 = float(row_dict['lon0'])
        lat0 = float(row_dict['lat0'])
        lon1 = float(row_dict['lon1'])
        lat1 = float(row_dict['lat1'])
        pt0 = {'lat': lat0, 'lon': lon0}
        pt1 = {'lat': lat1, 'lon': lon1}
        label.pts = {'pt0': pt0, 'pt1': pt1}
        return label

    @classmethod
    def loadLabelsFromDatabase(cls, db_fname, sourcedata_fname):
        labels = []
        sourcedata_basename = os.path.basename(sourcedata_fname)
        data_read = DatabaseOps.read_labels_by_sourcedata_basename(db_fname, sourcedata_basename, SQLite_Queries('MC'))
        if data_read and len(data_read) > 0:
            data_read_df = pd.DataFrame(np.array(data_read), columns=['label_id', 'label_uid', 'label_dt', 'label_name', 'lon0', 'lat0', 'lon1', 'lat1', 'sourcedata_fname'])
            data_read_df['label_dt'] = pd.to_datetime(data_read_df['label_dt'])
            for idx,row in data_read_df.iterrows():
                labeldata_dict = row.to_dict()
                label = MClabel.from_db_row_dict(labeldata_dict)
                labels.append(label)

        return labels

    @classmethod
    def MCLabelFrom_srvMClabel(cls, srvMC: srvMClabel):

        center_pt = [0.5*(srvMC.ltc_lon+srvMC.rbc_lon), 0.5*(srvMC.ltc_lat+srvMC.rbc_lat)]
        lat_arc = np.abs(srvMC.ltc_lat-srvMC.rbc_lat)
        lat_len = 111*lat_arc
        lon_arc = np.abs(srvMC.ltc_lon-srvMC.rbc_lon)
        lon_len = 111*np.cos(np.deg2rad(center_pt[1]))*lon_arc
        if lat_len > lon_len:
            lon0 = center_pt[0]
            lat0 = center_pt[1] - 0.5*lat_arc
            lon1 = center_pt[0]
            lat1 = center_pt[1] + 0.5*lat_arc
        else:
            lon0 = center_pt[0]-0.5*lon_arc
            lat0 = center_pt[1]
            lon1 = center_pt[0]+0.5*lon_arc
            lat1 = center_pt[1]

        vars_dict = {'label_id': '',
                     'label_uid': srvMC.uid,
                     'label_dt': srvMC.dt,
                     'label_name': srvMC.class_name,
                     'lon0': lon0,
                     'lat0': lat0,
                     'lon1': lon1,
                     'lat1': lat1,
                     'sourcedata_fname': srvMC.sourcedata_fname}

        mcs = MClabel.from_db_row_dict(vars_dict)

        return mcs