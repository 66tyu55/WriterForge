"""V65 fail-first contextual literary lesson feeding & applicability probes.

No model calls, R2 reads, imported original novels, self-promotions or
automatically declared literary improvement. Tests verify CONTEXT DIFFERENCE
rather than how many adjective-filled advice strings are present.
"""
from __future__ import annotations

from hashlib import sha256
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from contextlib import redirect_stdout
from unittest.mock import patch
import json
import unittest

from writerforge.scene_craft_teaching import (
    SceneCraftTeacher, SceneCraftInputError, diagnosis_prompt,
    compare_scene_drafts, load_scene_lessons
)
from writerforge.db import WriterForgeDB
from writerforge.runtime import RuntimeEngine
from writerforge.verified_flow import VerifiedWritingFlow


def fact(state, note="角色在这个已设情境中可观察到相应的条件和行动影响"):
    return {"state":state,"observation":note}


def profile(*,mode="pursuit",effect="tension",tempo="fast",
            viewpoint="limited",facts=None,scene="synthetic_scene"):
    return {
        "schema":"writerforge.scene-profile.v1",
        "scene_id":scene,
        "diagnosis_origin":"TEACHER_DEMO",
        "mode":mode,"reader_effect":effect,"tempo":tempo,
        "viewpoint":viewpoint,
        "scene_goal":"少年必须在船离岸前保护契据并追上离开的人。",
        "active_obstacle":"雨中木桥湿滑，船只正在远去。",
        "planned_change":"少年在保护契据与追船之间被迫改变选择。",
        "facts":facts or {
            "environmental_obstacle":fact("PRESENT"),
            "urgent_goal":fact("PRESENT"),
            "safe_stationary":fact("ABSENT"),
            "deadline":fact("PRESENT"),
            "irreversible_action":fact("PRESENT"),
            "meditative_pause":fact("ABSENT"),
        },
    }


