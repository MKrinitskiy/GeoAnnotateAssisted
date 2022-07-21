from FlaskExtended import *
from libs.TrackingBasemapHelper import TrackingBasemapHelperClass
import datetime



def MakeTrackingBasemapHelper_progress(app: FlaskExtended,
                                       webapi_client_id: str = '',
                                       basemap_args_json: str = None):
    if webapi_client_id == '':
        raise Exception('client ID not specified!')

    step = 0
    total_steps = 2

    while True:
        step_description = ''
        if step == 0:
            step_description = 'Creating server-side comm. agent'
        elif step == 1:
            step_description = 'Creating server-side basemap renderer'

        yield 'step %d / %d : %s\n' % (step + 1, total_steps, step_description)
        print('step %d / %d ^ %s' % (step + 1, total_steps, step_description))

        if step == 0:
            app.bmhelpers[webapi_client_id] = TrackingBasemapHelperClass()
        elif step == 1:
            app.bmhelpers[webapi_client_id].createBasemapObj(basemap_args_json)
            yield 'READY\n'
            print('READY')
            break

        step = step + 1


def ListAvailableDataSnapshots_progress(app: FlaskExtended,
                                        dt_start: datetime.datetime = datetime.datetime(1970, 1, 1, 0, 0, 0),
                                        dt_end: datetime.datetime = datetime.datetime(2101, 1, 1, 0, 0, 0),
                                        webapi_client_id = ''):
    if webapi_client_id == '':
        raise Exception('client ID not specified!')

    step = 0
    total_steps = 1

    while True:
        step_description = ''
        if step == 0:
            step_description = 'Listing availabe data for datetime interval from %s till %s' % (datetime.datetime.strftime(dt_start, "%Y-%m-%dT%H:%M:%S"),
                                                                                                datetime.datetime.strftime(dt_end, "%Y-%m-%dT%H:%M:%S"))

        yield 'step %d / %d : %s\n' % (step + 1, total_steps, step_description)
        print('step %d / %d ^ %s' % (step + 1, total_steps, step_description))

        if step == 0:
            sourceDataManager = app.bmhelpers[webapi_client_id].sourceDataManager
            _ = sourceDataManager.ListAvailableData(dt_start, dt_end)
            yield 'READY\n'
            print('READY')
            break

        step = step + 1


# def ProcessSourceData_progress(app: FlaskExtended,
#                                curr_fname: str,
#                                calculateLatLonLimits: bool = True,
#                                resolution: str = 'f',
#                                webapi_client_id: str = ''):
#     if webapi_client_id == '':
#         raise Exception('client ID not specified!')
#     elif webapi_client_id not in app.bmhelpers.keys():
#         raise Exception('there is no basemap helper object for this client yet!!')
#
#     step = 0
#     total_steps = 5
#
#     while True:
#         step_description = ''
#         if step == 0:
#             step_description = 'Reading source data'
#         elif step == 1:
#             step_description = 'Creating Basemap object'
#         elif step == 2:
#             step_description = 'Plotting Basemap background'
#         elif step == 3:
#             step_description = 'Plotting Data Layer'
#         elif step == 4:
#             step_description = 'Fusing Basemapbeckground with Data layer'
#
#         yield 'step %d / %d : %s\n' % (step + 1, total_steps, step_description)
#         print('step %d / %d ^ %s' % (step + 1, total_steps, step_description))
#
#         if step == 0:
#             app.bmhelpers[webapi_client_id].ReadSourceData(calculateLatLonLimits)
#         elif step == 1:
#             app.bmhelpers[webapi_client_id].createBasemapObj(resolution=resolution)
#         elif step == 2:
#             app.bmhelpers[webapi_client_id].PlotBasemapBackground()
#         elif step == 3:
#             app.bmhelpers[webapi_client_id].PlotDataLayer(debug=False)
#             ### DEBUG ###
#             # for dataname in app.bmhelper.channelNames:
#             #     app.bmhelper.__dict__['DataLayerImage_%s' % dataname] = np.copy(app.bmhelper.BasemapLayerImage)
#         elif step == 4:
#             app.bmhelpers[webapi_client_id].FuseBasemapWithData()
#             yield 'READY\n'
#             print('READY')
#             break
#
#         step = step + 1
#


