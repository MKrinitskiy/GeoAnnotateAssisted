import datetime
import os, sys
python_path = sys.executable
if sys.platform == 'win32':
    os.environ['PROJ_LIB'] = os.path.join(os.path.split(python_path)[0], 'Library', 'share')
elif ((sys.platform == 'linux') | (sys.platform == 'darwin')):
    os.environ['PROJ_LIB'] = os.path.join(sys.executable.replace('bin/python', ''), 'share', 'proj')

from flask import Flask, request, send_file, make_response, Response, jsonify
import numpy as np
from FlaskExtended import *
from Support_defs import *
from libs.service_defs import *
from libs.TrackingBasemapHelper import *
import binascii, logging, time
from PIL import Image
from io import BytesIO
import json
import sys
import collections
from libs.parse_args import parse_args
import ast
from libs.ProgressOperations import *


args = sys.argv[1:]
args = parse_args(args)
if not args.no_cnn:
    from libs.CNNPredictor import CNNPredictor


if 'gpu' in args.__dict__.keys():
    os.environ['CUDA_VISIBLE_DEVICES'] = str(args.gpu)

app = FlaskExtended(__name__)
app.config['SECRET_KEY'] = binascii.hexlify(os.urandom(24))

logging.basicConfig(filename='./logs/app.log', level=logging.INFO, format='%(asctime)s %(message)s')
logging.info('Started AI-assisted GeoAnnotate server-side app')
logging.info('args: %s' % sys.argv[1:])


tmp_imag_dir = os.path.join(os.getcwd(), 'tmp')
src_data_dir = os.path.join(os.getcwd(), 'src_data')
channels_list = ['ch9', 'ch5', 'ch5_ch9']



@app.route('/')
def main():
    response = make_response('Nothing to do here')
    response.headers['ErrorDesc'] = 'CommandNotUnderstood'
    return response



