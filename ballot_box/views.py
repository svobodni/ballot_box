# -*- coding: utf-8 -*-

import json
import time
import pickle
import urllib
import hashlib
import datetime
from os import urandom
from functools import wraps
from collections import defaultdict
from base64 import b64encode, b64decode

import bleach
from flask import render_template, g, request, redirect, \
    url_for, session, abort, flash, Markup
from wtforms.validators import ValidationError
from babel.dates import format_datetime, format_date

from utils import compute_hash_base, DAYS_RANGE
from ballot_box import app, db, BallotBoxError, tasks
from models import Connection, User, Ballot, \
    BallotOption, Vote, Voter, BallotProtocol
from forms import BallotForm, BallotEditForm, \
    BallotProtocolForm, BallotProtocolEditForm
from registry import registry_request, send_vote_confirmation, get_jwt


def sanitize_html(html, extended=False):
    allowed_tags = bleach.ALLOWED_TAGS + ['p']
    allowed_attrs = bleach.ALLOWED_ATTRIBUTES
    if extended:
        allowed_tags += ['p', 'table', 'thead', 'tbody', 'tr', 'th', 'td',
                         'dd', 'dt', 'dl', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6']
        allowed_attrs['*'] = ['class']

    return bleach.clean(html, tags=allowed_tags, attributes=allowed_attrs)


def force_auth():
    return redirect(
        "%s/auth/token?%s" % (
            app.config["REGISTRY_URI"],
            urllib.urlencode({
                "redirect_uri": url_for(
                    'login',
                    redirect_after=b64encode(request.url),
                    _external=True
                ),
            }),
        )
    )


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if g.get("user", None) is None:
            conn_id = session.get("conn_id", False)
            conn_token = session.get("conn_token", False)

            if conn_id and conn_token:
                conn = (db.session.query(Connection)
                                  .filter_by(id=conn_id, token=conn_token,
                                             remote_addr=request.remote_addr)
                                  .filter(Connection.last_click
                                          > datetime.datetime.now()
                                          - app.config["LOGIN_TIMEOUT"])
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


@app.template_filter('fmt_dt')
def fmt_dt_filter(dt):
    return format_datetime(dt, format='EEEE d. M. yyyy HH:mm', locale='cs_CZ')


@app.template_filter('fmt_dt_line')
def fmt_dt_line_filter(dt):
    return Markup("&nbsp;".join(format_datetime(
        dt, format='d. M. yyyy HH:mm', locale='cs_CZ').split(" ")))


@app.template_filter('fmt_dt_range')
def fmt_dt_range_filter(dt):
    return u"%s %s" % (
        DAYS_RANGE[dt.weekday()],
        format_datetime(dt, format='d. M. yyyy HH:mm', locale='cs_CZ'),
    )


@app.template_filter('fmt_d')
def fmt_d_filter(d):
    return format_date(d, format='EEEE d. M. yyyy', locale='cs_CZ')


@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404


@app.errorhandler(403)
def forbidden(e):
    return render_template('403.html'), 403


@app.errorhandler(BallotBoxError)
def handle_ballot_box_error(error):
    return (render_template('error.html', message=error.message),
            error.status_code)


@app.route("/registry/people.json")
@login_required
def registry_people():
    return registry_request("/people.json").text


@app.route("/registry/people/<int:user_id>.json")
@login_required
def registry_person(user_id):
    return registry_request("/people/{}.json".format(user_id)).text


@app.route("/")
@login_required
def index():
    return render_template('index.html')


@app.route("/login/")
@app.route("/login/<redirect_after>/")
def login(redirect_after=None):
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
        if redirect_after:
            return redirect(b64decode(redirect_after))
        return redirect(url_for("index"))
    except:
        raise
        return force_auth()


@app.route("/ballot/")
@login_required
def ballot_list():
    if not g.user.can_list_ballot():
        abort(403)
    ballots = db.session.query(Ballot).order_by(Ballot.begin_at.desc())
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
        ballot.description = sanitize_html(ballot.description)
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
    if ballot.in_progress or ballot.is_finished:
        abort(403)
    form = BallotEditForm(request.form, ballot)
    if form.validate_on_submit():
        form.populate_obj(ballot)
        ballot.description = sanitize_html(ballot.description)
        db.session.add(ballot)

        if ballot.approved and ballot.type == "VOTING" and not ballot.options:
            db_option = BallotOption()
            db_option.title = ballot.name
            db_option.ballot = ballot
            db.session.add(db_option)

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
    if ballot.in_progress or ballot.is_finished:
        abort(403)
    if request.method == 'POST':
        added = 0
        removed = 0
        unchanged = 0
        bos = set()
        for key in request.values.keys():
            try:
                name, index = key.rsplit('-')
                if name == "bo":
                    bos.add((
                        request.values.get(key),
                        request.values.get("bo-userid-" + index, "")
                    ))
            except:
                pass
        bos = bos - set([(u"", u"")])
        for db_option in ballot.options:
            bo = (db_option.title, unicode(db_option.user_id or ""))
            if bo not in bos:
                db.session.delete(db_option)
                removed += 1
            else:
                bos.discard(bo)
                unchanged += 1
        for (title, user_id) in bos:
            db_option = BallotOption()
            db_option.title = title
            try:
                db_option.user_id = int(user_id)
            except:
                db_option.user_id = None
            db_option.ballot = ballot
            db.session.add(db_option)
            added += 1
        db.session.commit()
        flash(u"Úspěšně přidáno {}, obebráno {}, nezměněno {}"
              .format(added, removed, unchanged), "success")
        return redirect(url_for("ballot_list"))
    return render_template('ballot_options.html', ballot=ballot)


@app.route("/ballot/<int:ballot_id>/preview/")
@login_required
def ballot_preview(ballot_id):
    if not g.user.can_edit_ballot_options():
        abort(403)
    ballot = db.session.query(Ballot).get(ballot_id)
    if ballot is None:
        abort(404)
    if ballot.is_yes_no:
        return render_template('polling_station_mark_yes_no.html',
                               ballot=ballot)
    return render_template('polling_station_mark_regular.html', ballot=ballot)


@app.route("/ballot/<int:ballot_id>/protocol/")
@login_required
def ballot_protocol_list(ballot_id):
    if not g.user.can_edit_ballot():
        abort(403)
    ballot = db.session.query(Ballot).get(ballot_id)
    if ballot is None:
        abort(404)
    return render_template('ballot_protocol_list.html', ballot=ballot)


@app.route("/ballot/<int:ballot_id>/protocol/new/", methods=('GET', 'POST'))
@login_required
def ballot_protocol_new(ballot_id):
    if not g.user.can_edit_ballot():
        abort(403)
    ballot = db.session.query(Ballot).get(ballot_id)
    if ballot is None:
        abort(404)
    today = datetime.date.today()
    name = g.user.name
    form = BallotProtocolForm()
    result = ballot_result(ballot)
    if form.validate_on_submit():
        protocol = BallotProtocol()
        protocol.ballot_id = ballot.id
        form.populate_obj(protocol)
        protocol.body_html = sanitize_html(protocol.body_html, extended=True)
        db.session.add(protocol)
        db.session.commit()
        flash(u"Protokol úspěšně uložen.", "success")
        return redirect(url_for("ballot_protocol_list", ballot_id=ballot_id))
    form.body_html.data = render_template(
        'protocol_template.html', ballot=ballot, name=name, date=today,
        result=result, elected=filter(lambda o: o["elected"], result))
    return render_template('ballot_protocol_new.html', form=form)


@app.route("/ballot/<int:ballot_id>/mail_template/")
@login_required
def ballot_mail_template(ballot_id):
    if not g.user.can_edit_ballot():
        abort(403)
    ballot = db.session.query(Ballot).get(ballot_id)
    if ballot is None:
        abort(404)
    return render_template('ballot_mail_template.html', ballot=ballot)


@app.route("/ballot/<int:ballot_id>/abstainers/", methods=('GET', 'POST'))
@login_required
def ballot_abstainers(ballot_id):
    if not g.user.can_edit_ballot():
        abort(403)
    ballot = db.session.query(Ballot).get(ballot_id)
    if ballot is None:
        abort(404)
    if not ballot.is_finished:
        abort(404)
    if request.method == "POST" and request.values.get("add_abstainers"):
        tasks.add_abstainers.delay(ballot_id=ballot.id, jwt=get_jwt())
        flash(u"Akce přidání nevoličů asynchronně spuštěna.", "success")
    elif (request.method == "POST" and
          request.values.get("send_abstainer_confirmations")):
        tasks.send_abstainer_confirmations.delay(ballot_id=ballot.id)
        flash(
            u"Akce odeslání potvrzení nevoličům asynchronně spuštěna.",
            "success"
        )
    abstainers = list(ballot.abstainers)
    return render_template(
        'ballot_abstainers.html', ballot=ballot,
        abstainers_len=len(abstainers),
        abstainers_unconfirmed_len=sum(
            1 for a in abstainers if not a.confirmation_sent
        ),
    )


@app.route("/protocol/")
@app.route("/protokol/")
@login_required
def protocol_list():
    protocols = (db.session.query(BallotProtocol)
                           .filter_by(approved=True)
                           .order_by(BallotProtocol.created_at.desc()))
    return render_template('protocol_list.html', protocols=protocols)


@app.route("/protocol/<int:protocol_id>/edit", methods=('GET', 'POST'))
@login_required
def ballot_protocol_edit(protocol_id):
    if not g.user.can_edit_ballot():
        abort(403)
    protocol = db.session.query(BallotProtocol).get(protocol_id)
    if protocol is None:
        abort(404)
    form = BallotProtocolEditForm(request.form, protocol)
    if form.validate_on_submit():
        form.populate_obj(protocol)
        protocol.body_html = sanitize_html(protocol.body_html, extended=True)
        db.session.add(protocol)
        db.session.commit()
        flash(u"Protokol úspěšně uložen.", "success")
        return redirect(url_for(
            "ballot_protocol_list", ballot_id=protocol.ballot_id))
    return render_template('protocol_edit.html', form=form)


@app.route("/protocol/<int:protocol_id>/")
@app.route("/protokol/<int:protocol_id>/")
@login_required
def protocol_item(protocol_id):
    protocol = db.session.query(BallotProtocol).get(protocol_id)
    if protocol is None:
        abort(404)
    if not g.user.can_edit_ballot() and not protocol.approved:
        raise BallotBoxError(u"Protokol ještě nebyl schválen.", 403)
    return render_template('protocol_item.html', protocol=protocol)


@app.route("/polling_station/")
@app.route("/volebni_mistnost/")
@login_required
def polling_station():
    ballots = (db.session.query(Ballot)
               .filter_by(approved=True)
               .filter(Ballot.finish_at >
                       datetime.datetime.now() - datetime.timedelta(days=60))
               .order_by(Ballot.begin_at.desc()))
    ballot_groups = {
        "not_voted": [],
        "already_voted": [],
        "finished": [],
        "other": []
    }
    for ballot in ballots:
        if ballot.is_finished:
            ballot_groups["finished"].append(ballot)
        elif g.user.already_voted(ballot):
            ballot_groups["already_voted"].append(ballot)
        elif g.user.can_vote(ballot) and ballot.in_progress:
            ballot_groups["not_voted"].append(ballot)
        else:
            ballot_groups["other"].append(ballot)
    return render_template('polling_station.html', ballot_groups=ballot_groups)


def permit_voting(ballot):
    if g.user.already_voted(ballot):
        raise BallotBoxError(u"Již jste hlasoval/a.", 403)
    if not g.user.can_vote(ballot):
        raise BallotBoxError(u"Nemáte právo hlasovat.", 403)
    if ballot.cancelled:
        raise BallotBoxError(u"Tato volba byla zrušena.", 404)
    if ballot.is_finished:
        raise BallotBoxError(u"Tato volba již skončila.", 404)
    if not ballot.approved:
        raise BallotBoxError(
            u"Tato volba nebyla schválena Volební komisí.", 404)
    if not ballot.in_progress:
        raise BallotBoxError(u"Tato volba nyní neprobíhá.", 404)


@app.route("/polling_station/<int:ballot_id>/")
@app.route("/volebni_mistnost/<int:ballot_id>/")
@login_required
def polling_station_item(ballot_id):
    ballot = db.session.query(Ballot).get(ballot_id)
    if ballot is None:
        abort(404)
    permit_voting(ballot)
    if ballot.is_yes_no:
        return render_template('polling_station_mark_yes_no.html',
                               ballot=ballot)
    return render_template('polling_station_mark_regular.html', ballot=ballot)


def validate_options(input_options, ballot):
    allowed_option_ids = set(option.id for option in ballot.options)
    invalid_options = set(input_options.keys()) - allowed_option_ids
    if len(invalid_options) > 0:
        raise ValidationError(u"Možnost/i ID {} jsou neplatné."
                              .format(", ".join(invalid_options)))
    if (not ballot.is_yes_no and
        any(value != 1
            for value in input_options.values())):
        raise ValidationError(u"Lze udílet pouze hlasy PRO (+1).")
    elif (ballot.is_yes_no and
          any(value != 1 and value != -1
              for value in input_options.values())):
        raise ValidationError(
            u"Lze udílet pouze hlasy PRO NÁVRH (+1) a PROTI NÁVRHU (-1).")
    if len(input_options) == 0:
        raise ValidationError(u"Musíte udělit nejméně jeden hlas.")
    if len(input_options) > ballot.max_votes:
        raise ValidationError(
            u"Můžete udělit nejvýše {} hlasů.".format(ballot.max_votes))
    return True


@app.route("/polling_station/<int:ballot_id>/confirm/", methods=('POST',))
@app.route("/volebni_mistnost/<int:ballot_id>/potvrdit/", methods=('POST',))
@login_required
def polling_station_confirm(ballot_id):
    ballot = db.session.query(Ballot).get(ballot_id)
    if ballot is None:
        abort(404)
    permit_voting(ballot)

    input_options = {}
    try:
        for key in request.form.keys():
            key_split = key.split(',')
            if len(key_split) == 2 and key_split[0] == 'option':
                option_id = int(key_split[1])
                if option_id in input_options:
                    raise ValidationError(u"Možnost ID {} zvolena vícekrát."
                                          .format(option_id))
                elif request.form[key]:
                    input_options[option_id] = int(request.form[key])
        validate_options(input_options, ballot)
    except ValidationError as e:
        flash(unicode(e), "danger")
        return redirect(url_for('polling_station_item', ballot_id=ballot_id))
    except ValueError as e:
        flash(u"Některý z hlasů má neplatnou hodnotu", "danger")
        return redirect(url_for('polling_station_item', ballot_id=ballot_id))

    title_dict = {option.id: option.title for option in ballot.options}
    summary = [
        {
            "title": title_dict[option],
            "value": input_options[option],
        } for option in sorted(
            input_options.keys(), key=lambda x: title_dict[x]
        )
    ]
    input_options_pickle = pickle.dumps(input_options)

    vote_timestamp = int(time.time())
    session["vote_timestamp_{}".format(ballot_id)] = vote_timestamp
    hash_base = compute_hash_base(ballot_id, g.user.id,
                                  input_options, vote_timestamp)
    hash_salt = b64encode(urandom(30))[:15]

    return render_template('polling_station_confirm.html',
                           ballot=ballot,
                           options_summary=summary,
                           input_options_data=input_options_pickle,
                           hash_base=hash_base,
                           hash_salt=hash_salt)


@app.route("/polling_station/<int:ballot_id>/vote/", methods=('POST',))
@app.route("/volebni_mistnost/<int:ballot_id>/hlasovat/", methods=('POST',))
@login_required
def polling_station_vote(ballot_id):
    ballot = db.session.query(Ballot).get(ballot_id)
    if ballot is None:
        abort(404)
    permit_voting(ballot)

    input_options = pickle.loads(request.form["input_options_data"])
    try:
        validate_options(input_options, ballot)
    except ValidationError as e:
        flash(unicode(e), "danger")
        return redirect(url_for('polling_station_item', ballot_id=ballot_id))
    except ValueError as e:
        flash(u"Některý z hlasů má neplatnou hodnotu", "danger")
        return redirect(url_for('polling_station_item', ballot_id=ballot_id))

    try:
        vote_timestamp = session.get(
            "vote_timestamp_{}".format(ballot_id), False)
        if not vote_timestamp:
            raise ValidationError()
        hash_base = compute_hash_base(ballot_id, g.user.id,
                                      input_options, vote_timestamp)
        hash_salt = request.form["hash_salt"]
        h = hashlib.sha1()
        h.update(hash_base.encode("utf-8"))
        h.update(hash_salt.encode("utf-8"))
        hash_digest = h.hexdigest()
    except Exception as e:
        flash(u"Chyba při výpočtu kontrolního řetězce", "danger")
        return redirect(url_for('polling_station_item', ballot_id=ballot_id))

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

    email_body = send_vote_confirmation(ballot, voter, hash_digest,
                                        hash_salt, vote_timestamp)

    db.session.commit()

    return render_template(
        'polling_station_vote.html', ballot=ballot,
        hash_digest=hash_digest, email_body=email_body)


def ballot_result(ballot):
    result = []
    for db_option in ballot.options:
        option = {
            "title": db_option.title,
            "votes": defaultdict(list),
            "elected": False,
        }
        for db_vote in db_option.votes:
            option["votes"][db_vote.value].append(db_vote.hash_digest)
        result.append(option)
    if ballot.is_yes_no:
        for option in result:
            if len(option["votes"][1]) > len(option["votes"][-1]):
                option["elected"] = True
            option["order_by"] = len(option["votes"][1]) \
                - len(option["votes"][-1])
        result = sorted(result, key=lambda x: -x["order_by"])
    else:
        for option in result:
            option["order_by"] = len(option["votes"][1])
        result = sorted(result, key=lambda x: -x["order_by"])
        places_left = ballot.max_votes
        current_place = []
        current_votes = 1 << 20
        for i in range(len(result)):
            if result[i]["order_by"] < current_votes and places_left >= 0:
                for r in current_place:
                    if r["order_by"] > 0:
                        r["elected"] = True
                current_place = []
            current_votes = result[i]["order_by"]
            current_place.append(result[i])
            places_left -= 1

    return result


@app.route("/polling_station/<int:ballot_id>/result/")
@app.route("/volebni_mistnost/<int:ballot_id>/vysledek/")
@login_required
def polling_station_result(ballot_id):
    ballot = db.session.query(Ballot).get(ballot_id)
    if ballot is None:
        abort(404)
    if ballot.cancelled:
        raise BallotBoxError(u"Tato volba byla zrušena.", 404)
    if not ballot.is_finished:
        raise BallotBoxError(u"Tato volba ještě probíhá.", 404)
    if not ballot.approved:
        raise BallotBoxError(
            u"Tato volba nebyla schválena Volební komisí.", 404)

    result = ballot_result(ballot)

    return render_template('polling_station_result.html',
                           ballot=ballot, result=result)


@app.route("/candidate_signup/")
@app.route("/podani_kandidatury/")
@login_required
def candidate_signup():
    ballots = (db.session.query(Ballot)
               .filter_by(approved=True, candidate_self_signup=True,
                          cancelled=False, type="ELECTION")
               .filter(Ballot.begin_at > datetime.datetime.now())
               .order_by(Ballot.begin_at.desc()))
    # Show ballots where the user can sign up first (stored is stable, so it
    # keeps the time ordering)
    ballots = sorted(ballots, key=lambda b: g.user.can_candidate_signup(b),
                     reverse=True)
    return render_template('candidate_signup.html', ballots=ballots)


@app.route("/candidate_signup/<int:ballot_id>/", methods=("GET", "POST"))
@app.route("/podani_kandidatury/<int:ballot_id>/", methods=("GET", "POST"))
@login_required
def candidate_signup_confirm(ballot_id):
    ballot = db.session.query(Ballot).get(ballot_id)
    if ballot is None:
        abort(404)
    if ballot.type != "ELECTION":
        raise BallotBoxError(u"V hlasování není možno kandidovat.", 403)
    if not g.user.can_candidate_signup(ballot):
        raise BallotBoxError(u"V této volbě nemáte právo kandidovat.", 403)
    if not ballot.candidate_self_signup:
        raise BallotBoxError(
            u"V této volbě není povoleno přímé podání kandidatury. "
            u"Kontaktujte prosím vyhlašovatele volby nebo Volební komisi.",
            403)
    if ballot.cancelled:
        raise BallotBoxError(u"Tato volba byla zrušena.", 403)
    if ballot.begin_at < datetime.datetime.now():
        raise BallotBoxError(u"Tato volba již probíhá.", 403)
    if not ballot.approved:
        raise BallotBoxError(
            u"Tato volba nebyla schválena Volební komisí.", 403)
    if ballot.candidate_signup_until < datetime.datetime.now():
        raise BallotBoxError(
            u"Přihlašovnání do této volby již skončilo.", 403)

    if request.method == "POST":
        user_id = g.user.id
        db_option = (db.session.query(BallotOption)
                     .filter_by(ballot_id=ballot.id, user_id=user_id)
                     .first())
        if db_option:
            flash(u"V této volbě již kandidujete.", "danger")
        else:
            db_option = BallotOption()
            db_option.title = g.user.canonical_name
            db_option.user_id = int(user_id)
            db_option.ballot = ballot
            db.session.add(db_option)
            db.session.commit()
            flash(u"Kandidatura úspěšně podána.", "success")
            return redirect(url_for('candidate_signup'))
    return render_template('candidate_signup_confirm.html', ballot=ballot)
