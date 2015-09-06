# -*- coding: utf-8 -*-
import json
import requests
from ballot_box import app, BallotBoxError, mail
from flask import g, request, render_template
from flask.ext.mail import Message


def get_jwt(jwt=None):
    if jwt is None:
        jwt = request.args.get("jwt", None)
        if jwt is None:
            jwt = g.user.jwt
    if jwt is None:
        raise BallotBoxError(u"Autorizační token nenalezen.")
    return jwt


def registry_request(resource, jwt=None):
    jwt = get_jwt(jwt)
    headers = {"Authorization": "Bearer {}".format(jwt)}
    return requests.get(app.config["REGISTRY_URI"] + resource,
                        headers=headers)


def registry_units():
    units = [("country,1", u"Celá republika")]
    try:
        r = registry_request("/regions.json")
        regions = r.json()["regions"]
        for region in regions:
            units.append(("region,{}".format(region["id"]), region["name"]))
    except KeyError:
        pass

    try:
        r = registry_request("/bodies.json")
        bodies = r.json()["bodies"]
        for body in bodies:
            # Only republic organs
            if body["organization"]["id"] == 100:
                units.append(("body,{}".format(body["id"]), body["name"]))
    except KeyError:
        pass
    return units


def send_vote_confirmation(ballot, voter, hash_digest, hash_salt, vote_timestamp, jwt=None):
    body = render_template('confirmation_email.txt',
                           ballot=ballot,
                           voter=voter,
                           hash_digest=hash_digest,
                           hash_salt=hash_salt,
                           vote_timestamp=vote_timestamp)

    if app.config["USE_SMTP"]:
        msg = Message("Potvrzení hlasování",
                      sender=(u"Volební komise", "vk@svobodni.cz"),
                      recipients=[g.user.email])
        msg.body = body
        mail.send(msg)
    else:
        jwt = get_jwt(jwt)
        email_dict = {
            "auth": jwt,
            "from": {
                "name": "Volební komise",
                "email": "vk@svobodni.cz"
            },
            "subject": "Potvrzení hlasování",
            "plain": body,
            "files": [],
            "recipients": [{
                "email": g.user.email,
            }]
        }

        r = requests.post("https://mailer.svobodni.cz/json/send",
                          data=json.dumps(email_dict))
        if r.status_code != requests.codes.ok:
            raise BallotBoxError("Nepodařilo se odeslat e-mail s potrvzením volby.")

    return body
