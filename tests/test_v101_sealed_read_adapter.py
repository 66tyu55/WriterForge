"""Offline V101 real orchestration protocol with fake private CAS / fake model.

NO external networking, R2, user API secrets or billable provider calls.
Checks paid-call uniqueness BEFORE any model and preexisting PASS-A seal.
"""
import unittest
from hashlib import sha256
from types import SimpleNamespace
from unittest.mock import Mock

from writerforge.runtime import RuntimeEngine
from writerforge.v79_provisional_r2_cas_journal import WFProvisionalR2CASJournal
from writerforge.v80_large_chapter_batch import WFLargeChapterBatch
from writerforge.v101_sealed_read_bridge import (
    read_sealed_narrative, V101ReadingError,
)
from test_v101_narrative_reader import WINDOWS,output1,SHA,STORY
from writerforge.v101_narrative_reader import digest


class AdapterTest(unittest.TestCase):
    def fixture(self):
        records={}
        journal=WFProvisionalR2CASJournal.__new__(
            WFProvisionalR2CASJournal)
        def put(raw):
            h=digest(raw)
            was_new=h not in records
            records.setdefault(h,raw)
            return h,was_new
        journal._put_content=put
        journal._get_content=lambda h:records[h]
        journal.require_writer_ready=lambda:True
        prior=None
        events={}
        for unit,text in enumerate(WINDOWS,1):
            event_hash=f"{unit}"*64
            events[("first_read",unit)]={
                "event_sha256":event_hash,
                "doc":{
                    "source_unit_sha256":digest(text.encode("utf8")),
                    "previous_event_sha256":prior,
                },
            }
            prior=event_hash
        events[("seal",None)]={
            "event_sha256":"f"*64,
            "doc":{"units_read":len(WINDOWS),
                   "last_first_read_sha256":prior,
                   "future_source_seen":False}
        }
        journal.fetch_event=lambda *,ident,stage,unit=None: events.get(
            (stage,unit))
        budget=SimpleNamespace(max_total_tokens=150000,calls_reserved=0)
        model=SimpleNamespace(name="deepseek-flash",budget=budget)
        def fake_ask_json(**kwargs):
            budget.calls_reserved+=1
            self.assertEqual(kwargs["role"],"craft_analysis")
            self.assertIn("林霁",kwargs["user"])
            return output1()
        model.ask_json=Mock(side_effect=fake_ask_json)
        batch=WFLargeChapterBatch.__new__(WFLargeChapterBatch)
        batch.journal=journal
        batch.model=model
        batch.key="private-test-source"
        batch.keyhash=sha256(batch.key.encode("utf8")).hexdigest()
        batch.source_sha=SHA
        chapter=SimpleNamespace(
            ordinal=2,
            body_sha256=digest("".join(WINDOWS).encode("utf8")),
        )
        batch.finished_chapters=[{
            "chapter":2,"chapter_body_sha256":chapter.body_sha256
        }]
        return batch,chapter,journal,model,events,records

    def test_one_manual_optin_seals_actual_source_then_refuses_double_bill(self):
        batch,chapter,journal,model,events,records=self.fixture()
        rt=RuntimeEngine()
        args=dict(batch=batch,chapter=chapter,windows=WINDOWS,
                  runtime=rt,story_id=STORY)
        with self.assertRaisesRegex(Exception,"Operation requires"):
            read_sealed_narrative(**args)
        self.assertEqual(model.ask_json.call_count,0)
        rt.enter_learn()
        good=read_sealed_narrative(**args)
        self.assertEqual(good["model_calls"],1)
        self.assertEqual(good["relation_hypotheses"],1)
        self.assertEqual(good["plot_hypotheses"],1)
        self.assertEqual(good["prose_quality_hypotheses"],1)
        self.assertFalse(good["human_literary_verified"])
        self.assertEqual(model.ask_json.call_count,1)
        self.assertIn(good["reader_receipt_cas_sha256"],records)
        # Same story/chapter/actual source is reserved forever even when
        # called again with a fresh model budget or modified prompt.
        with self.assertRaisesRegex(V101ReadingError,
                                    "ALREADY_RESERVED_NO_REPEAT"):
            read_sealed_narrative(**args)
        self.assertEqual(model.ask_json.call_count,1)

    def test_no_valid_seal_no_llm_no_precommit(self):
        batch,chapter,journal,model,events,records=self.fixture()
        events.pop(("seal",None))
        rt=RuntimeEngine();rt.enter_learn()
        with self.assertRaisesRegex(V101ReadingError,"FULL_SEAL_MISSING"):
            read_sealed_narrative(
                batch=batch,chapter=chapter,windows=WINDOWS,
                runtime=rt,story_id=STORY)
        self.assertEqual(model.ask_json.call_count,0)
        self.assertEqual(len(records),0)

    def test_source_unit_forgery_fails_before_any_model(self):
        batch,chapter,journal,model,events,records=self.fixture()
        events[("first_read",2)]["doc"]["source_unit_sha256"]="0"*64
        rt=RuntimeEngine();rt.enter_learn()
        with self.assertRaisesRegex(V101ReadingError,"SOURCE_CHANGED"):
            read_sealed_narrative(
                batch=batch,chapter=chapter,windows=WINDOWS,
                runtime=rt,story_id=STORY)
        self.assertEqual(model.ask_json.call_count,0)
        self.assertFalse(records)


if __name__=="__main__":
    unittest.main()