# @app.route('/exec', methods=['POST', 'GET'])
@app.route('/exec', methods=['GET'])
def exec():
    command = request.args['command']

    if command == 'createbmhelper':
        try:
            webapi_client_id = request.args['webapi_client_id']
        except Exception as ex:
            print(ex)
            ReportException('./logs/error.log', ex)
            response = make_response('client webapi ID was not specified')
            response.headers['ErrorDesc'] = 'ClientIDnotSpecified'
            return response

        try:
            basemap_args_json = request.json
        except:
            ReportException('./logs/error.log', None)
            response = make_response('unable to process expected json containing basemap projection args')
            response.headers['ErrorDesc'] = 'BasemapArgsNotRecognized'
            return response

        return Response(MakeTrackingBasemapHelper_progress(app,
                                                           webapi_client_id=webapi_client_id,
                                                           basemap_args_json=basemap_args_json),
                        mimetype='text/stream')

    elif command == 'listData':
        try:
            webapi_client_id = request.args['webapi_client_id']
        except Exception as ex:
            print(ex)
            ReportException('./logs/error.log', ex)
            response = make_response('client webapi ID was not specified')
            response.headers['ErrorDesc'] = 'ClientIDnotSpecified'
            return response

        try:
            dt_start = request.args['dt_start']
            dt_start = datetime.datetime.strptime(dt_start, '%Y-%m-%d-%H-%M-%S')
        except Exception as ex:
            dt_start = datetime.datetime(1900, 1, 1, 0, 0, 0)

        try:
            dt_end = request.args['dt_end']
            dt_end = datetime.datetime.strptime(dt_end, '%Y-%m-%d-%H-%M-%S')
        except Exception as ex:
            dt_end = datetime.datetime(2101, 1, 1, 23, 59, 59)

        return Response(ListAvailableDataSnapshots_progress(app,
                                                            dt_start, dt_end,
                                                            webapi_client_id=webapi_client_id),
                        mimetype='text/stream')

    elif command == 'processDataSnapshot':
        try:
            arg_srcdata_uuid = request.args['src_data_uuid']
        except Exception as ex:
            print(ex)
            ReportException('./logs/error.log', ex)
            response = make_response('source data uuid was not specified')
            response.headers['ErrorDesc'] = 'DataNotFound'
            return response

        try:
            webapi_client_id = request.args['webapi_client_id']
        except Exception as ex:
            print(ex)
            ReportException('./logs/error.log', ex)
            response = make_response('client webapi ID was not specified')
            response.headers['ErrorDesc'] = 'ClientIDnotSpecified'
            return response

        try:
            calculateLatLonLimits = request.args['calculateLatLonLimits']
            calculateLatLonLimits = True if (calculateLatLonLimits.lower() == 'true') else False
        except:
            calculateLatLonLimits = True

        try:
            resolution = request.args['resolution']
        except:
            resolution = 'f'

        datetime_fname_stamp = os.path.splitext(os.path.basename(arg_src_fname))[0][-14:]
        sat_name = os.path.splitext(os.path.basename(arg_src_fname))[0][-33:-29]
        found_fnames = [f for f in find_files('./src_data/', '*%s*%s.nc' % (sat_name, datetime_fname_stamp))]
        if len(found_fnames) == 0:
            ReportError('./logs/app.err.log', webapi_client_id, 'FileNotFound', arg_src_fname)
            response = make_response('Unable to find file %s' % arg_src_fname)
            response.headers['ErrorDesc'] = 'FileNotFound'
            return response
        else:
            curr_fname = found_fnames[0]

        if not DoesPathExistAndIsFile(curr_fname):
            response = make_response('Unable to find file %s' % arg_src_fname)
            response.headers['ErrorDesc'] = 'FileNotFound'
            return response
        else:
            return Response(MakeTrackingBasemapHelper_progress(curr_fname,
                                                               calculateLatLonLimits,
                                                               resolution,
                                                               webapi_client_id=webapi_client_id),
                            mimetype='text/stream')



    elif command == 'SwitchSourceData':
        try:
            arg_src_uuid = request.args['uuid']
        except Exception as ex:
            print(ex)
            ReportException('./logs/error.log', ex)
            response = make_response('source data uuid was not specified')
            response.headers['ErrorDesc'] = 'UUIDnotRecognized'
            return response

        try:
            webapi_client_id = request.args['webapi_client_id']
        except Exception as ex:
            print(ex)
            ReportException('./logs/error.log', ex)
            response = make_response('client webapi ID was not specified')
            response.headers['ErrorDesc'] = 'ClientIDnotSpecified'
            return response

        sourceDataManager = app.bmhelpers[webapi_client_id].sourceDataManager
        data_desc_dict = sourceDataManager.uids2DataDesc[arg_src_uuid]
        curr_fname = data_desc_dict['full_fname']

        if not DoesPathExistAndIsFile(curr_fname):
            response = make_response('Unable to find file %s' % curr_fname)
            response.headers['ErrorDesc'] = 'FileNotFound'
            return response
        else:
            return Response(SwitchSourceData_progress(app,
                                                      curr_fname,
                                                      webapi_client_id=webapi_client_id),
                            mimetype='text/stream')


    elif command == 'PredictMCScurrentData':
        try:
            webapi_client_id = request.args['webapi_client_id']
        except Exception as ex:
            print(ex)
            ReportException('./logs/error.log', ex)
            response = make_response('client webapi ID was not specified')
            response.headers['ErrorDesc'] = 'ClientIDnotSpecified'
            return response

        if type(app.bmhelpers[webapi_client_id]) is not TrackingBasemapHelperClass:
            print('Data renderer is empty. You need to specify source data imagery first!')
            response = make_response('Data renderer is empty. You need to specify source data imagery first!')
            response.headers['ErrorDesc'] = 'DataNotLoaded'
            return response

        if args.no_cnn:
            response = make_response('CNN functionality is turned off for this service.')
            response.headers['ErrorDesc'] = 'CNNturnedOFF'
            return response
        else:
            return Response(PredictMCS_progress(app,
                                                args,
                                                app.bmhelpers[webapi_client_id].dataSourceFile,
                                                webapi_client_id=webapi_client_id),
                            mimetype='text/stream')



@app.route('/datalist', methods=['GET'])
def data_list():
    try:
        try:
            webapi_client_id = request.args['webapi_client_id']
        except Exception as ex:
            print(ex)
            ReportException('./logs/error.log', ex)
            response = make_response('client webapi ID was not specified')
            response.headers['ErrorDesc'] = 'ClientIDnotSpecified'
            return response

        sourceDataManager = app.bmhelpers[webapi_client_id].sourceDataManager

        if len(sourceDataManager.uids2DataDesc) == 0:
            response = make_response('There is no data in this date/time range')
            response.headers['ErrorDesc'] = 'DataListEmpty'
            return response
        else:
            response = jsonify(sourceDataManager.uids2DataDesc)
            return response
    except Exception as ex:
        print(ex)
        ReportException('./logs/error.log', ex)
        response = make_response('Unable to return source data snapshots list')
        response.headers['ErrorDesc'] = 'SourceDataSnaphotsListGenerating'
        return response



@app.route('/coordinates', methods=['GET'])
def coordinates():
    try:
        webapi_client_id = request.args['webapi_client_id']
    except Exception as ex:
        print(ex)
        ReportException('./logs/error.log', ex)
        response = make_response('client webapi ID was not specified')
        response.headers['ErrorDesc'] = 'ClientIDnotSpecified'
        return response

    try:
        xypt_json = request.json
        xypt = ast.literal_eval(xypt_json)
    except:
        ReportException('./logs/error.log', None)
        response = make_response('unable to process expected json containing xy point coordinates')
        response.headers['ErrorDesc'] = 'XYpointNotRecognized'
        return response

    ret_dict = {}
    try:
        ret = app.bmhelpers[webapi_client_id].getLatLonCoordinates(xypt)
    except:
        ReportException('./logs/error.log', None)
        response = make_response('unable to determine lat-lon coordinates of the point position')
        response.headers['ErrorDesc'] = 'LatLonCoordinatesCouldNotDetemined'
        return response

    response = jsonify(ret)
    return response