class V65ApplicabilityTests(unittest.TestCase):
    def setUp(self):
        self.teacher=SceneCraftTeacher()

    def test_thirteen_explicit_taught_lessons_have_both_good_bad_examples(self):
        data=load_scene_lessons()
        self.assertEqual(len(data["lessons"]),13)
        self.assertEqual(data["origin"],"ASSISTANT_TAUGHT_BY_USER_REQUEST")
        self.assertEqual(data["training_status"],
                         "INSTRUCTION_NOT_LEARNER_DISCOVERED")
        self.assertTrue(all(x["example_before"] and x["example_after"] and
                            x["pitfall"] and x["review_question"]
                            for x in data["lessons"]))

    def test_pursuit_uses_environment_and_urgent_rhythm_not_aftermath(self):
        result=self.teacher.plan(profile())
        self.assertEqual(result["selected_ids"],[
            "ENVIRONMENT_CHANGES_ACTION",
            "SENTENCE_PACE_FOLLOWS_PRESSURE"])
        self.assertNotIn("AFTERMATH_IN_SMALL_ACTION",result["selected_ids"])
        self.assertIn("环境",result["writer_guidance"])
        self.assertNotIn("栈桥第二块木板翻了边",result["writer_guidance"])
        self.assertTrue(result["example_prose_not_sent_to_writer"])

    def test_aftermath_uses_small_action_not_pursuit_rhythm(self):
        result=self.teacher.plan(profile(
            mode="aftermath",effect="grief",tempo="slow",
            facts={
                "consequence_irreversible":fact("PRESENT"),
                "character_changed":fact("PRESENT"),
                "fresh_immediate_chase":fact("ABSENT"),
            }))
        self.assertEqual(result["selected_ids"],["AFTERMATH_IN_SMALL_ACTION"])
        self.assertNotIn("SENTENCE_PACE_FOLLOWS_PRESSURE",
                         result["selected_ids"])
        self.assertIn("细小动作",result["writer_guidance"])

    def test_reveal_missing_prior_seed_must_refuse_fake_foreshadowing(self):
        facts={
            "earlier_clue":fact("ABSENT"),
            "later_reinterpretation":fact("PRESENT"),
            "no_prior_setup":fact("PRESENT"),
        }
        result=self.teacher.plan(profile(
            mode="revelation",effect="surprise",tempo="measured",
            facts=facts))
        item=next(x for x in result["decisions"]
                  if x["lesson_id"]=="SETUP_IS_NOT_PAYOFF")
        self.assertEqual(item["decision"],"SKIP")
        self.assertIn(item["reason_code"],{
            "CONTRAINDICATED","REQUIRED_CONDITION_FALSE"})
        self.assertEqual(result["writer_guidance"],"")

    def test_investigative_misread_chooses_clue_and_plausible_error(self):
        facts={
            "visible_clue":fact("PRESENT"),"information_gap":fact("PRESENT"),
            "facts_fully_revealed":fact("ABSENT"),
            "ambiguous_evidence":fact("PRESENT"),
            "plausible_false_belief":fact("PRESENT"),
            "proof_already_certain":fact("ABSENT"),
        }
        result=self.teacher.plan(profile(
            mode="investigation",effect="suspense",tempo="measured",
            facts=facts))
        self.assertEqual(result["selected_ids"],[
            "CLUE_BEFORE_EXPLANATION",
            "MISTAKE_COMES_FROM_LIMITED_EVIDENCE"])
        self.assertNotIn("悬念很重要",result["writer_guidance"])

    def test_uncertain_or_missing_evidence_cannot_be_confident_select(self):
        facts={
            "visible_clue":fact("UNCERTAIN"),
            "information_gap":fact("PRESENT"),
            "facts_fully_revealed":fact("ABSENT"),
        }
        result=self.teacher.plan(profile(
            mode="investigation",effect="suspense",tempo="measured",
            facts=facts))
        item=next(x for x in result["decisions"]
                  if x["lesson_id"]=="CLUE_BEFORE_EXPLANATION")
        self.assertEqual(item["decision"],"UNCERTAIN")
        self.assertEqual(item["reason_code"],"SCENE_EVIDENCE_UNCERTAIN")
        self.assertNotIn("CLUE_BEFORE_EXPLANATION",result["selected_ids"])

    def test_negotiation_uses_necessary_dialogue_not_generic_sceneries(self):
        facts={
            "opposing_goals":fact("PRESENT"),
            "exchange_changes_options":fact("PRESENT"),
            "lecture_only":fact("ABSENT"),
            "concealed_intent":fact("PRESENT"),
            "visible_choice":fact("PRESENT"),
            "clarity_needed_now":fact("ABSENT"),
        }
        result=self.teacher.plan(profile(mode="negotiation",effect="tension",
                                          tempo="measured",facts=facts))
        self.assertIn("DIALOGUE_IS_ATTEMPT",result["selected_ids"])
        self.assertNotIn("ENVIRONMENT_CHANGES_ACTION",result["selected_ids"])
        self.assertLessEqual(len(result["selected_ids"]),2)

    def test_transition_does_not_expand_into_ornate_description(self):
        result=self.teacher.plan(profile(
            mode="transition",effect="clarity",tempo="fast",
            facts={"time_place_shift":fact("PRESENT"),
                   "active_goal":fact("PRESENT"),
                   "pivotal_choice_now":fact("ABSENT")}))
        self.assertEqual(result["selected_ids"],
                         ["TRANSITION_ONLY_WHAT_CHANGES"])
        self.assertNotIn("AWE_HAS_HUMAN_SCALE",result["selected_ids"])

    def test_disabled_lessons_affect_nothing_and_reasons_are_explicit(self):
        result=self.teacher.plan(profile(),enabled=False)
        self.assertEqual(result["selected_ids"],[])
        self.assertEqual(result["writer_guidance"],"")
        self.assertTrue(all(x["decision"]=="SKIP" for x in
                            result["decisions"]))
        self.assertTrue(all(x["reason_code"]=="USER_DISABLED" for x in
                            result["decisions"]))

    def test_profile_invalid_schema_and_ungrounded_feature_are_rejected(self):
        bad=profile();bad["facts"]["invented_new_superpower"]=fact("PRESENT")
        with self.assertRaisesRegex(SceneCraftInputError,"FEATURE"):
            self.teacher.plan(bad)
        bad=profile();bad["facts"]["deadline"]=fact("PRESENT"," ")
        with self.assertRaisesRegex(SceneCraftInputError,"OBSERVATION"):
            self.teacher.plan(bad)
        bad=profile();bad["reader_effect"]="everything_is_amazing"
        with self.assertRaisesRegex(SceneCraftInputError,"SCENE_PROFILE"):
            self.teacher.plan(bad)

    def test_deterministic_semantic_profile_order_and_source_hash(self):
        one=profile()
        two={**one,"facts":dict(reversed(list(one["facts"].items())))}
        a=self.teacher.plan(one);b=self.teacher.plan(two)
        self.assertEqual(a["plan_sha256"],b["plan_sha256"])
        self.assertEqual(a["teaching_pack_sha256"],b["teaching_pack_sha256"])
        self.assertFalse(a["literary_improvement_proven"])

    def test_wf_diagnosis_prompt_asks_for_causal_context_not_keyword_match(self):
        prompt=diagnosis_prompt(
            "渡船离岸前必须追上，同时不能让契据淋湿。",
            scene_id="synthetic_scene")
        self.assertIn("人物",prompt)
        self.assertIn("行动",prompt)
        self.assertIn("证据",prompt)
        self.assertIn("UNCERTAIN",prompt)
        self.assertNotIn("例文：",prompt)

    def test_teacher_demo_profiles_show_four_different_applicability_outcomes(self):
        expected={
            "pursuit_pier.json":["ENVIRONMENT_CHANGES_ACTION",
                                "SENTENCE_PACE_FOLLOWS_PRESSURE"],
            "quiet_aftermath.json":["AFTERMATH_IN_SMALL_ACTION"],
            "revelation_without_seed.json":[],
            "negotiation_two_goals.json":["DIALOGUE_IS_ATTEMPT"],
        }
        for name,wanted in expected.items():
            with self.subTest(name=name):
                path=Path("examples/scene_craft")/name
                self.assertTrue(path.is_file())
                scene=json.loads(path.read_text(encoding="utf-8"))
                self.assertEqual(scene["diagnosis_origin"],"TEACHER_DEMO")
                actual=self.teacher.plan(scene)
                self.assertEqual(actual["selected_ids"],wanted)



