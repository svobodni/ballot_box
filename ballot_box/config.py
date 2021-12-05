# -*- coding: utf-8 -*-

import datetime


class Config(object):
    DEBUG = False
    TESTING = False
    SQLALCHEMY_DATABASE_URI = "sqlite:////tmp/test.db"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    REGISTRY_URI = "http://localhost:3000"
    SECRET_KEY = "not a secret"
    LOGIN_TIMEOUT = datetime.timedelta(minutes=30)
    USE_SMTP = False
    MAX_CONTENT_LENGTH = 1 * 1024 * 1024  # 1 MB
    CELERY_BROKER_URL = "redis://localhost:6379/11"
    CELERY_RESULT_BACKEND = "redis://localhost:6379/11"
    SERVER_NAME = "127.0.0.1:5000"
    CACHE_DIR = "/tmp/vs"
    ANNOUNCE_RESULTS_RECIPIENTS = ["kancelar@svobodni.cz", "kk@svobodni.cz"]


class ProductionConfig(Config):
    PREFERRED_URL_SCHEME = "https"
    SQLALCHEMY_DATABASE_URI = "mysql://user@localhost/foo"
    USE_SMTP = True


class DevelopmentConfig(Config):
    DEBUG = True
    REGISTRY_URI = "https://registr-test.svobodni.cz"
    CELERY_BROKER_URL = "redis://redis:6379/11"
    CELERY_RESULT_BACKEND = "redis://redis:6379/11"
    SERVER_NAME = "localhost:3001"

class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:////tmp/ballot_box_testing.db"
