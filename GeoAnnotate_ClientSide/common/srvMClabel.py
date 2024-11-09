import json
import uuid
import numpy as np
import datetime

class srvMClabel(object):
    def __init__(self, sourcedata_fname = ''):
        # self.class_name = type(self).__name__
        self.class_name = ''
        self.uid = str(uuid.uuid4())
        self.dt = datetime.datetime.utcnow()
        self.ltc_lon = 37.556730 + np.random.randn()*1e-2 # left top lon
        self.ltc_lat = 55.671874 + np.random.randn()*1e-2 # left top lat
        self.rbc_lon = 38.0 + np.random.randn()*1e-2 # right bottom lon
        self.rbc_lat = 55.0 + np.random.randn()*1e-2 # right bottom lat
        self.sourcedata_fname = sourcedata_fname
        self.probability = 0.0

    def to_dict(self):
        return {
            "class_name": self.class_name,
            "uid": self.uid,
            "dt": self.dt,
            "ltc_lon": self.ltc_lon,
            "ltc_lat": self.ltc_lat,
            "rbc_lon": self.rbc_lon,
            "rbc_lat": self.rbc_lat,
            "sourcedata_fname": self.sourcedata_fname,
            "probability": self.probability
        }

    @staticmethod
    def from_dict(data):
        label = srvMClabel(data.get("sourcedata_fname", ''))
        label.class_name = data.get("class_name", '')
        label.uid = data.get("uid", str(uuid.uuid4()))
        label.dt = data.get("dt", datetime.datetime.utcnow())
        label.ltc_lon = data.get("ltc_lon", 37.556730 + np.random.randn()*1e-2)
        label.ltc_lat = data.get("ltc_lat", 55.671874 + np.random.randn()*1e-2)
        label.rbc_lon = data.get("rbc_lon", 38.0 + np.random.randn()*1e-2)
        label.rbc_lat = data.get("rbc_lat", 55.0 + np.random.randn()*1e-2)
        label.probability = data.get("probability", 0.0)
        return label
