# -*- coding: utf-8 -*-

import datetime

from flask_wtf import Form
from wtforms import SubmitField, validators, SelectField, DateField
from wtforms_alchemy import model_form_factory
from wtforms_components import DateRange
from wtforms_components.widgets import BaseDateTimeInput

# The variable db here is a SQLAlchemy object instance from
# Flask-SQLAlchemy package
from ballot_box import db
from models import Ballot, BallotProtocol, Settings, UNITS
from utils import add_years

# Workaround to fix lambdas in DateRange(min)
BaseDateTimeInput.range_validator_class = int
BaseModelForm = model_form_factory(Form)

validator_name = validators.Length(
    min=10, message=u"Název musí mít alespoň 10 znaků.")


class ModelForm(BaseModelForm):
    @classmethod
    def get_session(self):
        return db.session


def morning(days=1, at=9):
    return ((datetime.datetime.now() + datetime.timedelta(days=days))
            .replace(hour=at, minute=0, second=0))


def midnight(days=10):
    return ((datetime.datetime.now() + datetime.timedelta(days=days))
            .replace(hour=23, minute=59, second=59))


def min_timedelta(*args, **kwargs):
    return lambda: datetime.datetime.now() \
        + datetime.timedelta(*args, **kwargs)


class Difference(object):
    def __init__(self, fieldname, difference, message, reverse=False, enabled=None):
        self.fieldname = fieldname
        self.difference = difference
        self.message = message
        self.reverse = reverse
        self.enabled = enabled

    def __call__(self, form, field):
        if self.enabled != None:
            try:
                enabledfield = form[self.enabled]
            except KeyError:
                raise validators.ValidationError(
                    field.gettext("Invalid field name '%s'.") % self.enabled
                )
        try:
            other = form[self.fieldname]
        except KeyError:
            raise validators.ValidationError(
                field.gettext("Invalid field name '%s'.") % self.fieldname
            )
        if self.enabled == None or enabledfield.data:
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
                "candidate_self_signup", "candidate_signup_from",
                "candidate_signup_until", "quorum"]
        field_args = {
            "name": {
                "validators": [validator_name],
                "description": u"Např. Volba předsedy Jihomoravského KrS",
            },
            "begin_at": {
                "validators": [
                    DateRange(
                        min=min_timedelta(hours=1),
                        message=u"Začátek musí být nejdříve za hodinu."),
                ],
                "default": lambda: morning(days=3, at=9),
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
            "candidate_signup_from": {
                "validators": [validators.Optional()],
            },
            "candidate_signup_until": {
                "validators": [
                    validators.Optional(),
                    Difference(
                        "begin_at",
                        difference=datetime.timedelta(hours=-24),
                        message=u"Konec přihlašování musí být "
                        u"nejméně 24 hodin před začátkem voleb.",
                        reverse=True,
                        enabled="candidate_self_signup"
                    ),
                ],
                "default": lambda: midnight(days=1),
                "description": u"Nejméně 24 hodin před začátkem voleb.",
            },
            "quorum": {
                "description": u"Minimální počet hlasů, nutných k zvolení. Nechte prázdné, pokud nechcete aplikovat.<span><br />" + \
                               u"Momentální počet členů zvolené jednotky je <span id=\"unit_members_count\">?</span>, nadpoloviční většina <b>?</b>.</span>"
            }
        }
BallotForm.submit = SubmitField(u'Uložit')


class BallotEditForm(ModelForm):
    class Meta:
        model = Ballot
        only = ["type", "name", "description", "unit",
                "supporters_too", "max_votes", "begin_at", "finish_at",
                "candidate_self_signup", "candidate_signup_from",
                "candidate_signup_until", "quorum", "approved", "cancelled"]
        field_args = {
            "name": {
                "validators": [validator_name],
            },
            "begin_at": {
                "validators": [
                    DateRange(
                        min=min_timedelta(minutes=5),
                        message=u"Začátek musí být nejméně za 5 minut."
                    ),
                ],
                "default": lambda: morning(days=3, at=9),
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
            "candidate_signup_from": {
                "validators": [validators.Optional()],
            },
            "candidate_signup_until": {
                "validators": [validators.Optional()],
                "default": lambda: midnight(days=1),
            },
            "quorum": {
                "description": u"Minimální počet hlasů, nutných k zvolení. Nechte prázdné, pokud nechcete aplikovat.<span><br />" + \
                               u"Momentální počet členů zvolené jednotky je <span id=\"unit_members_count\">?</span>, nadpoloviční většina <b>?</b>.</span>"
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


class SettingsForm(ModelForm):
    class Meta:
        model = Settings
        only = ["signature"]
SettingsForm.submit = SubmitField(u'Uložit')


class ExportResultsForm(Form):
    body = SelectField(u'Jednotka', choices=filter(lambda o: o[0][:4] == "body", UNITS))
    membertype = SelectField(u'Funkce', choices=[('Member', u'Člen'), ('Coordinator', u'Koordinátor'), ('Vicepresident', u'Místopředseda'), ('President', u'Předseda')])
    since = DateField(u'Od', format='%Y-%m-%d', default = datetime.datetime.now())
    till = DateField(u'Do', format='%Y-%m-%d', default = add_years(datetime.datetime.now(), 2))
    
ExportResultsForm.submit = SubmitField(u'Exportovat')
