from PyQt5.QtGui import *


class HashableQStandardItem(QStandardItem):
    def __init__(self, *args):
        super(HashableQStandardItem, self).__init__(*args)

    def __hash__(self):
        return hash(id(self))