def SwitchSourceData_progress(app: FlaskExtended,
                              curr_fname: str,
                              webapi_client_id: str = ''):
    if webapi_client_id == '':
        raise Exception('client ID not specified!')
    elif webapi_client_id not in app.bmhelpers.keys():
        raise Exception('there is no basemap helper object for this client yet!!')

    step = 0
    total_steps = 4
    while True:
        step_description = ''
        if step == 0:
            step_description = 'Reading new data snapshot'
        elif step == 1:
            step_description = 'Rendering basemap'
        elif step == 2:
            step_description = 'Rendering data'
        elif step == 3:
            step_description = 'Fusing basemap with data'


        yield 'step %d / %d : %s\n' % (step + 1, total_steps, step_description)
        print('step %d / %d ^ %s' % (step + 1, total_steps, step_description))

        if step == 0:
            app.bmhelpers[webapi_client_id].SwitchSourceData(curr_fname)
            app.bmhelpers[webapi_client_id].ReadSourceData()
        elif step == 1:
            app.bmhelpers[webapi_client_id].PlotBasemapBackground()
        elif step == 2:
            app.bmhelpers[webapi_client_id].PlotDataLayer(debug=False)
            ### DEBUG ###
            # for dataname in app.bmhelper.channelNames:
            #     app.bmhelper.__dict__['DataLayerImage_%s' % dataname] = np.copy(app.bmhelper.BasemapLayerImage)
        elif step == 3:
            app.bmhelpers[webapi_client_id].FuseBasemapWithData()
            yield 'READY\n'
            print('READY')
            break

        step = step + 1




def SetNewLatLonLimits_progress(app: FlaskExtended,
                                llcrnrlon: float,
                                llcrnrlat: float,
                                urcrnrlon: float,
                                urcrnrlat: float,
                                resolution: str ='c',
                                webapi_client_id: str = ''):
    if webapi_client_id == '':
        raise Exception('client ID not specified!')
    elif webapi_client_id not in app.bmhelpers.keys():
        raise Exception('there is no basemap helper object for this client yet!!')
    step = 0
    total_steps = 5
    while True:
        step_description = ''
        if step == 0:
            step_description = 'SetNewLatLonLimits'
        elif step == 1:
            step_description = 'createBasemapObj'
        elif step == 2:
            step_description = 'PlotBasemapBackground'
        elif step == 3:
            step_description = 'PlotDataLayer'
        elif step == 4:
            step_description = 'FuseBasemapWithData'

        yield 'step %d / %d : %s\n' % (step + 1, total_steps, step_description)
        print('step %d / %d ^ %s' % (step + 1, total_steps, step_description))

        if step == 0:
            app.bmhelpers[webapi_client_id].SetNewLatLonLimits(llcrnrlon, llcrnrlat, urcrnrlon, urcrnrlat)
        elif step == 1:
            app.bmhelpers[webapi_client_id].createBasemapObj(resolution=resolution)
        elif step == 2:
            app.bmhelpers[webapi_client_id].PlotBasemapBackground()
        elif step == 3:
            app.bmhelpers[webapi_client_id].PlotDataLayer(debug=False)
            ### DEBUG ###
            # for dataname in app.bmhelper.channelNames:
            #     app.bmhelper.__dict__['DataLayerImage_%s' % dataname] = np.copy(app.bmhelper.BasemapLayerImage)
        elif step == 4:
            app.bmhelpers[webapi_client_id].FuseBasemapWithData()
            yield 'READY\n'
            print('READY')
            break

        step = step + 1




def PredictMCS_progress(app: FlaskExtended,
                        args,
                        curr_fname: str,
                        webapi_client_id: str = ''):
    if not args.no_cnn:
        from libs.CNNPredictor import CNNPredictor

    if webapi_client_id == '':
        raise Exception('client ID not specified!')
    elif webapi_client_id not in app.bmhelpers.keys():
        raise Exception('there is no renderer object for this client yet! (required for CNN to apply to renderer data)')

    step = 0
    total_steps = 4
    while True:
        step_description = ''
        if step == 0:
            step_description = 'LoadingCNN'
        elif step == 1:
            step_description = 'ReadingDataFile'
        elif step == 2:
            step_description = 'PreprocessingData'
        elif step == 3:
            step_description = 'ApplyingNeuralNetwork'


        yield 'step %d / %d : %s\n' % (step + 1, total_steps, step_description)
        print('step %d / %d ^ %s' % (step + 1, total_steps, step_description))

        if step == 0:
            if app.cnn is None:
                app.cnn = CNNPredictor(args)
            else:
                pass
        elif step == 1:
            app.cnn.LoadSourceData(curr_fname, webapi_client_id)
        elif step == 2:
            app.cnn.PreprocessSourceData(webapi_client_id)
        elif step == 3:
            app.cnn.ApplyCNN(webapi_client_id)
            yield 'READY\n'
            print('READY')
            break
        step = step + 1