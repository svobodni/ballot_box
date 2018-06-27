# -*- coding: utf-8 -*-

import time
import hashlib
import datetime
from os import urandom
from base64 import b64encode

from flask import render_template
from flask_mail import Message
from celery.utils.log import get_task_logger

from ballot_box import celery, db, mail, app
from ballot_box.models import Ballot, Abstainer
from ballot_box.registry import get_people
from ballot_box.utils import compute_hash_base

logger = get_task_logger(__name__)


@celery.task()
def add_abstainers(ballot_id, jwt):
    ballot = db.session.query(Ballot).get(ballot_id)
    right_to_vote = get_people(ballot, jwt)
    voter_ids = set(v.person_id for v in ballot.voters)
    abstainers = [p for p in right_to_vote if p["id"] not in voter_ids]

    for a in abstainers:
        abstainer = Abstainer()
        abstainer.ballot = ballot
        abstainer.name = u"{0} {1}".format(
            a.get("first_name", ""),
            a.get("last_name", ""),
        )
        abstainer.email = a.get("email", "")
        abstainer.person_id = a["id"]
        abstainer.hash_salt = b64encode(urandom(30))[:15]
        abstainer.created_at = datetime.datetime.now()
        hash_base = compute_hash_base(
            ballot_id, abstainer.person_id, {},
            int(time.mktime(abstainer.created_at.timetuple())))
        h = hashlib.sha1()
        h.update(hash_base.encode("utf-8"))
        h.update(abstainer.hash_salt.encode("utf-8"))
        abstainer.hash_digest = h.hexdigest()
        db.session.add(abstainer)
        logger.info(
            u"Added abstainer {0} {1}".format(abstainer.name, abstainer.email),
        )
    db.session.commit()
    return ballot_id


def send_abstainer_confirmation(abstainer_id):
    abstainer = db.session.query(Abstainer).get(abstainer_id)
    ballot = abstainer.ballot
    body = render_template(
        'abstainer_email.txt',
        ballot=ballot,
        abstainer=abstainer,
        timestamp=int(time.mktime(abstainer.created_at.timetuple())),
    )

    if app.config["USE_SMTP"]:
        msg = Message(u"Potvrzení o zdržení se hlasování",
                      sender=(u"Volební komise", "vk@svobodni.cz"),
                      recipients=[abstainer.email])
        msg.body = body
        logger.info(u"Sending abstainer confirmation {0} {1}"
                    .format(abstainer.name, abstainer.email))
        mail.send(msg)
        logger.info(u"Abstainer confirmation sent {0} {1}"
                    .format(abstainer.name, abstainer.email))
    else:
        # Only SMTP supported here
        logger.warning(u"Not sending abstainer confirmation {0} {1}"
                       .format(abstainer.name, abstainer.email))

    abstainer.confirmation_sent = True


@celery.task()
def send_abstainer_confirmations(ballot_id, resend_all=False):
    abstainers = db.session.query(Abstainer).filter_by(ballot_id=ballot_id)

    if not resend_all:
        abstainers = abstainers.filter_by(confirmation_sent=False)

    for a in abstainers.all():
        try:
            send_abstainer_confirmation(a.id)
        except Exception as e:
            logger.error(e, exc_info=True)

    db.session.commit()
