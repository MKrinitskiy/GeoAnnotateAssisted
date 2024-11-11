import uuid
import numpy as np
import datetime

class srvQuasiLinearLabel(object):
    def __init__(self, sourcedata_fname=''):
        self.points = []
        self.uid = str(uuid.uuid4())
        self.dt = datetime.datetime.now(datetime.UTC)
        self.sourcedata_fname = sourcedata_fname
        self.probability = 0.0
    
    
    def calculate_length(self):
        # Implement the logic to calculate the length of the quasi-linear label
        if not self.points:
            return 0
        return len(self.points)

    def to_dict(self):
        # Convert the label data to a dictionary format
        return {
            "points": self.points,
            "uid": self.uid,
            "dt": self.dt,
            "sourcedata_fname": self.sourcedata_fname,
            "probability": self.probability
        }

    @staticmethod
    def from_dict(data):
        # Create an srvQuasiLinearLabel instance from a dictionary
        label = srvQuasiLinearLabel(data.get("sourcedata_fname", ''))
        label.points = data.get("points", [])
        label.uid = data.get("uid", str(uuid.uuid4()))
        label.dt = data.get("dt",datetime.datetime.now(datetime.UTC))
        label.probability = data.get("probability", 0.0)
        return label



class srvQuasiLinearLabelPoint(object):
    def __init__(self, lon, lat):
        self.clon = lon
        self.clat = lat
        self.veclon = lon + np.random.randn() * 1e-2
        self.veclat = lat + np.random.randn() * 1e-2

    def to_dict(self):
        return {
            "clon": self.clon,
            "clat": self.clat,
            "veclon": self.veclon,
            "veclat": self.veclat,
        }
    
    @staticmethod
    def from_dict(data):
        point = srvQuasiLinearLabelPoint(data.get("clon", 0.0), data.get("clat", 0.0))
        point.clon = data.get("clon", 0.0)
        point.clat = data.get("clat", 0.0)
        point.veclon = data.get("veclon", 0.0)
        point.veclat = data.get("veclat", 0.0)
        return point
