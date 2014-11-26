# -*- coding: utf-8 -*-
import datetime
from wtforms import SubmitField, SelectField
from models import Ballot
from wtforms_components import DateRange
from flask.ext.wtf import Form
from wtforms_alchemy import model_form_factory
from wtforms import validators
# The variable db here is a SQLAlchemy object instance from
# Flask-SQLAlchemy package
from ballot_box import db
from registry import registry_units

# Workaround to fix lambdas in DateRange(min)
from wtforms_components.widgets import BaseDateTimeInput
BaseDateTimeInput.range_validator_class = int

BaseModelForm = model_form_factory(Form)


class ModelForm(BaseModelForm):
    @classmethod
    def get_session(self):
        return db.session


def morning(at=9):
    return ((datetime.datetime.now() + datetime.timedelta(days=1))
            .replace(hour=at, minute=0, second=0))


def midnight(days=8):
    return ((datetime.datetime.now() + datetime.timedelta(days=days))
            .replace(hour=23, minute=59, second=59))


class Difference(object):
    def __init__(self, fieldname, difference, message):
        self.fieldname = fieldname
        self.difference = difference
        self.message = message

    def __call__(self, form, field):
        try:
            other = form[self.fieldname]
        except KeyError:
            raise validators.ValidationError(field.gettext("Invalid field name '%s'.") % self.fieldname)
        if field.data - other.data <= self.difference:
            raise validators.ValidationError(self.message)


class BallotForm(ModelForm):
    class Meta:
        model = Ballot
        only = ["type", "name", "description", "unit",
                "supporters_too", "max_votes", "begin_at", "finish_at"]
        field_args = {
            "name": {
                "validators": [validators.Length(min=10)],
                "description": u"Např. Volba předsedy Jihomoravského KrS",
            },
            "begin_at": {
                "validators": [DateRange(min=lambda: datetime.datetime.now()+datetime.timedelta(hours=1), message=u"Začátek musí být nejméně za hodinu.")],
                "default": lambda: morning(),
            },
            "finish_at": {
                "validators": [Difference("begin_at", difference=datetime.timedelta(hours=72), message=u"Trvání musí být nejméně 72 hodin.")],
                "default": lambda: midnight(),
                "description": u"Trvání musí být nejméně 72 hodin.",
            }
        }
BallotForm.submit = SubmitField(u'Uložit')
