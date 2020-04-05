CREATE_TRACKS_TABLE = '''CREATE TABLE tracks (id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT UNIQUE, ''' + \
                      '''                     track_uid TEXT NOT NULL UNIQUE, ''' + \
                      '''                     start_dt TEXT, ''' + \
                      '''                     end_dt TEXT, ''' + \
                      '''                     human_readable_name TEXT NOT NULL)'''

# CREATE_TRACK_LABELS_TABLE = '''CREATE TABLE track_labels (id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT UNIQUE, ''' + \
#                             '''                           label_uid TEXT NOT NULL UNIQUE, ''' + \
#                             '''                           track_id INTEGER NOT NULL, ''' + \
#                             '''                           prev_label_uid TEXT, ''' + \
#                             '''                           dt TEXT NOT NULL, ''' + \
#                             '''                           name TEXT NOT NULL, ''' + \
#                             '''                           lon0 REAL NOT NULL, ''' + \
#                             '''                           lat0 REAL NOT NULL, ''' + \
#                             '''                           lon1 REAL NOT NULL, ''' + \
#                             '''                           lat1 REAL NOT NULL, ''' + \
#                             '''                           lon2 REAL NOT NULL, ''' + \
#                             '''                           lat2 REAL NOT NULL)'''
CREATE_TRACK_LABELS_TABLE = '''CREATE TABLE track_labels (id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT UNIQUE, ''' + \
                            '''                           label_uid TEXT NOT NULL UNIQUE, ''' + \
                            '''                           track_id INTEGER NOT NULL, ''' + \
                            '''                           dt TEXT NOT NULL, ''' + \
                            '''                           name TEXT NOT NULL, ''' + \
                            '''                           lon0 REAL NOT NULL, ''' + \
                            '''                           lat0 REAL NOT NULL, ''' + \
                            '''                           lon1 REAL NOT NULL, ''' + \
                            '''                           lat1 REAL NOT NULL, ''' + \
                            '''                           lon2 REAL NOT NULL, ''' + \
                            '''                           lat2 REAL NOT NULL)'''

INSERT_TRACK_QUERY_TEXT = '''INSERT OR IGNORE INTO tracks (track_uid, human_readable_name) ''' + \
                          '''       VALUES ("%s", "%s")'''

# INSERT_LABEL_QUERY_TEXT = '''INSERT INTO track_labels (label_uid, track_id, prev_label_uid, dt) ''' + \
#                           '''       SELECT "%s", tr.id, "%s", "%s" FROM  tracks tr ''' + \
#                           '''       WHERE tr.track_uid = "%s"'''
INSERT_LABEL_QUERY_TEXT = '''INSERT INTO track_labels (label_uid, track_id, dt) ''' + \
                          '''       SELECT "%s", tr.id, "%s", "%s" FROM  tracks tr ''' + \
                          '''       WHERE tr.track_uid = "%s"'''

UPDATE_TRACK_START_DT_QUERY_TEXT = '''UPDATE tracks SET start_dt = strftime("%%Y-%%m-%%dT%%H:%%M:%%S", (SELECT min(d1.dt) as dt_min FROM ''' + \
                                   '''    (SELECT datetime(dt) as dt FROM track_labels WHERE track_labels.track_id IN ''' + \
                                   '''        (SELECT id FROM tracks WHERE tracks.track_uid = "%s")''' + \
                                   '''    ) AS d1)) WHERE tracks.track_uid = "%s"'''

UPDATE_TRACK_END_DT_QUERY_TEXT = '''UPDATE tracks SET end_dt = strftime("%%Y-%%m-%%dT%%H:%%M:%%S", (SELECT max(d1.dt) as dt_max FROM ''' + \
                                 '''    (SELECT datetime(dt) as dt FROM track_labels WHERE track_labels.track_id IN ''' + \
                                 '''        (SELECT id FROM tracks WHERE tracks.track_uid = "%s")''' + \
                                 '''    ) AS d1)) WHERE tracks.track_uid = "%s"'''

DELETE_LABELS_OF_TRACK_QUERY_TEXT = '''DELETE FROM track_labels WHERE track_labels.track_id IN (SELECT id FROM tracks tr WHERE tr.track_uid = "%s")'''

SELECT_LABELS_OF_TRACK_QUERY_TEXT = '''SELECT label_uid,strftime("%%Y-%%m-%%dT%%H:%%M:%%S",dt) FROM track_labels WHERE track_labels.track_id IN (SELECT id FROM tracks tr WHERE tr.track_uid = "%s")'''

