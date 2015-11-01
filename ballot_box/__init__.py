from flask import Flask
from flask.ext.sqlalchemy import SQLAlchemy
from flask_bootstrap import Bootstrap
from werkzeug.contrib.cache import SimpleCache
from flask_wtf.csrf import CsrfProtect
from flask.ext.mail import Mail
from celery import Celery


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
app.config.from_object('ballot_box.config.DevelopmentConfig')
Bootstrap(app)
CsrfProtect(app)
mail = Mail(app)

db = SQLAlchemy(app)


def make_celery(app):
    celery = Celery(app.import_name, broker=app.config['CELERY_BROKER_URL'])
    celery.conf.update(app.config)
    TaskBase = celery.Task

    class ContextTask(TaskBase):
        abstract = True

        def __call__(self, *args, **kwargs):
            with app.app_context():
                return TaskBase.__call__(self, *args, **kwargs)

    celery.Task = ContextTask
    return celery

celery = make_celery(app)
import tasks

cache = SimpleCache()

import ballot_box.views
