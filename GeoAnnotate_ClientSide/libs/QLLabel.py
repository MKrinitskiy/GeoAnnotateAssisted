from datetime import datetime
import json
import os
from .DatabaseOps import DatabaseOps
import pandas as pd
import numpy as np
from .SQLite_queries import SQLite_Queries


class QuasiLinearLabel:
    def __init__(self, name, uid, dt, pts, widthkeypoints, sourcedata_fname):
        """
        Initialize a QuasiLinearLabel.

        :param name: Name of the label
        :param uid: Unique identifier for the label
        :param dt: Date and time associated with the label
        :param pts: List of points defining the piecewise straight line
        :param widthkeypoints: List of circles, each circle is a dict with 'latc', 'lonc', 'lat_arc', 'lon_arc'
        :param sourcedata_fname: Identifier for the source data
        """
        self.name = name
        self.uid = uid
        self.dt = dt
        self.pts = pts  # List of points, each point is a dict with 'lat' and 'lon'
        self.widthkeypoints = widthkeypoints # List of circles, each circle is a dict with 'latc', 'lonc', 'lat_arc', 'lon_arc'
        self.sourcedata_fname = sourcedata_fname
    

    @classmethod
    def from_db_row_dict(cls, row_dict):
        """
        Create a QuasiLinearLabel from a database row dictionary.

        :param row_dict: Dictionary containing database row data
        :return: QuasiLinearLabel instance
        """
        label = QuasiLinearLabel(None, None, None, [], [], None)
        label.name = row_dict['label_name']
        label.uid = row_dict['label_uid']
        label.dt = row_dict['label_dt']
        label.sourcedata_fname = row_dict['sourcedata_fname']

        # Assuming points are stored as a list of tuples in the database
        points_json = row_dict['pts']  # This should be a list of tuples [(lat, lon), ...]
        points = json.loads(points_json.replace("'", '"'))
        # Convert dictionary of points to list of points
        points_list = []
        for pt_key in sorted(points.keys()):  # Sort to maintain order pt0, pt1, pt2
            points_list.append({'lat': points[pt_key]['lat'],
                                'lon': points[pt_key]['lon']})
        label.pts = points_list

        widthkeypoints_json = row_dict['widthkeypoints']  # This should be a list of tuples [(latc, lonc, lat_arc, lon_arc), ...]
        widthkeypoints = json.loads(widthkeypoints_json.replace("'", '"'))
        # Convert dictionary of circles to list of circles
        widthkeypoints_list = []
        for circle_key in sorted(widthkeypoints.keys()):  # Sort to maintain order pt0, pt1, pt2
            widthkeypoints_list.append({'latc': widthkeypoints[circle_key]['lat'],
                                        'lonc': widthkeypoints[circle_key]['lon']})
        label.widthkeypoints = widthkeypoints_list
        
        return label


    @classmethod
    def loadLabelsFromDatabase(cls, db_fname, sourcedata_fname):
        labels = []
        sourcedata_basename = os.path.basename(sourcedata_fname)
        data_read = DatabaseOps.read_labels_by_sourcedata_basename(db_fname, sourcedata_basename, SQLite_Queries('QLL'))
        if data_read and len(data_read) > 0:
            data_read_df = pd.DataFrame(np.array(data_read), columns=['label_id',
                                                                      'label_uid',
                                                                      'label_dt',
                                                                      'label_name',
                                                                      'sourcedata_fname',
                                                                      'pts',
                                                                      'widthkeypoints'])
            data_read_df['label_dt'] = pd.to_datetime(data_read_df['label_dt'])
            for idx,row in data_read_df.iterrows():
                labeldata_dict = row.to_dict()
                label = QuasiLinearLabel.from_db_row_dict(labeldata_dict)
                labels.append(label)

        return labels
