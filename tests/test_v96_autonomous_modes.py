"""V96 opt-in AutonomousWriting A/B/C integration against existing Xuehai.

Uses existing WriterForgeDB and real VerifiedWritingFlow preparation, but
substitutes synthetic local_chat_completion responses. Neither external
model nor Cloudflare R2 are contacted. Compare same frozen event plan across
split-only B vs causally checked C; author acceptance stays explicitly FALSE.
"""
from __future__ import annotations
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import json
import time
import unittest

from test_v26_invisible_writer import PLAN,make_db
from test_v96_causal_turns import (
    ACTION1,EFFECT1,ACTION2,EFFECT2,GUARD,turns,prose1,prose2,response,
)
from writerforge import WriterForgeDB,RuntimeEngine
from writerforge.writing_assist import (
    AutonomousWriting,InvisibleWritingAssist,WritingExecutionError
)
from writerforge.v96_causal_turns import canonical,digest
from writerforge.studio_server import StudioService,StudioError

OUTLINE="少年要赶在涨水前送药入城，桥头守卫的行动却让他迟疑。陪同女子掌握一本旧账册，但其真正意图仍然未知。"
GOALS=["本章：少年发现桥边异常并决定暂时避开渡河危险"]
PLAN_TURNS=json.dumps(turns(),ensure_ascii=False)


