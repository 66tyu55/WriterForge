"""V89 real SQLite synthetic persistence and negative-evidence quarantine tests."""
from __future__ import annotations

from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
import sqlite3
import unittest
from unittest.mock import patch

from writerforge.db import WriterForgeDB
from writerforge.runtime import RuntimeEngine,RuntimeErrorState
from writerforge.v89_source_anchor_gate import (
    resolve_quote_only_answer,WF89AnchorError,
)
from writerforge.v89_anchor_failure_journal import (
    V89FailureJournal,V89FailureJournalError,
)
from writerforge.v88_frozen_blind_exam import canonical,validate_wf_answer

U1=("暮色笼罩着河岸，守桥人突然收起了最后一块木牌。"
    "几名村民互相张望，没有人继续走向石桥。")
U2=("远处传来一声钟响，少年带着妹妹退回村口，决定等天亮再查明前路。"
    "同行女子却始终没有回答他的疑问。")
VISIBLE=(U1,U2)

def h(text):
    return sha256(text.encode("utf8")).hexdigest()

def question():
    return {
      "status":"HYPOTHESIS","claim_id":"guess01",
      "question":"少年停止过桥是否因为守桥人突然收起木牌？",
      "observation":{"unit":1,"quote":"守桥人突然收起了最后一块木牌"},
      "consequence":{"unit":2,"quote":"少年带着妹妹退回村口"},
      "character_knowledge":{
        "actor":"少年",
        "known":"他注意到守桥人的异常行为与桥边动静。",
        "unknown":"尚不知道收起木牌的真正原因和前路风险。"},
      "hypothesis":"少年观察到异常后可能决定暂时离开。",
      "alternative":"钟声和天色也是促使少年返回的可能原因。",
      "falsifier":"若后文证明少年早已决定回村，这个假说需要被推翻。",
      "uncertainty":"这只是局部文本推断，没有完整章节或独立考官判定。",
    }

