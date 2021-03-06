import os, sys
python_path = sys.executable
if sys.platform == 'win32':
    os.environ['PROJ_LIB'] = os.path.join(os.path.split(python_path)[0], 'Library', 'share')
elif ((sys.platform == 'linux') | (sys.platform == 'darwin')):
    os.environ['PROJ_LIB'] = os.path.join(sys.executable.replace('bin/python', ''), 'share', 'proj')

from flask import Flask, request, send_file, make_response, Response
import numpy as np
from FlaskExtended import *
from Support_defs import *
from libs.TrackingBasemapHelper import *
import binascii, logging, time
from PIL import Image
from io import BytesIO


app = FlaskExtended(__name__)
app.config['SECRET_KEY'] = binascii.hexlify(os.urandom(24))
file_handler = logging.FileHandler('./logs/app.log')


tmp_imag_dir = os.path.join(os.getcwd(), 'tmp')
src_data_dir = os.path.join(os.getcwd(), 'src_data')
channels_list = ['ch9', 'ch5', 'ch5_ch9']



@app.route('/')
def main():
    response = make_response('Nothing to do here')
    response.headers['ErrorDesc'] = 'CommandNotUnderstood'
    return response


def MakeTrackingBasemapHelper_progress(curr_fname, calculateLatLonLimits = True, resolution = 'f', webapi_client_id = ''):
    if webapi_client_id == '':
        raise Exception('client ID not specified!')
    x = 0
    total_steps = 6
    while True:
        step_description = ''
        if x == 0:
            step_description = 'TrackingBasemapHelperClass'
        elif x == 1:
            step_description = 'ReadSourceData'
        elif x == 2:
            step_description = 'createBasemapObj'
        elif x == 3:
            step_description = 'PlotBasemapBackground'
        elif x == 4:
            step_description = 'PlotDataLayer'
        elif x == 5:
            step_description = 'FuseBasemapWithData'

        yield 'step %d / %d : %s\n' % (x+1, total_steps, step_description)
        print('step %d / %d ^ %s' % (x+1, total_steps, step_description))

        if x == 0:
            app.bmhelpers[webapi_client_id] = TrackingBasemapHelperClass(curr_fname)
        elif x == 1:
            app.bmhelpers[webapi_client_id].ReadSourceData(calculateLatLonLimits)
        elif x == 2:
            app.bmhelpers[webapi_client_id].createBasemapObj(resolution=resolution)
        elif x == 3:
            app.bmhelpers[webapi_client_id].PlotBasemapBackground()
        elif x == 4:
            app.bmhelpers[webapi_client_id].PlotDataLayer(debug=False)
            ### DEBUG ###
            # for dataname in app.bmhelper.channelNames:
            #     app.bmhelper.__dict__['DataLayerImage_%s' % dataname] = np.copy(app.bmhelper.BasemapLayerImage)
        elif x == 5:
            app.bmhelpers[webapi_client_id].FuseBasemapWithData()
            yield 'READY\n'
            print('READY')
            break

        x = x + 1


def SetNewLatLonLimits_progress(llcrnrlon, llcrnrlat, urcrnrlon, urcrnrlat, resolution='c', webapi_client_id = ''):
    if webapi_client_id == '':
        raise Exception('client ID not specified!')
    elif webapi_client_id not in app.bmhelpers.keys():
        raise Exception('there is no basemap helper object for this client yet!!')
    x = 0
    total_steps = 5
    while True:
        step_description = ''
        if x == 0:
            step_description = 'SetNewLatLonLimits'
        elif x == 1:
            step_description = 'createBasemapObj'
        elif x == 2:
            step_description = 'PlotBasemapBackground'
        elif x == 3:
            step_description = 'PlotDataLayer'
        elif x == 4:
            step_description = 'FuseBasemapWithData'

        yield 'step %d / %d : %s\n' % (x+1, total_steps, step_description)
        print('step %d / %d ^ %s' % (x+1, total_steps, step_description))

        if x == 0:
            app.bmhelpers[webapi_client_id].SetNewLatLonLimits(llcrnrlon, llcrnrlat, urcrnrlon, urcrnrlat)
        elif x == 1:
            app.bmhelpers[webapi_client_id].createBasemapObj(resolution=resolution)
        elif x == 2:
            app.bmhelpers[webapi_client_id].PlotBasemapBackground()
        elif x == 3:
            app.bmhelpers[webapi_client_id].PlotDataLayer(debug=False)
            ### DEBUG ###
            # for dataname in app.bmhelper.channelNames:
            #     app.bmhelper.__dict__['DataLayerImage_%s' % dataname] = np.copy(app.bmhelper.BasemapLayerImage)
        elif x == 4:
            app.bmhelpers[webapi_client_id].FuseBasemapWithData()
            yield 'READY\n'
            print('READY')
            break

        x = x + 1


