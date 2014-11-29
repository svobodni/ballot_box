# -*- coding: utf-8 -*-
from ballot_box import app, db
from models import Connection, User, Ballot, BallotOption, Vote, Voter
from forms import BallotForm, BallotEditForm
from registry import registry_request, registry_units
from flask import (render_template, g, request, redirect, url_for, session,
                   abort, flash)
from wtforms.validators import ValidationError
from functools import wraps
import json
import pickle
import datetime
from os import urandom
from base64 import b64encode
import hashlib


def force_auth():
    return redirect(app.config["REGISTRY_URI"] +
                    "/auth/token?redirect_uri=" +
                    url_for('login', _external=True))


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if g.get("user", None) is None:
            conn_id = session.get("conn_id", False)
            conn_token = session.get("conn_token", False)
            if conn_id and conn_token:
                conn = (db.session.query(Connection)
                        .filter(Connection.id == conn_id)
                        .filter(Connection.token == conn_token)
                        .filter(Connection.remote_addr == request.remote_addr)
                        .filter(Connection.last_click > datetime.datetime.now()-app.config["LOGIN_TIMEOUT"])
                        .first())
                if conn is not None:
                    try:
                        profile = json.loads(conn.profile)
                        g.user = User(profile, conn.jwt)
                    except:
                        return force_auth()
                    return f(*args, **kwargs)

            return force_auth()
        return f(*args, **kwargs)
    return decorated_function


@app.route("/")
@login_required
def index():
    return render_template('index.html')


@app.route("/login/")
def login():
    jwt = request.args.get("jwt", False)
    if not jwt:
        return force_auth()
    r = registry_request("/auth/profile.json", jwt)
    try:
        profile = r.json()
        conn = Connection()
        conn.token = b64encode(urandom(30))[:30]
        conn.logged_in = datetime.datetime.now()
        conn.last_click = conn.logged_in
        conn.remote_addr = request.remote_addr
        conn.user_id = profile["person"]["id"]
        conn.name = profile["person"]["name"]
        conn.profile = r.text
        conn.jwt = jwt
        db.session.add(conn)
        db.session.commit()
        session["conn_id"] = conn.id
        session["conn_token"] = conn.token
        return redirect(url_for("index"))
    except:
        raise
        return force_auth()


@app.route("/ballot/")
@login_required
def ballot_list():
    if not g.user.can_list_ballot():
        abort(403)
    ballots = db.session.query(Ballot).order_by(Ballot.id.desc())
    return render_template('ballot_list.html', ballots=ballots)


@app.route("/ballot/new/", methods=('GET', 'POST'))
@login_required
def ballot_new():
    if not g.user.can_create_ballot():
        abort(403)
    form = BallotForm()
    if form.validate_on_submit():
        ballot = Ballot()
        form.populate_obj(ballot)
        db.session.add(ballot)
        db.session.commit()
        flash(u"Volba/hlasování bylo úspěšně přidáno.", "success")
        return redirect(url_for("ballot_list"))
    return render_template('ballot_new.html', form=form)


@app.route("/ballot/<int:ballot_id>/", methods=('GET', 'POST'))
@login_required
def ballot_edit(ballot_id):
    if not g.user.can_edit_ballot():
        abort(403)
    ballot = db.session.query(Ballot).get(ballot_id)
    if ballot is None:
        abort(404)
    if ballot.in_time_progress():
        abort(403)
    form = BallotEditForm(request.form, ballot)
    if form.validate_on_submit():
        form.populate_obj(ballot)
        db.session.add(ballot)
        db.session.commit()
        flash(u"Volba/hlasování bylo úspěšně změněno.", "success")
        return redirect(url_for("ballot_list"))
    return render_template('ballot_edit.html', form=form)


@app.route("/ballot/<int:ballot_id>/options/", methods=('GET', 'POST'))
@login_required
def ballot_options(ballot_id):
    if not g.user.can_edit_ballot_options():
        abort(403)
    ballot = db.session.query(Ballot).get(ballot_id)
    if ballot is None:
        abort(404)
    if ballot.in_time_progress():
        abort(403)
    if request.method == 'POST':
        added = 0
        removed = 0
        unchanged = 0
        bos = set(request.values.getlist('bo')) - set([u""])
        for db_option in ballot.options:
            if db_option.title not in bos:
                db.session.delete(db_option)
                removed += 1
            else:
                bos.discard(db_option.title)
                unchanged += 1
        for option in bos:
            db_option = BallotOption()
            db_option.title = option
            db_option.ballot = ballot
            db.session.add(db_option)
            added += 1
        db.session.commit()
        flash(u"Úspěšně přidáno {}, obebráno {}, nezměněno {}"
              .format(added, removed, unchanged), "success")
        return redirect(url_for("ballot_list"))
    return render_template('ballot_options.html', ballot=ballot)


@app.route("/polling_station/")
@app.route("/volebni_mistnost/")
@login_required
def polling_station():
    # TODO: filter ballots
    ballots = db.session.query(Ballot).order_by(Ballot.id.desc())
    return render_template('polling_station.html', ballots=ballots)


