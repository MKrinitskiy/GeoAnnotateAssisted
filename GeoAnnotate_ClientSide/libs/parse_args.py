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
                        help="""switching between types of labels: \nMCS - mesoscale convective systems;\nMC (a.k.a. PL) - mesoscale cyclones, polar lows""")

    return preprocess_args(parser.parse_args(args))



def preprocess_args(parsed_args):

    return parsed_args