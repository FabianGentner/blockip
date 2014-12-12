"""
Holds some global context that would be difficult to get to where it's needed if it weren't here. Note that these
remain constant during the application's lifetime.
"""

import flask

app = flask.Flask(__name__)
logger = None
arguments = None
settings = None
