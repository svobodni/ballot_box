# -*- coding: utf-8 -*-

import datetime

from flask.ext.wtf import Form
from wtforms import SubmitField, validators
from wtforms_alchemy import model_form_factory
from wtforms_components import DateRange
# Workaround to fix lambdas in DateRange(min)
from wtforms_components.widgets import BaseDateTimeInput

# The variable db here is a SQLAlchemy object instance from
# Flask-SQLAlchemy package
from ballot_box import db
from models import Ballot, BallotProtocol

BaseDateTimeInput.range_validator_class = int

BaseModelForm = model_form_factory(Form)


class ModelForm(BaseModelForm):
    @classmethod
    def get_session(self):
        return db.session


def morning(days=1, at=9):
    return ((datetime.datetime.now() + datetime.timedelta(days=days))
            .replace(hour=at, minute=0, second=0))


def midnight(days=8):
    return ((datetime.datetime.now() + datetime.timedelta(days=days))
            .replace(hour=23, minute=59, second=59))


def min_timedelta(*args, **kwargs):
    return lambda: datetime.datetime.now() \
        + datetime.timedelta(*args, **kwargs)


class Difference(object):
    def __init__(self, fieldname, difference, message, reverse=False):
        self.fieldname = fieldname
        self.difference = difference
        self.message = message
        self.reverse = reverse

    def __call__(self, form, field):
        try:
            other = form[self.fieldname]
        except KeyError:
            raise validators.ValidationError(
                field.gettext("Invalid field name '%s'.") % self.fieldname
            )
        try:
            if not self.reverse and field.data - other.data <= self.difference:
                raise validators.ValidationError(self.message)
            elif self.reverse and other.data - field.data <= self.difference:
                raise validators.ValidationError(self.message)
        except TypeError:
            raise validators.ValidationError(self.message)


class BallotForm(ModelForm):
    class Meta:
        model = Ballot
        only = ["type", "name", "description", "unit",
                "supporters_too", "max_votes", "begin_at", "finish_at",
                "candidate_self_signup", "candidate_signup_until"]
        field_args = {
            "name": {
                "validators": [validators.Length(min=10)],
                "description": u"Např. Volba předsedy Jihomoravského KrS",
            },
            "begin_at": {
                "validators": [
                    DateRange(
                        min=min_timedelta(hours=1),
                        message=u"Začátek musí být nejméně za hodinu."),
                ],
                "default": lambda: morning(days=2, at=9),
            },
            "finish_at": {
                "validators": [
                    Difference(
                        "begin_at",
                        difference=datetime.timedelta(hours=72),
                        message=u"Trvání musí být nejméně 72 hodin."),
                    ],
                "default": lambda: midnight(),
                "description": u"Trvání musí být nejméně 72 hodin.",
            },
            "description": {
                "description": u"HTML",
            },
            "candidate_signup_until": {
                "validators": [
                    validators.Optional(),
                    Difference(
                        "begin_at",
                        difference=datetime.timedelta(hours=-24),
                        message=u"Konec přihlašování musí být "
                        u"nejméně 24 hodin před začátkem voleb.",
                        reverse=True
                    ),
                ],
                "default": lambda: morning(days=1, at=8),
                "description": u"Nejméně 24 hodin před začátkem voleb",
            }
        }
BallotForm.submit = SubmitField(u'Uložit')


class BallotEditForm(ModelForm):
    class Meta:
        model = Ballot
        only = ["type", "name", "description", "unit",
                "supporters_too", "max_votes", "begin_at", "finish_at",
                "candidate_self_signup", "candidate_signup_until",
                "approved", "cancelled"]
        field_args = {
            "name": {
                "validators": [validators.Length(min=10)],
            },
            "begin_at": {
                "validators": [
                    DateRange(
                        min=min_timedelta(minutes=5),
                        message=u"Začátek musí být nejméně za 5 minut."
                    ),
                ],
                "default": lambda: morning(days=2, at=9),
            },
            "finish_at": {
                "validators": [
                    Difference(
                        "begin_at",
                        difference=datetime.timedelta(hours=72),
                        message=u"Trvání musí být nejméně 72 hodin.",
                    )
                ],
                "default": lambda: midnight(),
                "description": u"Trvání musí být nejméně 72 hodin.",
            },
            "description": {
                "description": u"HTML",
            },
            "candidate_signup_until": {
                "validators": [validators.Optional()],
                "default": lambda: morning(days=1, at=8),
            }
        }
BallotEditForm.submit = SubmitField(u'Uložit')


class BallotProtocolForm(ModelForm):
    class Meta:
        model = BallotProtocol
        only = ["body_html"]
BallotProtocolForm.submit = SubmitField(u'Uložit')


class BallotProtocolEditForm(ModelForm):
    class Meta:
        model = BallotProtocol
        only = ["body_html", "approved"]
BallotProtocolEditForm.submit = SubmitField(u'Uložit')
