import codecs
import datetime
import distutils.spawn
import os.path
import cv2
import platform, re, sys, subprocess, logging
from functools import partial
from collections import defaultdict
import threading
import pandas as pd
import sqlite3
import resources

import sys
python_path = sys.executable

from PyQt5.QtGui import *
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *

from libs import *
from libs.parse_args import parse_args
from common import *
import asyncio

import os
try:
    os.environ.pop("QT_QPA_PLATFORM_PLUGIN_PATH")
except Exception as ex:
    ReportException('./logs/errors.log', ex)




__appname__ = 'GeoAnnotate assisted'

args = sys.argv[1:]
args = parse_args(args)
EnsureDirectoryExists('./logs/')
logging.basicConfig(filename='./logs/app.log', level=logging.INFO, format='%(asctime)s %(message)s')
logging.info('Started AI-assisted GeoAnnotate client-side app')
logging.info('args: %s' % sys.argv[1:])


class MainWindow(QMainWindow):
    FIT_WINDOW, FIT_WIDTH, MANUAL_ZOOM = list(range(3))

    # def __init__(self, defaultFilename=None, defaultPrefdefClassFile=None, defaultSaveDir=None):
    def __init__(self, defaultFilename=None, defaultPrefdefClassFile=None):
        super(MainWindow, self).__init__()
        action = partial(newAction, self)

        self.setWindowTitle(__appname__)

        self._basemaphelper = None

        # LabelFile.suffix = MCC_XML_EXT
        self.trackingFunctionsAvailable = False

        # Load setting in the main thread
        self.settings = Settings(os.path.dirname(os.path.abspath(__file__)))
        self.settings.load()
        try:
            fn = args.proj_json_settings_fname
            with open(fn, 'r') as f:
                basemap_args_json = f.read()
            self.basemap_args = ast.literal_eval(basemap_args_json)
        except:
            basemap_args_json = '{"width": 5500000, "height": 4500000, "rsphere": [6378137.0, 6356752.3142], "resolution": "l", "area_thresh": 1000.0, "projection": "lcc", "lat_1": 45.0, "lat_2": 65.0, "lat_0": 60.0, "lon_0": 35.0}'
            self.basemap_args = ast.literal_eval(basemap_args_json)


        # self.defaultSaveDir = defaultSaveDir

        # For loading all image under a directory
        # self.mImgList = []
        self.dirname = None
        self.labelHist = []
        self.lastOpenDir = None

        self.curr_dt = datetime.datetime.now()

        # Whether we need to save or not.
        self.dirty = False

        self._noSelectionSlot = False

        self.label_types = args.labels_type
        self.shapes_points_count = 3
        if self.label_types == 'MCS':
            self.shapes_points_count = 3
            self.label_class = MCSlabel
        elif self.label_types == 'MC':
            self.shapes_points_count = 2
            self.label_class = MClabel
        elif self.label_types == 'PL':
            self.shapes_points_count = 2
            self.label_class = MClabel
        elif self.label_types == 'AMRC':
            self.shapes_points_count = 2
            self.label_class = MClabel
        elif self.label_types == 'CS':
            self.shapes_points_count = 3
            self.label_class = MCSlabel

        # Load predefined classes to the list
        self.loadPredefinedClasses(defaultPrefdefClassFile)

        # Main widgets and related state.
        self.labelDialog = LabelDialog(parent=self, listItem=self.labelHist)

        self.itemsToShapes = {}
        self.shapesToItems = {}
        self.ghosts_shapesToItems = {}
        self.ghosts_itemsToShapes = {}
        self.prevLabelText = ''

        self.TrackItemsToTracks = {}
        self.TracksToTrackItems = {}

        self.tracks = {}

        listLayout = QVBoxLayout()
        listLayout.setContentsMargins(0, 0, 0, 0)

        # Create a widget for using default label
        self.useDefaultLabelCheckbox = QCheckBox(u'Use default label')
        self.useDefaultLabelCheckbox.setChecked(False)
        self.defaultLabelTextLine = QLineEdit()
        useDefaultLabelQHBoxLayout = QHBoxLayout()
        useDefaultLabelQHBoxLayout.addWidget(self.useDefaultLabelCheckbox)
        useDefaultLabelQHBoxLayout.addWidget(self.defaultLabelTextLine)
        useDefaultLabelContainer = QWidget()
        useDefaultLabelContainer.setLayout(useDefaultLabelQHBoxLayout)

        self.editButton = QToolButton()
        self.editButton.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)

        # Add some of widgets to listLayout
        listLayout.addWidget(self.editButton)
        listLayout.addWidget(useDefaultLabelContainer)

        #region Create and add a widget for showing current label items
        self.labelList = QTreeWidget()
        self.labelList.setColumnCount(3)
        self.labelList.setHeaderLabels(['name', 'uid', 'date,time'])
        labelListContainer = QWidget()
        labelListContainer.setLayout(listLayout)
        self.labelList.itemActivated.connect(self.labelSelectionChanged)
        self.labelList.itemSelectionChanged.connect(self.labelSelectionChanged)
        self.labelList.itemDoubleClicked.connect(self.editLabel)
        # Connect to itemChanged to detect checkbox changes.
        self.labelList.itemChanged.connect(self.labelItemChanged)
        listLayout.addWidget(self.labelList)

        self.dock = QDockWidget(u'Labels', self)
        self.dock.setObjectName(u'Labels')
        self.dock.setWidget(labelListContainer)
        #endregion
        self.addDockWidget(Qt.RightDockWidgetArea, self.dock)



        #region MKrinitskiy - track list widget
        self.trackListWidget = QTreeWidget()
        self.trackListWidget.setColumnCount(2)
        self.trackListWidget.setHeaderLabels(['name', 'uid', 'date,time'])
        trackListLayout = QVBoxLayout()
        trackListLayout.setContentsMargins(0, 0, 0, 0)
        trackListLayout.addWidget(self.trackListWidget)
        trackListContainer = QWidget()
        trackListContainer.setLayout(trackListLayout)
        self.trackdock = QDockWidget(u'Track List', self)
        self.trackdock.setObjectName(u'Tracks')
        self.trackListWidget.itemChanged.connect(self.trackItemChanged)
        self.trackdock.setWidget(trackListContainer)
        self.addDockWidget(Qt.RightDockWidgetArea, self.trackdock)
        #endregion MKrinitskiy - track list widget



        try:
            self.start_dt = self.settings.get(SETTING_DATERANGE_START_DATE, datetime.datetime.utcnow() + datetime.timedelta(days=-30))
        except:
            self.start_dt = datetime.datetime.utcnow() + datetime.timedelta(days=-30)

        try:
            self.end_dt = self.settings.get(SETTING_DATERANGE_END_DATE, datetime.datetime.utcnow())
        except:
            self.end_dt = datetime.datetime.utcnow()

        #region File List widget
        filelistLayout = QVBoxLayout()
        filelistLayout.setContentsMargins(0, 0, 0, 0)

        self.startDateEdit = QtWidgets.QDateEdit(calendarPopup=True, )
        self.startDateEdit.setDisplayFormat("dd-MM-yyyy")
        try:
            startQDateTime = QtCore.QDateTime.fromString(datetime.datetime.strftime(self.start_dt, '%Y-%m-%dT%H:%M:%S'),
                                                         Qt.ISODate)
        except:
            startQDateTime = QtCore.QDateTime.currentDateTime().addDays(-30)
        self.startDateEdit.setDateTime(startQDateTime)
        self.startDateEdit.dateChanged.connect(self.startDateEdit_dateChanged)

        self.endDateEdit = QtWidgets.QDateEdit(calendarPopup=True)
        self.endDateEdit.setDisplayFormat("dd-MM-yyyy")
        try:
            endQDateTime = QtCore.QDateTime.fromString(datetime.datetime.strftime(self.end_dt, '%Y-%m-%dT%H:%M:%S'),
                                                         Qt.ISODate)
        except:
            endQDateTime = QtCore.QDateTime.currentDateTime().addDays(-30)
        self.endDateEdit.setDateTime(endQDateTime)
        self.endDateEdit.dateChanged.connect(self.endDateEdit_dateChanged)

        self.listServersideDataButton = QToolButton()
        self.listServersideDataButton.setToolButtonStyle(Qt.ToolButtonTextOnly)
        listServersideDataAction = action('List server-side data', self.ListServersideDataSnapshots, None, None,
                                     u'Pick date for data list at server', enabled=True)
        self.listServersideDataButton.setDefaultAction(listServersideDataAction)

        dateRangePickerButtons = QHBoxLayout()
        dateRangePickerButtons.addWidget(self.startDateEdit)
        dateRangePickerButtons.addWidget(self.endDateEdit)
        dateRangePickerButtons.addWidget(self.listServersideDataButton)
        dateRangePickerButtonsContainer = QWidget()
        dateRangePickerButtonsContainer.setLayout(dateRangePickerButtons)
        filelistLayout.addWidget(dateRangePickerButtonsContainer)



        self.fileListWidget = QListWidget()
        self.fileListWidget.itemDoubleClicked.connect(self.fileitemDoubleClicked)

        filelistLayout.addWidget(self.fileListWidget)
        fileListContainer = QWidget()
        fileListContainer.setLayout(filelistLayout)
        self.filedock = QDockWidget(u'File List', self)
        self.filedock.setObjectName(u'Files')
        self.filedock.setWidget(fileListContainer)
        self.addDockWidget(Qt.RightDockWidgetArea, self.filedock)
        #endregion File List widget


        # # region MKrinitskiy - log widget
        # self.logsDock = QDockWidget(u'log', self)
        # self.logsDock.setObjectName(u'log')
        # logTextBox = QPlainTextEditLogger(self)
        # logging.getLogger().addHandler(logTextBox)
        # logging.getLogger().setLevel(logging.INFO)
        # self.logsDock.setWidget(logTextBox.widget)
        # self.addDockWidget(Qt.BottomDockWidgetArea, self.logsDock)
        # # endregion MKrinitskiy - track list widget


        self.currently_opened_source_file = None

        self.zoomWidget = ZoomWidget()
        self.colorDialog = ColorDialog(parent=self)

        self.canvas = Canvas(parent=self)
        self.canvas.zoomRequest.connect(self.zoomRequestCallback)

        scroll = QScrollArea()
        scroll.setWidget(self.canvas)
        scroll.setWidgetResizable(True)
        self.scrollBars = {
            Qt.Vertical: scroll.verticalScrollBar(),
            Qt.Horizontal: scroll.horizontalScrollBar()
        }
        self.scrollArea = scroll
        self.canvas.scrollRequest.connect(self.scrollRequestCallback)

        self.canvas.newShape.connect(self.newShapeCallback)
        self.canvas.shapeMoved.connect(self.setDirty)
        self.canvas.shapeMovesFinished.connect(self.ShapeModifiedCallback)
        self.canvas.selectionChanged.connect(self.shapeSelectionChanged)
        self.canvas.drawingPolygon.connect(self.toggleDrawingSensitive)

        self.setCentralWidget(scroll)

        #region Actions
        quit = action('&Quit', self.closing,
                      'Ctrl+Q', 'quit', u'Quit application')



        # open = action('&Open', self.openFile,
        #               'Ctrl+O', 'open', u'Open image or label file')

        # opendir = action('&Open Dir', self.openDirDialog,
        #                  'Ctrl+u', 'open', u'Open Dir')

        # listServersideDataSnapshots = action('&List server-side\ndata files', self.ListServersideDataSnapshots, 'Ctrl+u', 'open', u'Open Dir')

        openNextImg = action('Next file', self.openNextImg,
                             'd', 'next', u'Open Next')

        openPrevImg = action('&Prev file', self.openPrevImg,
                             'a', 'prev', u'Open Prev')

        # save = action('&Save', self.saveFile,
        #               'Ctrl+S', 'save', u'Save labels to file', enabled=False)

        # close = action('&Close', self.closeFile, 'Ctrl+W', 'close', u'Close current file')

        resetAll = action('&ResetAll', self.resetAll, None, 'resetall', u'Reset all')

        # color1 = action('Box Line Color', self.chooseColor1,
        #                 'Ctrl+L', 'color_line', u'Choose Box line color')

        createMode = action('Create new label', self.setCreateMode,
                            'w', 'new', u'Start drawing a new label', enabled=False)
        editMode = action('&Edit ellipse', self.setEditMode,
                          'Ctrl+J', 'edit', u'Move and edit Boxs', enabled=False)

        # create = action('Create a label', self.createShape,
        #                 'w', 'new', u'Draw a new label', enabled=False)

        delete = action('Delete label', self.deleteSelectedShape,
                        'Delete', 'delete', u'Delete', enabled=False)

        # duplicate_label = action('Create duplicated label', self.createDuplicatedLabel, 'Ctrl+D',
        #                      'new dupl. label', u'Create new label duplicating this one')

        start_track = action('Start &new track', self.startNewTrack, 'Ctrl+N',
                             'new track', u'Creating new track starting from this label')

        continue_track = action('Continue a track', self.continueExistingTrack, None,
                             'continue track', u'Continue an existing track...')

        hideAll = action('&Hide labels', partial(self.togglePolygons, False),
                         'Ctrl+H', 'hide', u'Hide all labels',
                         enabled=False)
        showAll = action('&Show labels', partial(self.togglePolygons, True),
                         'Ctrl+A', 'hide', u'Show all labels',
                         enabled=False)

        showInfo = action('&Information', self.showInfoDialog, None, 'help', u'Information')

        zoom = QWidgetAction(self)
        zoom.setDefaultWidget(self.zoomWidget)
        self.zoomWidget.setWhatsThis(
            u"Zoom in or out of the image. Also accessible with"
            " %s and %s from the canvas." % (fmtShortcut("Ctrl+[-+]"),
                                             fmtShortcut("Ctrl+Wheel")))
        self.zoomWidget.setEnabled(True)

        zoomIn = action('Zoom &In', partial(self.addZoom, 10),
                        'Ctrl++', 'zoom-in', u'Increase zoom level', enabled=False)
        zoomOut = action('&Zoom Out', partial(self.addZoom, -10),
                         'Ctrl+-', 'zoom-out', u'Decrease zoom level', enabled=False)
        zoomOrg = action('&Original size', partial(self.setZoom, 100),
                         'Ctrl+=', 'zoom', u'Zoom to original size', enabled=False)
        fitWindow = action('&Fit Window', self.setFitWindow,
                           'Ctrl+F', 'fit-window', u'Zoom follows window size',
                           checkable=True, enabled=False)
        fitWidth = action('Fit &Width', self.setFitWidth,
                          'Ctrl+Shift+F', 'fit-width', u'Zoom follows window width',
                          checkable=True, enabled=False)

        zoomReplotBasemap = action('Refresh &Map', lambda: self.refreshBasemap(hires=False),
                          'Ctrl+Shift+M', 'refresh-basemap', u'Reconstruct zoomed basemap',
                          checkable=True, enabled=False)

        zoomIncreaseResolution = action('Refresh map Hires', self.refreshBasemapHires, '', 'refresh-basemap-hires', u'', checkable=True, enabled=False)

        switchDataChannel = action('Switch data\nchannel', self.switchChannel, '', 'switch-channel', 'Switch data channel', checkable=True, enabled=False)


        # Group zoom controls into a list for easier toggling.
        zoomActions = (self.zoomWidget, zoomIn, zoomOut,
                       zoomOrg, fitWindow, fitWidth)
        self.zoomMode = self.MANUAL_ZOOM
        self.scalers = {
            self.FIT_WINDOW: self.scaleFitWindow,
            self.FIT_WIDTH: self.scaleFitWidth,
            # Set to one to scale to 100% when loading files.
            self.MANUAL_ZOOM: lambda: 1,
        }

        edit = action('&Edit Label', self.editLabel, 'Ctrl+E', 'edit', u'Modify the label of the selected Box', enabled=False)
        self.editButton.setDefaultAction(edit)

        shapeLineColor = action('Shape &Line Color', self.chshapeLineColor, icon='color_line', tip=u'Change the line color for this specific shape', enabled=False)
        shapeFillColor = action('Shape &Fill Color', self.chshapeFillColor, icon='color', tip=u'Change the fill color for this specific shape', enabled=False)


        labels = self.dock.toggleViewAction()
        labels.setText('Show/Hide Label Panel')
        labels.setShortcut('Ctrl+Shift+L')

        # Lavel list context menu.
        labelMenu = QMenu()
        addActions(labelMenu, (edit, delete))
        self.labelList.setContextMenuPolicy(Qt.CustomContextMenu)
        self.labelList.customContextMenuRequested.connect(self.popLabelListMenu)

        # self.actions = struct(save=save, open=open, close=close,
        #                       resetAll=resetAll,
        #                       lineColor=color1, create=create, delete=delete, edit=edit,
        #                       createMode=createMode, editMode=editMode,
        #                       shapeLineColor=shapeLineColor, shapeFillColor=shapeFillColor,
        #                       zoom=zoom, zoomIn=zoomIn, zoomOut=zoomOut, zoomOrg=zoomOrg,
        #                       fitWindow=fitWindow, fitWidth=fitWidth,
        #                       zoomActions=zoomActions,
        #                       refreshBasemap=zoomReplotBasemap,
        #                       zoomHires=zoomIncreaseResolution,
        #                       fileMenuActions=(open, opendir, save, close, resetAll, quit),
        #                       beginner=(),
        #                       advanced=(),
        #                       editMenu=(edit, delete, None, color1),
        #                       beginnerContext=(create, edit, delete, start_track, continue_track),
        #                       advancedContext=(createMode, editMode, edit, delete, shapeLineColor, shapeFillColor),
        #                       onLoadActive=(close, create, createMode, editMode),
        #                       onShapesPresent=(hideAll, showAll),
        #                       switchDataChannel=switchDataChannel)

        self.actions = struct(resetAll=resetAll,
                              delete=delete, edit=edit,
                              createMode=createMode, editMode=editMode,
                              shapeLineColor=shapeLineColor, shapeFillColor=shapeFillColor,
                              zoom=zoom, zoomIn=zoomIn, zoomOut=zoomOut, zoomOrg=zoomOrg,
                              fitWindow=fitWindow, fitWidth=fitWidth,
                              zoomActions=zoomActions,
                              refreshBasemap=zoomReplotBasemap,
                              zoomHires=zoomIncreaseResolution,
                              fileMenuActions=(listServersideDataAction, resetAll, quit),
                              editMenu=(edit, delete, None),
                              tools = (),
                              context=(createMode, editMode, edit, delete, start_track, continue_track),
                              onLoadActive=(createMode, editMode),
                              onShapesPresent=(hideAll, showAll),
                              switchDataChannel=switchDataChannel)

        self.menus = struct(
            file=self.menu('&File'),
            edit=self.menu('&Edit'),
            view=self.menu('&View'),
            help=self.menu('&Help'),
            recentFiles=QMenu('Open &Recent'),
            labelList=labelMenu)

        # Auto preserving basemap config
        self.preserveBasemapConfig = QAction("Preserve basemap configuration", self)
        self.preserveBasemapConfig.setCheckable(True)
        self.preserveBasemapConfig.setChecked(self.settings.get(SETTING_PRESERVE_BASEMAP_CONFIG, True))

        # Sync single class mode from PR#106
        self.singleClassMode = QAction("Single Class Mode", self)
        self.singleClassMode.setShortcut("Ctrl+Shift+S")
        self.singleClassMode.setCheckable(True)
        self.singleClassMode.setChecked(self.settings.get(SETTING_SINGLE_CLASS, False))
        self.lastLabel = None
        # Add option to enable/disable labels being painted at the top of bounding boxes
        self.paintLabelsOption = QAction("Paint Labels", self)
        self.paintLabelsOption.setShortcut("Ctrl+Shift+P")
        self.paintLabelsOption.setCheckable(True)
        self.paintLabelsOption.setChecked(self.settings.get(SETTING_PAINT_LABEL, False))
        self.paintLabelsOption.triggered.connect(self.togglePaintLabelsOption)

        addActions(self.menus.file,
                   (listServersideDataAction, resetAll, quit))
        # addActions(self.menus.help, (help, showInfo))
        addActions(self.menus.help, [showInfo])
        addActions(self.menus.view, (
            self.preserveBasemapConfig,
            # self.autoSaving,
            self.singleClassMode,
            self.paintLabelsOption,
            labels, None,
            hideAll, showAll, None,
            zoomIn, zoomOut, zoomOrg, None,
            fitWindow, fitWidth, zoomReplotBasemap, zoomIncreaseResolution, switchDataChannel))

        self.menus.file.aboutToShow.connect(self.updateFileMenu)

        # Custom context menu for the canvas widget:
        addActions(self.canvas.menus[1], [action('&Move here', self.moveShape)])

        self.tools = self.toolbar('Tools')
        # self.actions.beginner = (
        #     openNextImg, openPrevImg, None, create,
        #     delete, None,
        #     zoomIn, zoom, zoomOut, fitWindow, fitWidth, zoomReplotBasemap, zoomIncreaseResolution, switchDataChannel)

        self.actions.tools = (openNextImg, openPrevImg, None,
                              createMode, editMode, delete, None,
                              hideAll, showAll, None,
                              zoomIn, zoom, zoomOut, fitWindow, fitWidth, zoomReplotBasemap, zoomIncreaseResolution, switchDataChannel)

        #endregion Actions

        self.statusBar().showMessage('%s started.' % __appname__)
        self.statusBar().show()

        # Application state.
        self.image = QImage()
        self.filePath = ustr(defaultFilename)
        self.recentFiles = []
        self.maxRecent = 7
        self.lineColor = None
        self.fillColor = None
        self.zoom_level = 100
        self.fit_window = False
        # Add Chris
        self.difficult = False

        ## Fix the compatible issue for qt4 and qt5. Convert the QStringList to python list
        if self.settings.get(SETTING_RECENT_FILES):
            if not (sys.version_info.major >= 3 or QT_VERSION_STR.startswith('5.')):
                recentFileQStringList = self.settings.get(SETTING_RECENT_FILES)
                self.recentFiles = [ustr(i) for i in recentFileQStringList]
            else:
                self.recentFiles = recentFileQStringList = self.settings.get(SETTING_RECENT_FILES)

        size = self.settings.get(SETTING_WIN_SIZE, QSize(600, 500))
        position = self.settings.get(SETTING_WIN_POSE, QPoint(0, 0))
        self.resize(size)
        self.move(position)
        saveDir = ustr(self.settings.get(SETTING_SAVE_DIR, None))
        self.lastOpenDir = ustr(self.settings.get(SETTING_LAST_OPEN_DIR, None))

        #region tracks database
        self.queries_collection = SQLite_Queries(label_types=self.label_types)

        try:
            self.tracks_db_fname = self.settings.get(SETTING_TRACKS_DATABASE_FNAME, os.path.join('./', 'tracks.db'))
            # self.tracks_db_fname = './tracks.db'
            self.settings[SETTING_TRACKS_DATABASE_FNAME] = self.tracks_db_fname
        except:
            self.tracks_db_fname = os.path.join(os.getcwd(), 'tracks.db')
            self.settings[SETTING_TRACKS_DATABASE_FNAME] = self.tracks_db_fname

        if (os.path.exists(self.tracks_db_fname) and os.path.isfile(self.tracks_db_fname)):
            if DatabaseOps.test_db_connection(self.tracks_db_fname, self.queries_collection):
                print('tracks database connection successful')
                self.tracking_available = True
            else:
                print('WARNING! tracks database connection failed')
                self.tracking_available = False
        else:
            if DatabaseOps.create_tracks_db(self.tracks_db_fname, self.queries_collection):
                print('created new tracks database file: %s' % self.tracks_db_fname)
                self.tracking_available = True
            else:
                self.tracking_available = False
        #endregion


        self.restoreState(self.settings.get(SETTING_WIN_STATE, QByteArray()))
        Shape.line_color = self.lineColor = QColor(self.settings.get(SETTING_LINE_COLOR, DEFAULT_LINE_COLOR))
        Shape.fill_color = self.fillColor = QColor(self.settings.get(SETTING_FILL_COLOR, DEFAULT_FILL_COLOR))
        self.canvas.setDrawingColor(self.lineColor)
        # Add chris
        Shape.difficult = self.difficult

        def xbool(x):
            if isinstance(x, QVariant):
                return x.toBool()
            return bool(x)

        # Populate the File menu dynamically.
        self.updateFileMenu()

        # Since loading the file may take some time, make sure it runs in the background.
        # if self.filePath and os.path.isdir(self.filePath):
        #     self.queueEvent(partial(self.importDirImages, self.filePath or ""))
        # elif self.filePath:
        #     self.queueEvent(partial(self.loadFile, self.filePath or ""))

        # Callbacks:
        self.zoomWidget.valueChanged.connect(self.paintCanvas)

        self.populateModeActions()

        # Display cursor coordinates at the right of status bar
        self.labelCoordinates = QLabel('')
        self.statusBar().addPermanentWidget(self.labelCoordinates)

        # Open Dir if deafult file
        # if self.filePath and os.path.isdir(self.filePath):
        #     self.openDirDialog(dirpath=self.filePath)



    def menu(self, title, actions=None):
        menu = self.menuBar().addMenu(title)
        if actions:
            addActions(menu, actions)
        return menu


    def toolbar(self, title, actions=None):
        toolbar = ToolBar(title)
        toolbar.setObjectName(u'%sToolBar' % title)
        # toolbar.setOrientation(Qt.Vertical)
        toolbar.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        if actions:
            addActions(toolbar, actions)
        self.addToolBar(Qt.LeftToolBarArea, toolbar)
        return toolbar


    @property
    def basemaphelper(self):
        if self._basemaphelper:
            return self._basemaphelper
        else:
            self._basemaphelper = create_basemaphelper(args, self.basemap_args)
            return self._basemaphelper



    def noShapes(self):
        return not self.itemsToShapes



    def populateModeActions(self):
        # if self.beginner():
        #     tool, menu = self.actions.beginner, self.actions.beginnerContext
        # else:
        tool, menu = self.actions.tools, self.actions.context
        self.tools.clear()
        addActions(self.tools, tool)
        self.canvas.menus[0].clear()
        addActions(self.canvas.menus[0], menu)
        self.menus.edit.clear()
        # actions = (self.actions.create,) if self.beginner()\
        #     else (self.actions.createMode, self.actions.editMode)
        actions = (self.actions.createMode, self.actions.editMode)
        addActions(self.menus.edit, actions + self.actions.editMenu)



    def setDirty(self):
        self.dirty = True
        # self.actions.save.setEnabled(True)


    def setClean(self):
        self.dirty = False
        self.actions.createMode.setEnabled(True)
        self.app.restoreOverrideCursor()



    def toggleActions(self, value=True):
        """Enable/Disable widgets which depend on an opened image."""
        for z in self.actions.zoomActions:
            z.setEnabled(value)
        for action in self.actions.onLoadActive:
            action.setEnabled(value)

    def queueEvent(self, function):
        QTimer.singleShot(0, function)

    def status(self, message, delay=5000):
        self.statusBar().showMessage(message, delay)

    def resetState(self):
        self.itemsToShapes.clear()
        self.shapesToItems.clear()

        self.tracks.clear()
        self.TracksToTrackItems.clear()
        self.TrackItemsToTracks.clear()

        self.trackListWidget.clear()

        self.labelList.clear()
        self.filePath = None
        self.imageData = None
        self.labelFile = None
        self.canvas.resetState()
        self.labelCoordinates.clear()

    def currentItem(self):
        items = self.labelList.selectedItems()
        if items:
            return items[0]
        return None

    # def addRecentFile(self, filePath):
    #     if filePath in self.recentFiles:
    #         self.recentFiles.remove(filePath)
    #     elif len(self.recentFiles) >= self.maxRecent:
    #         self.recentFiles.pop()
    #     self.recentFiles.insert(0, filePath)

    # def beginner(self):
    #     return self._beginner

    # def advanced(self):
    #     return not self.beginner()

    ## Callbacks ##
    def showInfoDialog(self):
        msg = u'Name:{0} \n{1} '.format(__appname__, sys.version_info)
        QMessageBox.information(self, u'Information', msg)



    # def createDuplicatedLabel(self):
    #     if self.canvas.selectedShape:




    def startNewTrack(self):
        if self.canvas.selectedShape:
            curr_label_track_data = DatabaseOps.read_tracks_by_label_uids(self.tracks_db_fname, self.queries_collection, [self.canvas.selectedShape.label.uid])
            if len(curr_label_track_data) > 0:
                # there is a track which this label belongs to
                DisplayWarning("SORRY, we cannot do this.",
                               "WARNING! There is already a track which this label belongs to.\nOne cannot assign a label to more than one track.",
                               "label UID: %s\nTrack UID: %s" % (self.canvas.selectedShape.label.uid, curr_label_track_data[0][0]))
                return
            else:
                curr_track = Track(args)
                self.addTrack(curr_track)
                curr_track.append_new_label(self.canvas.selectedShape)
                label_item = HashableQTreeWidgetItem(['', self.canvas.selectedShape.label.uid, datetime.datetime.strftime(self.canvas.selectedShape.label.dt, DATETIME_HUMAN_READABLE_FORMAT_STRING)])
                self.TracksToTrackItems[curr_track].addChild(label_item)

                if curr_track.database_insert_track_info(self.tracks_db_fname):
                    self.setClean()
                else:
                    DisplayWarning('OOPS', 'Something went wrong!', 'Some of the new track data were not written to the database.\nPlease refer to the "errors.log" file and make the developer know about the error.')
                    self.setDirty()

                self.trackListWidget.resizeColumnToContents(0)
                self.trackListWidget.resizeColumnToContents(1)


    def addTrack(self, curr_track):
        track_item = HashableQTreeWidgetItem([curr_track.human_readable_name, curr_track.uid, ''])
        track_item.setFlags(track_item.flags() | Qt.ItemIsUserCheckable)
        track_item.setCheckState(0, Qt.Unchecked)
        # item.setBackground(generateColorByText(track.uid))
        self.trackListWidget.addTopLevelItem(track_item)
        self.tracks[curr_track.uid] = curr_track
        self.TrackItemsToTracks[track_item] = curr_track
        self.TracksToTrackItems[curr_track] = track_item

        for label in curr_track.labels:
            label_item = HashableQTreeWidgetItem(['', label['uid'], datetime.datetime.strftime(label.dt, DATETIME_HUMAN_READABLE_FORMAT_STRING)])
            # label_item.setBackground(generateColorByText(curr_track.uid))
            track_item.addChild(label_item)
        track_item.setExpanded(True)
        self.trackListWidget.resizeColumnToContents(0)
        self.trackListWidget.resizeColumnToContents(1)


    def continueExistingTrack(self):
        if self.canvas.selectedShape:
            curr_label_track_data = DatabaseOps.read_tracks_by_label_uids(self.tracks_db_fname, self.queries_collection, [self.canvas.selectedShape.label.uid])
            if len(curr_label_track_data) > 0:
                # there is a track which this label belongs to
                DisplayWarning("SORRY, we cannot do this.",
                               "WARNING! There is already a track which this label belongs to.\nOne cannot assign a label to more than one track.",
                               "label UID: %s\nTrack UID: %s" % (self.canvas.selectedShape.label.uid, curr_label_track_data[0][0]))

                return
            else:
                tracks_items = [{'uid': uid, 'track': self.tracks[uid], 'hr_name': self.TracksToTrackItems[self.tracks[uid]].text(0)} for uid in self.tracks.keys()]
                # trackUIDs = [k for k in self.tracks.keys()]
                dial = TrackSelectionDialog("Select a track", "List of tracks", tracks_items, self)
                if dial.exec_() == QDialog.Accepted:
                    selected_track_item = dial.itemsSelected()[0]
                    selected_track = self.tracks[selected_track_item['uid']]
                    selected_track.append_new_label(self.canvas.selectedShape)
                    selected_track.database_update_track_info(self.tracks_db_fname)

                    label_item = HashableQTreeWidgetItem(['', self.canvas.selectedShape.label.uid, datetime.datetime.strftime(self.canvas.selectedShape.label.dt, DATETIME_HUMAN_READABLE_FORMAT_STRING)])
                    self.TracksToTrackItems[selected_track].addChild(label_item)
                self.trackListWidget.resizeColumnToContents(0)
                self.trackListWidget.resizeColumnToContents(1)


    # def createShape(self):
    #     assert self.beginner()
    #     self.canvas.setEditing(False)
    #     self.actions.create.setEnabled(False)
    #     self.app.setOverrideCursor(Qt.CrossCursor)

    def toggleDrawingSensitive(self, drawing=True):
        """In the middle of drawing, toggling between modes should be disabled."""
        self.actions.editMode.setEnabled(not drawing)
        # if not drawing and self.beginner():
            # # Cancel creation.
            # print('Cancel creation.')
            # self.canvas.setEditing(True)
            # self.canvas.restoreCursor()
            # self.actions.create.setEnabled(True)

    def toggleDrawMode(self, edit=True):
        self.canvas.setEditing(edit)
        self.actions.createMode.setEnabled(edit)
        self.actions.editMode.setEnabled(not edit)

    def setCreateMode(self):
        # assert self.advanced()
        self.toggleDrawMode(False)
        self.app.setOverrideCursor(Qt.CrossCursor)

    def setEditMode(self):
        # assert self.advanced()
        self.toggleDrawMode(True)
        self.labelSelectionChanged()

    def updateFileMenu(self):
        currFilePath = self.filePath

        def exists(filename):
            return os.path.exists(filename)
        menu = self.menus.recentFiles
        menu.clear()
        files = [f for f in self.recentFiles if f !=
                 currFilePath and exists(f)]
        for i, f in enumerate(files):
            icon = newIcon('labels')
            action = QAction(
                icon, '&%d %s' % (i + 1, QFileInfo(f).fileName()), self)
            # action.triggered.connect(partial(self.loadRecent, f))
            menu.addAction(action)

    def popLabelListMenu(self, point):
        self.menus.labelList.exec_(self.labelList.mapToGlobal(point))

    def editLabel(self):
        if not self.canvas.editing():
            return
        item = self.currentItem()
        text = self.labelDialog.popUp(item.text(0))
        if text is not None:
            item.setText(0, text)
            item.setRowBackground(generateColorByText(text))
            self.setDirty()



    def fileitemDoubleClicked(self, item=None):
        selected_str = ustr(item.text())
        if args.labels_type == 'MCS':
            pattern = r'(\d{4})-(\d{2})-(\d{2}) (\d{2}):(\d{2}):(\d{2}) \| (MSG\d) \| uuid:(.+) \|.+\.nc'
            uuid_group_No = 7
        elif args.labels_type in ['PL', 'MC']:
            pattern = r'(\d{4})-(\d{2})-(\d{2}) (\d{2}):(\d{2}):(\d{2}) \| uuid:(.+) \|.+\.nc'
            uuid_group_No = 6
        elif args.labels_type == 'AMRC':
            pattern = r'(\d{4})-(\d{2})-(\d{2}) (\d{2}):(\d{2}):(\d{2}) \| uuid:(.+) \|.+\.nc'
            uuid_group_No = 6
        elif args.labels_type == 'CS':
            pattern = r'(\d{4})-(\d{2})-(\d{2}) (\d{2}):(\d{2}):(\d{2}) \| uuid:(.+)'
            uuid_group_No = 6

        m = re.match(pattern, selected_str)
        if m is not None:
            curr_uuid = m.groups()[uuid_group_No]
            item.setSelected(True)
            self.loadFile(curr_uuid)


    def btnstate(self, item= None):
        """ Function to handle difficult examples
        Update on each object """
        if not self.canvas.editing():
            return

        item = self.currentItem()
        if not item: # If not selected Item, take the first one
            item = self.labelList.item(self.labelList.count()-1)

        # difficult = self.diffcButton.isChecked()

        try:
            shape = self.itemsToShapes[item]
        except:
            pass
        # Checked and Update
        try:
            self.canvas.setShapeVisible(shape, item.checkState() == Qt.Checked)
        except:
            pass


    # React to canvas signals.
    def shapeSelectionChanged(self, selected=False):
        if self._noSelectionSlot:
            self._noSelectionSlot = False
        else:
            shape = self.canvas.selectedShape
            if shape:
                if shape in self.shapesToItems:
                    self.shapesToItems[shape].setSelected(True)
                elif shape in self.ghosts_shapesToItems:
                    self.ghosts_shapesToItems[shape].setSelected(True)
            else:
                self.labelList.clearSelection()
        self.actions.delete.setEnabled(selected)
        # self.actions.copy.setEnabled(selected)
        self.actions.edit.setEnabled(selected)
        self.actions.shapeLineColor.setEnabled(selected)
        self.actions.shapeFillColor.setEnabled(selected)



    def addLabel(self, shape):
        shape.paintLabel = self.paintLabelsOption.isChecked()
        item = HashableQTreeWidgetItem(self.labelList, [shape.label.name, shape.label.uid, datetime.datetime.strftime(shape.label.dt, DATETIME_HUMAN_READABLE_FORMAT_STRING)])
        self.itemsToShapes[item] = shape
        self.shapesToItems[shape] = item
        item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
        item.setCheckState(0, Qt.Checked)
        item.setRowBackground(generateColorByText(shape.label.name))
        self.labelList.addTopLevelItem(item)
        for action in self.actions.onShapesPresent:
            action.setEnabled(True)
        self.labelList.resizeColumnToContents(0)
        self.labelList.resizeColumnToContents(1)


    def remLabel(self, shape):
        if shape is None:
            return
        if shape in self.shapesToItems:
            item = self.shapesToItems[shape]
            # self.labelList.takeItem(self.labelList.row(item))
            self.labelList.takeTopLevelItem(self.labelList.indexOfTopLevelItem(item))
            del self.shapesToItems[shape]
            del self.itemsToShapes[item]
        elif shape in self.ghosts_shapesToItems:
            item = self.ghosts_shapesToItems[shape]
            del self.ghosts_shapesToItems[shape]
            del self.ghosts_itemsToShapes[item]



    def loadLabels(self, labels):
        s = []

        # for label, points, latlonPoints, line_color, fill_color, isEllipse in shapes:
        for label in labels:
            shape = Shape(label=label, parent_canvas=self.canvas)

            # for (x, y),(lon,lat) in zip(latlonPoints):
            for (pt_name, pt_latlon) in sorted(label.pts.items(), key=lambda x: x[0]):
                # x_pic,y_pic = self.canvas.transformLatLonToPixmapCoordinates(pt_latlon['lon'], pt_latlon['lat'])
                x_pic, y_pic = self.basemaphelper.latlon2xy(pt_latlon['lat'], pt_latlon['lon'])
                shape.addPoint(QPointF(x_pic, y_pic), QPointF(pt_latlon['lon'], pt_latlon['lat']))
            shape.close()
            s.append(shape)

            self.addLabel(shape)

        self.canvas.loadShapes(s)

        self.loadTracks()

        return


    def loadPredictedLabels(self, srvLabels):
        s = []

        if len(srvLabels) == 0:
            return

        # for label, points, latlonPoints, line_color, fill_color, isEllipse in shapes:
        for label_class,labels_of_class  in srvLabels.items():
            if labels_of_class is None:
                continue
            for label in labels_of_class:
                mcs = self.label_class.LabelFrom_srvLabel(label)
                shape = Shape(label=mcs, parent_canvas=self.canvas)

                for (pt_name, pt_latlon) in sorted(mcs.pts.items(), key=lambda x: x[0]):
                    # x_pic,y_pic = self.canvas.transformLatLonToPixmapCoordinates(pt_latlon['lon'], pt_latlon['lat'])
                    x_pic, y_pic = self.basemaphelper.latlon2xy(pt_latlon['lat'], pt_latlon['lon'])
                    shape.addPoint(QPointF(x_pic, y_pic), QPointF(pt_latlon['lon'], pt_latlon['lat']))
                shape.close()
                s.append(shape)

                self.addLabel(shape)

        if len(s) > 0:
            self.canvas.loadShapes(s, extend=True)


    def loadTracks(self):
        if (args.labels_type == 'MCS'):
            time_tolerance_minutes = 30
        elif (args.labels_type in ['MC', 'PL']):
            time_tolerance_minutes = 3*60+1
        elif (args.labels_type == 'AMRC'):
            time_tolerance_minutes = 3 * 60 + 1
        elif (args.labels_type == 'CS'):
            time_tolerance_minutes = 3*60+1

        tracks_from_db = DatabaseOps.read_tracks_by_datetime(self.tracks_db_fname, self.curr_dt, self.queries_collection, time_tol_minutes = time_tolerance_minutes)
        if tracks_from_db and len(tracks_from_db) > 0:
            columns = ['track_uid', 'track_human_readable_name', 'label_id', 'label_uid', 'label_dt', 'label_name']
            for i in range(self.shapes_points_count):
                columns = columns + ['lon%d'%i, 'lat%d'%i]
            columns = columns + ['sourcedata_fname']
            tracks_df = pd.DataFrame(np.array(tracks_from_db), columns=columns)
            tracks_df['label_dt'] = pd.to_datetime(tracks_df['label_dt'])
            track_uids = tracks_df['track_uid'].unique()
            for track_uid in track_uids:
                if track_uid not in self.tracks.keys():
                    track_human_readable_name = np.array(tracks_df[tracks_df['track_uid'] == track_uid]['track_human_readable_name'])[0]
                    curr_track = Track(args, {'uid': track_uid, 'human_readable_name': track_human_readable_name})
                    track_labels = tracks_df[tracks_df['track_uid'] == track_uid]
                    for idx, track_label_row in track_labels.iterrows():
                        curr_track.append_new_label(self.label_class.from_db_row_dict(track_label_row.to_dict()))

                    track_item = HashableQTreeWidgetItem([curr_track.human_readable_name, curr_track.uid, ''])
                    track_item.setFlags(track_item.flags() | Qt.ItemIsUserCheckable)
                    track_item.setCheckState(0, Qt.Unchecked)
                    track_item.setRowBackground(generateColorByText(curr_track.uid))
                    self.trackListWidget.addTopLevelItem(track_item)
                    self.tracks[curr_track.uid] = curr_track
                    self.TrackItemsToTracks[track_item] = curr_track
                    self.TracksToTrackItems[curr_track] = track_item

                    for label in curr_track.labels:
                        label_item = HashableQTreeWidgetItem(['', label.uid, datetime.datetime.strftime(label.dt, DATETIME_HUMAN_READABLE_FORMAT_STRING)])
                        label_item.setRowBackground(generateColorByText(curr_track.uid))
                        track_item.addChild(label_item)
                    track_item.setExpanded(True)
            self.trackListWidget.resizeColumnToContents(0)
            self.trackListWidget.resizeColumnToContents(1)
        return


    def saveLabels(self):
        try:
            for shape in self.canvas.shapes:
                curr_label = shape.label
                if DatabaseOps.insert_label_data(self.tracks_db_fname, curr_label, self.queries_collection):
                    self.setClean()
                else:
                    DisplayWarning('OOPS', 'Something went wrong!', 'Some of labels were not written to the database.\nPlease refer to the "errors.log" file and make the developer know about the error.')
            return True
        except Exception as ex:
            ReportException('./logs/errors.log', ex)
            return False



    def labelSelectionChanged(self):
        item = self.currentItem()
        if item and self.canvas.editing():
            self._noSelectionSlot = True
            self.canvas.selectShape(self.itemsToShapes[item])
            shape = self.itemsToShapes[item]
            label = shape.label

            tree_items = get_all_items(self.trackListWidget)
            tree_items = [{'item': ti, 'uid': ti.text(1)} for ti in tree_items]

            for track_item in tree_items:
                track_item['item'].setSelected(False)

            found_items = [tree_items[i] for i in [i for i in np.where(np.array([ti['uid'] for ti in tree_items]) == label.uid)[0]]]
            if found_items:
                for found_item in found_items:
                    found_item['item'].setSelected(True)



    def labelItemChanged(self, item):
        shape = self.itemsToShapes[item]
        shape_name = item.text(0)
        if shape.label.name != shape_name:
            shape.label.name = shape_name
            shape.line_color = generateColorByText(shape.label.name)
            self.setDirty()
            res = DatabaseOps.update_label(self.tracks_db_fname, shape.label, self.queries_collection)
            if res:
                self.setClean()
            else:
                DisplayWarning('OOPS', 'Something went wrong!',
                               'The label updates were not written to the database for some reason.\nPlease refer to the "errors.log" file and make the developer know about the error.')
        else:  # User probably changed item visibility
            self.canvas.setShapeVisible(shape, item.checkState(0) == Qt.Checked)



    def trackItemChanged(self, curr_item):
        # load all the shapes of the track
        if (not curr_item.parent()):
            if curr_item.checkState(0) == Qt.Checked:
                self.temporary_shapes = []
    
                # for track_item in get_all_toplevel_items(self.trackListWidget):
                #     if track_item != curr_item:
                #         track_item.setCheckState(0, Qt.Unchecked)
                curr_track = self.TrackItemsToTracks[curr_item]
                track_labels_data = DatabaseOps.read_track_labels_by_track_uid(self.tracks_db_fname, curr_track.uid, self.queries_collection)

                columns = ['label_id', 'label_uid', 'label_dt', 'label_name']
                for i in range(self.shapes_points_count):
                    columns = columns + ['lon%d' % i, 'lat%d' % i]
                columns = columns + ['sourcedata_fname']

                track_labels_df = pd.DataFrame(np.array(track_labels_data), columns=columns)
                track_labels_df['label_dt'] = pd.to_datetime(track_labels_df['label_dt'])
                track_labels_df.sort_values(by = 'label_dt', inplace=True)
                self.curr_track_shapes = []
                for idx,label_row in track_labels_df.iterrows():
                    curr_label = self.label_class.from_db_row_dict(label_row.to_dict())
                    shape = Shape(label=curr_label, parent_canvas=self.canvas)
                    for (pt_name, pt_latlon) in sorted(curr_label.pts.items(), key=lambda x: x[0]):
                        # x_pic, y_pic = self.canvas.transformLatLonToPixmapCoordinates(pt_latlon['lon'], pt_latlon['lat'])
                        x_pic, y_pic = self.basemaphelper.latlon2xy(pt_latlon['lat'], pt_latlon['lon'])
                        shape.addPoint(QPointF(x_pic, y_pic), QPointF(pt_latlon['lon'], pt_latlon['lat']))
                    shape.close()
                    self.temporary_shapes.append(shape)
    
                self.canvas.shapes.extend(self.temporary_shapes)
                self.canvas.current = None
                self.canvas.repaint()
            else:
                # remove all temporary shapes from canvas
                for tmp_shape in self.temporary_shapes:
                    self.canvas.shapes.remove(tmp_shape)
                    self.canvas.current = None
                    self.canvas.repaint()
                self.temporary_shapes.clear()
                self.temporary_shapes = None



    # Callback functions:
    def newShapeCallback(self):
        """Pop-up and give focus to the label editor.
        position MUST be in global coordinates.
        """
        if not self.useDefaultLabelCheckbox.isChecked() or not self.defaultLabelTextLine.text():
            if len(self.labelHist) > 0:
                self.labelDialog = LabelDialog(
                    parent=self, listItem=self.labelHist)

            # Sync single class mode from PR#106
            if self.singleClassMode.isChecked() and self.lastLabel:
                text = self.lastLabel
            else:
                text = self.labelDialog.popUp(text=self.prevLabelText)
                self.lastLabel = text
        else:
            text = self.defaultLabelTextLine.text()

        # Add Chris
        # self.diffcButton.setChecked(False)
        if text is not None:
            self.prevLabelText = text
            generate_color = generateColorByText(text)
            shape = self.canvas.setLastLabel(text, generate_color, generate_color)
            self.addLabel(shape)
            # if self.beginner():  # Switch to edit mode.
            #     self.canvas.setEditing(True)
            #     self.actions.create.setEnabled(True)
            # else:
            self.canvas.setEditing(True)
            self.actions.editMode.setEnabled(True)
            self.setDirty()

            if text not in self.labelHist:
                self.labelHist.append(text)
        else:
            # self.canvas.undoLastLine()
            self.canvas.resetAllLines()

        # MK: set latlon points of the new shape to pts of the label of this shape
        new_shape = self.canvas.shapes[-1]
        pts = {}
        for i in range(new_shape.shapes_points_count):
            lon = new_shape.latlonPoints[i].x()
            lat = new_shape.latlonPoints[i].y()
            pt = {'lat': lat, 'lon': lon}
            pts['pt%d'%i] = pt
        new_shape.label.pts = pts

        new_shape.label.sourcedata_fname = os.path.basename(self.filePath)
        if DatabaseOps.insert_label_data(self.tracks_db_fname, new_shape.label, self.queries_collection):
            self.setClean()
        else:
            DisplayWarning('OOPS', 'Something went wrong!',
                           'The new label was not written to the database for some reason.\nPlease refer to the "errors.log" file and make the developer know about the error.')



    def ShapeModifiedCallback(self):
        self.setDirty()
        selected_shape = self.canvas.selectedShape
        pts = {}
        for i in range(selected_shape.shapes_points_count):
            lon = selected_shape.latlonPoints[i].x()
            lat = selected_shape.latlonPoints[i].y()
            pt = {'lat': lat, 'lon': lon}
            pts['pt%d'%i] = pt
        selected_shape.label.pts = pts
        selected_shape.label.sourcedata_fname = os.path.basename(self.filePath)
        self.setDirty()
        res = DatabaseOps.update_label(self.tracks_db_fname, selected_shape.label, self.queries_collection)
        if not res:
            print('WARNING! the label was not updated in the database. Please refer to the errors.log file for details.')
        else:
            self.setClean()


    def scrollRequestCallback(self, delta, orientation):
        units = - delta / (8 * 15)
        bar = self.scrollBars[orientation]
        bar.setValue(bar.value() + bar.singleStep() * units)




    def setZoom(self, value):
        self.actions.fitWidth.setChecked(False)
        self.actions.fitWindow.setChecked(False)
        self.zoomMode = self.MANUAL_ZOOM
        self.zoomWidget.setValue(value)

    def addZoom(self, increment=10):
        self.setZoom(self.zoomWidget.value() + increment)

    def zoomRequestCallback(self, delta):
        # get the current scrollbar positions
        # calculate the percentages ~ coordinates
        h_bar = self.scrollBars[Qt.Horizontal]
        v_bar = self.scrollBars[Qt.Vertical]

        # get the current maximum, to know the difference after zooming
        h_bar_max = h_bar.maximum()
        v_bar_max = v_bar.maximum()

        # get the cursor position and canvas size
        # calculate the desired movement from 0 to 1
        # where 0 = move left
        #       1 = move right
        # up and down analogous
        cursor = QCursor()
        pos = cursor.pos()
        relative_pos = QWidget.mapFromGlobal(self, pos)

        cursor_x = relative_pos.x()
        cursor_y = relative_pos.y()

        w = self.scrollArea.width()
        h = self.scrollArea.height()

        # the scaling from 0 to 1 has some padding
        # you don't have to hit the very leftmost pixel for a maximum-left movement
        margin = 0.1
        move_x = (cursor_x - margin * w) / (w - 2 * margin * w)
        move_y = (cursor_y - margin * h) / (h - 2 * margin * h)

        # clamp the values from 0 to 1
        move_x = min(max(move_x, 0), 1)
        move_y = min(max(move_y, 0), 1)

        # zoom in
        units = delta / (8 * 15)
        scale = 10
        self.addZoom(scale * units)

        # get the difference in scrollbar values
        # this is how far we can move
        d_h_bar_max = h_bar.maximum() - h_bar_max
        d_v_bar_max = v_bar.maximum() - v_bar_max

        # get the new scrollbar values
        new_h_bar_value = h_bar.value() + move_x * d_h_bar_max
        new_v_bar_value = v_bar.value() + move_y * d_v_bar_max

        h_bar.setValue(new_h_bar_value)
        v_bar.setValue(new_v_bar_value)

    def setFitWindow(self, value=True):
        if value:
            self.actions.fitWidth.setChecked(False)
        self.zoomMode = self.FIT_WINDOW if value else self.MANUAL_ZOOM
        self.adjustScale()

    def setFitWidth(self, value=True):
        if value:
            self.actions.fitWindow.setChecked(False)
        self.zoomMode = self.FIT_WIDTH if value else self.MANUAL_ZOOM
        self.adjustScale()

    def switchChannel(self):
        newChannel = self.basemaphelper.cycleChannel(perform=True)
        self.status('channel switched to %s' % newChannel)
        self.actions.switchDataChannel.setChecked(False)
        self.actions.switchDataChannel.setText(self.basemaphelper.channelsDescriptions[self.basemaphelper.currentChannel])

        self.imageData = self.basemaphelper.CVimageCombined
        self.imageData = cv2.cvtColor(self.imageData, cv2.COLOR_BGR2RGB)

        height, width, channel = self.basemaphelper.CVimageCombined.shape
        bytesPerLine = 3 * width

        image = QImage(self.imageData, width, height, bytesPerLine, QImage.Format_RGB888)

        self.image = image
        self.canvas.loadPixmap(QPixmap.fromImage(image), clearShapes=False)

    def refreshBasemapHires(self):
        self.refreshBasemap(hires=True)




    def refreshBasemap(self, hires = False):
        self.labelList.clear()

        self.actions.refreshBasemap.setChecked(False)
        self.actions.zoomHires.setChecked(False)
        scale1 = 1.0/self.canvas.scale

        if scale1 > 1.0:
            # zoom out
            vp_size = self.scrollArea.viewport().size()
            CanvasChildren = self.scrollArea.viewport().children()[0]
            CanvasChidrenRect = self.scrollArea.viewport().childrenRect()
            s1 = 0.5 * (self.canvas.pixmap.size() - scale1 * vp_size)
            vp_pos_at_pixmap = QPoint(s1.width(), s1.height())
            # vp_pos_at_pixmap = vp_pos_at_childrenRect * scale1
            vp_size_pixmap_units = vp_size * scale1
            # self.labelCoordinates.setText('vp_pos_pixmap: %g,%g; vp_size_pixmap_units: %g,%g' % (vp_pos_at_pixmap.x(), vp_pos_at_pixmap.y(), vp_size_pixmap_units.width(), vp_size_pixmap_units.height()))
            llcrnrPt = QPointF(vp_pos_at_pixmap.x(), vp_pos_at_pixmap.y() + vp_size_pixmap_units.height())
            urcrnrPt = QPointF(vp_pos_at_pixmap.x() + vp_size_pixmap_units.width(), vp_pos_at_pixmap.y())
            # llcrnrlat, llcrnrlon = self.canvas.transformToLatLon(llcrnrPt)
            llcrnrlon, llcrnrlat = self.basemaphelper.xy2latlon(llcrnrPt.x(), llcrnrPt.y())
            llcrnrlat = min([llcrnrlat, 87.])
            llcrnrlat = max([llcrnrlat, -87.])
            llcrnrlon = min([llcrnrlon, 180.])
            llcrnrlon = max([llcrnrlon, -180.])
            # urcrnrlat, urcrnrlon = self.canvas.transformToLatLon(urcrnrPt)
            urcrnrlon, urcrnrlat = self.basemaphelper.xy2latlon(urcrnrPt.x(), urcrnrPt.y())
            urcrnrlat = min([urcrnrlat, 87.])
            urcrnrlat = max([urcrnrlat, -87.])
            urcrnrlon = min([urcrnrlon, 180.])
            urcrnrlon = max([urcrnrlon, -180.])

        else:
            #zoom in
            vp_size = self.scrollArea.viewport().size()
            CanvasChildren = self.scrollArea.viewport().children()[0]
            CanvasChidrenRect = self.scrollArea.viewport().childrenRect()
            vp_pos_at_childrenRect = QPoint(-CanvasChidrenRect.x(), -CanvasChidrenRect.y())
            vp_pos_at_pixmap = vp_pos_at_childrenRect * scale1
            vp_size_pixmap_units = vp_size * scale1
            # self.labelCoordinates.setText('vp_pos_pixmap: %g,%g; vp_size_pixmap_units: %g,%g' % (vp_pos_at_pixmap.x(), vp_pos_at_pixmap.y(), vp_size_pixmap_units.width(), vp_size_pixmap_units.height()))
            llcrnrPt = QPointF(vp_pos_at_pixmap.x(), vp_pos_at_pixmap.y()+vp_size_pixmap_units.height())
            urcrnrPt = QPointF(vp_pos_at_pixmap.x() + vp_size_pixmap_units.width(), vp_pos_at_pixmap.y())
            # llcrnrlat,llcrnrlon = self.canvas.transformToLatLon(llcrnrPt)
            # urcrnrlat, urcrnrlon = self.canvas.transformToLatLon(urcrnrPt)
            llcrnrlon,llcrnrlat = self.basemaphelper.xy2latlon(llcrnrPt.x(), llcrnrPt.y())
            urcrnrlon,urcrnrlat = self.basemaphelper.xy2latlon(urcrnrPt.x(), urcrnrPt.y())

        try:
            self.basemaphelper.SetNewLatLonLimits(llcrnrlon, llcrnrlat, urcrnrlon, urcrnrlat, resolution = 'h' if hires else 'c')
        except:
            return None

        self.basemaphelper.FuseBasemapWithData()

        height, width, channel = self.basemaphelper.CVimageCombined.shape
        bytesPerLine = 3 * width

        self.imageData = self.basemaphelper.CVimageCombined
        self.imageData = cv2.cvtColor(self.imageData, cv2.COLOR_BGR2RGB)
        self.actions.switchDataChannel.setText(self.basemaphelper.channelsDescriptions[self.basemaphelper.currentChannel])
        image = QImage(self.imageData, width, height, bytesPerLine, QImage.Format_RGB888)

        self.image = image
        self.canvas.loadPixmap(QPixmap.fromImage(image))
        self.setClean()

        if self.label_types == 'MCS':
            labels_from_database = self.label_class.loadLabelsFromDatabase(self.tracks_db_fname, self.filePath)
        elif ((self.label_types == 'MC') | (self.label_types == 'PL')):
            labels_from_database = MClabel.loadLabelsFromDatabase(self.tracks_db_fname, self.filePath)
        elif (self.label_types == 'AMRC'):
            labels_from_database = MClabel.loadLabelsFromDatabase(self.tracks_db_fname, self.filePath)
        elif (self.label_types == 'CS'):
            labels_from_database = MClabel.loadLabelsFromDatabase(self.tracks_db_fname, self.filePath)

        self.loadLabels(labels_from_database)


        self.canvas.setEnabled(True)
        self.adjustScale(initial=True)
        self.paintCanvas()



    def togglePolygons(self, value):
        for item, shape in self.itemsToShapes.items():
            item.setCheckState(0, Qt.Checked if value else Qt.Unchecked)


    def loadData(self, uuid=None):
        self.resetState()
        self.canvas.setEnabled(False)
        if uuid is None:
            return

        curr_srcdata_row = self.basemaphelper.srvSourceDataList[self.basemaphelper.srvSourceDataList['uuid'] == uuid].iloc[0, :]  # supposedly it will be 1-row DataFrame

        self.currDataUUID = uuid
        self.curr_dt = curr_srcdata_row['dt']
        # self.filePath = curr_srcdata_row['full_fname']

        try:
            self.basemaphelper.SwitchSourceData(uuid)
            self.basemaphelper.FuseBasemapWithData()
        except:
            ReportException('./logs/error.log', None)
            return False

        self.imageData = self.basemaphelper.CVimageCombined
        self.imageData = cv2.cvtColor(self.imageData, cv2.COLOR_BGR2RGB)
        self.actions.switchDataChannel.setText(
            self.basemaphelper.channelsDescriptions[self.basemaphelper.currentChannel])

        height, width, channel = self.basemaphelper.CVimageCombined.shape
        bytesPerLine = 3 * width
        image = QImage(self.imageData, width, height, bytesPerLine, QImage.Format_RGB888)

        self.status("Loaded data for %s with serverside-uuid: %s" % (
        datetime.datetime.strftime(self.curr_dt, '%Y-%m-%d %H:%M:%S'), uuid))
        self.image = image
        # self.filePath = unicodeFilePath
        self.canvas.loadPixmap(QPixmap.fromImage(image))

        self.setClean()
        self.canvas.setEnabled(True)
        self.adjustScale(initial=True)
        self.paintCanvas()
        # self.addRecentFile(self.filePath)
        self.toggleActions(True)

        self.actions.refreshBasemap.setEnabled(True)
        self.actions.zoomHires.setEnabled(True)
        self.actions.switchDataChannel.setEnabled(True)

        if args.labels_type in ['MCS', 'MC', 'PL', 'AMRC']:
            labels_from_database = self.label_class.loadLabelsFromDatabase(self.tracks_db_fname,
                                                                           os.path.basename(self.filePath))
        elif args.labels_type in ['CS']:
            labels_from_database = self.label_class.loadLabelsFromDatabase(self.tracks_db_fname,
                                                                           self.curr_dt)
        self.loadLabels(labels_from_database)

        if self.settings.get(SETTING_DETECTION_USE_NEURAL_ASSISTANCE):
            labels_cnn_predicted = self.basemaphelper.RequestPredictedMCSlabels()
            if labels_cnn_predicted is not None:
                self.loadPredictedLabels(labels_cnn_predicted)

        self.setWindowTitle(
            __appname__ + ' ' + "%s :uuid: %s" % (datetime.datetime.strftime(self.curr_dt, '%Y-%m-%d %H:%M:%S'), uuid))

        # Default : select last item if there is at least one item
        if self.labelList.topLevelItemCount():
            self.labelList.setCurrentItem(self.labelList.topLevelItem(self.labelList.topLevelItemCount() - 1))
            self.labelList.topLevelItem(self.labelList.topLevelItemCount() - 1).setSelected(True)

        self.canvas.setFocus(True)
        return True


    def loadFile(self, uuid=None):
        self.resetState()
        self.canvas.setEnabled(False)
        if uuid is None:
            return

        curr_srcdata_row = self.basemaphelper.srvSourceDataList[self.basemaphelper.srvSourceDataList['uuid'] == uuid].iloc[0,:]  # supposedly it will be 1-row DataFrame

        self.currDataUUID = uuid
        self.curr_dt = curr_srcdata_row['dt']
        self.filePath = curr_srcdata_row['full_fname']

        try:
            self.basemaphelper.SwitchSourceData(uuid)
            self.basemaphelper.FuseBasemapWithData()
        except:
            ReportException('./logs/error.log', None)
            return False



        self.imageData = self.basemaphelper.CVimageCombined
        self.imageData = cv2.cvtColor(self.imageData, cv2.COLOR_BGR2RGB)
        self.actions.switchDataChannel.setText(self.basemaphelper.channelsDescriptions[self.basemaphelper.currentChannel])

        height, width, channel = self.basemaphelper.CVimageCombined.shape
        bytesPerLine = 3 * width
        image = QImage(self.imageData, width, height, bytesPerLine, QImage.Format_RGB888)

        self.status("Loaded data for %s with serverside-uuid: %s" % (datetime.datetime.strftime(self.curr_dt, '%Y-%m-%d %H:%M:%S'), uuid))
        self.image = image
        # self.filePath = unicodeFilePath
        self.canvas.loadPixmap(QPixmap.fromImage(image))

        self.setClean()
        self.canvas.setEnabled(True)
        self.adjustScale(initial=True)
        self.paintCanvas()
        # self.addRecentFile(self.filePath)
        self.toggleActions(True)

        self.actions.refreshBasemap.setEnabled(True)
        self.actions.zoomHires.setEnabled(True)
        self.actions.switchDataChannel.setEnabled(True)

        labels_from_database = self.label_class.loadLabelsFromDatabase(self.tracks_db_fname, os.path.basename(self.filePath))
        self.loadLabels(labels_from_database)

        if self.settings.get(SETTING_DETECTION_USE_NEURAL_ASSISTANCE):
            labels_cnn_predicted = self.basemaphelper.RequestPredictedMCSlabels()
            if labels_cnn_predicted is not None:
                self.loadPredictedLabels(labels_cnn_predicted)

        self.setWindowTitle(__appname__ + ' ' + "%s :uuid: %s" % (datetime.datetime.strftime(self.curr_dt, '%Y-%m-%d %H:%M:%S'), uuid))

        # Default : select last item if there is at least one item
        if self.labelList.topLevelItemCount():
            self.labelList.setCurrentItem(self.labelList.topLevelItem(self.labelList.topLevelItemCount()-1))
            self.labelList.topLevelItem(self.labelList.topLevelItemCount()-1).setSelected(True)

        self.canvas.setFocus(True)
        return True




    def resizeEvent(self, event):
        if self.canvas and not self.image.isNull()\
           and self.zoomMode != self.MANUAL_ZOOM:
            self.adjustScale()
        super(MainWindow, self).resizeEvent(event)

    def paintCanvas(self):
        assert not self.image.isNull(), "cannot paint null image"
        self.canvas.scale = 0.01 * self.zoomWidget.value()
        self.canvas.adjustSize()
        self.canvas.update()

    def adjustScale(self, initial=False):
        value = self.scalers[self.FIT_WINDOW if initial else self.zoomMode]()
        self.zoomWidget.setValue(int(100 * value))

    def scaleFitWindow(self):
        """Figure out the size of the pixmap in order to fit the main widget."""
        e = 2.0  # So that no scrollbars are generated.
        w1 = self.centralWidget().width() - e
        h1 = self.centralWidget().height() - e
        a1 = w1 / h1
        # Calculate a new scale value based on the pixmap's aspect ratio.
        w2 = self.canvas.pixmap.width() - 0.0
        h2 = self.canvas.pixmap.height() - 0.0
        a2 = w2 / h2
        return w1 / w2 if a2 >= a1 else h1 / h2

    def scaleFitWidth(self):
        # The epsilon does not seem to work too well here.
        w = self.centralWidget().width() - 2.0
        return w / self.canvas.pixmap.width()

    def closeEvent(self, event):
        if not self.mayContinue():
            event.ignore()

        settings = self.settings
        if self.dirname is None:
            settings[SETTING_FILENAME] = self.filePath if self.filePath else ''
        else:
            settings[SETTING_FILENAME] = ''

        settings[SETTING_WIN_SIZE] = self.size()
        settings[SETTING_WIN_POSE] = self.pos()
        settings[SETTING_WIN_STATE] = self.saveState()
        settings[SETTING_LINE_COLOR] = self.lineColor
        settings[SETTING_FILL_COLOR] = self.fillColor
        # settings[SETTING_RECENT_FILES] = self.recentFiles
        # settings[SETTING_ADVANCE_MODE] = not self._beginner

        # if self.lastOpenDir and os.path.exists(self.lastOpenDir):
        #     settings[SETTING_LAST_OPEN_DIR] = self.lastOpenDir
        # else:
        #     settings[SETTING_LAST_OPEN_DIR] = ""

        settings[SETTING_DATERANGE_START_DATE] = self.start_dt
        settings[SETTING_DATERANGE_END_DATE] = self.end_dt

        settings[SETTING_SINGLE_CLASS] = self.singleClassMode.isChecked()
        settings[SETTING_PAINT_LABEL] = self.paintLabelsOption.isChecked()
        settings[SETTING_PRESERVE_BASEMAP_CONFIG] = self.preserveBasemapConfig.isChecked()
        settings.save()
    ## User Dialogs ##




    def ListServersideDataSnapshots(self, _value=False):
        try:
            self.basemaphelper.RequestDataSnapshotsList(self.start_dt, self.end_dt)
        except:
            ReportException('./logs/error.log', None)
            return

        if self.basemaphelper.srvSourceDataList is not None:
            self.importServersideDataSnapshotsList(self.basemaphelper.srvSourceDataList)


    def startDateEdit_dateChanged(self):
        self.start_dt = datetime.datetime.combine(self.startDateEdit.date().toPyDate(), datetime.datetime.min.time())

    def endDateEdit_dateChanged(self):
        self.end_dt = datetime.datetime.combine(self.endDateEdit.date().toPyDate(), datetime.datetime.max.time())



    def importServersideDataSnapshotsList(self, srvSourceDataList):
        self.currDataUUID = ''
        self.fileListWidget.clear()
        # srvSourceDataList should be Pandas.DataFrame
        for idx,row in srvSourceDataList.iterrows():
            if args.labels_type == 'MCS':
                item_str = '%s | %s | uuid:%s | %s' % (datetime.datetime.strftime(row['dt'], '%Y-%m-%d %H:%M:%S'), row['MSG_label'], row['uuid'], os.path.basename(row['full_fname']))
            elif args.labels_type in ['PL', 'MC']:
                item_str = '%s | uuid:%s | %s' % (datetime.datetime.strftime(row['dt'], '%Y-%m-%d %H:%M:%S'), row['uuid'], os.path.basename(row['full_fname']))
            elif args.labels_type == 'AMRC':
                item_str = '%s | uuid:%s | %s' % (datetime.datetime.strftime(row['dt'], '%Y-%m-%d %H:%M:%S'), row['uuid'], os.path.basename(row['full_fname']))
            if args.labels_type == 'CS':
                item_str = '%s | uuid:%s' % (datetime.datetime.strftime(row['dt'], '%Y-%m-%d %H:%M:%S'), row['uuid'])
            item = QListWidgetItem(item_str)
            self.fileListWidget.addItem(item)



    def openPrevImg(self, _value=False):
        if not self.mayContinue():
            return

        if self.fileListWidget.count() <= 0:
            return

        currRow = self.fileListWidget.currentRow()
        currItem = self.fileListWidget.currentItem()

        if not currItem:
            self.fileListWidget.setCurrentItem(self.fileListWidget.item(self.fileListWidget.count()-2))
        elif currRow == 0:
            return
        else:
            self.fileListWidget.setCurrentRow(currRow - 1)

        self.fileitemDoubleClicked(self.fileListWidget.currentItem())


    def openNextImg(self, _value=False):
        if not self.mayContinue():
            return

        if self.fileListWidget.count() <= 0:
            return

        currRow = self.fileListWidget.currentRow()
        currItem = self.fileListWidget.currentItem()

        if not currItem:
            self.fileListWidget.setCurrentItem(self.fileListWidget.item(0))
        elif currRow == self.fileListWidget.count()-1:
            return
        else:
            self.fileListWidget.setCurrentRow(currRow + 1)

        self.fileitemDoubleClicked(self.fileListWidget.currentItem())



    def closing(self):
        if self.basemaphelper is not None:
            try:
                self.basemaphelper.send_close_signal()
            except:
                pass
        self.close()


    def openFile(self, _value=False):
        if not self.mayContinue():
            return
        path = os.path.dirname(ustr(self.filePath)) if self.filePath else '.'
        formats = ['*.nc']
        filters = "NetCDF files %s" % ' '.join(formats)
        filename = QFileDialog.getOpenFileName(self, '%s - Choose Image or Label file' % __appname__, path, filters)
        if filename:
            if isinstance(filename, (tuple, list)):
                filename = filename[0]
            self.loadFile(filename)



    def closeFile(self, _value=False):
        if not self.mayContinue():
            return
        self.resetState()
        self.setClean()
        self.toggleActions(False)
        self.canvas.setEnabled(False)



    def resetAll(self):
        self.settings.reset()
        self.close()
        proc = QProcess()
        proc.startDetached(os.path.abspath(__file__))


    def mayContinue(self):
        return not (self.dirty and not self.discardChangesDialog())


    def discardChangesDialog(self):
        yes, no = QMessageBox.Yes, QMessageBox.No
        msg = u'You have unsaved changes, proceed anyway?'
        return yes == QMessageBox.warning(self, u'Attention', msg, yes | no)


    def errorMessage(self, title, message):
        return QMessageBox.critical(self, title,
                                    '<p><b>%s</b></p>%s' % (title, message))


    def currentPath(self):
        return os.path.dirname(self.filePath) if self.filePath else '.'


    def chooseColor1(self):
        color = self.colorDialog.getColor(self.lineColor, u'Choose line color',
                                          default=DEFAULT_LINE_COLOR)
        if color:
            self.lineColor = color
            Shape.line_color = color
            self.canvas.setDrawingColor(color)
            self.canvas.update()
            self.setDirty()


    def deleteSelectedShape(self):
        shape_to_delete = self.canvas.deleteSelected()
        self.remLabel(shape_to_delete)
        self.setDirty()
        res = DatabaseOps.remove_label(self.tracks_db_fname, shape_to_delete.label.uid, self.queries_collection)
        if not res:
            print('WARNING! the label was not removed from database. Please refer to the errors.log file for details.')
        else:
            self.setClean()
            self.tracks.clear()
            self.TrackItemsToTracks.clear()
            self.TracksToTrackItems.clear()
            self.trackListWidget.clear()
            self.loadTracks()
        if self.noShapes():
            for action in self.actions.onShapesPresent:
                action.setEnabled(False)


    def chshapeLineColor(self):
        color = self.colorDialog.getColor(self.lineColor, u'Choose line color',
                                          default=DEFAULT_LINE_COLOR)
        if color:
            self.canvas.selectedShape.line_color = color
            self.canvas.update()
            self.setDirty()


    def chshapeFillColor(self):
        color = self.colorDialog.getColor(self.fillColor, u'Choose fill color',
                                          default=DEFAULT_FILL_COLOR)
        if color:
            self.canvas.selectedShape.fill_color = color
            self.canvas.update()
            self.setDirty()


    def moveShape(self):
        self.canvas.endMove()
        self.setDirty()


    def loadPredefinedClasses(self, predefClassesFile):
        if os.path.exists(predefClassesFile) is True:
            with codecs.open(predefClassesFile, 'r', 'utf8') as f:
                for line in f:
                    line = line.strip()
                    if self.labelHist is None:
                        self.labelHist = [line]
                    else:
                        self.labelHist.append(line)


    def togglePaintLabelsOption(self):
        paintLabelsOptionChecked = self.paintLabelsOption.isChecked()
        for shape in self.canvas.shapes:
            shape.paintLabel = paintLabelsOptionChecked





def inverted(color):
    return QColor(*[255 - v for v in color.getRgb()])




def get_main_app(argv=[]):
    app = QApplication(argv)
    app.setApplicationName(__appname__)
    app.setWindowIcon(newIcon("app"))
    win = MainWindow(None, os.path.join(os.path.dirname(sys.argv[0]), 'data', 'predefined_classes.txt'))
    win.app = app

    win.show()
    return app, win


def main():
    '''construct main app and run it'''
    app, _win = get_main_app(sys.argv)
    return app.exec_()


if __name__ == '__main__':
    sys.exit(main())