class V65ComparisonTests(unittest.TestCase):
    def test_pair_without_grades_never_claims_writing_improvement(self):
        result=compare_scene_drafts(
            scene_id="bridge01",
            scene_profile_sha256="a"*64,
            teaching_pack_sha256="b"*64,
            selected_lesson_ids=["ENVIRONMENT_CHANGES_ACTION"],
            baseline_draft="少年抵达栈桥，" + "他追船并保护契据。"*42,
            taught_draft="少年踏上木板，" + "湿木板逼他护住契据。"*42)
        self.assertEqual(result["comparison_status"],
                         "TEXT_PAIR_READY_FOR_BLIND_REVIEW")
        self.assertFalse(result["literary_improvement_proven"])
        self.assertNotIn("baseline_draft",result)
        self.assertNotIn("taught_draft",result)

    def test_large_length_mismatch_is_unscorable_not_fake_negative(self):
        with self.assertRaisesRegex(SceneCraftInputError,"LENGTH_MISMATCH"):
            compare_scene_drafts(
                scene_id="bridge01",
                scene_profile_sha256="a"*64,
                teaching_pack_sha256="b"*64,
                selected_lesson_ids=["ENVIRONMENT_CHANGES_ACTION"],
                baseline_draft="一段拖延的文字。"*150,
                taught_draft="一段简短的文字。"*20)

    def test_scoped_negative_blind_review_never_promotes_any_lesson(self):
        baseline="人物去追赶船只，" + "他反复用行动确认了手中的纸张。"*32
        taught="人物踏过雨中栈桥，" + "他在湿滑路面上缓慢检查契据。"*32
        base=compare_scene_drafts(
            scene_id="bridge01",
            scene_profile_sha256="a"*64,
            teaching_pack_sha256="b"*64,
            selected_lesson_ids=["ENVIRONMENT_CHANGES_ACTION"],
            baseline_draft=baseline,taught_draft=taught)
        tag=[name for name,hash_ in
             base["review_blinding_labels_by_sha256"].items()
             if hash_==base["draft_sha256"]["taught"]][0]
        ratings={
            "A":{name:80 for name in (
                "causality","character_agency","information",
                "emotional_effect","prose_rhythm")},
            "B":{name:80 for name in (
                "causality","character_agency","information",
                "emotional_effect","prose_rhythm")},
        }
        ratings[tag]["information"]=50
        ratings[tag]["causality"]=90
        report=compare_scene_drafts(
            scene_id="bridge01",scene_profile_sha256="a"*64,
            teaching_pack_sha256="b"*64,
            selected_lesson_ids=["ENVIRONMENT_CHANGES_ACTION"],
            baseline_draft=baseline,taught_draft=taught,ratings=ratings)
        self.assertEqual(report["comparison_status"],
                         "TASK_SCOPED_REGRESSION")
        self.assertLess(report["per_dimension_taught_minus_baseline"]
                        ["information"],0)
        self.assertFalse(report["literary_improvement_proven"])

    def test_cli_comparison_emits_sha_only_no_prose_or_fake_score(self):
        from writerforge.cli import main
        with TemporaryDirectory() as tmp:
            old=Path(tmp)/"without.txt"
            new=Path(tmp)/"with.txt"
            old.write_text("少年守在桥头，" +
                           "他想追上渡船但没能前进。"*30,
                           encoding="utf-8")
            new.write_text("少年踏上湿桥，" +
                           "木板滑动迫他先护住契据。"*30,
                           encoding="utf-8")
            result=StringIO()
            with redirect_stdout(result):
                main(["scene-craft-compare",
                      "--scene","bridge01",
                      "--profile-sha256","a"*64,
                      "--pack-sha256","b"*64,
                      "--lessons","ENVIRONMENT_CHANGES_ACTION",
                      "--baseline-file",str(old),
                      "--taught-file",str(new)])
            output=json.loads(result.getvalue())
            self.assertEqual(output["comparison_status"],
                             "TEXT_PAIR_READY_FOR_BLIND_REVIEW")
            self.assertFalse(output["literary_improvement_proven"])
            self.assertTrue(output["original_drafts_not_retained"])
            self.assertNotIn("湿桥",result.getvalue())



