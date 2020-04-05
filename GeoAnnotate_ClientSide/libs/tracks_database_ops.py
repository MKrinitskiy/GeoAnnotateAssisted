import sqlite3
from .SQLite_queries import *
from .ServiceDefs import ReportException
from datetime import datetime, timedelta


def test_db_connection(fname):
    try:
        with sqlite3.connect(fname) as conn:
            c = conn.cursor()
            c.execute(TEST_SQLITE_DB_CONNECTION_QUERY_TEXT)
            res = c.fetchall()
        return True
    except Exception as ex:
        ReportException('./errors.log', ex)
        return False


def create_tracks_db(fname):
    try:
        with sqlite3.connect(fname) as conn:
            c = conn.cursor()
            c.execute(CREATE_TRACKS_TABLE)
            c.execute(CREATE_TRACK_LABELS_TABLE)
            conn.commit()
        return True
    except:
        print("WARNING! Tracks database was not created. Tracking functions will not be available.")
        return False


def read_track(db_fname, track_uid):
    with sqlite3.connect() as conn:
        c = conn.cursor()
        q_result = c.execute(SELECT_TRACK_QUERY_TEXT % track_uid)
        res_data = c.fetchall()
    return res_data


def read_tracks(db_fname):
    with sqlite3.connect(db_fname) as conn:
        c = conn.cursor()
        q_result = c.execute(SELECT_TRACKS_QUERY_TEXT)
        res_data = c.fetchall()
    return res_data


def read_tracks_by_labels(db_fname, labels_uids):
    with sqlite3.connect(db_fname) as conn:
        c = conn.cursor()
        labels_uid_list = ",".join(['\"' + uid + '\"' for uid in labels_uids])
        q_result = c.execute(SELECT_TRACKS_BY_LABELS_QUERY_TEXT % labels_uid_list)
        res_data = c.fetchall()
    return res_data


def read_tracks_by_datetime(db_fname, dt):
    with sqlite3.connect(db_fname) as conn:
        c = conn.cursor()
        dt_start = dt + timedelta(minutes=-30)
        dt_end = dt + timedelta(minutes=30)
        q_result = c.execute(SELECT_TRACKS_BY_DATETIME_RANGE_QUERY_TEXT % (datetime.strftime(dt_start, DATETIME_FORMAT_STRING),
                                                                           datetime.strftime(dt_end, DATETIME_FORMAT_STRING)))
        res_data = c.fetchall()
    return res_data


def read_track_labels_by_track_uid(db_fname, track_uid):
    with sqlite3.connect(db_fname) as conn:
        c = conn.cursor()
        q_result = c.execute(SELECT_LABELS_OF_TRACK_QUERY_TEXT % track_uid)
        res_data = c.fetchall()
    return res_data