"""V98 novel writing logic: actual-prose-driven rolling plan, not self-grade.

No model, no R2, no external network. Uses the already-grounded V96
action/effect/check_turn evidence, then proposes the NEXT beat from actual
source text. Not enough to establish narrative truth or literary quality.
"""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import json
import time
import unittest

from test_v26_invisible_writer import PLAN,make_db
from test_v96_causal_turns import (
    ACTION1,EFFECT1,ACTION2,EFFECT2,GUARD,
    turns,prose1,prose2,response,
)
from writerforge import WriterForgeDB,RuntimeEngine
from writerforge.writing_assist import (
    AutonomousWriting,InvisibleWritingAssist,WritingExecutionError
)
from writerforge.studio_server import StudioService
from writerforge.v96_causal_turns import (
    parse_turn_outline,check_turn,canonical,digest
)
from writerforge.v98_rolling_causal_planner import (
    V98RollingPlanError,validate_replan,prepare_replan_instructions,
    latest_observed_effect,MAX_ROLLING_REPLANS_PER_JOB
)

OUTLINE="少年必须把重病老人的药送进城，桥边守夜人收起木牌，同行女子知道旧账册却不知今晚发生了什么。"
GOALS=["本章：少年因桥边异常绕路，并与同行者从实际后果中重新决策"]
BASE_BEATS=parse_turn_outline(json.dumps(turns(),ensure_ascii=False))
REAL_COST="他本来答应朋友当夜入城"
REAL_OBSTACLE="桥下的铁链刮过石壁"


def first():
    return check_turn(response(prose1(),ACTION1,EFFECT1),
                      BASE_BEATS[0],mode="causal_guard")


def proposed(*,basis=EFFECT1,cost=REAL_COST,pressure=REAL_OBSTACLE,
             actor="女子",parent="t01",goal=None):
    return {
        "next_turn":{
            "id":"t02","kind":"decision","actor":actor,
            "goal":goal or "女子沿着旧堤停下，先核查桥索去向并与少年商量新的行动",
            "causal_parent":parent,"craft_focus":["dialogue","detail"]
        },
        "basis_effect_quote":basis,
        "pressure_quote":pressure,
        "cost_quote":cost,
        "unresolved_question":"守夜人真正收起通行牌的原因仍没有人在场证实。",
        "reason_for_shift":"上段实际决定绕桥，下一幕要面对失去进城时机的新代价。",
    }


def raw(obj):
    return json.dumps(obj,ensure_ascii=False)