def SwitchSourceData_progress(curr_fname, webapi_client_id = ''):
    if webapi_client_id == '':
        raise Exception('client ID not specified!')
    elif webapi_client_id not in app.bmhelpers.keys():
        raise Exception('there is no basemap helper object for this client yet!!')

    x = 0
    total_steps = 6
    while True:
        step_description = ''
        if x == 0:
            step_description = 'SwitchSourceData'
        elif x == 1:
            step_description = 'PlotBasemapBackground'
        elif x == 2:
            step_description = 'PlotDataLayer'
        elif x == 3:
            step_description = 'FuseBasemapWithData'


        yield 'step %d / %d : %s\n' % (x+1, total_steps, step_description)
        print('step %d / %d ^ %s' % (x+1, total_steps, step_description))

        if x == 0:
            app.bmhelpers[webapi_client_id].SwitchSourceData(curr_fname)
        elif x == 1:
            app.bmhelpers[webapi_client_id].PlotBasemapBackground()
        elif x == 2:
            app.bmhelpers[webapi_client_id].PlotDataLayer(debug=False)
            ### DEBUG ###
            # for dataname in app.bmhelper.channelNames:
            #     app.bmhelper.__dict__['DataLayerImage_%s' % dataname] = np.copy(app.bmhelper.BasemapLayerImage)
        elif x == 3:
            app.bmhelpers[webapi_client_id].FuseBasemapWithData()
            yield 'READY\n'
            print('READY')
            break

        x = x + 1




# @app.route('/exec', methods=['POST', 'GET'])
@app.route('/exec', methods=['GET'])
def exec():
    command = request.args['command']
    if command == 'createbmhelper':
        try:
            arg_src_fname = request.args['src_fname']
        except Exception as ex:
            print(ex)
            ReportException('./logs/app.log', ex)
            response = make_response('source file was not specified')
            response.headers['ErrorDesc'] = 'FileNotFound'
            return response

        try:
            webapi_client_id = request.args['webapi_client_id']
        except Exception as ex:
            print(ex)
            ReportException('./logs/app.log', ex)
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

        # curr_fname = os.path.join(os.getcwd(), 'src_data', arg_src_fname)
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
            return Response(MakeTrackingBasemapHelper_progress(curr_fname, calculateLatLonLimits, resolution, webapi_client_id=webapi_client_id),
                            mimetype='text/stream')

    elif command == 'SetNewLatLonLimits':
        try:
            llcrnrlon = np.float(request.args['llcrnrlon'])
            llcrnrlat = np.float(request.args['llcrnrlat'])
            urcrnrlon = np.float(request.args['urcrnrlon'])
            urcrnrlat = np.float(request.args['urcrnrlat'])
            resolution = request.args['resolution']
            webapi_client_id = request.args['webapi_client_id']
            return Response(SetNewLatLonLimits_progress(llcrnrlon, llcrnrlat, urcrnrlon, urcrnrlat, resolution, webapi_client_id=webapi_client_id), mimetype='text/stream')
        except Exception as ex:
            print(ex)
            ReportException('./logs/app.log', ex)
            response = make_response('SetNewLatLonLimits: UnknownError')
            response.headers['ErrorDesc'] = 'UnknownError'
            return response


    elif command == 'SwitchSourceData':
        try:
            arg_src_fname = request.args['src_fname']
        except Exception as ex:
            print(ex)
            ReportException('./logs/app.log', ex)
            response = make_response('source file was not specified')
            response.headers['ErrorDesc'] = 'FileNotFound'
            return response

        try:
            webapi_client_id = request.args['webapi_client_id']
        except Exception as ex:
            print(ex)
            ReportException('./logs/app.log', ex)
            response = make_response('client webapi ID was not specified')
            response.headers['ErrorDesc'] = 'ClientIDnotSpecified'
            return response

        # curr_fname = os.path.join(os.getcwd(), 'src_data', arg_src_fname)
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
            response = make_response('Unable to find file %s' % curr_fname)
            response.headers['ErrorDesc'] = 'FileNotFound'
            return response
        else:
            return Response(SwitchSourceData_progress(curr_fname, webapi_client_id=webapi_client_id), mimetype='text/stream')




