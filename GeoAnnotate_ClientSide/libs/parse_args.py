import argparse, warnings, datetime, os
import numpy as np
from .ServiceDefs import DoesPathExistAndIsFile, DoesPathExistAndIsDirectory
import ast


def parse_args(args):
    parser = argparse.ArgumentParser(description='script for client-side of GeoAnnotate with AI-based assistant')

    parser.add_argument('--http-logging', dest='http_logging', action='store_true',
                        help="""turns logging of http requests on""")

    return preprocess_args(parser.parse_args(args))



def preprocess_args(parsed_args):

    return parsed_args