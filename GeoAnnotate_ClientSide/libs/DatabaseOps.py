import sqlite3
from .SQLite_queries import *
from .ServiceDefs import ReportException
from datetime import datetime, timedelta

class DatabaseOps():
    @classmethod
    def test_db_connection(cls, fname):
        try:
            with sqlite3.connect(fname) as conn:
                c = conn.cursor()
                c.execute(TEST_SQLITE_DB_CONNECTION_QUERY_TEXT)
                res = c.fetchall()
            return True
        except Exception as ex:
            ReportException('./errors.log', ex)
            return False

    @classmethod
    def create_tracks_db(cls, fname):
        try:
            with sqlite3.connect(fname) as conn:
                c = conn.cursor()
                c.execute(CREATE_TRACKS_TABLE_QUERY_TEXT)
                c.execute(CREATE_LABELS_TABLE_QUERY_TEXT)
                c.execute(CREATE_TRACK_LABELS_QUERY_TEXT)
                conn.commit()
            return True
        except Exception as ex:
            ReportException('./errors.log', ex)
            print("Tracks database was not created.")
            return False

    @classmethod
    def read_track(cls, db_fname, track_uid):
        with sqlite3.connect() as conn:
            c = conn.cursor()
            q_result = c.execute(SELECT_TRACK_QUERY_TEXT % track_uid)
            res_data = c.fetchall()
        return res_data

    @classmethod
    def read_tracks(cls, db_fname):
        with sqlite3.connect(db_fname) as conn:
            c = conn.cursor()
            q_result = c.execute(SELECT_TRACKS_QUERY_TEXT)
            res_data = c.fetchall()
        return res_data

    @classmethod
    def read_tracks_by_labels(cls, db_fname, labels_uids):
        with sqlite3.connect(db_fname) as conn:
            c = conn.cursor()
            labels_uid_list = ",".join(['\"' + uid + '\"' for uid in labels_uids])
            q_result = c.execute(SELECT_TRACKS_BY_LABELS_QUERY_TEXT % labels_uid_list)
            res_data = c.fetchall()
        return res_data

    @classmethod
    def read_tracks_by_datetime(cls, db_fname, dt):
        with sqlite3.connect(db_fname) as conn:
            c = conn.cursor()
            dt_start = dt + timedelta(minutes=-30)
            dt_end = dt + timedelta(minutes=30)
            q_result = c.execute(SELECT_TRACKS_BY_DATETIME_RANGE_QUERY_TEXT % (datetime.strftime(dt_start, DATETIME_FORMAT_STRING),
                                                                               datetime.strftime(dt_end, DATETIME_FORMAT_STRING)))
            res_data = c.fetchall()
        return res_data

    @classmethod
    def read_track_labels_by_track_uid(cls, db_fname, track_uid):
        with sqlite3.connect(db_fname) as conn:
            c = conn.cursor()
            q_result = c.execute(SELECT_LABELS_OF_TRACK_QUERY_TEXT % track_uid)
            res_data = c.fetchall()
        return res_data


    @classmethod
    def read_labels_by_sourcedata_basename(cls, db_fname, sourcedata_basename):
        with sqlite3.connect(db_fname) as conn:
            c = conn.cursor()
            q_result = c.execute(SELECT_LABELS_BY_SOURCEDATA_BASENAME % sourcedata_basename)
            res_data = c.fetchall()
        return res_data




    @classmethod
    def insert_label_data(cls, db_fname, label):
        try:
            with sqlite3.connect(db_fname) as conn:
                c = conn.cursor()
                q_result = c.execute(INSERT_LABEL_QUERY_TEXT % (label.uid,
                                                                datetime.strftime(label.dt, DATETIME_FORMAT_STRING),
                                                                label.name,
                                                                '%.14f' % label.pts['pt0']['lon'],
                                                                '%.14f' % label.pts['pt0']['lat'],
                                                                '%.14f' % label.pts['pt1']['lon'],
                                                                '%.14f' % label.pts['pt1']['lat'],
                                                                '%.14f' % label.pts['pt2']['lon'],
                                                                '%.14f' % label.pts['pt2']['lat'],
                                                                label.sourcedata_fname))
                # res_data = c.fetchall()
                return True
        except Exception as ex:
            ReportException('./errors.log', ex)
            return False
        return


    @classmethod
    def insert_track_data(cls, db_fname, track):
        try:
            with sqlite3.connect(db_fname) as conn:
                c = conn.cursor()
                q_result = c.execute(INSERT_TRACK_QUERY_TEXT % (track.uid, track.human_readable_name))
                # res_data = c.fetchall()
                return True
        except Exception as ex:
            ReportException('./errors.log', ex)
            return False
        return


    @classmethod
    def insert_track_label_entry(cls, db_fname, track, label):
        try:
            with sqlite3.connect(db_fname) as conn:
                c = conn.cursor()
                q_result = c.execute(INSERT_TRACK_LABEL_QUERY_TEXT % (track.uid, label.uid))
                return True
        except Exception as ex:
            ReportException('./errors.log', ex)
            return False
        return
