from ballot_box import app, db
import unittest
from ballot_box.models import Ballot, BallotOption, Vote
from ballot_box.views import ballot_result
import datetime

class BallotBoxTestCase(unittest.TestCase):

    def setUp(self):
        app.config.from_object('ballot_box.config.TestingConfig')
        db.session.close()
        db.drop_all()
        db.create_all()

    def create_ballot(self, max_votes):
        pre_count = db.session.query(Ballot).count()
        ballot = Ballot()
        ballot.name = "Test1"
        ballot.begin_at = datetime.datetime.now()
        ballot.finish_at = datetime.datetime.now()
        ballot.type = "VOTING"
        ballot.unit = "country,1"
        ballot.max_votes = max_votes

        db.session.add(ballot)
        db.session.commit()

        self.assertEqual(db.session.query(Ballot).count(), pre_count+1)

        return ballot

    def create_options(self, ballot, count):
        pre_count = db.session.query(BallotOption).count()
        options = []
        for i in range(count):
            bo = BallotOption()
            bo.ballot_id = ballot.id
            bo.title = "{0} {1}".format(ballot.id, i)
            db.session.add(bo)
            options.append(bo)
        db.session.commit()
        self.assertEqual(db.session.query(BallotOption).count(), pre_count+count)

        return options

    def add_votes(self, bo, count, value=1):
        pre_count = (db.session.query(Vote)
                               .filter(Vote.ballot_option_id == bo.id)
                               .count())
        votes = []
        for i in range(count):
            v = Vote()
            v.ballot_option_id = bo.id
            v.hash_digest = "hd {0} {1}".format(bo.id, i)
            v.value = value
            db.session.add(v)
            votes.append(v)
        db.session.commit()

        post_count = (db.session.query(Vote)
                                .filter(Vote.ballot_option_id == bo.id)
                                .count())
        self.assertEqual(post_count, pre_count+count)

        return votes

    def elected_count(self, result):
        return len(filter(lambda x: x["elected"], result))

    def test_ballot_result1(self):
        ballot = self.create_ballot(1)
        ops = self.create_options(ballot, 5)
        
        # 0 0 0 0 0
        self.assertEqual(0, self.elected_count(ballot_result(ballot)))

        self.add_votes(ops[0], 1)
        # 1 0 0 0 0
        self.assertEqual(1, self.elected_count(ballot_result(ballot)))
        
        self.add_votes(ops[1], 1)
        # 1 1 0 0 0
        self.assertEqual(0, self.elected_count(ballot_result(ballot)))

        self.add_votes(ops[2], 1)
        # 1 1 1 0 0
        self.assertEqual(0, self.elected_count(ballot_result(ballot)))

        self.add_votes(ops[0], 1)
        # 2 1 1 0 0
        self.assertEqual(1, self.elected_count(ballot_result(ballot)))
        
        self.add_votes(ops[1], 1)
        # 2 2 1 0 0
        self.assertEqual(0, self.elected_count(ballot_result(ballot)))

        self.add_votes(ops[0], 1)
        # 3 2 1 0 0
        self.assertEqual(1, self.elected_count(ballot_result(ballot)))

    def test_ballot_result2(self):
        ballot = self.create_ballot(2)
        ops = self.create_options(ballot, 5)
        
        # 0 0 0 0 0
        self.assertEqual(0, self.elected_count(ballot_result(ballot)))

        self.add_votes(ops[0], 1)
        # 1 0 0 0 0
        self.assertEqual(1, self.elected_count(ballot_result(ballot)))
        
        self.add_votes(ops[1], 1)
        # 1 1 0 0 0
        self.assertEqual(2, self.elected_count(ballot_result(ballot)))

        self.add_votes(ops[2], 1)
        # 1 1 1 0 0
        self.assertEqual(0, self.elected_count(ballot_result(ballot)))

        self.add_votes(ops[0], 1)
        # 2 1 1 0 0
        self.assertEqual(1, self.elected_count(ballot_result(ballot)))
        
        self.add_votes(ops[1], 1)
        # 2 2 1 0 0
        self.assertEqual(2, self.elected_count(ballot_result(ballot)))

        self.add_votes(ops[0], 1)
        # 3 2 1 0 0
        self.assertEqual(2, self.elected_count(ballot_result(ballot)))

    def test_ballot_result1_yn(self):
        ballot = self.create_ballot(1)
        ops = self.create_options(ballot, 1)
        
        # 0
        self.assertEqual(0, self.elected_count(ballot_result(ballot)))

        self.add_votes(ops[0], 1)
        # 1 
        self.assertEqual(1, self.elected_count(ballot_result(ballot)))

        self.add_votes(ops[0], 1, -1)
        # 0 
        self.assertEqual(0, self.elected_count(ballot_result(ballot)))

        self.add_votes(ops[0], 1, -1)
        # -1 
        self.assertEqual(0, self.elected_count(ballot_result(ballot)))

        self.add_votes(ops[0], 1)
        self.add_votes(ops[0], 1)
        self.add_votes(ops[0], 1)
        # 2
        self.assertEqual(1, self.elected_count(ballot_result(ballot)))

    def test_ballot_result2_yn1(self):
        ballot = self.create_ballot(2)
        ops = self.create_options(ballot, 1)
        
        # 0
        self.assertEqual(0, self.elected_count(ballot_result(ballot)))

        self.add_votes(ops[0], 1)
        # 1 
        self.assertEqual(1, self.elected_count(ballot_result(ballot)))

        self.add_votes(ops[0], 1, -1)
        # 0 
        self.assertEqual(0, self.elected_count(ballot_result(ballot)))

        self.add_votes(ops[0], 1, -1)
        # -1 
        self.assertEqual(0, self.elected_count(ballot_result(ballot)))

        self.add_votes(ops[0], 1)
        self.add_votes(ops[0], 1)
        self.add_votes(ops[0], 1)
        # 2
        self.assertEqual(1, self.elected_count(ballot_result(ballot)))

    def test_ballot_result2_yn2(self):
        ballot = self.create_ballot(2)
        ops = self.create_options(ballot, 2)
        
        # 0 0
        self.assertEqual(0, self.elected_count(ballot_result(ballot)))

        self.add_votes(ops[0], 1)
        # 1 0
        self.assertEqual(1, self.elected_count(ballot_result(ballot)))

        self.add_votes(ops[0], 1, -1)
        # 0 0
        self.assertEqual(0, self.elected_count(ballot_result(ballot)))

        self.add_votes(ops[0], 1, -1)
        # -1 0
        self.assertEqual(0, self.elected_count(ballot_result(ballot)))

        self.add_votes(ops[0], 1)
        self.add_votes(ops[0], 1)
        self.add_votes(ops[0], 1)
        # 2 0
        self.assertEqual(1, self.elected_count(ballot_result(ballot)))

        self.add_votes(ops[1], 1)
        # 2 1
        self.assertEqual(2, self.elected_count(ballot_result(ballot)))
        

if __name__ == '__main__':
    unittest.main()

