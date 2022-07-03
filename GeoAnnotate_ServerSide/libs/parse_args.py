import argparse, warnings, datetime, os
import numpy as np
from .service_defs import DoesPathExistAndIsFile, DoesPathExistAndIsDirectory
import ast


def parse_args(args):
    parser = argparse.ArgumentParser(description='script for server-side of GeoAnnotate with AI-based assistant')

    parser.add_argument('--ncfiles-index', dest='ncfiles_index', type=str,
                        default='/app/mk/geoseg_server/src_data/METEOSAT_ncfiles_wrtAppContainer_wMetadata.pkl',
                        help="""Path to pkl file containing list of METEOSAT source data *.nc filenames with metadata pre-computed""")
    parser.add_argument('--caches-path', dest='caches_path', type=str,
                        default='/app/mk/geoseg_server/.cache',
                        help="""Directory containing pre-computed projection and interpolation constants """)
    parser.add_argument('--model-snapshot', dest='model_snapshot', type=str,
                        default='/app/mk/geoseg_server/retinanet-snapshot/model.pt',
                        help="""Filename of Retinanet snapshot""")
    parser.add_argument('--classes-csv', dest='classes_csv', type=str,
                        default='/app/mk/geoseg_server/retinanet-snapshot/csv_classes.csv',
                        help="""CSV file containing mapping id <-> class_name""")
    parser.add_argument('--backbone-depth', dest='backbone_depth', type=int,
                        default=152,
                        help="""ResNet backbone depth""")
    parser.add_argument('--score-threshold', dest='score_threshold', type=float,
                        default=0.4,
                        help="""Prediction score threshold""")
    parser.add_argument('--max-detections', dest='max_detections', type=int,
                        default=20,
                        help="""Maximum number of detected events per snapshot""")


    parser.add_argument('--cached-read-data', dest='cached_read_data', type=int,
                        default=16,
                        help="""Number of preprocessed data snapshots to cache in memory for improving reading speed""")

    parser.add_argument('--gpu', type=str, default='0', help="""GPU number to exploit (only single-GPU mode is supported currently)""")

    return preprocess_args(parser.parse_args(args))



def preprocess_args(parsed_args):
    assert DoesPathExistAndIsFile(parsed_args.ncfiles_index), 'ncfiles_index cannot be found'
    assert DoesPathExistAndIsDirectory(parsed_args.caches_path), 'caches_path directory cannot be found'
    assert DoesPathExistAndIsFile(parsed_args.model_snapshot), 'model_snapshot cannot be found'
    assert DoesPathExistAndIsFile(parsed_args.classes_csv), 'classes_csv cannot be found'
    #TODO: check if interpolation constants and other pre-computed data are in the place in caches_path

    return parsed_args