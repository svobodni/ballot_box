# -*- coding: utf-8 -*-
from ballot_box import db
from sqlalchemy_utils import ChoiceType
from wtforms import SelectField
from sqlalchemy.schema import UniqueConstraint
import datetime


class User(object):
    def __init__(self, profile, jwt=None):
        self.profile = profile
        self.jwt = jwt

    @property
    def name(self):
        return self.profile["person"]["name"]

    @property
    def canonical_name(self):
        return " ".join((self.profile["person"]["last_name"].upper(), self.profile["person"]["first_name"]))

    @property
    def email(self):
        return self.profile["person"]["email"]

    @property
    def id(self):
        return self.profile["person"]["id"]

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

    def can_edit_ballot(self):
        return self.is_election_commission_member

    def can_edit_ballot_options(self):
        return self.can_edit_ballot()

    def is_in_unit(self, unit_type, unit_id):
        if unit_type == "country":
            return True
        elif unit_type == "body":
            try:
                for role in self.profile["person"]["roles"]:
                    if role["organization"]["id"] == unit_id:
                        return True
            except KeyError:
                pass
        elif unit_type == "region":
            try:
                if self.profile["person"]["domestic_region"]["id"] == unit_id:
                    return True
            except KeyError:
                pass

        return False

    def has_right_to_vote(self, ballot):
        if not ballot.supporters_too and not self.is_party_member:
            return False
        (unit_type, unit_id) = tuple(ballot.unit.code.split(','))
        return self.is_in_unit(unit_type, int(unit_id))

    def already_voted(self, ballot):
        return bool(ballot.voters.filter(Voter.person_id == self.id).first())

    def can_vote(self, ballot):
        return self.has_right_to_vote(ballot) and not self.already_voted(ballot)

    def can_candidate_signup(self, ballot):
        return self.has_right_to_vote(ballot)

    @property
    def votable_unit_codes(self):
        # TODO: make more efficient
        unit_codes = []
        for (unit_code, unit_value) in Ballot.UNITS:
            (unit_type, unit_id) = tuple(unit_code.split(','))
            if self.is_in_unit(unit_type, int(unit_id)):
                unit_codes.append(unit_code)
        return unit_codes


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

UNITS_GREETING = dict([
    ('country,1', u''),
    ('region,1', u' v Jihočeském kraji'),
    ('region,2', u' v Jihomoravském kraji'),
    ('region,3', u' v Karlovarském kraji'),
    ('region,4', u' v Královéhradeckém kraji'),
    ('region,5', u' v Libereckém kraji'),
    ('region,6', u' v Moravskoslezském kraji'),
    ('region,7', u' v Olomouckém kraji'),
    ('region,8', u' v Pardubickém kraji'),
    ('region,9', u' v Plzeňském kraji'),
    ('region,10', u'v Praze'),
    ('region,11', u' ve Středočeském kraji'),
    ('region,12', u' v Ústeckém kraji'),
    ('region,13', u' v Kraji Vysočina'),
    ('region,14', u've Zlínském kraji'),
    ('body,1', u' v Republikovém předsednictvu'),
    ('body,2', u' v Kontrolní komisi'),
    ('body,3', u' ve Volební komisi'),
    ('body,4', u' v Rozhodčí komisi'),
    ('body,5', u' v Republikovém výboru')
])


