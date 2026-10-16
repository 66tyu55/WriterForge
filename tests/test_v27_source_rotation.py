"""Regression tests for bounded, non-repeating real-source selection in V27."""
import json
import sqlite3
import unittest

from writerforge.literary_ladder import LiteraryLadder


class LiterarySourceRotationTests(unittest.TestCase):
    def setUp(self):
        self.conn=sqlite3.connect(":memory:")
        self.conn.row_factory=sqlite3.Row
        self.conn.executescript("""
            CREATE TABLE source_spans (
                work_id TEXT, chapter INTEGER, paragraph INTEGER,
                sentence INTEGER, excerpt TEXT, source_sha256 TEXT
            );
            CREATE TABLE literary_training_attempts (
                project_id TEXT, work_id TEXT, stage INTEGER, receipt_json TEXT
            );
        """)
        for i in range(3):
            self.conn.execute(
                "INSERT INTO source_spans VALUES(?,?,?,?,?,?)",
                ("original",1,1,i+1,"古代白话原文十二字以上，有来处。"+str(i),"sha"+str(i)),
            )
        self.conn.commit()
        self.ladder=object.__new__(LiteraryLadder)
        self.ladder.db=type("DB",(),{"conn":self.conn})()
        self.ladder.project_id="project-a"

    def tearDown(self):
        self.conn.close()

    def mark_seen(self,sentence,stage=1,status="generation_failed"):
        receipt={"task":{"source_location":[1,1,sentence]},"status":status}
        self.conn.execute(
            "INSERT INTO literary_training_attempts VALUES(?,?,?,?)",
            ("project-a","original",stage,json.dumps(receipt)),
        )
        self.conn.commit()

    def test_each_attempt_advances_even_when_previous_generation_failed(self):
        self.assertEqual(self.ladder._source("original")["sentence"],1)
        self.mark_seen(1)
        self.assertEqual(self.ladder._source("original")["sentence"],2)
        self.mark_seen(2,status="not_run_short_stage")
        self.assertEqual(self.ladder._source("original")["sentence"],3)

    def test_other_projects_and_stages_do_not_consume_source(self):
        self.mark_seen(1,stage=2)
        self.conn.execute(
            "INSERT INTO literary_training_attempts VALUES(?,?,?,?)",
            ("project-b","original",1,'{"task":{"source_location":[1,1,1]}}'),
        )
        self.assertEqual(self.ladder._source("original")["sentence"],1)

    def test_all_seen_fails_closed(self):
        for sentence in (1,2,3):
            self.mark_seen(sentence)
        self.assertIsNone(self.ladder._source("original"))

    def test_invalid_legacy_receipt_is_ignored_safely(self):
        self.conn.execute(
            "INSERT INTO literary_training_attempts VALUES(?,?,?,?)",
            ("project-a","original",1,"invalid-json"),
        )
        self.assertEqual(self.ladder._source("original")["sentence"],1)


if __name__=="__main__":
    unittest.main()
