import datetime


class Config(object):
    DEBUG = False
    TESTING = False
    SQLALCHEMY_DATABASE_URI = "sqlite:////tmp/test.db"
    REGISTRY_URI = "https://registr.svobodni.cz"
    SECRET_KEY = "not a secret"
    LOGIN_TIMEOUT = datetime.timedelta(minutes=30)


class ProductionConfig(Config):
    SQLALCHEMY_DATABASE_URI = "mysql://user@localhost/foo"


class DevelopmentConfig(Config):
    DEBUG = True


class TestingConfig(Config):
    TESTING = True
