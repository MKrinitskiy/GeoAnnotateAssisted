from datetime import datetime
import os
from .DatabaseOps import DatabaseOps
import pandas as pd
import numpy as np
from common.srvMCSlabel import srvMCSlabel
from .SQLite_queries import SQLite_Queries


class MCSlabel():
    def __init__(self, name, uid, dt, pts, sourcedata_fname):
        self.name = name
        self.uid = uid
        self.dt = dt
        self.pts = pts
        self.sourcedata_fname = sourcedata_fname

    @classmethod
    def from_db_row_dict(cls, row_dict):
        label = MCSlabel(None, None, None, None, None)
        label.name = row_dict['label_name']
        label.uid = row_dict['label_uid']
        label.dt = row_dict['label_dt']
        label.sourcedata_fname = row_dict['sourcedata_fname']

        lon0 = float(row_dict['lon0'])
        lat0 = float(row_dict['lat0'])
        lon1 = float(row_dict['lon1'])
        lat1 = float(row_dict['lat1'])
        lon2 = float(row_dict['lon2'])
        lat2 = float(row_dict['lat2'])
        pt0 = {'lat': lat0, 'lon': lon0}
        pt1 = {'lat': lat1, 'lon': lon1}
        pt2 = {'lat': lat2, 'lon': lon2}
        label.pts = {'pt0': pt0, 'pt1': pt1, 'pt2': pt2}
        return label

    @classmethod
    def loadLabelsFromDatabase(cls, db_fname, sourcedata_fname):
        labels = []
        sourcedata_basename = os.path.basename(sourcedata_fname)
        data_read = DatabaseOps.read_labels_by_sourcedata_basename(db_fname, sourcedata_basename, SQLite_Queries('MCS'))
        if data_read and len(data_read) > 0:
            data_read_df = pd.DataFrame(np.array(data_read), columns=['label_id', 'label_uid', 'label_dt', 'label_name', 'lon0', 'lat0', 'lon1', 'lat1', 'lon2', 'lat2', 'sourcedata_fname'])
            data_read_df['label_dt'] = pd.to_datetime(data_read_df['label_dt'])
            for idx,row in data_read_df.iterrows():
                labeldata_dict = row.to_dict()
                label = MCSlabel.from_db_row_dict(labeldata_dict)
                labels.append(label)

        return labels

    @classmethod
    def LabelFrom_srvLabel(cls, srvMCS: srvMCSlabel):

        center_pt = [0.5*(srvMCS.ltc_lon+srvMCS.rbc_lon), 0.5*(srvMCS.ltc_lat+srvMCS.rbc_lat)]
        lat_arc = np.abs(srvMCS.ltc_lat-srvMCS.rbc_lat)
        lat_len = 111*lat_arc
        lon_arc = np.abs(srvMCS.ltc_lon-srvMCS.rbc_lon)
        lon_len = 111*np.cos(np.deg2rad(center_pt[1]))*lon_arc
        if lat_len > lon_len:
            lon0 = center_pt[0]
            lat0 = center_pt[1] - 0.5*lat_arc
            lon1 = center_pt[0]
            lat1 = center_pt[1] + 0.5*lat_arc
            lon2 = center_pt[0] + 0.5*lon_arc
            lat2 = center_pt[1]
        else:
            lon0 = center_pt[0]-0.5*lon_arc
            lat0 = center_pt[1]
            lon1 = center_pt[0]+0.5*lon_arc
            lat1 = center_pt[1]
            lon2 = center_pt[0]
            lat2 = center_pt[1]+0.5*lat_arc

        vars_dict = {'label_id': '',
                     'label_uid': srvMCS.uid,
                     'label_dt': srvMCS.dt,
                     'label_name': srvMCS.class_name,
                     'lon0': lon0,
                     'lat0': lat0,
                     'lon1': lon1,
                     'lat1': lat1,
                     'lon2': lon2,
                     'lat2': lat2,
                     'sourcedata_fname': srvMCS.sourcedata_fname}

        mcs = MCSlabel.from_db_row_dict(vars_dict)

        return mcs