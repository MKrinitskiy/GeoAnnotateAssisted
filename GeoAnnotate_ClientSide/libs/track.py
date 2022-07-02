import uuid
import sqlite3
from .SQLite_queries import *
from datetime import datetime
from .shape import Shape
from .MCSlabel import MCSlabel
from .MClabel import MClabel
from .ServiceDefs import ReportException
from .horsephrase_implementation import generate_horsephrase
from .DatabaseOps import *

class Track():
    def __init__(self, app_args, data_dict = None):
        self.app_args = app_args
        self.queries_collection = SQLite_Queries(label_types = self.app_args.labels_type)
        if data_dict is None:
            # self.uid = str(uuid.uuid4()).replace('-', '')
            self.uid = str(uuid.uuid4())
            self.human_readable_name = generate_horsephrase(2)
        else:
            for k in data_dict.keys():
                self.__dict__[k] = data_dict[k]

        self.labels = []

    def append_new_label(self, label):
        if isinstance(label, Shape):
            self.labels.append(label.label)
        elif isinstance(label, MCSlabel):
            self.labels.append(label)
        elif isinstance(label, MClabel):
            self.labels.append(label)
        elif isinstance(label, dict):
            raise NotImplementedError('Unable to parse the label data to append it to to the track')
        else:
            raise NotImplementedError('Unable to parse the label data to append it to to the track')

    def database_update_track_info(self, db_fname):
        self.database_remove_track_info(db_fname)
        self.database_insert_track_info(db_fname)

    def database_remove_track_info(self, db_fname):
        try:
            with sqlite3.connect(db_fname) as conn:
                c = conn.cursor()
                c.execute(self.queries_collection.DELETE_LABELS_OF_TRACK_QUERY_TEXT     % self.uid)
                c.execute(self.queries_collection.DELETE_TRACK_QUERY_TEXT               % self.uid)
                conn.commit()
        except Exception as ex:
            ReportException('./errors.log', ex)
            print('Failed executing sqlite query')

    def database_insert_track_info(self, db_fname):
        DatabaseOps.insert_track_data(db_fname, self, self.queries_collection)
        try:
            for curr_label in self.labels:
                DatabaseOps.insert_label_data(db_fname, curr_label, self.queries_collection)
                DatabaseOps.insert_track_label_entry(db_fname, self, curr_label, self.queries_collection)
            return True
        except Exception as ex:
            ReportException('./errors.log', ex)
            print('Failed executing sqlite query')
            return False
