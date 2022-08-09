import matplotlib
matplotlib.use('ps')
from libs.scaling import *

from matplotlib import pyplot as plt
from mpl_toolkits.basemap import Basemap
import numpy as np
from netCDF4 import Dataset
import io
import cv2
import pandas as pd
from libs.ga_defs import *
import pickle
import uuid
import threading
from libs.colormaps import *
from libs.SourceDataManagers import *
from hashlib import sha512
import json
from tempfile import NamedTemporaryFile
from libs.u_interpolate import interpolation_weights, interpolate_data
from hashlib import md5
from matplotlib import cm


class BaseRenderer:
    def __init__(self, parent):
        self.parent = parent


    def PlotBasemapBackground(self):
        raise NotImplementedError()

    def PlotDataLayer(self):
        raise NotImplementedError()