class V98RollingPlannerTests(unittest.TestCase):
    def invoke(self,obj=None):
        return validate_replan(raw(obj or proposed()),
            accepted=(first(),),accepted_beats=(BASE_BEATS[0],),
            seed_next_beat=BASE_BEATS[1],
            allowed_actor_names=("少年","女子"))

    def test_real_prose_consequence_anchors_next_plan_without_canon(self):
        new,receipt=self.invoke()
        self.assertNotEqual(new["goal"],BASE_BEATS[1]["goal"])
        self.assertEqual(new["causal_parent"],"t01")
        self.assertTrue(receipt["changed_from_frozen_seed"])
        self.assertEqual(receipt["cost_state"],
                         "QUOTED_NOT_SEMANTICALLY_VERIFIED")
        self.assertTrue(receipt["cost_anchor"]["start"]>=0)
        self.assertEqual(receipt["grounded_prior_beat_id"],"t01")
        self.assertFalse(receipt["narrative_semantics_independently_verified"])
        self.assertFalse(receipt["character_knowledge_promoted_to_KNOWN"])
        self.assertEqual(receipt["canon_or_factjournal_writes"],0)
        self.assertFalse(receipt["skill_promotion_approved"])
        self.assertNotIn("本来答应朋友",str(receipt))
        self.assertNotIn("核查桥索去向",str(receipt))
        instruction=prepare_replan_instructions(
            accepted=(first(),),seed_next_beat=BASE_BEATS[1],
            allowed_actor_names=("少年","女子"))
        self.assertIn(EFFECT1,instruction)
        self.assertIn(BASE_BEATS[1]["goal"],instruction)
        self.assertIn("不是已知事实",instruction)

    def test_fabricated_nonexistent_prior_effect_rejected(self):
        with self.assertRaisesRegex(V98RollingPlanError,
                                    "NOT_ANCHORED_TO_ACTUAL_EFFECT"):
            self.invoke(proposed(basis="少年已经找到幕后操纵者"))
        with self.assertRaisesRegex(V98RollingPlanError,
                                    "COST_QUOTE_NOT_UNIQUE_IN_ACTUAL_PROSE"):
            self.invoke(proposed(cost="他付出了不存在的代价"))

    def test_declared_cost_missing_is_unknown_not_story_truth(self):
        p=proposed(cost=None,pressure=None)
        new,receipt=self.invoke(p)
        self.assertIsNone(receipt["cost_anchor"])
        self.assertIsNone(receipt["pressure_anchor"])
        self.assertEqual(receipt["cost_state"],"UNRESOLVED_NOT_STATED")
        self.assertFalse(receipt["narrative_semantics_independently_verified"])

    def test_noncast_actor_and_wrong_parent_cannot_drift(self):
        with self.assertRaisesRegex(V98RollingPlanError,
                                    "ID_CAST_OR_CAUSAL_PARENT"):
            self.invoke(proposed(actor="未登场仙帝"))
        with self.assertRaisesRegex(V98RollingPlanError,
                                    "ID_CAST_OR_CAUSAL_PARENT"):
            self.invoke(proposed(parent="t99"))

    def test_guessed_future_knowledge_blocked_from_new_goal(self):
        p=proposed(goal="女子突然知道密钥的真相并要求少年去救另外一个朋友")
        with self.assertRaisesRegex(V98RollingPlanError,
                                    "AUTHOR_KNOWLEDGE_BOUNDARY"):
            validate_replan(raw(p),accepted=(first(),),
                accepted_beats=(BASE_BEATS[0],),
                seed_next_beat=BASE_BEATS[1],
                allowed_actor_names=("少年","女子"),
                author_forbidden_phrases=("密钥的真相",))

    def test_bad_unicode_json_duplicate_keys_and_fake_fields(self):
        with self.assertRaisesRegex(V98RollingPlanError,"JSON_INVALID"):
            validate_replan('{"a":1,"a":2}',
                accepted=(first(),),accepted_beats=(BASE_BEATS[0],),
                seed_next_beat=BASE_BEATS[1],
                allowed_actor_names=("少年","女子"))
        p=proposed()
        p["literary_pass"]=True
        with self.assertRaisesRegex(V98RollingPlanError,"RESPONSE_SCHEMA"):
            self.invoke(p)
        with self.assertRaisesRegex((V98RollingPlanError),
                                    "JSON"):
            self.invoke(proposed(goal="试图插入非法代码\ud800"))

    def test_model_cannot_skip_turn_id(self):
        p=proposed()
        p["next_turn"]["id"]="t04"
        with self.assertRaisesRegex(V98RollingPlanError,
                                    "ID_CAST_OR_CAUSAL_PARENT"):
            self.invoke(p)

    def test_no_actual_causal_effect_is_not_a_fake_parent(self):
        idle_beat={
            "id":"t01","kind":"quiet","actor":"少年",
            "goal":"少年安静地观察时不能提前声明产生任何决定",
            "causal_parent":None,"craft_focus":["restraint"]
        }
        prose="雨停之前两人一直沉默地站在门边。药箱上的绳子还湿着，远处的船铃若隐若现。"*2
        quiet=check_turn(
            response(prose,None,None),idle_beat,mode="causal_guard")
        with self.assertRaisesRegex(V98RollingPlanError,"NO_ACTUAL_PRIOR_EFFECT"):
            latest_observed_effect((quiet,))

    def test_repeated_quoted_cost_does_not_become_unique_evidence(self):
        cost="他本来答应朋友当夜入城"
        repeated=prose1()+"。"+cost
        a=check_turn(response(repeated,ACTION1,EFFECT1),
                     BASE_BEATS[0],mode="causal_guard")
        with self.assertRaisesRegex(V98RollingPlanError,
                                    "COST_QUOTE_NOT_UNIQUE"):
            validate_replan(raw(proposed()),
                accepted=(a,),accepted_beats=(BASE_BEATS[0],),
                seed_next_beat=BASE_BEATS[1],
                allowed_actor_names=("少年","女子"))


