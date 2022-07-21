import argparse, warnings, datetime, os
import numpy as np
from .ServiceDefs import DoesPathExistAndIsFile, DoesPathExistAndIsDirectory
import ast


def parse_args(args):
    parser = argparse.ArgumentParser(description='script for client-side of GeoAnnotate with AI-based assistant')

    parser.add_argument('--http-logging', dest='http_logging', action='store_true',
                        help="""turns logging of http requests on""")

    parser.add_argument('--labels-type', '-t', dest='labels_type', default='MCS',
                        choices = ['MCS', 'MC', 'PL'],
                        help="""switching between types of labels: \n
                                MCS - mesoscale convective systems; \n
                                MC (a.k.a. PL) - mesoscale cyclones, polar lows""")

    parser.add_argument('--proj-json-settings', '-p', dest='proj_json_settings_fname', type=str,
                        default='./settings/projection_METEOSAT.json',
                        help="""JSON-file with exported dict containing basemap settings (resolution, projection \n
                                arguments, etc. - see mpl_toolkits.basemap.Basemap help)""")

    parser.add_argument('--comm-debug', '-d', dest='comm_debug', action="store_true",
                        help="""The switch rules whether the app should dump everything sent and received to/from
                                server for debug purposes.""")

    return preprocess_args(parser.parse_args(args))



def preprocess_args(parsed_args):

    return parsed_args