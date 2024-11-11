import datetime
import os, sys
python_path = sys.executable
from flask import Flask, request, send_file, make_response, Response, jsonify
import numpy as np
from FlaskExtended import *
import binascii, logging, time
from PIL import Image
from io import BytesIO
import json
import sys
import collections
from libs.parse_args import parse_args
import ast

args = sys.argv[1:]
args = parse_args(args)

app = FlaskExtended(__name__, launch_args = args)
app.config['SECRET_KEY'] = binascii.hexlify(os.urandom(24))

logging.basicConfig(filename='./logs/app.log', level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logging.info('Started AI-assisted GeoAnnotate server-side app')
logging.info('args: %s' % sys.argv[1:])


@app.route('/')
def main():
    print('got GET request at main route')
    response = make_response('Hello, world!')
    return response



@app.route('/images', methods=['GET'])
def image():
    print('got GET request at images route')
    try:
        response = make_response('images directory')
        return response
    except Exception as ex:
        print(ex)
        response = make_response('exception mock')
        response.headers['ErrorDesc'] = 'ExceptionMock'
        return response



if __name__ == '__main__':
    print('starting servermock at port %s' % args.port)
    app.run(host='0.0.0.0', port=args.port)