class V65FormalWritingIntegrationTests(unittest.TestCase):
    def test_actual_prepare_receives_only_conditional_instructions(self):
        with TemporaryDirectory() as tmp:
            db=WriterForgeDB(Path(tmp)/"synthetic.db")
            try:
                runtime=RuntimeEngine()
                runtime.enter_learn()
                sid=db.conn.execute(
                    "INSERT INTO snapshots(status,layout,note) "
                    "VALUES('published','full','v65 fixture')").lastrowid
                db.conn.execute(
                    "INSERT INTO studied_works(work_id,title,source_uri,"
                    "source_sha256,chapter_count) VALUES(?,?,?,?,?)",
                    ("synthetic_work","Test","test://source","f"*64,1))
                db.conn.execute(
                    "INSERT INTO studied_chapters(work_id,chapter,chapter_sha256,"
                    "heading,source_spans,retrieval_entries,snapshot_id)"
                    " VALUES(?,?,?,?,?,?,?)",
                    ("synthetic_work",1,"f"*64,"Test",1,1,sid))
                db.conn.commit()
                runtime.exit();runtime.enter_write(sid)
                wf=VerifiedWritingFlow(db,runtime,"project65")
                stub=[{"entry_id":1,"work_id":"synthetic_work",
                       "location":[1,1,1],"function":"narration",
                       "effect":"unverified"}]
                with patch.object(wf.xuehai,"query",return_value=stub):
                    base=wf.prepare("synthetic_scene","追上离岸船只")
                    taught=wf.prepare("synthetic_scene","追上离岸船只",
                        scene_craft_profile=profile())
                    skipped=wf.prepare("synthetic_scene","追上离岸船只",
                        scene_craft_profile=profile(),scene_craft_enabled=False)
                self.assertNotEqual(base.prompt_sha256,taught.prompt_sha256)
                self.assertEqual(base.prompt_sha256,skipped.prompt_sha256)
                self.assertIn("环境",taught.prompt)
                self.assertNotIn("栈桥第二块木板翻了边",taught.prompt)
                self.assertEqual(taught.scene_craft_receipt["selected_ids"],
                                 ["ENVIRONMENT_CHANGES_ACTION",
                                  "SENTENCE_PACE_FOLLOWS_PRESSURE"])
                self.assertFalse(taught.manifest()["scene_craft"]
                                 ["literary_improvement_proven"])
                self.assertIsNone(base.scene_craft_receipt)
            finally:
                db.close()

    def test_wf_own_local_planner_can_produce_conditional_profile_and_persist(self):
        from writerforge.cli import main
        with TemporaryDirectory() as tmp:
            brief=Path(tmp)/"own_scene_outline.txt"
            brief.write_text(
                "少年追赶已离岸的渡船，木板湿滑可能让契据落水；"
                "船离开后行动机会消失，尚未到安静余波阶段。",
                encoding="utf-8")
            saved=Path(tmp)/"wf_scene_profile.json"
            raw=profile()
            raw["diagnosis_origin"]="WF_PLANNER"
            response=json.dumps(raw,ensure_ascii=False)
            with patch("writerforge.verified_flow.local_chat_completion",
                       return_value=response) as wf_model:
                capture=StringIO()
                with redirect_stdout(capture):
                    main(["scene-craft-diagnosis",
                          "--scene","synthetic_scene",
                          "--goal","少年必须在船离岸前追上离开的人。",
                          "--brief-file",str(brief),
                          "--model","synthetic-offline-planner",
                          "--output-profile",str(saved)])
            wf_model.assert_called_once()
            args=wf_model.call_args
            self.assertIn("UNCERTAIN",args.args[0].prompt)
            self.assertIn("木板湿滑",args.args[0].prompt)
            self.assertIn("场景语义诊断器",
                          args.kwargs["system_role_instruction"])
            received=json.loads(capture.getvalue())
            self.assertEqual(received["selected_ids"],[
                "ENVIRONMENT_CHANGES_ACTION",
                "SENTENCE_PACE_FOLLOWS_PRESSURE"])
            self.assertTrue(saved.is_file())
            stored=json.loads(saved.read_text(encoding="utf-8"))
            self.assertEqual(stored["diagnosis_origin"],"WF_PLANNER")
            self.assertFalse(received["literary_improvement_proven"])

    def test_cli_diagnosis_without_model_is_instruction_only(self):
        from writerforge.cli import main
        output=StringIO()
        with redirect_stdout(output):
            main(["scene-craft-diagnosis",
                  "--scene","synthetic_scene",
                  "--goal","少年赶在渡船离岸之前找到送信的人。"])
        doc=json.loads(output.getvalue())
        self.assertEqual(doc["model_calls"],0)
        self.assertIn("active_obstacle",doc["prompt"])
        self.assertFalse(doc["wf_writing_quality_verified"])

    def test_cli_scene_craft_plan_without_any_literary_model(self):
        from writerforge.cli import main
        with TemporaryDirectory() as tmp:
            config=Path(tmp)/"profile.json"
            config.write_text(json.dumps(profile(),ensure_ascii=False),
                              encoding="utf-8")
            capture=StringIO()
            with redirect_stdout(capture):
                main(["scene-craft-plan","--profile-file",str(config)])
            out=json.loads(capture.getvalue())
            self.assertEqual(out["selected_ids"],[
                "ENVIRONMENT_CHANGES_ACTION",
                "SENTENCE_PACE_FOLLOWS_PRESSURE"])
            self.assertFalse(out["literary_improvement_proven"])
            self.assertTrue(out["example_prose_not_sent_to_writer"])

if __name__=="__main__":
    unittest.main()
