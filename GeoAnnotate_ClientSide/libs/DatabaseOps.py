import sqlite3
from .SQLite_queries import *
from .ServiceDefs import ReportException
from datetime import datetime, timedelta

class DatabaseOps():
    @classmethod
    def test_db_connection(cls, fname, queries_collection):
        try:
            with sqlite3.connect(fname) as conn:
                c = conn.cursor()
                c.execute(queries_collection.TEST_SQLITE_DB_CONNECTION_QUERY_TEXT)
                res = c.fetchall()
            return True
        except Exception as ex:
            ReportException('./errors.log', ex)
            return False


    @classmethod
    def create_tracks_db(cls, fname, queries_collection):
        try:
            with sqlite3.connect(fname) as conn:
                c = conn.cursor()
                c.execute(queries_collection.CREATE_TRACKS_TABLE_QUERY_TEXT)
                c.execute(queries_collection.CREATE_LABELS_TABLE_QUERY_TEXT)
                c.execute(queries_collection.CREATE_TRACK_LABELS_QUERY_TEXT)
                conn.commit()
            return True
        except Exception as ex:
            ReportException('./errors.log', ex)
            print("Tracks database was not created.")
            return False





    @classmethod
    def read_tracks_by_label_uids(cls, db_fname, queries_collection, labels_uids):
        labels_uid_list = ",".join(['\"' + uid + '\"' for uid in labels_uids])
        sqlite_query = queries_collection.SELECT_TRACKS_BY_LABEL_UIDS_QUERY_TEXT % labels_uid_list
        try:
            with sqlite3.connect(db_fname) as conn:
                c = conn.cursor()
                q_result = c.execute(sqlite_query)
                res_data = c.fetchall()
            return res_data
        except Exception as ex:
            ReportException('./errors.log', ex, sqlite_query=sqlite_query)
            return None


    @classmethod
    def read_tracks_by_datetime(cls, db_fname, dt, queries_collection):
        dt_start = dt + timedelta(minutes=-30)
        dt_end = dt + timedelta(minutes=30)
        sqlite_query = queries_collection.SELECT_TRACKS_BY_DATETIME_RANGE_QUERY_TEXT % (datetime.strftime(dt_start, DATETIME_FORMAT_STRING),
                                                                                        datetime.strftime(dt_end, DATETIME_FORMAT_STRING))
        try:
            with sqlite3.connect(db_fname) as conn:
                c = conn.cursor()
                q_result = c.execute(sqlite_query)
                res_data = c.fetchall()
            return res_data
        except Exception as ex:
            ReportException('./errors.log', ex, sqlite_query=sqlite_query)
            return None


    @classmethod
    def read_track_labels_by_track_uid(cls, db_fname, track_uid, queries_collection):
        sqlite_query = queries_collection.SELECT_LABELS_OF_TRACK_QUERY_TEXT % track_uid
        try:
            with sqlite3.connect(db_fname) as conn:
                c = conn.cursor()
                q_result = c.execute(sqlite_query)
                res_data = c.fetchall()
            return res_data
        except Exception as ex:
            ReportException('./errors.log', ex, sqlite_query=sqlite_query)
            return None


    @classmethod
    def read_labels_by_sourcedata_basename(cls, db_fname, sourcedata_basename, queries_collection):
        sqlite_query = queries_collection.SELECT_LABELS_BY_SOURCEDATA_BASENAME % sourcedata_basename
        try:
            with sqlite3.connect(db_fname) as conn:
                c = conn.cursor()
                q_result = c.execute(sqlite_query)
                res_data = c.fetchall()
            return res_data
        except Exception as ex:
            ReportException('./errors.log', ex, sqlite_query=sqlite_query)
            return None


    @classmethod
    def insert_label_data(cls, db_fname, label, queries_collection):
        vars = [label.uid,
                datetime.strftime(label.dt, DATETIME_FORMAT_STRING),
                label.name]
        for pt_name, pt in label.pts.items():
            vars = vars + ['%.14f' % pt['lon'], '%.14f' % pt['lat']]
        vars = vars + [label.sourcedata_fname]
        vars = tuple(vars)
        sqlite_query = queries_collection.INSERT_LABEL_QUERY_TEXT % vars

        try:
            with sqlite3.connect(db_fname) as conn:
                c = conn.cursor()
                q_result = c.execute(sqlite_query)
                rows_affected = q_result.rowcount
                conn.commit()
                return rows_affected if rows_affected>0 else True
        except Exception as ex:
            ReportException('./errors.log', ex, sqlite_query=sqlite_query)
            # raise ex
            return False
        return


    @classmethod
    def insert_track_data(cls, db_fname, track, queries_collection):
        sqlite_query = queries_collection.INSERT_TRACK_QUERY_TEXT % (track.uid, track.human_readable_name)

        try:
            with sqlite3.connect(db_fname) as conn:
                c = conn.cursor()
                q_result = c.execute(sqlite_query)
                rows_affected = q_result.rowcount
                conn.commit()
                return rows_affected if rows_affected>0 else True
        except Exception as ex:
            ReportException('./errors.log', ex, sqlite_query=sqlite_query)
            return False


    @classmethod
    def insert_track_label_entry(cls, db_fname, track, label, queries_collection):
        sqlite_query = queries_collection.INSERT_TRACK_LABEL_QUERY_TEXT % (label.uid, track.uid)
        try:
            with sqlite3.connect(db_fname) as conn:
                c = conn.cursor()
                q_result = c.execute(sqlite_query)
                rows_affected = q_result.rowcount
                conn.commit()
                return True
        except Exception as ex:
            ReportException('./errors.log', ex, sqlite_query = sqlite_query)
            return False


    @classmethod
    def remove_label(cls, db_fname, label_uid, queries_collection):
        try:
            with sqlite3.connect(db_fname, isolation_level=None) as conn:
                c = conn.cursor()
                rows_affected = 0
                for t in queries_collection.REMOVE_LABEL_QUERY_TEXTS:
                    q_result = c.execute(t % label_uid)
                    rows_affected += q_result.rowcount
                conn.commit()
                return rows_affected if rows_affected > 0 else True
        except Exception as ex:
            ReportException('./errors.log', ex)
            return False


    @classmethod
    def update_label(cls, db_fname, label, queries_collection):
        vars = [datetime.strftime(label.dt, DATETIME_FORMAT_STRING), label.name]
        for pt_name, pt in label.pts.items():
            vars = vars + ['%.14f' % pt['lon'], '%.14f' % pt['lat']]
        vars = vars + [label.uid]
        vars = tuple(vars)
        sqlite_query = queries_collection.UPDATE_LABEL_DATA_QUERY_TEXT % vars

        try:
            with sqlite3.connect(db_fname) as conn:
                c = conn.cursor()
                q_result = c.execute(sqlite_query)
                rows_affected = q_result.rowcount
                conn.commit()
                return rows_affected if rows_affected > 0 else True
        except Exception as ex:
            ReportException('./errors.log', ex, sqlite_query = sqlite_query)
            return False