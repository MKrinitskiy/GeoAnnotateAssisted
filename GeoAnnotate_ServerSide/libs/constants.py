from types import SimpleNamespace

SETTING_FILENAME = 'filename'
SETTING_RECENT_FILES = 'recentFiles'
SETTING_WIN_SIZE = 'window/size'
SETTING_WIN_POSE = 'window/position'
SETTING_WIN_GEOMETRY = 'window/geometry'
SETTING_LINE_COLOR = 'line/color'
SETTING_FILL_COLOR = 'fill/color'
SETTING_ADVANCE_MODE = 'advanced'
SETTING_WIN_STATE = 'window/state'
SETTING_SAVE_DIR = 'savedir'
SETTING_PAINT_LABEL = 'paintlabel'
SETTING_LAST_OPEN_DIR = 'lastOpenDir'
SETTING_AUTO_SAVE = 'autosave'
SETTING_SINGLE_CLASS = 'singleclass'
SETTING_PRESERVE_BASEMAP_CONFIG = 'preservebasemapconfig'
FORMAT_PASCALVOC='PascalVOC'
FORMAT_YOLO='YOLO'
FORMAT_MCC='MCCxml'


norm_constants = SimpleNamespace()
norm_constants.ch5_vmin = 205.
norm_constants.ch5_vmax = 260.
norm_constants.ch5_thresh = 223.

norm_constants.ch9_vmin = 200.
# norm_constants.ch9_vmin = 220.
norm_constants.ch9_vmax = 320.
# norm_constants.ch9_thresh = 227.
norm_constants.ch9_thresh = 240.

norm_constants.btd_vmin = -80.
norm_constants.btd_vmax = 5.5
norm_constants.btd_thresh = 0.
