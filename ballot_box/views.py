from ballot_box import app, db
from models import Connection, User
from flask import render_template, g, request, redirect, url_for, session
from functools import wraps
import json
import datetime
import requests
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
                        g.user = User(profile)
                        return f(*args, **kwargs)
                    except:
                        pass

            return force_auth()
        return f(*args, **kwargs)
    return decorated_function


@app.route("/")
@login_required
def index():
    return render_template('index.html')


@app.route("/login")
def login():
    jwt = request.args.get("jwt", False)
    if not jwt:
        return force_auth()
    headers = {"Authorization": "Bearer {}".format(jwt)}
    r = requests.get(app.config["REGISTRY_URI"] + "/auth/profile.json",
                     headers=headers)
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
        db.session.add(conn)
        db.session.commit()
        session["conn_id"] = conn.id
        session["conn_token"] = conn.token
        return redirect(url_for("index"))
    except:
        raise
        return force_auth()
