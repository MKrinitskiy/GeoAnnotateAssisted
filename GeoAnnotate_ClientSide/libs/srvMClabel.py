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
        self.ltc_lat = 55.671874 + np.random.randn()*1e-2 # left top lon
        self.rbc_lon = 38.0 + np.random.randn()*1e-2 # right bottom lon
        self.rbc_lat = 55.0 + np.random.randn()*1e-2# right bottom lon
        self.sourcedata_fname = sourcedata_fname
        self.probability = 0.0