class Ballot(db.Model):
    __tablename__ = "ballot"
    TYPES = [
        ("ELECTION", u'Volba'),
        ("VOTING", u'Hlasování')
    ]
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.Unicode(100), nullable=False, info={'label': u'Název'})
    description = db.Column(db.UnicodeText, nullable=True, info={'label': u'Popis'})
    begin_at = db.Column(db.DateTime, nullable=False, info={'label': u'Začátek'})
    finish_at = db.Column(db.DateTime, nullable=False, info={'label': u'Konec'})
    approved = db.Column(db.Boolean, nullable=False, default=False, info={'label': u'Schváleno'})
    cancelled = db.Column(db.Boolean, nullable=False, default=False, info={'label': u'Zrušeno'})
    type = db.Column(ChoiceType(TYPES, impl=db.String(20)), nullable=False, info={'label': u'Druh'})
    unit = db.Column(ChoiceType(UNITS, impl=db.String(20)), nullable=False, info={'label': u'Jednotka', 'form_field_class': SelectField})
    supporters_too = db.Column(db.Boolean, nullable=False, default=False, info={'label': u'Také příznivci'})
    max_votes = db.Column(db.Integer, default=1, nullable=False, info={'label': u'Max. hlasů'})

    options = db.relationship('BallotOption', backref='ballot',
                              lazy='select', order_by="BallotOption.title")
    voters = db.relationship('Voter', backref='ballot', lazy='dynamic')
    abstainers = db.relationship('Abstainer', backref='ballot', lazy='dynamic',
                                 order_by="Abstainer.hash_digest")
    protocols = db.relationship('BallotProtocol', backref='ballot',
                                lazy='dynamic', order_by="desc(BallotProtocol.created_at)")
    candidate_self_signup = db.Column(db.Boolean, nullable=False, default=True, info={'label': u'Kandidáti se přihlašují sami'})
    candidate_signup_until = db.Column(db.DateTime, nullable=False, info={'label': u'Přihlášení kandidátů do'})

    @property
    def in_time_progress(self):
        now = datetime.datetime.now()
        return self.begin_at < now < self.finish_at

    @property
    def in_time_finished(self):
        now = datetime.datetime.now()
        return self.finish_at < now

    @property
    def in_progress(self):
        return self.approved and not self.cancelled and self.in_time_progress

    @property
    def is_finished(self):
        return self.in_time_finished

    @property
    def in_time_candidate_signup(self):
        now = datetime.datetime.now()
        return self.candidate_signup_until > now

    @property
    def is_election(self):
        return self.type == "ELECTION"

    @property
    def is_yes_no(self):
        return len(self.options) <= self.max_votes

    @property
    def method(self):
        if self.is_yes_no:
            return u"PRO NÁVRH / PROTI NÁVRHU"
        return u"podle pořadí počtu získaných hlasů"

    @property
    def approved_protocol(self):
        return self.protocols.filter(BallotProtocol.approved == True).first()

    @property
    def mail_greeting(self):
        return UNITS_GREETING.get(self.unit.code, "")

    @property
    def mail_name(self):
        return self.name[0].lower()+self.name[1:]

    @property
    def type_short(self):
        return self.type.value[0]


class BallotOption(db.Model):
    __tablename__ = "ballot_option"
    id = db.Column(db.Integer, primary_key=True)
    ballot_id = db.Column(db.Integer, db.ForeignKey('ballot.id'))
    title = db.Column(db.Unicode(100))
    user_id = db.Column(db.Integer, nullable=True)
    votes = db.relationship('Vote', backref='ballot_option',
                            lazy='dynamic', order_by="Vote.hash_digest")


class Vote(db.Model):
    __tablename__ = "vote"
    id = db.Column(db.Integer, primary_key=True)
    ballot_option_id = db.Column(db.Integer, db.ForeignKey('ballot_option.id'))
    value = db.Column(db.Integer)
    hash_digest = db.Column(db.Unicode(100))


class Voter(db.Model):
    __tablename__ = "voter"
    __table_args__ = (UniqueConstraint("ballot_id", "person_id"),)
    id = db.Column(db.Integer, primary_key=True)
    ballot_id = db.Column(db.Integer, db.ForeignKey('ballot.id'))
    name = db.Column(db.Unicode(100))
    email = db.Column(db.Unicode(100))
    person_id = db.Column(db.Integer)
    voted_at = db.Column(db.DateTime)
    remote_addr = db.Column(db.String(50))
    user_agent = db.Column(db.String(500))


class Abstainer(db.Model):
    __tablename__ = "abstainer"
    __table_args__ = (UniqueConstraint("ballot_id", "person_id"),)
    id = db.Column(db.Integer, primary_key=True)
    ballot_id = db.Column(db.Integer, db.ForeignKey('ballot.id'))
    name = db.Column(db.Unicode(100))
    email = db.Column(db.Unicode(100))
    person_id = db.Column(db.Integer)
    hash_digest = db.Column(db.Unicode(100))
    confirmation_sent = db.Column(db.Boolean, nullable=False, default=False)


class BallotProtocol(db.Model):
    __tablename__ = "ballotprotocol"
    id = db.Column(db.Integer, primary_key=True)
    ballot_id = db.Column(db.Integer, db.ForeignKey('ballot.id'))
    created_at = db.Column(db.DateTime, default=lambda: datetime.datetime.now())
    body_html = db.Column(db.UnicodeText, nullable=False, info={'label': u'HTML tělo'})
    approved = db.Column(db.Boolean, nullable=False, default=False, info={'label': u'Schváleno'})
