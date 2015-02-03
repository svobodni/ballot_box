from flask import Flask
from flask.ext.sqlalchemy import SQLAlchemy
from flask_bootstrap import Bootstrap
from werkzeug.contrib.cache import SimpleCache
from flask_wtf.csrf import CsrfProtect
import datetime


class BallotBoxError(Exception):
    status_code = 400

    def __init__(self, message, status_code=None, payload=None):
        Exception.__init__(self)
        self.message = message
        if status_code is not None:
            self.status_code = status_code
        self.payload = payload

    def to_dict(self):
        rv = dict(self.payload or ())
        rv['message'] = self.message
        return rv


app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:////tmp/test.db"
app.config["LOGIN_TIMEOUT"] = datetime.timedelta(minutes=30)
app.config["REGISTRY_URI"] = "https://registr.svobodni.cz"
app.secret_key = "not a secret"
Bootstrap(app)
CsrfProtect(app)

db = SQLAlchemy(app)

cache = SimpleCache()

import ballot_box.views