@app.route('/images', methods=['GET'])
def image():
    try:
        try:
            webapi_client_id = request.args['webapi_client_id']
        except Exception as ex:
            print(ex)
            ReportException('./logs/app.log', ex)
            response = make_response('client webapi ID was not specified')
            response.headers['ErrorDesc'] = 'ClientIDnotSpecified'
            return response

        dict1 = {'CVimageCombined': np.copy(app.bmhelpers[webapi_client_id].CVimageCombined)}
        for ch in channels_list:
            dict1['DataLayerImage_%s' % ch] = np.copy(app.bmhelpers[webapi_client_id].__dict__['DataLayerImage_%s' % ch])
        dict1['BasemapLayerImage'] = np.copy(app.bmhelpers[webapi_client_id].__dict__['BasemapLayerImage'])
        dict1['llcrnrlon'] = app.bmhelpers[webapi_client_id].llcrnrlon
        dict1['llcrnrlat'] = app.bmhelpers[webapi_client_id].llcrnrlat
        dict1['urcrnrlon'] = app.bmhelpers[webapi_client_id].urcrnrlon
        dict1['urcrnrlat'] = app.bmhelpers[webapi_client_id].urcrnrlat
        dict1['cLat'] = app.bmhelpers[webapi_client_id].cLat
        dict1['cLon'] = app.bmhelpers[webapi_client_id].cLon
        dict1['LathalfRange'] = app.bmhelpers[webapi_client_id].LathalfRange
        dict1['LonHalfRange'] = app.bmhelpers[webapi_client_id].LonHalfRange
        dict1['dataToPlot'] = app.bmhelpers[webapi_client_id].dataToPlot

        tmp_fname = './cache/webapi_cache/basemap-plot-%s.pickle' % binascii.hexlify(os.urandom(5)).decode('ascii')
        with open(tmp_fname, 'wb') as f:
            pickle.dump(dict1, f, pickle.HIGHEST_PROTOCOL)
        response = make_response(send_file(tmp_fname, mimetype='application/octet-stream'))
        response.headers['fileName'] = os.path.basename(tmp_fname)
        return response
    except Exception as ex:
        print(ex)
        ReportException('./logs/app.log', ex)
        response = make_response('Unable to generate basemap image')
        response.headers['ErrorDesc'] = 'BasemapImageGenerating'
        return response


@app.route('/imdone', methods=['GET'])
def imdone():
    try:
        try:
            webapi_client_id = request.args['webapi_client_id']
        except Exception as ex:
            print(ex)
            ReportException('./logs/app.log', ex)
            response = make_response('client webapi ID was not specified')
            response.headers['ErrorDesc'] = 'ClientIDnotSpecified'
            return response

        del app.bmhelpers[webapi_client_id]

        response = make_response('OK')
        response.headers['ErrorDesc'] = ''
        return response
    except Exception as ex:
        print(ex)
        ReportException('./logs/app.log', ex)
        response = make_response('SetNewLatLonLimits: UnknownError')
        response.headers['ErrorDesc'] = 'UnknownError'
        return response



app.run(host='0.0.0.0',port=1999)