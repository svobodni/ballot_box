from flask import Flask
from flask.ext.sqlalchemy import SQLAlchemy
import datetime


app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:////tmp/test.db"
app.config["LOGIN_TIMEOUT"] = datetime.timedelta(minutes=30)
app.config["REGISTRY_URI"] = "https://registr.svobodni.cz"
app.secret_key = "not a secret"
db = SQLAlchemy(app)

import ballot_box.views
