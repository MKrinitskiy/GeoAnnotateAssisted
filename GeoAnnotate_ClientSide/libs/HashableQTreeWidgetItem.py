from PyQt5.QtWidgets import *


class HashableQTreeWidgetItem(QTreeWidgetItem):
    def __init__(self, *args):
        super(HashableQTreeWidgetItem, self).__init__(*args)

    def __hash__(self):
        return hash(id(self))

    def setRowBackground(self, color):
        for col in range(self.columnCount()):
            self.setBackground(col, color)