"""V105 production WRITE call-graph simulation, always synthetic, zero billing."""
from __future__ import annotations
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import json,unittest

from test_v26_invisible_writer import PLAN,make_db
from test_v96_causal_turns import (
    ACTION1,EFFECT1,ACTION2,EFFECT2,turns,prose1,prose2,
)
from test_v102_emotional_causality import emotional,note1,note2
from test_v98_rolling_causal_planner import proposed,raw,OUTLINE,GOALS
from test_v105_forward_horizon import simple_branches
from writerforge import WriterForgeDB,RuntimeEngine
from writerforge.writing_assist import (
    AutonomousWriting,InvisibleWritingAssist,WritingExecutionError,
)
from writerforge.studio_server import StudioService

def foresight_plan():
    p=json.loads(PLAN)
    p["horizon"]=simple_branches()
    return json.dumps(p,ensure_ascii=False,separators=(",",":"))

def replies(*,continued=False):
    n1=note1()
    n2=note2()
    if continued:
        n1["before"]="未知"
        n2["before"]="不确定"
    return [
        foresight_plan(),
        emotional(prose1(),ACTION1,EFFECT1,None,"少年",n1),
        raw(proposed()),
        emotional(prose2(),ACTION2,EFFECT2,EFFECT1,"女子",n2),
    ]