@app.route('/images', methods=['GET'])
def image():
    try:
        try:
            webapi_client_id = request.args['webapi_client_id']
        except Exception as ex:
            print(ex)
            ReportException('./logs/error.log', ex)
            response = make_response('client webapi ID was not specified')
            response.headers['ErrorDesc'] = 'ClientIDnotSpecified'
            return response

        dict1 = {'CVimageCombined': np.copy(app.bmhelpers[webapi_client_id].CVimageCombined)}
        for ch in channels_list:
            dict1['DataLayerImage_%s' % ch] = np.copy(app.bmhelpers[webapi_client_id].__dict__['DataLayerImage_%s' % ch])
        dict1['lats_proj'] = np.copy(app.bmhelpers[webapi_client_id].projection_grid['lats_proj'])
        dict1['lons_proj'] = np.copy(app.bmhelpers[webapi_client_id].projection_grid['lons_proj'])

        dict1['BasemapLayerImage'] = np.copy(app.bmhelpers[webapi_client_id].__dict__['BasemapLayerImage'])
        # dict1['llcrnrlon'] = app.bmhelpers[webapi_client_id].llcrnrlon
        # dict1['llcrnrlat'] = app.bmhelpers[webapi_client_id].llcrnrlat
        # dict1['urcrnrlon'] = app.bmhelpers[webapi_client_id].urcrnrlon
        # dict1['urcrnrlat'] = app.bmhelpers[webapi_client_id].urcrnrlat
        # dict1['cLat'] = app.bmhelpers[webapi_client_id].cLat
        # dict1['cLon'] = app.bmhelpers[webapi_client_id].cLon
        # dict1['LathalfRange'] = app.bmhelpers[webapi_client_id].LathalfRange
        # dict1['LonHalfRange'] = app.bmhelpers[webapi_client_id].LonHalfRange
        dict1['dataToPlot'] = app.bmhelpers[webapi_client_id].dataToPlot

        tmp_fname = './cache/webapi_cache/basemap-plot-%s.pickle' % binascii.hexlify(os.urandom(5)).decode('ascii')
        EnsureDirectoryExists(os.path.dirname(tmp_fname))
        with open(tmp_fname, 'wb') as f:
            pickle.dump(dict1, f, pickle.HIGHEST_PROTOCOL)
        response = make_response(send_file(tmp_fname, mimetype='application/octet-stream'))
        response.headers['fileName'] = os.path.basename(tmp_fname)
        return response
    except Exception as ex:
        print(ex)
        ReportException('./logs/error.log', ex)
        response = make_response('Unable to generate basemap image')
        response.headers['ErrorDesc'] = 'BasemapImageGenerating'
        return response



@app.route('/predictions', methods=['GET'])
def predictions():
    try:
        try:
            webapi_client_id = request.args['webapi_client_id']
        except Exception as ex:
            print(ex)
            ReportException('./logs/error.log', ex)
            response = make_response('client webapi ID was not specified')
            response.headers['ErrorDesc'] = 'ClientIDnotSpecified'
            return response

        preds = app.cnn.GetPredictions(webapi_client_id, clear=True)

        tmp_fname = './cache/webapi_cache/labels-predicted-%s.pickle' % binascii.hexlify(os.urandom(5)).decode('ascii')
        with open(tmp_fname, 'wb') as f:
            pickle.dump(preds, f, pickle.HIGHEST_PROTOCOL)
        response = make_response(send_file(tmp_fname, mimetype='application/octet-stream'))
        response.headers['fileName'] = os.path.basename(tmp_fname)
        return response
    except Exception as ex:
        print(ex)
        ReportException('./logs/error.log', ex)
        response = make_response('Unable to predict MCS labels')
        response.headers['ErrorDesc'] = 'MCSLabelsPredicting'
        return response



@app.route('/imdone', methods=['GET'])
def imdone():
    try:
        try:
            webapi_client_id = request.args['webapi_client_id']
        except Exception as ex:
            print(ex)
            ReportException('./logs/error.log', ex)
            response = make_response('client webapi ID was not specified')
            response.headers['ErrorDesc'] = 'ClientIDnotSpecified'
            return response

        del app.bmhelpers[webapi_client_id]

        response = make_response('OK')
        response.headers['ErrorDesc'] = ''
        return response
    except Exception as ex:
        print(ex)
        ReportException('./logs/error.log', ex)
        response = make_response('SetNewLatLonLimits: UnknownError')
        response.headers['ErrorDesc'] = 'UnknownError'
        return response



if __name__ == '__main__':
    app.run(host='127.0.0.1', port=1999)