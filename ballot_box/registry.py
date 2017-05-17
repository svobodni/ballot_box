# -*- coding: utf-8 -*-

import json

import requests
from flask import g, request, render_template
from flask.ext.mail import Message

from ballot_box import app, cache, mail, BallotBoxError


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

def registry_body_members():
    units = {}
    try:
        r = registry_request("/bodies.json")
        bodies = r.json()["bodies"]
        for body in bodies:
            # Only republic organs
            if body["organization"]["id"] == 100:
                units["body,{}".format(body["id"])] = len(body["members"])
    except KeyError:
        pass
    return units

def send_vote_confirmation(ballot, voter, hash_digest, hash_salt,
                           vote_timestamp, jwt=None):
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
            raise BallotBoxError(
                "Nepodařilo se odeslat e-mail s potrvzením volby."
            )

    return body


def get_people(ballot, jwt=None):
    (unit_type, unit_id) = tuple(ballot.unit.code.split(','))
    region_id = None

    if unit_type == "region":
        region_id = int(unit_id)
    elif unit_type != "country":
        # don't support other type of units
        return []

    return registry_get_people(not ballot.supporters_too,
                               region_id, jwt=get_jwt(jwt))


def registry_get_people(members_only=False, region_id=None, jwt=None):
    all_people = cache.get("people")

    if all_people is None:
        r = registry_request(
            "/people.json{0}".format(
                "?region_id={0}".format(region_id) if region_id else ""
            ),
            jwt=jwt,
        )
        all_people = r.json()["people"]
        cache.set("people", all_people, timeout=1e4)

    people = []

    for p in all_people:
        status_ok = p.get("status", "") in \
            ("regular_member", "regular_supporter")

        member_ok = not members_only or \
            p.get("member_status", "") == "regular_member"

        region_ok = not region_id or \
            p.get("domestic_region", {}).get("id", -1) == region_id

        if member_ok and status_ok and region_ok:
            people.append(p)

    return people
