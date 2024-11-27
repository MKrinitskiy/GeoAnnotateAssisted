import argparse, warnings, datetime, os
import numpy as np
from .ServiceDefs import DoesPathExistAndIsFile, DoesPathExistAndIsDirectory
import ast


def parse_args(args):
    parser = argparse.ArgumentParser(description='script for client-side of GeoAnnotate with AI-based assistant')

    parser.add_argument('--http-logging', dest='http_logging', action='store_true',
                        help="""turns logging of http requests on""")

    parser.add_argument('--labels-type', '-t', dest='labels_type', default='MCS',
                        choices = ['MCS', 'MC', 'PL', 'AMRC', 'CS', 'QLL'],
                        help="""Switching between labeling problems: \n
                                MCS - for tracking (M)esoscale (C)onvective (S)ystems in METEOSAT remote sensing 
                                imagery; \n
                                MC (a.k.a. PL) - for tracking (M)esoscale (C)yclones, (P)olar (L)ows in
                                NAAD atmospheric modeling data \n
                                AMRC - for tracking mesoscale cyclones or polar lows in AMRC remote sensing mosaics in
                                Southern ocean \n
                                CS - for tracking (C)oherent (Structures) in NAAD atmospheric modeling data.""")


    parser.add_argument('--proj-json-settings', '-j', dest='proj_json_settings_fname', type=str,
                        default='./settings/projection_METEOSAT.json',
                        help="""JSON-file with exported dict containing basemap settings (resolution, projection \n
                                arguments, etc. - see mpl_toolkits.basemap.Basemap help)""")

    parser.add_argument('--comm-debug', '-d', dest='comm_debug', action="store_true",
                        help="""The switch rules whether the app should dump everything sent and received to/from
                                server for debug purposes.""")

    parser.add_argument('--port', '-p', dest='port', type=int, default=1999,
                        help='''Server-side port to connect to.''')

    parser.add_argument('--server', '-s', dest='remotehost', type=str, default='localhost',
                        help='''Server host address (ip or domain name, default is "localhost").''')
    
    parser.add_argument('--debug-local', '-u', dest='debug_local', action='store_true',
                        help='''The switch rules whether the app should run in debug mode (i.e. without connecting to the server).''')

    return preprocess_args(parser.parse_args(args))



def preprocess_args(parsed_args):

    return parsed_args