from datetime import datetime as dt
from flask import Flask, request, send_file, make_response, Response
import requests, re, os
import cv2
from io import BytesIO, StringIO
from PIL import Image
import numpy as np
from netCDF4 import Dataset
from libs.TrackingBasemapHelper import *

# host = '192.168.192.42' # TESLA
host = 'localhost' # TESLA via SSH

req_src_fname = '20160713090010.nc'
url1 = 'http://%s:1999/exec?command=createbmhelper&src_fname=%s' % (host, req_src_fname)
url2 = 'http://%s:1999/images' % host

channels_list = ['ch9', 'ch5', 'ch5_ch9']

req1 = requests.get(url1, stream = True)

print(req1.headers)
ctype = req1.headers['Content-Type']
m = re.match(r'.+charset=(.+)', ctype)
enc = 'utf-8'
if m is not None:
    enc = m.groups()[0]
    print('encoding detected: %s' % enc)
print(req1.status_code)


def streamlines_gen(stream, encoding = 'utf-8'):
    line = ''
    for b in stream.iter_content():
        c = b.decode(encoding)
        if c == '\n':
            yield line
            line = ''
        else:
            line = line + c

for line in streamlines_gen(req1):
    print(line)
    if line == 'READY':
        print('got READY response')
        print('requesting image')

        start_time = dt.now()
        req2 = requests.get(url2)
        print(req2.status_code)
        print(req2.headers)
        # with open(os.path.join(os.getcwd(), 'demo', r2.headers['fileName']), 'wb') as f:
        #     f.write(r2.content)

        rec_dict = None
        with BytesIO() as bytesf:
            bytesf.write(req2.content)
            bytesf.seek(0)
            # pilImage = Image.open(bytesf, 'r')
            # cv2Image = np.copy(np.array(pilImage))
            rec_dict = pickle.load(bytesf)

        cv2Image = rec_dict['cv_img']
        ch5Image = rec_dict['DataLayerImage_%s' % 'ch5']
        ch9Image = rec_dict['DataLayerImage_%s' % 'ch9']
        ch5ch9_Image = rec_dict['DataLayerImage_%s' % 'ch5_ch9']
        BasemapLayerImage = rec_dict['BasemapLayerImage']
        end_time = dt.now()

        print('data received in %f s' % (end_time-start_time).total_seconds())

        # cv2Image = cv2.cvtColor(cv2Image, cv2.COLOR_RGB2BGR)
        cv2.imshow('Received image', cv2Image)
        cv2.waitKey()
