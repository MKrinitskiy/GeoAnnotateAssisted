import json
import uuid
import numpy as np

class MCSlabel(object):
    def __init__(self):
        self.class_name = type(self).__name__
        self.uid = str(uuid.uuid4())
        self.ltc_lon = 37.556730 + np.random.randn()*1e-2 # left top lon
        self.ltc_lat = 55.671874 + np.random.randn()*1e-2 # left top lon
        self.rbc_lon = 38.0 + np.random.randn()*1e-2 # right bottom lon
        self.rbc_lat = 55.0 + np.random.randn()*1e-2# right bottom lon


    # def toJSON(self):
    #     return json.dumps(self, default=lambda o: o.__dict__, sort_keys=True, indent=4)