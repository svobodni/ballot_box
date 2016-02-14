# -*- coding: utf-8 -*-

import os

from celery import Celery
from flask import Flask
from flask.ext.mail import Mail
from flask.ext.sqlalchemy import SQLAlchemy
from flask_bootstrap import Bootstrap
from flask_wtf.csrf import CsrfProtect
from werkzeug.contrib.cache import FileSystemCache


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

try:
    os.makedirs(app.config['CACHE_DIR'])
except OSError:
    pass

cache = FileSystemCache(app.config['CACHE_DIR'])  # default_timeout=300

import tasks  # NOQA
import ballot_box.views  # NOQA
