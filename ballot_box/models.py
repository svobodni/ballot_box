# -*- coding: utf-8 -*-
from ballot_box import db
from sqlalchemy_utils import ChoiceType


class User(object):
    def __init__(self, profile):
        self.profile = profile

    @property
    def name(self):
        return self.profile["person"]["name"]

    @property
    def is_party_member(self):
        try:
            return self.profile["person"]["type"] == "member"
        except KeyError:
            return False

    @property
    def is_party_supporter(self):
        # TODO:
        try:
            return self.profile["person"]["type"] == "supporter"
        except KeyError:
            return False

    @property
    def is_election_commission_member(self):
        try:
            for role in self.profile["person"]["roles"]:
                if role["organization"]["id"] == 3:
                    return True
            return False
        except KeyError:
            return False

    @property
    def is_central_presidium_member(self):
        return False

    @property
    def is_local_presidium_member(self):
        return False

    def can_create_ballot(self):
        return (self.is_election_commission_member or
                self.is_central_presidium_member or
                self.is_local_presidium_member)


class Connection(db.Model):
    __tablename__ = "connection"
    id = db.Column(db.Integer, primary_key=True)
    token = db.Column(db.String(30), unique=True)
    logged_in = db.Column(db.DateTime)
    last_click = db.Column(db.DateTime, index=True)
    remote_addr = db.Column(db.String(50))
    user_id = db.Column(db.Integer)
    name = db.Column(db.Unicode(100))
    profile = db.Column(db.UnicodeText)


class Ballot(db.Model):
    __tablename__ = "ballot"
    STATUSES = [
        ("PLANNED", u'Plánováno'),
        ("APPROVED", u'Schváleno'),
        ("IN_PROGRESS", u'Probíhá'),
        ("FINISHED", u'Ukončeno'),
        ("CANCELLED", u'Zrušeno')
    ]
    TYPES = [
        ("VOTE", u'Hlasování'),
        ("ELECTION", u'Volba'),
    ]
    UNITS = [
        ("ALL", u'Všichni'),
        ("REGION", u'Kraj'),
        ("BRANCH", u'Pobočka'),
        ("ORGAN", u'Orgán'),
    ]
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.Unicode(100))
    description = db.Column(db.UnicodeText)
    begin_at = db.Column(db.DateTime)
    finish_at = db.Column(db.DateTime)
    status = db.Column(ChoiceType(STATUSES, impl=db.String(20)))
    type = db.Column(ChoiceType(TYPES, impl=db.String(20)))
    unit = db.Column(ChoiceType(UNITS, impl=db.String(20)))
    unit_id = db.Column(db.Integer)
    supporters_too = db.Column(db.Boolean)
    max_votes = db.Column(db.Integer)

    options = db.relationship('BallotOption', backref='ballot',
                              lazy='select')


class BallotOption(db.Model):
    __tablename__ = "ballot_option"
    id = db.Column(db.Integer, primary_key=True)
    ballot_id = db.Column(db.Integer, db.ForeignKey('ballot.id'))
    title = db.Column(db.Unicode(100))

    votes = db.relationship('Vote', backref='ballot_option',
                            lazy='dynamic')


class Vote(db.Model):
    __tablename__ = "vote"
    id = db.Column(db.Integer, primary_key=True)
    ballot_option_id = db.Column(db.Integer, db.ForeignKey('ballot_option.id'))
    hash = db.Column(db.Unicode(100))


class Voters(db.Model):
    __tablename__ = "voters"
    id = db.Column(db.Integer, primary_key=True)
    ballot_id = db.Column(db.Integer, db.ForeignKey('ballot.id'))
    name = db.Column(db.Unicode(100))
    email = db.Column(db.Unicode(100))
    user_id = db.Column(db.Integer)
    voted_at = db.Column(db.DateTime)
    remote_addr = db.Column(db.String(50))
    user_agent = db.Column(db.String(500))
