from libs import *
import os, sys, sqlite3



def main(argv):
    tracks_db_fname = os.path.join(os.getcwd(), 'tracks.db')

    if (os.path.exists(tracks_db_fname) and os.path.isfile(tracks_db_fname)):
        print('Database file already exists. I will not try to corrupt it.\nExiting.')
        return
    else:
        if DatabaseOps.create_tracks_db(tracks_db_fname):
            print('created new tracks database file: %s' % tracks_db_fname)
        else:
            print('Failed creating database. Please refer to the errors.log file.')
            return

    xml_data_files = find_files('./', '*.MCC.xml')
    for xml_fname in xml_data_files:
        MCCxmlParseReader = ArbitraryXMLReader(xml_fname)
        labels_loaded = MCCxmlParseReader.labels
        print('file %s: found %d labels' % (os.path.basename(xml_fname), len(labels_loaded)))
        for label in labels_loaded:
            DatabaseOps.insert_label_data(tracks_db_fname, label)



if __name__ == '__main__':
    sys.exit(main(sys.argv))