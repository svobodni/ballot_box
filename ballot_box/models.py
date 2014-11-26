# -*- coding: utf-8 -*-
from ballot_box import db
from sqlalchemy_utils import ChoiceType
from wtforms import SelectField
import datetime


class User(object):
    def __init__(self, profile, jwt=None):
        self.profile = profile
        self.jwt = jwt

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
        return not self.is_party_member()

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

    def can_list_ballot(self):
        return self.can_create_ballot()


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
    jwt = db.Column(db.Text)


class Ballot(db.Model):
    __tablename__ = "ballot"
    STATUSES = [
        ("PLANNED", u'Plánováno'),
        ("APPROVED", u'Schváleno'),
        ("FINISHED", u'Ukončeno'),
        ("CANCELLED", u'Zrušeno')
    ]
    TYPES = [
        ("ELECTION", u'Volba'),
        ("VOTING", u'Hlasování')
    ]
    UNITS = [
        ('country,1', u'Cel\xe1 republika'),
        ('region,1', u'Jiho\u010desk\xfd kraj'),
        ('region,2', u'Jihomoravsk\xfd kraj'),
        ('region,3', u'Karlovarsk\xfd kraj'),
        ('region,4', u'Kr\xe1lov\xe9hradeck\xfd kraj'),
        ('region,5', u'Libereck\xfd kraj'),
        ('region,6', u'Moravskoslezsk\xfd kraj'),
        ('region,7', u'Olomouck\xfd kraj'),
        ('region,8', u'Pardubick\xfd kraj'),
        ('region,9', u'Plze\u0148sk\xfd kraj'),
        ('region,10', u'Praha'),
        ('region,11', u'St\u0159edo\u010desk\xfd kraj'),
        ('region,12', u'\xdasteck\xfd kraj'),
        ('region,13', u'Kraj Vyso\u010dina'),
        ('region,14', u'Zl\xednsk\xfd kraj'),
        ('body,1', u'Republikov\xe9 p\u0159edsednictvo'),
        ('body,2', u'Kontroln\xed komise'),
        ('body,3', u'Volebn\xed komise'),
        ('body,4', u'Rozhod\u010d\xed komise'),
        ('body,5', u'Republikov\xfd v\xfdbor')
    ]
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.Unicode(100), nullable=False, info={'label': u'Název'})
    description = db.Column(db.UnicodeText, nullable=True, info={'label': u'Popis'})
    begin_at = db.Column(db.DateTime, nullable=False, info={'label': u'Začátek'})
    finish_at = db.Column(db.DateTime, nullable=False, info={'label': u'Konec'})
    status = db.Column(ChoiceType(STATUSES, impl=db.String(20)), nullable=False, default="PLANNED",  info={'label': u'Stav'})
    type = db.Column(ChoiceType(TYPES, impl=db.String(20)), nullable=False, info={'label': u'Druh'})
    unit = db.Column(ChoiceType(UNITS, impl=db.String(20)), nullable=False, info={'label': u'Jednotka', 'form_field_class': SelectField})
    #unit_id = db.Column(db.Integer, nullable=False, info={'label': u'ID Jednotky'},)
    supporters_too = db.Column(db.Boolean, nullable=False, default=False, info={'label': u'Také příznivci'})
    max_votes = db.Column(db.Integer, default=1, nullable=False, info={'label': u'Max. hlasů'})

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
