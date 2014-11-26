# -*- coding: utf-8 -*-
from ballot_box import app, db
from models import Connection, User, Ballot
from forms import BallotForm
from registry import registry_request, registry_units
from flask import (render_template, g, request, redirect, url_for, session,
                   abort, flash)
from functools import wraps
import json
import datetime
from os import urandom
from base64 import b64encode


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
    ballots = db.session.query(Ballot).order_by(Ballot.finish_at.desc())
    return render_template('ballot_list.html', ballots=ballots)


@app.route("/ballot/new/", methods=('GET', 'POST'))
@login_required
def ballot_new():
    if not g.user.can_create_ballot():
        abort(403)
    form = BallotForm()
    #form.unit.choices = registry_units()
    if form.validate_on_submit():
        ballot = Ballot()
        form.populate_obj(ballot)
        db.session.add(ballot)
        db.session.commit()
        flash(u"Volba/hlasování bylo úspěšně přidáno.", "success")
        return redirect(url_for("ballot_list"))
    return render_template('ballot_new.html', form=form)