class V89FailureTests(unittest.TestCase):
    def setUp(self):
        self.tmp=TemporaryDirectory()
        self.path=Path(self.tmp.name)/"writer.sqlite3"
        self.db=WriterForgeDB(self.path)
        self.rt=RuntimeEngine()
        self.rt.enter_learn()
        self.journal=V89FailureJournal(self.db,self.rt)
        self.run="synthetic89"
        self.original=h("frozen original")
        self.pins=[h(t) for t in VISIBLE]

    def tearDown(self):
        self.db.close()
        self.tmp.cleanup()

    def fixture(self,*,wrong_quote=False):
        q=question()
        if wrong_quote:
            q["observation"]["quote"]="守桥人突然前往没有出现过的旧屋"
        return q

    def v89_args(self,q):
        return dict(
            run_id=self.run,raw_answer=q,visible_units=VISIBLE,
            pinned_visible_unit_sha256=self.pins,
            original_source_sha256=self.original,
            frozen_fragment_sha256=h("fragment"),
            sealed_future_unit_sha256=h("hidden"),
            genre_hint="历史",arm="baseline",
        )

    def v88_args(self,q):
        return dict(
            run_id=self.run,raw_answer=q,visible_units=VISIBLE,
            pinned_visible_unit_sha256=self.pins,
            source_sha256=self.original,
            genre_hint="历史",arm="baseline",
        )

    def test_legacy_mistaken_offsets_recorded_without_upgrading(self):
        bad=self.fixture()
        for key in ("observation","consequence"):
            bad[key]["start"]=0
            bad[key]["end"]=len(bad[key]["quote"])
        receipt=self.journal.capture_v88_failure(**self.v88_args(bad))
        self.assertEqual(receipt["failure_contract"],"LEGACY_V88_OFFSETS")
        self.assertEqual(receipt["failure_code"],
                         "WF88_ANCHOR_NOT_EXACT_VISIBLE_SOURCE")
        self.assertFalse(receipt["authoritative_literary_review"])
        self.assertFalse(receipt["source_prose_stored"])
        self.assertFalse(receipt["replayed"])
        checked=self.journal.read(
            run_id=self.run,original_answer_sha256=h(canonical(bad).decode()))
        self.assertFalse(checked["eligible_for_WF_write"])
        self.assertFalse(checked["may_be_imported_as_V86_independent_review"])
        repeated=self.journal.capture_v88_failure(**self.v88_args(bad))
        self.assertTrue(repeated["replayed"])

    def test_new_fake_quote_is_real_mechanical_failure(self):
        q=self.fixture(wrong_quote=True)
        failure=self.journal.capture_v89_failure(**self.v89_args(q))
        self.assertEqual(failure["failure_contract"],"V89_QUOTE_ONLY")
        self.assertEqual(failure["failure_code"],
                         "WF89_QUOTE_NOT_IN_VISIBLE_SOURCE")
        self.assertNotIn("守桥人突然前往没有出现过的旧屋",
                         str(failure))
        self.assertFalse(failure["authoritative_literary_review"])

    def test_valid_quote_candidate_cannot_be_falsely_marked_failure(self):
        q=self.fixture()
        with self.assertRaisesRegex(
            V89FailureJournalError,"VALID_SOURCE_CANDIDATE"):
            self.journal.capture_v89_failure(**self.v89_args(q))
        self.assertEqual(self.db.conn.execute(
            "SELECT COUNT(*) FROM wf_anchor_failure_receipts"
        ).fetchone()[0],0)

    def test_infrastructure_source_mismatch_not_student_error(self):
        q=self.fixture()
        args=self.v89_args(q)
        args["visible_units"]=(U1,U2+"非法篡改")
        with self.assertRaisesRegex(V89FailureJournalError,
                                    "INFRA_SOURCE_FAULT"):
            self.journal.capture_v89_failure(**args)
        self.assertEqual(self.db.conn.execute(
            "SELECT COUNT(*) FROM wf_anchor_failure_receipts"
        ).fetchone()[0],0)

    def test_database_blocks_edits_and_deletions(self):
        q=self.fixture(wrong_quote=True)
        self.journal.capture_v89_failure(**self.v89_args(q))
        with self.assertRaises(sqlite3.DatabaseError):
            self.db.conn.execute(
                "UPDATE wf_anchor_failure_receipts "
                "SET failure_code='WF89_FAKE' WHERE run_id=?",(self.run,))
        self.db.conn.rollback()
        with self.assertRaises(sqlite3.DatabaseError):
            self.db.conn.execute(
                "DELETE FROM wf_anchor_failure_receipts WHERE run_id=?",
                (self.run,))
        self.db.conn.rollback()
        self.assertEqual(len(self.journal.bounded_page(run_id=self.run)),1)

    def test_restart_and_bounded_pagination(self):
        a=self.fixture(wrong_quote=True)
        b=self.fixture()
        b["consequence"]["unit"]=3
        r1=self.journal.capture_v89_failure(**self.v89_args(a))
        r2=self.journal.capture_v89_failure(**self.v89_args(b))
        with self.assertRaisesRegex(V89FailureJournalError,
                                    "MORE_RECORDS_UNREAD"):
            self.journal.bounded_page(run_id=self.run,limit=1)
        self.db.close()
        self.db=WriterForgeDB(self.path)
        self.journal=V89FailureJournal(self.db,self.rt)
        self.assertEqual(self.journal.read(
            run_id=self.run,original_answer_sha256=r1[
                "original_answer_sha256"])["failure_code"],
                "WF89_QUOTE_NOT_IN_VISIBLE_SOURCE")
        self.assertEqual(self.journal.read(
            run_id=self.run,original_answer_sha256=r2[
                "original_answer_sha256"])["failure_code"],
                "WF89_CLAIMED_UNIT_NOT_VISIBLE")
        self.assertEqual(len(self.journal.bounded_page(run_id=self.run)),2)

    def test_duplicate_same_answer_cannot_be_rewritten_for_other_arm(self):
        q=self.fixture(wrong_quote=True)
        self.journal.capture_v89_failure(**self.v89_args(q))
        args=self.v89_args(q)
        args["arm"]="experience"
        with self.assertRaisesRegex(V89FailureJournalError,
                                    "IMMUTABLE_REPLAY_MISMATCH"):
            self.journal.capture_v89_failure(**args)

    def test_storage_budget_stops_growth_without_erasing_failures(self):
        original=self.fixture(wrong_quote=True)
        other=self.fixture()
        other["consequence"]["unit"]=3
        with patch("writerforge.v89_anchor_failure_journal.MAX_RECEIPTS_PER_RUN",1):
            initial=self.journal.capture_v89_failure(
                **self.v89_args(original))
            with self.assertRaisesRegex(V89FailureJournalError,
                                        "PER_RUN_STORAGE_BUDGET_REACHED"):
                self.journal.capture_v89_failure(**self.v89_args(other))
            # Exact replay remains allowed at full capacity; no new write.
            same=self.journal.capture_v89_failure(
                **self.v89_args(original))
            self.assertTrue(same["replayed"])
            self.assertEqual(initial["receipt_sha256"],same["receipt_sha256"])
        self.assertEqual(len(self.journal.bounded_page(run_id=self.run)),1)

    def test_global_capacity_blocks_new_run_but_preserves_existing(self):
        first=self.fixture(wrong_quote=True)
        different=self.fixture()
        different["observation"]["unit"]=3
        with patch("writerforge.v89_anchor_failure_journal.MAX_TOTAL_RECEIPTS",1):
            original=self.journal.capture_v89_failure(**self.v89_args(first))
            next_args=self.v89_args(different)
            next_args["run_id"]="separate_run"
            with self.assertRaisesRegex(V89FailureJournalError,
                                        "GLOBAL_STORAGE_BUDGET_REACHED"):
                self.journal.capture_v89_failure(**next_args)
            self.assertTrue(self.journal.capture_v89_failure(
                **self.v89_args(first))["replayed"])
        self.assertEqual(len(self.journal.bounded_page(run_id=self.run)),1)
        self.assertEqual(
            self.journal.read(run_id=self.run,
                original_answer_sha256=original["original_answer_sha256"]
            )["receipt_sha256"],original["receipt_sha256"])

    def test_learn_and_write_are_mutually_exclusive(self):
        q=self.fixture(wrong_quote=True)
        self.rt.exit()
        self.rt.enter_write(1)
        with self.assertRaisesRegex(RuntimeErrorState,
                                    "requires Mode.LEARN"):
            self.journal.capture_v89_failure(**self.v89_args(q))
        self.assertEqual(self.db.conn.execute(
            "SELECT COUNT(*) FROM wf_anchor_failure_receipts"
        ).fetchone()[0],0)

if __name__=="__main__":
    unittest.main()