@app.route("/polling_station/<int:ballot_id>/")
@app.route("/volebni_mistnost/<int:ballot_id>/")
@login_required
def polling_station_item(ballot_id):
    ballot = db.session.query(Ballot).get(ballot_id)
    if ballot is None:
        abort(404)
    if not g.user.can_vote(ballot):
        abort(403)
    if request.method == 'POST':
        pass
    return render_template('polling_station_item.html', ballot=ballot)


def validate_options(input_options, ballot):
    allowed_option_ids = set(option.id for option in ballot.options)
    invalid_options = set(input_options.keys())-allowed_option_ids
    if len(invalid_options) > 0:
        raise ValidationError(u"Možnost/i ID {} jsou neplatné."
                              .format(", ".join(invalid_options)))
    if not ballot.is_yes_no and any(value != 1 for value in input_options.values()):
        raise ValidationError(u"Lze udílet pouze hlasy PRO (+1).")
    elif ballot.is_yes_no and any(value != 1 and value != -1 for value in input_options.values()):
        raise ValidationError(u"Lze udílet pouze hlasy PRO NÁVRH (+1) a PROTI NÁVRHU (-1).")
    if len(input_options) == 0:
        raise ValidationError(u"Musíte udělit nejméně jeden hlas.")
    if len(input_options) > ballot.max_votes:
        raise ValidationError(u"Můžete udělit nejvýše {} hlasů.".format(ballot.max_votes))
    return True


@app.route("/polling_station/<int:ballot_id>/confirm", methods=('POST',))
@app.route("/volebni_mistnost/<int:ballot_id>/potvrdit", methods=('POST',))
@login_required
def polling_station_confirm(ballot_id):
    ballot = db.session.query(Ballot).get(ballot_id)
    if ballot is None:
        abort(404)
    if not g.user.can_vote(ballot):
        abort(403)

    input_options = {}
    try:
        for key in request.form.keys():
            key_split = key.split(',')
            if len(key_split) == 2 and key_split[0] == 'option':
                option_id = int(key_split[1])
                if option_id in input_options:
                    raise ValidationError(u"Možnost ID {} zvolena vícekrát."
                                          .format(option_id))
                else:
                    input_options[option_id] = int(request.form[key])
        validate_options(input_options, ballot)
    except ValidationError as e:
        flash(unicode(e), "danger")
        return redirect(url_for('polling_station_item', ballot_id=ballot_id))
    except ValueError as e:
        flash(u"Některý z hlasů má neplatnou hodnotu", "danger")
        return redirect(url_for('polling_station_item', ballot_id=ballot_id))

    title_dict = {option.id: option.title for option in ballot.options}
    summary = [{"title": title_dict[option_id], "value":input_options[option_id]}
               for option_id in sorted(input_options.keys(), key=lambda x: title_dict[x])]
    input_options_pickle = pickle.dumps(input_options)
    hash_base = "{}*{}*{}*{}".format(ballot_id, g.user.id, input_options, b64encode(urandom(30))[:15])

    return render_template('polling_station_confirm.html',
                           ballot=ballot,
                           options_summary=summary,
                           input_options_data=input_options_pickle,
                           hash_base=hash_base)


@app.route("/polling_station/<int:ballot_id>/vote", methods=('POST',))
@app.route("/volebni_mistnost/<int:ballot_id>/hlasovat", methods=('POST',))
@login_required
def polling_station_vote(ballot_id):
    ballot = db.session.query(Ballot).get(ballot_id)
    if ballot is None:
        abort(404)
    if not g.user.can_vote(ballot):
        abort(403)

    input_options = pickle.loads(request.form["input_options_data"])
    print(input_options)
    try:
        validate_options(input_options, ballot)
    except ValidationError as e:
        flash(unicode(e), "danger")
        return redirect(url_for('polling_station_item', ballot_id=ballot_id))
    except ValueError as e:
        flash(u"Některý z hlasů má neplatnou hodnotu", "danger")
        return redirect(url_for('polling_station_item', ballot_id=ballot_id))

    hash_base = request.form["hash_base"]
    h = hashlib.sha1()
    h.update(hash_base)
    # h.update(urandom(30))
    hash_digest = h.hexdigest()

    for (option_id, value) in input_options.items():
        vote = Vote()
        vote.ballot_option_id = option_id
        vote.value = value
        vote.hash_digest = hash_digest
        db.session.add(vote)

    voter = Voter()
    voter.ballot_id = ballot_id
    voter.name = g.user.name
    voter.email = g.user.email
    voter.person_id = g.user.id
    voter.voted_at = datetime.datetime.now()
    voter.remote_addr = request.remote_addr
    voter.user_agent = request.user_agent.string
    db.session.add(voter)

    db.session.commit()

    return render_template('polling_station_vote.html',
                           ballot=ballot, hash_digest=hash_digest)
