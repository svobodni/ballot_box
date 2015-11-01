import datetime


class Config(object):
    DEBUG = False
    TESTING = False
    SQLALCHEMY_DATABASE_URI = "sqlite:////tmp/test.db"
    REGISTRY_URI = "https://registr.svobodni.cz"
    SECRET_KEY = "not a secret"
    LOGIN_TIMEOUT = datetime.timedelta(minutes=30)
    USE_SMTP = False
    CELERY_BROKER_URL = "redis://localhost:6379/11"
    CELERY_RESULT_BACKEND = "redis://localhost:6379/11"
    SERVER_NAME = "127.0.0.1:5000"


class ProductionConfig(Config):
    PREFERRED_URL_SCHEME = "https"
    SQLALCHEMY_DATABASE_URI = "mysql://user@localhost/foo"
    USE_SMTP = True


class DevelopmentConfig(Config):
    DEBUG = True


class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:////tmp/ballot_box_testing.db"
