"""Semantic packet tests use synthetic evidence; never claim actual book understanding."""
import sqlite3
import unittest
from writerforge.semantic_review import review_packets


class SemanticPacketTests(unittest.TestCase):
    def setUp(self):
        self.conn=sqlite3.connect(":memory:")
        self.conn.row_factory=sqlite3.Row
        self.conn.executescript("""
            CREATE TABLE encyclopedia_entities(id INTEGER PRIMARY KEY,name TEXT,kind TEXT);
            CREATE TABLE encyclopedia_evidence(
                id INTEGER PRIMARY KEY,work_id TEXT,chapter INTEGER,paragraph INTEGER,
                sentence INTEGER,category_path TEXT,attribute TEXT,assertion TEXT,
                quotation TEXT,source_unit_sha256 TEXT,status TEXT,entity_id INTEGER
            );
            CREATE TABLE source_spans(
                work_id TEXT,chapter INTEGER,paragraph INTEGER,sentence INTEGER,
                excerpt TEXT,source_sha256 TEXT
            );
            INSERT INTO encyclopedia_entities VALUES(1,'小龙','character');
            INSERT INTO source_spans VALUES('a',1,1,1,'小龙是村中少年。','h1');
            INSERT INTO source_spans VALUES('a',1,1,2,'他听见远处雷声，躲入房间。','h2');
            INSERT INTO source_spans VALUES('a',1,1,3,'众人并未见到天劫。','h3');
            INSERT INTO source_spans VALUES('b',1,1,1,'另一部书不属于该上下文。','other');
            INSERT INTO encyclopedia_evidence VALUES(
                5,'a',1,1,2,'设定/天劫','雷声','inferred',
                '远处雷声','h2','proposed',1
            );
        """)
        self.db=type("DB",(),{"conn":self.conn})()

    def tearDown(self):
        self.conn.close()

    def test_proposals_are_not_certified_and_context_is_scoped(self):
        p=review_packets(self.db,work_id="a")[0].as_dict()
        self.assertEqual(p["status"],"review_required")
        self.assertFalse(p["human_verified_by_packet"])
        self.assertEqual(p["previous_excerpt"],"小龙是村中少年。")
        self.assertEqual(p["next_excerpt"],"众人并未见到天劫。")
        self.assertNotIn("另一部书",str(p))
        self.assertEqual(self.conn.execute(
            "SELECT status FROM encyclopedia_evidence WHERE id=5").fetchone()[0],"proposed")

    def test_stale_hash_blocks_review(self):
        self.conn.execute("UPDATE encyclopedia_evidence SET source_unit_sha256='old' WHERE id=5")
        p=review_packets(self.db,work_id="a")[0]
        self.assertEqual(p.status,"source_integrity_failed")

    def test_invalid_input_fails(self):
        for kwargs in ({"work_id":"","limit":10},{"work_id":"a","limit":100},
                       {"work_id":"a","offset":-1}):
            with self.assertRaises(ValueError):
                review_packets(self.db,**kwargs)

    def test_verified_not_mistaken_for_pending(self):
        self.conn.execute("UPDATE encyclopedia_evidence SET status='verified' WHERE id=5")
        self.assertEqual(review_packets(self.db,work_id="a"),[])


if __name__=="__main__":
    unittest.main()