class V96AutonomousWritingTests(unittest.TestCase):
    def setUp(self):
        self.tmp=TemporaryDirectory()
        self.root=Path(self.tmp.name)
        self.dbpath=self.root/"source.sqlite"
        self.snapshot=make_db(self.dbpath)
        self.db=WriterForgeDB(self.dbpath)
        self.rt=RuntimeEngine()
        self.rt.enter_write(self.snapshot)
        self.assist=InvisibleWritingAssist(
            self.db,self.rt,
            "v96-test-project","scene-v96",
            "桥头出现不明征兆，少年和女子争论该不该继续赶路。",
            model="synthetic-no-cost",
            api_base="http://127.0.0.1:1234/v1",
        )
    def tearDown(self):
        self.db.close()
        self.tmp.cleanup()
    def run_mode(self,mode,inputs,**kwargs):
        with patch("writerforge.writing_assist.local_chat_completion",
                   side_effect=inputs) as call:
            doc=AutonomousWriting(self.assist).run(
                outline=OUTLINE,chapter_goals=GOALS,
                output_dir=self.root/("out-"+mode),
                draft_mode=mode,
                frozen_turn_outlines=(PLAN_TURNS,),
                **kwargs)
        return doc,call.call_count

    def test_causal_guard_saved_real_prose_order_while_preserving_author_gate(self):
        doc,count=self.run_mode(
            "causal_guard",[
                PLAN,
                response(prose1(),ACTION1,EFFECT1),
                response(prose2(),ACTION2,EFFECT2,EFFECT1),
            ])
        self.assertEqual(count,3)
        self.assertEqual(doc["draft_mode"],"causal_guard")
        self.assertEqual(doc["segmented_model_turns"],2)
        self.assertEqual(doc["canonical_fact_writes"],0)
        self.assertFalse(doc["candidate_event_logic_independently_verified"])
        ch=doc["chapters"][0]
        self.assertFalse(ch["accepted"])
        self.assertFalse(ch["causal_logic_literary_verified"])
        self.assertTrue(ch["facts_not_committed"])
        prose=Path(ch["candidate"]).read_text(encoding="utf8")
        self.assertEqual(prose,prose1()+"\n\n"+prose2())
        evidence=json.loads(Path(ch["turn_evidence"]).read_text("utf8"))
        self.assertEqual(evidence["turn_count"],2)
        self.assertEqual(len(evidence["model_prompt_sha256s"]),2)
        sha=evidence.pop("manifest_sha256")
        self.assertEqual(sha,digest(canonical(evidence)))
        self.assertFalse(evidence["independent_literary_quality_verified"])
        self.assertFalse(evidence["turn_receipts"][1][
            "literary_causality_independently_verified"])
        self.assertIsNone(self.db.conn.execute(
            "SELECT 1 FROM accepted_prose").fetchone())

    def test_B_and_C_share_frozen_plan_and_same_model_call_count(self):
        answers=[
            PLAN,
            response(prose1(),ACTION1,EFFECT1),
            response(prose2(),ACTION2,EFFECT2,EFFECT1)
        ]
        b,bc=self.run_mode("split_only",answers)
        c,cc=self.run_mode("causal_guard",answers)
        self.assertEqual(bc,cc)
        self.assertEqual(bc,3)
        a=json.loads(Path(b["chapters"][0]["turn_evidence"]).read_text())
        z=json.loads(Path(c["chapters"][0]["turn_evidence"]).read_text())
        self.assertEqual(a["turn_outline_sha256"],z["turn_outline_sha256"])
        self.assertEqual(a["turn_count"],z["turn_count"])
        self.assertEqual(a["turn_receipts"][0]["causal_check"],
                         "SPLIT_ONLY_UNVERIFIED")
        self.assertEqual(z["turn_receipts"][0]["causal_check"],
                         "EXACT_OBSERVABLE_ANCHORS_ONLY")
        self.assertEqual(
            Path(b["chapters"][0]["candidate"]).read_text("utf8"),
            Path(c["chapters"][0]["candidate"]).read_text("utf8"))

    def test_real_source_quote_failure_quarantines_without_retry_or_candidate(self):
        wrong=response(prose1(),"守桥人进入不存在的密室",EFFECT1)
        with patch("writerforge.writing_assist.local_chat_completion",
                   side_effect=[PLAN,wrong]) as model:
            with self.assertRaisesRegex(WritingExecutionError,
                                        "WF96_SCENE_TURN_REJECTED"):
                AutonomousWriting(self.assist).run(
                    outline=OUTLINE,chapter_goals=GOALS,
                    output_dir=self.root/"bad",
                    draft_mode="causal_guard",
                    frozen_turn_outlines=(PLAN_TURNS,))
        self.assertEqual(model.call_count,2)
        failed=list((self.root/"bad").glob(
            "auto-*/chapter-001-rejected.json"))
        self.assertEqual(len(failed),1)
        report=json.loads(failed[0].read_text("utf8"))
        self.assertEqual(report["previous_valid_turn_count"],0)
        self.assertEqual(report["automatic_repair_attempts"],0)
        self.assertEqual(report["canonical_fact_writes"],0)
        self.assertNotIn("进入不存在的密室",str(report))
        self.assertEqual(list((self.root/"bad").rglob("candidate.txt")),[])
        self.assertIsNone(self.db.conn.execute(
            "SELECT 1 FROM accepted_prose").fetchone())

    def test_B_does_not_falsely_claim_detecting_hallucination(self):
        bogus=response(prose1(),"守桥人进入不存在的密室",EFFECT1)
        doc,count=self.run_mode(
            "split_only",
            [PLAN,bogus,response(prose2(),ACTION2,EFFECT2,
                                 "完全虚构的前置事件")])
        self.assertEqual(count,3)
        evidence=json.loads(Path(doc["chapters"][0]["turn_evidence"]
                                 ).read_text("utf8"))
        self.assertTrue(all(x["causal_check"]=="SPLIT_ONLY_UNVERIFIED"
                            for x in evidence["turn_receipts"]))
        self.assertFalse(doc["literary_quality_verified"])

    def test_forbidden_knowledge_only_blocks_C_not_comparison_B(self):
        injected=prose1()+"。"+GUARD+"，但没有可靠的原文说明。"
        sample=response(injected,ACTION1,EFFECT1)
        with patch("writerforge.writing_assist.local_chat_completion",
                   side_effect=[PLAN,sample]) as model:
            with self.assertRaisesRegex(WritingExecutionError,
                                        "KNOWLEDGE_BOUNDARY"):
                AutonomousWriting(self.assist).run(
                    outline=OUTLINE,chapter_goals=GOALS,
                    output_dir=self.root/"blocked",
                    draft_mode="causal_guard",
                    frozen_turn_outlines=(PLAN_TURNS,),
                    author_confirmed_forbidden_phrases=(GUARD,))
        self.assertEqual(model.call_count,2)
        b,_=self.run_mode(
            "split_only",[
                PLAN,sample,response(prose2(),ACTION2,EFFECT2,EFFECT1)],
            author_confirmed_forbidden_phrases=(GUARD,))
        self.assertFalse(b["literary_quality_verified"])
        self.assertFalse(b["chapters"][0]["accepted"])

    def test_opt_in_limit_and_legacy_default_stays_two_calls(self):
        with patch("writerforge.writing_assist.local_chat_completion") as m:
            with self.assertRaisesRegex(WritingExecutionError,
                                        "SEGMENTED_CHAPTER_REQUEST_BUDGET"):
                AutonomousWriting(self.assist).run(
                    outline=OUTLINE,chapter_goals=GOALS*3,
                    output_dir=self.root/"over",
                    draft_mode="causal_guard")
            m.assert_not_called()
        legacy=("夜里山道安静得只听见马铃。镖师压住少年的手，"
                "让他伏在车底。朋友的火把转过山梁，他没有迎上去。")*4
        with patch("writerforge.writing_assist.local_chat_completion",
                   side_effect=[PLAN,legacy]) as m:
            doc=AutonomousWriting(self.assist).run(
                outline=OUTLINE,chapter_goals=GOALS,
                output_dir=self.root/"legacy")
            self.assertEqual(m.call_count,2)
        self.assertNotIn("draft_mode",doc)
        self.assertNotIn("segmented_model_turns",doc)
        self.assertEqual(Path(doc["chapters"][0]["candidate"]).read_text(
            "utf8"),legacy)

    def test_local_studio_exposes_opt_in_mode_without_changing_default(self):
        html=(Path(__file__).parents[1]/"writerforge"/"ui"/
              "studio.html").read_text("utf8")
        self.assertIn('id="draft-mode"',html)
        self.assertIn('value="single"',html)
        self.assertIn('value="causal_guard"',html)
        self.assertIn("chapters,draft_mode",html)
        local=StudioService(
            db_path=self.dbpath,project="v96-test-project",
            scene="studio-scene",goal="用行动呈现河道上的人物抉择",
            model="synthetic-no-cost",
            output_dir=self.root/"studio")
        with self.assertRaisesRegex(StudioError,
                                    "WF96_UNKNOWN_EXPERIMENTAL_DRAFT_MODE"):
            local.start_auto(OUTLINE,GOALS,draft_mode="auto_publish_canon")
        with self.assertRaisesRegex(StudioError,
                                    "MAX_TWO_CHAPTERS"):
            local.start_auto(OUTLINE,GOALS*3,draft_mode="causal_guard")
        self.assertEqual(local.job()["status"],"idle")
        dummy={"chapter_count":1,"chapters":[],
               "all_generated_prose_requires_author_review":True}
        with patch("writerforge.studio_server.AutonomousWriting.run",
                   return_value=dummy) as model:
            queued=local.start_auto(OUTLINE,GOALS,draft_mode="causal_guard")
            for _ in range(60):
                if local.job()["status"] in ("completed","failed"):
                    break
                time.sleep(0.01)
            self.assertEqual(local.job()["status"],"completed")
            self.assertEqual(queued["draft_mode"],"causal_guard")
            self.assertTrue(queued["no_auto_accept"])
            self.assertEqual(model.call_args.kwargs["draft_mode"],
                             "causal_guard")
            self.assertEqual(model.call_count,1)

    def test_invalid_frozen_outline_leaves_rejection_not_success_receipt(self):
        malformed='{"turns":[{"id":"t55"}]}'
        with patch("writerforge.writing_assist.local_chat_completion",
                   side_effect=[PLAN]) as m:
            with self.assertRaisesRegex(WritingExecutionError,
                                        "WF96_SCENE_TURN_REJECTED"):
                AutonomousWriting(self.assist).run(
                    outline=OUTLINE,chapter_goals=GOALS,
                    output_dir=self.root/"badoutline",
                    draft_mode="causal_guard",
                    frozen_turn_outlines=(malformed,))
        self.assertEqual(m.call_count,1)
        self.assertFalse(list((self.root/"badoutline").rglob(
            "job_manifest.json")))
        self.assertEqual(len(list((self.root/"badoutline").rglob(
            "*-rejected.json"))),1)

if __name__=="__main__":
    unittest.main()
