from ballot_box import db, app


with app.app_context():
    db.create_all()


if __name__ == "__main__":
    app.debug = True
    app.run(host="0.0.0.0")
