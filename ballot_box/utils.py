# -*- coding: utf-8 -*-
import datetime 


DAYS_RANGE = [
    u"pondělí",
    u"úterý",
    u"středy",
    u"čtvrtka",
    u"pátku",
    u"soboty",
    u"neděle",
]


def compute_hash_base(ballot_id, user_id, input_options, vote_timestamp):
    io_str = "[{}]".format(
        ",".join((
            "{}:{}".format(k, input_options[k])
            for k in sorted(input_options.keys())
        ))
    )
    return "{}*{}*{}*{}*".format(ballot_id, user_id, io_str, vote_timestamp)

def add_years(dt, years):
    try:
        dt = dt.replace(year=dt.year+years) - datetime.timedelta(days=1)
    except ValueError:
        dt = dt.replace(year=dt.year+years, day=dt.day-1)  # leap year
    return dt