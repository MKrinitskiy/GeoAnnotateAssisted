import argparse, warnings, datetime, os
import numpy as np
from .service_defs import DoesPathExistAndIsFile, DoesPathExistAndIsDirectory
import shutil
import ast


def parse_args(args):
    parser = argparse.ArgumentParser(description='script for server-side of GeoAnnotate with AI-based assistant')

    source_group = parser.add_mutually_exclusive_group()
    source_group.add_argument('--source-data-dir', '-s', dest='source_data_dir', type=str,
                              default='./src_data/',
                              help='path to the directory containing source data to be annotated.')
    source_group.add_argument('--ncfiles-index', dest='ncfiles_index', type=str,
                        default='./src_data/METEOSAT_ncfiles_wrtAppContainer_wMetadata.pkl',
                        help="""Path to pkl file containing list of METEOSAT source data *.nc filenames with metadata pre-computed""")
    source_group.add_argument('--source-data-file', '-f', dest='source_data_file', type=str,
                              default='./src_data/source_data_file.nc',
                              help='path to the *.nc file containing source data to be annotated.')

    parser.add_argument('--caches-path', dest='caches_path', type=str,
                        default='./.cache',
                        help="""Directory containing pre-computed projection and interpolation constants """)

    parser.add_argument('--data-type', dest='data_type', type=str,
                        default='METEOSAT-MCS', choices = ['METEOSAT-MCS', "METEOSAT-QLL", 'NAAD-PL', 'AMRC-MC', 'NAAD-CS'],
                        help="""Switching between labeling problems: \n
                        METEOSAT-MCS - for tracking (M)esoscale (C)onvective (S)ystems 
                        in METEOSAT remote sensing imagery; \n
                        METEOSAT-QLL - for tracking (Q)uasi-(L)inear (L)abeled phenomena) 
                        in METEOSAT remote sensing imagery; \n
                        NAAD-PL - for tracking Mesoscale Cyclones (a.k.a. (P)olar (L)ows) 
                        in NAAD atmospheric modeling data \n
                        AMRC-MC - for tracking (M)esoscale (C)yclones (or polar lows)
                        in AMRC remote sensing mosaics in Southern ocean \n
                        NAAD-CS - for tracking (C)oherent (S)tructures in NAAD atmospheric modeling data.""")

    parser.add_argument('--port', '-p', dest='port', type=int, default=1999,
                        help='''Port for the server to listen to''')

    cnn_choice_group = parser.add_mutually_exclusive_group()
    cnn_choice_group.add_argument('--no-cnn', dest='no_cnn', action='store_true',
                                  help='turns off the CNN prediction capability')

    cnn_prefs = cnn_choice_group.add_argument_group('CNN preferences')
    cnn_prefs.add_argument('--model-snapshot', dest='model_snapshot', type=str,
                        default='./retinanet-snapshot/model.pt',
                        help="""Filename of Retinanet snapshot""")
    cnn_prefs.add_argument('--classes-csv', dest='classes_csv', type=str,
                        default='./retinanet-snapshot/csv_classes.csv',
                        help="""CSV file containing mapping id <-> class_name""")
    cnn_prefs.add_argument('--backbone-depth', dest='backbone_depth', type=int,
                        default=152,
                        help="""ResNet backbone depth""")
    cnn_prefs.add_argument('--score-threshold', dest='score_threshold', type=float,
                        default=0.4,
                        help="""Prediction score threshold""")
    cnn_prefs.add_argument('--max-detections', dest='max_detections', type=int,
                        default=20,
                        help="""Maximum number of detected events per snapshot""")


    parser.add_argument('--cached-read-data', dest='cached_read_data', type=int,
                        default=16,
                        help="""Number of preprocessed data snapshots to cache in memory for improving reading speed""")

    parser.add_argument('--gpu', type=str, default='0', help="""GPU number to exploit (only single-GPU mode is supported currently)""")

    return preprocess_args(parser.parse_args(args))



def preprocess_args(parsed_args):
    if not DoesPathExistAndIsDirectory(parsed_args.caches_path):
        os.makedirs(parsed_args.caches_path)
    if not DoesPathExistAndIsDirectory(os.path.join(os.getcwd(), 'logs')):
        os.makedirs(os.path.join(os.getcwd(), 'logs'))
    # assert DoesPathExistAndIsFile(parsed_args.ncfiles_index), 'ncfiles_index cannot be found'
    assert DoesPathExistAndIsDirectory(parsed_args.caches_path), 'caches_path directory cannot be found or created'
    assert DoesPathExistAndIsDirectory(os.path.join(os.getcwd(), 'logs')), 'logs directory cannot be found or created'
    # assert DoesPathExistAndIsFile(parsed_args.model_snapshot), 'model_snapshot cannot be found'
    # assert DoesPathExistAndIsFile(parsed_args.classes_csv), 'classes_csv cannot be found'
    #TODO: check if interpolation constants and other pre-computed data are in the place in caches_path

    if parsed_args.data_type == 'NAAD-CS':
        assert DoesPathExistAndIsFile(parsed_args.source_data_file), "When one specifies the data type (--data-type " \
                                                                     "argument) as \"NAAD-CS\", the path for source data" \
                                                                     " file should be specified explicitly " \
                                                                     "(--source-data-file argument)"

    return parsed_args