DELETE_TRACK_QUERY_TEXT = '''DELETE FROM tracks WHERE tracks.track_uid = "%s"'''

# SELECT_TRACK_QUERY_TEXT = '''SELECT lab.label_uid, lab.prev_label_uid from track_labels lab ''' + \
#                           ''' INNER JOIN tracks tr ON tr.id = lab.track_id ''' + \
#                           ''' WHERE tr.track_uid = "%s" '''
SELECT_TRACK_QUERY_TEXT = '''SELECT lab.label_uid from track_labels lab ''' + \
                          ''' INNER JOIN tracks tr ON tr.id = lab.track_id ''' + \
                          ''' WHERE tr.track_uid = "%s" '''

# SELECT_TRACKS_QUERY_TEXT = '''SELECT tr.track_uid, lab.label_uid, lab.prev_label_uid from track_labels lab ''' + \
#                            ''' INNER JOIN tracks tr ON tr.id = lab.track_id ''' + \
#                            ''' ORDER BY tr.track_uid '''
SELECT_TRACKS_QUERY_TEXT = '''SELECT tr.track_uid, lab.label_uid from track_labels lab ''' + \
                           ''' INNER JOIN tracks tr ON tr.id = lab.track_id ''' + \
                           ''' ORDER BY tr.track_uid '''

TEST_SQLITE_DB_CONNECTION_QUERY_TEXT = '''SELECT * FROM track_labels labs ''' + \
                                       '''INNER JOIN tracks tr ON labs.track_id = tr.id ''' + \
                                       '''ORDER BY RANDOM() LIMIT 1'''


# SELECT_TRACKS_BY_LABELS_QUERY_TEXT = '''SELECT tr.track_uid, lab.label_uid, lab.prev_label_uid, lab.dt FROM tracks tr ''' + \
#                                      '''    INNER JOIN track_labels lab ON tr.id = lab.track_id ''' + \
#                                      '''    WHERE tr.id IN (''' + \
#                                      '''                    SELECT tr1.id from tracks tr1 ''' + \
#                                      '''                        INNER JOIN track_labels lab1 ON tr1.id = lab1.track_id ''' + \
#                                      '''                        WHERE lab1.label_uid IN (%s))''' + \
#                                      '''    ORDER BY tr.track_uid'''
SELECT_TRACKS_BY_LABELS_QUERY_TEXT = '''SELECT tr.track_uid, lab.label_uid, lab.dt FROM tracks tr ''' + \
                                     '''    INNER JOIN track_labels lab ON tr.id = lab.track_id ''' + \
                                     '''    WHERE tr.id IN (''' + \
                                     '''                    SELECT tr1.id from tracks tr1 ''' + \
                                     '''                        INNER JOIN track_labels lab1 ON tr1.id = lab1.track_id ''' + \
                                     '''                        WHERE lab1.label_uid IN (%s))''' + \
                                     '''    ORDER BY tr.track_uid'''

# SELECT_TRACKS_BY_DATETIME_RANGE_QUERY_TEXT = ('''SELECT tr.track_uid, lab.label_uid, lab.prev_label_uid, lab.dt, tr.human_readable_name FROM tracks tr ''' + \
#                                               '''    INNER JOIN track_labels lab ON tr.id = lab.track_id ''' + \
#                                               '''    WHERE tr.id IN (''' + \
#                                               '''        SELECT tr1.id from tracks tr1 ''' + \
#                                               '''        INNER JOIN track_labels lab1 ON tr1.id = lab1.track_id ''' + \
#                                               '''        WHERE lab1.dt BETWEEN "%s" AND "%s") ''' + \
#                                               '''    ORDER BY tr.track_uid''')
SELECT_TRACKS_BY_DATETIME_RANGE_QUERY_TEXT = ('''SELECT tr.track_uid, lab.label_uid, lab.dt, tr.human_readable_name FROM tracks tr ''' + \
                                              '''    INNER JOIN track_labels lab ON tr.id = lab.track_id ''' + \
                                              '''    WHERE tr.id IN (''' + \
                                              '''        SELECT tr1.id from tracks tr1 ''' + \
                                              '''        INNER JOIN track_labels lab1 ON tr1.id = lab1.track_id ''' + \
                                              '''        WHERE lab1.dt BETWEEN "%s" AND "%s") ''' + \
                                              '''    ORDER BY tr.track_uid''')


DATETIME_FORMAT_STRING = '%Y-%m-%dT%H:%M:%S'