import uuid
import numpy as np
import datetime

class srvQuasiLinearLabel(object):
    def __init__(self, sourcedata_fname=''):
        self.label_id = ''
        self.points = []
        self.uid = str(uuid.uuid4())
        self.dt = datetime.datetime.utcnow()
        self.start_lon = 37.556730 + np.random.randn() * 1e-2
        self.start_lat = 55.671874 + np.random.randn() * 1e-2
        self.end_lon = 38.0 + np.random.randn() * 1e-2
        self.end_lat = 55.0 + np.random.randn() * 1e-2
        self.sourcedata_fname = sourcedata_fname
        self.probability = 0.0
    def calculate_length(self):
        # Implement the logic to calculate the length of the quasi-linear label
        pass

    def to_dict(self):
        # Convert the label data to a dictionary format
        return {
            "label_id": self.label_id,
            "points": self.points,
            "uid": self.uid,
            "dt": self.dt,
            "start_lon": self.start_lon,
            "start_lat": self.start_lat,
            "end_lon": self.end_lon,
            "end_lat": self.end_lat,
            "sourcedata_fname": self.sourcedata_fname,
            "probability": self.probability
        }

    @staticmethod
    def from_dict(data):
        # Create an srvQuasiLinearLabel instance from a dictionary
        label = srvQuasiLinearLabel(data.get("sourcedata_fname", ''))
        label.label_id = data.get("label_id", '')
        label.points = data.get("points", [])
        label.uid = data.get("uid", str(uuid.uuid4()))
        label.dt = data.get("dt", datetime.datetime.utcnow())
        label.start_lon = data.get("start_lon", 37.556730 + np.random.randn() * 1e-2)
        label.start_lat = data.get("start_lat", 55.671874 + np.random.randn() * 1e-2)
        label.end_lon = data.get("end_lon", 38.0 + np.random.randn() * 1e-2)
        label.end_lat = data.get("end_lat", 55.0 + np.random.randn() * 1e-2)
        label.probability = data.get("probability", 0.0)
        return label