class V98ExistingWritingIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp=TemporaryDirectory()
        self.root=Path(self.temp.name)
        path=self.root/"db.sqlite"
        self.snapshot=make_db(path)
        self.db=WriterForgeDB(path)
        self.runtime=RuntimeEngine()
        self.runtime.enter_write(self.snapshot)
        self.assist=InvisibleWritingAssist(
            self.db,self.runtime,
            "v98-real-writer-test","scene-v98",
            "护送药材经过封闭桥头，需要应付真正后果",
            model="fake-local-no-cost",
            api_base="http://127.0.0.1:1234/v1",
        )
        self.dbpath=path

    def tearDown(self):
        self.db.close()
        self.temp.cleanup()

    def run_with(self,inputs,output,mode="rolling_causal"):
        with patch("writerforge.writing_assist.local_chat_completion",
                   side_effect=inputs) as model:
            answer=AutonomousWriting(self.assist).run(
                outline=OUTLINE,chapter_goals=GOALS,
                output_dir=self.root/output,draft_mode=mode,
                frozen_turn_outlines=(raw(turns()),))
        return answer,model.call_args_list

    def test_real_existing_writing_path_replans_from_actual_first_effect(self):
        doc,calls=self.run_with([
            PLAN,
            response(prose1(),ACTION1,EFFECT1),
            raw(proposed()),
            response(prose2(),ACTION2,EFFECT2,EFFECT1),
        ],"valid")
        self.assertEqual(len(calls),4)  # C has 3; D adds exactly one replan.
        self.assertEqual([x.kwargs["max_tokens"] for x in calls],
                         [650,1450,650,1450])
        self.assertIn(EFFECT1,calls[2].args[0].prompt)
        self.assertIn("上一段实际",calls[2].args[0].prompt
                      .replace("刚刚真正写出的情节","上一段实际"))
        chapter=doc["chapters"][0]
        self.assertEqual(doc["draft_mode"],"rolling_causal")
        self.assertEqual(doc["rolling_replan_model_calls"],1)
        self.assertEqual(doc["canonical_fact_writes"],0)
        self.assertFalse(chapter["accepted"])
        self.assertEqual(Path(chapter["candidate"]).read_text("utf8"),
                         prose1()+"\n\n"+prose2())
        state=json.loads(Path(chapter["turn_evidence"]).read_text("utf8"))
        self.assertEqual(state["mode"],"rolling_causal")
        self.assertEqual(len(state["rolling_proposal_receipts"]),1)
        self.assertTrue(state["rewritten_future_from_actual_prose"])
        self.assertFalse(state["semantic_causality_proven"])
        data={k:v for k,v in state.items() if k!="manifest_sha256"}
        self.assertEqual(state["manifest_sha256"],digest(canonical(data)))
        private=json.loads(Path(chapter["v98_rolling_plan"]).read_text("utf8"))
        self.assertEqual(len(private["evolved_candidate_turns"]),2)
        self.assertNotEqual(private["initial_seed_turns"][1]["goal"],
                            private["evolved_candidate_turns"][1]["goal"])
        self.assertFalse(private["semantic_truth_verified"])
        self.assertIsNone(self.db.conn.execute(
            "SELECT 1 FROM accepted_prose").fetchone())

    def test_forged_replan_stops_without_second_prose_or_auto_retry(self):
        p=proposed(basis="先前已经捉住了不存在的幕后真凶")
        with patch("writerforge.writing_assist.local_chat_completion",
                   side_effect=[
                       PLAN,
                       response(prose1(),ACTION1,EFFECT1),
                       raw(p)
                   ]) as model:
            with self.assertRaisesRegex(WritingExecutionError,
                                        "WF96_SCENE_TURN_REJECTED_WF98"):
                AutonomousWriting(self.assist).run(
                    outline=OUTLINE,chapter_goals=GOALS,
                    output_dir=self.root/"bad",draft_mode="rolling_causal",
                    frozen_turn_outlines=(raw(turns()),))
        self.assertEqual(model.call_count,3)
        red=list((self.root/"bad").glob("auto-*/chapter-001-rejected.json"))
        self.assertEqual(len(red),1)
        failure=json.loads(red[0].read_text("utf8"))
        self.assertEqual(failure["previous_valid_turn_count"],1)
        self.assertEqual(failure["automatic_repair_attempts"],0)
        self.assertNotIn("不存在的幕后真凶",str(failure))
        self.assertFalse(list((self.root/"bad").rglob("candidate.txt")))
        self.assertIsNone(self.db.conn.execute(
            "SELECT 1 FROM accepted_prose").fetchone())

    def test_original_C_remains_three_calls_and_D_is_only_explicit(self):
        inputs=[
            PLAN,response(prose1(),ACTION1,EFFECT1),
            response(prose2(),ACTION2,EFFECT2,EFFECT1)]
        c,calls=self.run_with(inputs,"old-C",mode="causal_guard")
        self.assertEqual(len(calls),3)
        self.assertNotIn("rolling_replan_model_calls",c)
        html=(Path(__file__).parents[1]/"writerforge"/"ui"/
              "studio.html").read_text("utf8")
        self.assertIn('value="rolling_causal"',html)
        self.assertIn("额外模型调用",html)
        self.assertIn('value="single"',html)

    def test_bounded_replanning_for_two_chapters_and_default_mode(self):
        self.assertEqual(MAX_ROLLING_REPLANS_PER_JOB,14)
        studio=StudioService(
            db_path=self.dbpath,project="v98-real-writer-test",
            scene="local-studio",goal="桥上有人封锁通行，人物如何决定",
            model="synthetic-local",output_dir=self.root/"studio")
        self.assertEqual(studio.job()["status"],"idle")
        with self.assertRaisesRegex(Exception,"MAX_TWO_CHAPTERS"):
            studio.start_auto(OUTLINE,GOALS*3,
                              draft_mode="rolling_causal")
        self.assertEqual(studio.job()["status"],"idle")
        with patch("writerforge.studio_server.AutonomousWriting.run",
                   return_value={"status":"candidates_saved",
                                 "chapter_count":1,"chapters":[],
                                 "all_generated_prose_requires_author_review":True}
                   ) as run:
            queued=studio.start_auto(OUTLINE,GOALS,
                                     draft_mode="rolling_causal")
            for _ in range(80):
                if studio.job()["status"] in ("completed","failed"):
                    break
                time.sleep(.01)
            self.assertEqual(studio.job()["status"],"completed")
            self.assertEqual(queued["draft_mode"],"rolling_causal")
            self.assertEqual(run.call_args.kwargs["draft_mode"],
                             "rolling_causal")


if __name__=="__main__":
    unittest.main()
