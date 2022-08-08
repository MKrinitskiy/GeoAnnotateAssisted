from flask import Flask


class FlaskExtended(Flask):
    args = None
    bmhelpers = dict()
    cnn = None

    def __init__(self, import_name: str, launch_args=None):
        super().__init__(import_name)
        self.args = launch_args