try:
    from PyQt5.QtGui import *
    from PyQt5.QtCore import *
    from PyQt5.QtWidgets import *
except ImportError:
    # needed for py3+qt4
    # Ref:
    # http://pyqt.sourceforge.net/Docs/PyQt4/incompatible_apis.html
    # http://stackoverflow.com/questions/21217399/pyqt4-qtcore-qvariant-object-instead-of-a-string
    if sys.version_info.major >= 3:
        import sip
        sip.setapi('QVariant', 2)
    from PyQt4.QtGui import *
    from PyQt4.QtCore import *


def DisplayWarning(short_text='', long_text='', explanation='', type=QMessageBox.Warning):
    msg = QMessageBox()
    msg.setIcon(type)
    msg.setText(short_text)
    msg.setInformativeText(long_text)
    msg.setWindowTitle("WARNING")
    msg.setDetailedText(explanation)
    msg.setStandardButtons(QMessageBox.Ok)
    retval = msg.exec_()