# -*- coding: utf-8 -*-
import requests
from ballot_box import app
from flask import g, request


def registry_request(resource, jwt=None):
    if jwt is None:
        jwt = request.args.get("jwt", None)
        if jwt is None:
            jwt = g.user.jwt
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
