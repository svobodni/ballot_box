from ballot_box import db


class User(object):
    def __init__(self, profile):
        self.profile = profile

    @property
    def name(self):
        return self.profile["person"]["name"]


class Connection(db.Model):
    __tablename__ = "conn"
    id = db.Column(db.Integer, primary_key=True)
    token = db.Column(db.String(30), unique=True)
    logged_in = db.Column(db.DateTime)
    last_click = db.Column(db.DateTime, index=True)
    remote_addr = db.Column(db.String(50))
    user_id = db.Column(db.Integer)
    name = db.Column(db.String(100))
    profile = db.Column(db.Text)
