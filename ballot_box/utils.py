def compute_hash_base(ballot_id, user_id, input_options, vote_timestamp):
    io_str = "[{}]".format(",".join(("{}:{}".format(k, input_options[k]) for k in sorted(input_options.keys()))))
    return "{}*{}*{}*{}*".format(ballot_id, user_id, io_str, vote_timestamp)