class V105TrueWritingEntrypoint(unittest.TestCase):
    def setUp(self):
        self.temp=TemporaryDirectory()
        self.root=Path(self.temp.name)
        self.dbpath=self.root/"source.sqlite"
        self.snapshot=make_db(self.dbpath)
        self.db=WriterForgeDB(self.dbpath)
        self.rt=RuntimeEngine()
        self.rt.enter_write(self.snapshot)
        self.assist=InvisibleWritingAssist(
            self.db,self.rt,"v105-test-only","some-scene",
            "雨夜必须用代价来决定桥上的一件事",
            model="mock-local-no-billing",api_base="http://127.0.0.1:1234/v1")
    def tearDown(self):
        self.db.close()
        self.temp.cleanup()

    def run_f(self,answers,*,goals=None,facts=None,resume=None,folder="f"):
        with patch("writerforge.writing_assist.local_chat_completion",
                   side_effect=answers) as invocations:
            ret=AutonomousWriting(self.assist).run(
                outline=OUTLINE,chapter_goals=goals or GOALS,
                output_dir=self.root/folder,
                draft_mode="foresight_rolling",
                frozen_turn_outlines=tuple(json.dumps(
                    turns(),ensure_ascii=False) for _ in (goals or GOALS)),
                forward_author_pinned_facts=facts,
                resume_candidate_checkpoint=resume)
        return ret,invocations.call_args_list

    def test_f_plans_before_prose_and_exports_future_and_real_open_debts(self):
        doc,calls=self.run_f(replies(),facts={"power:station":"on"})
        self.assertEqual(len(calls),4)  # same E replan cadence
        self.assertEqual([v.kwargs["max_tokens"] for v in calls],
                         [2400,1450,650,1450])
        self.assertIn("horizon",calls[0].args[0].prompt)
        self.assertIn("SYMBOLICALLY_BLOCKED",calls[1].args[0].prompt)
        self.assertIn("未来只是假设",calls[2].args[0].prompt)
        self.assertIn("未来只是假设",calls[3].args[0].prompt)
        ch=doc["chapters"][0]
        self.assertTrue(ch["v105_original_model_answers_prevalidation_stored"])
        self.assertIn("horizon",Path(ch["v105_raw_chapter_plan"]).read_text("utf8"))
        private_raw=list((self.root/"f").rglob("*-raw.json"))
        # The old first model output and next-turn replan are saved before
        # structural filters, never printed as a public literary verdict.
        self.assertGreaterEqual(len(private_raw),3)
        self.assertEqual(ch["draft_mode"],"foresight_rolling")
        self.assertFalse(ch["accepted"])
        self.assertEqual(doc["rolling_replan_model_calls"],1)
        self.assertEqual(doc["canonical_fact_writes"],0)
        saved=json.loads(Path(ch["v105_horizon_plan"]).read_text("utf8"))
        self.assertEqual(saved["branches"][0]["status"],"SYMBOLICALLY_BLOCKED")
        check=json.loads(Path(ch["v105_candidate_checkpoint"]).read_text("utf8"))
        self.assertEqual(check["open_debts_count"],2)
        self.assertFalse(check["literary_semantics_verified"])
        self.assertEqual(check["auto_debt_settlements"],0)
        self.assertEqual(doc["final_candidate_checkpoint_sha256"],
                         check["receipt_sha256"])
        self.assertIsNone(self.db.conn.execute(
            "SELECT 1 FROM accepted_prose").fetchone())

    def test_two_chapters_share_unpaid_cost_and_no_extra_provider_request(self):
        doc,calls=self.run_f(replies()+replies(continued=True),goals=GOALS*2,
                             facts={"power:station":"on"},
                             folder="f-two")
        self.assertEqual(len(calls),8)
        self.assertEqual(doc["open_unreviewed_debts"],4)
        self.assertEqual(doc["rolling_replan_model_calls"],2)
        self.assertIn("过去数章",calls[4].args[0].prompt)
        self.assertIn("朋友仍在城中等药",calls[4].args[0].prompt)
        self.assertIn("以前章节尚未偿付的代价",calls[5].args[0].prompt)
        last=json.loads(Path(doc["chapters"][1][
            "v105_candidate_checkpoint"]).read_text("utf8"))
        first=json.loads(Path(doc["chapters"][0][
            "v105_candidate_checkpoint"]).read_text("utf8"))
        self.assertEqual(last["previous_checkpoint_sha256"],
                         first["receipt_sha256"])
        self.assertEqual(last["open_debts_count"],4)

    def test_resumes_a_third_chapter_without_resetting_prior_debt(self):
        first,_=self.run_f(replies(),folder="original")
        prev=json.loads(Path(first["chapters"][0][
            "v105_candidate_checkpoint"]).read_text("utf8"))
        next_doc,calls=self.run_f(
            replies(),resume=prev,folder="resumed")
        self.assertEqual(len(calls),4)
        final=json.loads(Path(next_doc["chapters"][0][
            "v105_candidate_checkpoint"]).read_text("utf8"))
        self.assertEqual(final["chapter"],2)
        self.assertEqual(final["open_debts_count"],4)
        self.assertEqual(final["previous_checkpoint_sha256"],
                         prev["receipt_sha256"])
        self.assertFalse(final["literary_semantics_verified"])

    def test_all_forecasts_blocked_red_before_first_story_and_no_retry(self):
        p=json.loads(foresight_plan())
        # Both paths depend on known-off mains power but demand known-on.
        p["horizon"]["choices"][1]["steps"][0]["requires"]=[
            {"key":"power:station","is":"on"}]
        with patch("writerforge.writing_assist.local_chat_completion",
                   side_effect=[json.dumps(p,ensure_ascii=False)]) as model:
            with self.assertRaisesRegex(WritingExecutionError,"ALL_FUTURE_PATHS"):
                AutonomousWriting(self.assist).run(
                    outline=OUTLINE,chapter_goals=GOALS,
                    output_dir=self.root/"impossible",draft_mode="foresight_rolling",
                    forward_author_pinned_facts={"power:station":"off"},
                    frozen_turn_outlines=(json.dumps(turns(),ensure_ascii=False),))
        self.assertEqual(model.call_count,1)
        red=list((self.root/"impossible").rglob("foresight-rejected.json"))
        self.assertEqual(len(red),0)  # actual file has chapter prefix
        red=list((self.root/"impossible").rglob("*-foresight-rejected.json"))
        self.assertEqual(len(red),1)
        saved=json.loads(red[0].read_text("utf8"))
        self.assertEqual(saved["new_model_retries"],0)
        preplan=list((self.root/"impossible").rglob("*-raw-plan.json"))
        self.assertEqual(len(preplan),1)
        self.assertEqual(json.loads(preplan[0].read_text("utf8")),
                         p)
        self.assertEqual(saved["accepted_prose"],False)
        self.assertFalse(list((self.root/"impossible").rglob("candidate.txt")))

    def test_malformed_chapter_plan_still_stores_raw_evidence_and_red(self):
        incomplete='{"objective":"空故事，但关键字段没有齐全"}'
        with patch("writerforge.writing_assist.local_chat_completion",
                   side_effect=[incomplete]) as calls:
            with self.assertRaises(WritingExecutionError):
                AutonomousWriting(self.assist).run(
                    outline=OUTLINE,chapter_goals=GOALS,
                    output_dir=self.root/"bad-json-forecast",
                    draft_mode="foresight_rolling",
                    frozen_turn_outlines=(
                        json.dumps(turns(),ensure_ascii=False),))
        self.assertEqual(calls.call_count,1)
        body=list((self.root/"bad-json-forecast").rglob(
            "*-raw-plan.json"))
        self.assertEqual(len(body),1)
        self.assertEqual(body[0].read_text("utf8"),incomplete)
        red=list((self.root/"bad-json-forecast").rglob(
            "*-foresight-rejected.json"))
        self.assertEqual(len(red),1)
        self.assertEqual(json.loads(red[0].read_text("utf8"))["code"],
                         "WF105_ORIGINAL_CHAPTER_PLAN_INVALID")

    def test_f_only_author_controls_cannot_launder_model_into_canon(self):
        with patch("writerforge.writing_assist.local_chat_completion") as model:
            with self.assertRaisesRegex(WritingExecutionError,
                                        "PINNED_AUTHOR_FACT_INVALID"):
                AutonomousWriting(self.assist).run(
                    outline=OUTLINE,chapter_goals=GOALS,
                    output_dir=self.root/"invalid-facts",
                    draft_mode="foresight_rolling",
                    forward_author_pinned_facts={"I know everything":"yes"})
            self.assertEqual(model.call_count,0)
        with patch("writerforge.writing_assist.local_chat_completion") as model:
            with self.assertRaisesRegex(WritingExecutionError,
                                        "GUARDS_CANNOT_BE_IGNORED"):
                AutonomousWriting(self.assist).run(
                    outline=OUTLINE,chapter_goals=GOALS,
                    output_dir=self.root/"legacy-ignored",
                    draft_mode="rolling_causal",
                    forward_author_pinned_facts={"power:station":"on"})
            self.assertEqual(model.call_count,0)

    def test_studio_f_is_explicit_nonautomatic_optional(self):
        html=(Path(__file__).parents[1]/"writerforge"/"ui"/
              "studio.html").read_text("utf8")
        self.assertIn('value="foresight_rolling"',html)
        self.assertIn('value="single"',html)
        service=StudioService(
            db_path=self.dbpath,project="v105-test-only",
            scene="another-scene",goal="夜里从尚未决定的风险中作出选择",
            model="synthetic-no-network",output_dir=self.root/"studio")
        with self.assertRaisesRegex(Exception,"MAX_TWO_CHAPTERS"):
            service.start_auto(OUTLINE,GOALS*3,draft_mode="foresight_rolling")
        self.assertEqual(service.job()["status"],"idle")


if __name__=="__main__":
    unittest.main()
