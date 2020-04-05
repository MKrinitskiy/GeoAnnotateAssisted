try:
    from PyQt5.QtGui import *
    from PyQt5.QtCore import *
    from PyQt5.QtWidgets import *
except ImportError:
    from PyQt4.QtGui import *
    from PyQt4.QtCore import *

from .HashableQStandardItem import HashableQStandardItem


class TrackSelectionDialog(QDialog):
    def __init__(self,  title, message, tracks_items, parent=None):
        super(TrackSelectionDialog, self).__init__(parent=parent)
        form = QFormLayout(self)
        form.addRow(QLabel(message))
        self.listView = QListView(self)
        form.addRow(self.listView)
        model = QStandardItemModel(self.listView)
        self.setWindowTitle(title)

        self.items_to_tracks = {}

        # {'uid': uid,
        # 'track': self.tracks[uid],
        # 'hr_name': self.TracksToTrackItems[self.tracks[uid]].text(0)}
        for item in tracks_items:
            # create an item with a caption
            standardItem = HashableQStandardItem(item['hr_name'])
            standardItem.setCheckable(True)
            standardItem.setEditable(False)
            model.appendRow(standardItem)
            self.items_to_tracks[standardItem] = item

        model.itemChanged.connect(self.itemSelectionChanged)
        self.listView.setModel(model)

        buttonBox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, Qt.Horizontal, self)
        form.addRow(buttonBox)
        buttonBox.accepted.connect(self.accept)
        buttonBox.rejected.connect(self.reject)

    def itemsSelected(self):
        selected = []
        model = self.listView.model()
        i = 0
        while model.item(i):
            if model.item(i).checkState():
                selected.append(self.items_to_tracks[model.item(i)])
            i += 1
        return selected

    def itemSelectionChanged(self, item):
        # print('the item changed: %s' % item.text())
        model = self.listView.model()
        model.itemChanged.disconnect(self.itemSelectionChanged)
        i = 0
        while model.item(i):
            if ((model.item(i).checkState() == Qt.Checked) and (model.item(i) != item)):
                model.item(i).setCheckState(Qt.Unchecked)
            i += 1
        model.itemChanged.connect(self.itemSelectionChanged)
