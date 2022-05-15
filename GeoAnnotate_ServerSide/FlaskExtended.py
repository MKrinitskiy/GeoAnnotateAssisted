from flask import Flask


class FlaskExtended(Flask):
    bmhelpers = dict()
    cnn = None