"""0.CA replay of 0.BZ REAL local original bytes; no model inference.

Only candidate source prose can survive an untrusted *optional trace* envelope.
Never turn copied model claims into effects/known facts; malformed JSON, missing
prose, prohibited source text and unsourced character choices stay RED.
"""
from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path
import unittest

from writerforge.v96_causal_turns import (
    V96CausalDraftError,parse_turn_outline,check_turn,
    review_only_model_turn,
)
from writerforge.writing_assist import _normalize_optional_model_craft_labels

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/"experiments/wf_0bz_real_local_originals_20261029"


def real_reply(scene,arm,n):
    path=SOURCE/scene/arm/f"call_{n:02d}_raw.json"
    return json.loads(path.read_text("utf8"))["choices"][0]["text"]


class RealAuthorSourceFirstRecovery(unittest.TestCase):
    def test_short_real_character_goals_survive_without_changing_authored_intent(self):
        original=real_reply("medicine-rights","wf_g",2)
        adjusted,receipt=_normalize_optional_model_craft_labels(original)
        self.assertIsNotNone(receipt)
        beats=parse_turn_outline(adjusted)
        self.assertEqual(len(beats),10)
        self.assertEqual(beats[1]["goal"],"扣住药签")
        self.assertEqual(beats[1]["causal_parent"],"t01")
        self.assertEqual(beats[4]["actor"],"夏舟")
        self.assertEqual(beats[4]["craft_focus"],[])
        self.assertNotEqual(original,adjusted)
        self.assertEqual(receipt["model_calls"],0)

    def test_actual_original_prose_is_kept_only_for_review_with_invalid_trace(self):
        plan=real_reply("medicine-rights","wf_g_reading",2)
        beats=parse_turn_outline(plan)
        raw=real_reply("medicine-rights","wf_g_reading",3)
        original_doc=json.loads(raw)
        self.assertEqual(original_doc["trace"],{})
        with self.assertRaisesRegex(V96CausalDraftError,
                                    "WF96_TURN_PROSE_OR_TRACE_SCHEMA_INVALID"):
            check_turn(raw,beats[0],mode="causal_guard",
                       max_prose_chars=1024)
        with self.assertRaisesRegex(V96CausalDraftError,
                                    "WF96_TRACE_RECOVERY_NOT_AN_OPTIONAL_CITATION_FAILURE"):
            review_only_model_turn(
                raw,beats[0],
                failure_code="WF96_TURN_PROSE_OR_TRACE_SCHEMA_INVALID",
                max_prose_chars=1024)
        candidate=review_only_model_turn(
            raw,beats[0],
            failure_code="WF96_TURN_PROSE_OR_TRACE_SCHEMA_INVALID",
            max_prose_chars=1024,
            allow_untrusted_trace_envelope=True)
        self.assertEqual(candidate["prose"],original_doc["prose"].strip())
        self.assertIsNone(candidate["effect_quote"])
        receipt=candidate["receipt"]
        self.assertTrue(receipt["source_causal_review_required"])
        self.assertEqual(receipt["causal_check"],
                         "TRACE_REJECTED_SOURCE_PROSE_REVIEW_ONLY")
        self.assertEqual(receipt["model_trace_failure_code"],
                         "WF96_TURN_PROSE_OR_TRACE_SCHEMA_INVALID")
        self.assertTrue(receipt["untrusted_trace_envelope_ignored"])
        self.assertFalse(receipt["causal_relation_verified"])
        self.assertFalse(receipt["eligible_for_factjournal_KNOWN"])
        self.assertFalse(receipt["eligible_for_experience_promotion"])
        self.assertTrue(receipt["candidate_requires_author_acceptance"])

    def test_not_a_general_json_or_story_repair(self):
        raw=real_reply("mountain-array","wf_g",2)
        with self.assertRaisesRegex(V96CausalDraftError,
                                    "WF96_JSON_INVALID_OR_DUPLICATE_KEYS"):
            parse_turn_outline(raw)
        bad=real_reply("mountain-array","wf_g_reading",2)
        adjusted,_=_normalize_optional_model_craft_labels(bad)
        with self.assertRaisesRegex(V96CausalDraftError,
                                    "WF96_TURN_PLAN_FIELDS_ID_OR_CRAFT_INVALID"):
            parse_turn_outline(adjusted)

    def test_missing_prose_extra_story_facts_and_approved_exclusions_stay_red(self):
        raw=real_reply("medicine-rights","wf_g_reading",3)
        beat=parse_turn_outline(
            real_reply("medicine-rights","wf_g_reading",2))[0]
        obj=json.loads(raw)
        cases=[
            {**obj,"prose":""},
            {**obj,"prose":"写"},
            {**obj,"confirmed_private_fact":"伪造"},
            {**obj,"trace":{"whatever":"unverified"}},
        ]
        for case in cases:
            with self.subTest(case=str(case)[:75]):
                with self.assertRaisesRegex(V96CausalDraftError,
                                            "WF96_TRACE_RECOVERY_UNSAFE_PROSE_OR_SCHEMA"):
                    review_only_model_turn(
                        json.dumps(case,ensure_ascii=False),beat,
                        failure_code="WF96_TURN_PROSE_OR_TRACE_SCHEMA_INVALID",
                        max_prose_chars=1024,
                        allow_untrusted_trace_envelope=True)
        with self.assertRaisesRegex(
                V96CausalDraftError,
                "WF96_AUTHOR_CONFIRMED_KNOWLEDGE_BOUNDARY_VIOLATION"):
            review_only_model_turn(
                raw,beat,
                failure_code="WF96_TURN_PROSE_OR_TRACE_SCHEMA_INVALID",
                max_prose_chars=1024,
                allow_untrusted_trace_envelope=True,
                author_confirmed_forbidden_phrases=("失踪者姐姐的弟弟夏舟",))

    def test_real_three_original_outputs_replayed_through_actual_g_before_forced_stop(self):
        """Replay saved author bytes, NOT another 3B call or a fabricated chapter."""
        from tempfile import TemporaryDirectory
        from unittest.mock import patch
        from writerforge import WriterForgeDB,RuntimeEngine,XuehaiStore
        from writerforge.writing_assist import InvisibleWritingAssist,AutonomousWriting
        from writerforge.verified_flow import WritingExecutionError
        from test_v26_invisible_writer import make_db
        from experiments.wf_0bz_real_local_literary_three_arm_once import SCENES

        scene=SCENES[0]
        pack=json.loads((ROOT/"experiments/wf_0bt_original_eight_close_readings_20261028.json").read_text("utf8"))
        item=next(x for x in pack["items"] if x["id"]=="original-read-bq-09")
        src=pack["sources"][item["source_key"]]
        full=(f"【出处】{item['work']}·{item['chapter']}｜{src['url']}\n"
              f"【原文】\n{item['original']}\n【批注】\n"+
              "\n".join(f"{j}. {note}" for j,note in enumerate(item["annotation"],1))+
              "\n【心得】\n"+item["reflection"])
        fixed_originals=[
            real_reply("medicine-rights","wf_g_reading",i)
            for i in (1,2,3)
        ]
        with TemporaryDirectory() as tmp:
            root=Path(tmp)
            dbfile=root/"only-isolated-source.sqlite"
            parent=make_db(dbfile)
            db=WriterForgeDB(dbfile)
            rt=RuntimeEngine()
            try:
                rt.enter_learn()
                store=XuehaiStore(db,rt)
                sid=store.create_staging_snapshot(parent_id=parent)
                entry=store.add_entry(
                    sid,work_id="book-original",text=full,
                    library_class="古代原文＋批注＋心得",
                    culture="中国",genre="玄幻",
                    source_role="original_annotation_reflection",
                    function="宗门分药堂与失踪者姐姐代领药签",
                    effect=item["title"],method_cluster=item["id"])
                store.publish(sid)
                rt.exit();rt.enter_write(sid)
                selected=store.select_literary_reading_for_author(
                    goal=scene["goal"],max_chars=4900)
                self.assertEqual(selected["entry_id"],entry)
                self.assertIn(item["original"],selected["complete_reading"])

                assist=InvisibleWritingAssist(
                    db,rt,"wf0cb-source-replay","medicine-rights",
                    scene["goal"],model="saved-Qwen25-replay-NO-INFERENCE",
                    api_base="http://127.0.0.1:1/v1",source_genre="玄幻")
                packets=[]
                def saved_author(packet,*,model,api_base,max_tokens):
                    packets.append(packet)
                    if len(packets)<=3:
                        return fixed_originals[len(packets)-1]
                    # Deliberate test-only invalid fourth answer to stop
                    # before any made-up continuation is called a real model.
                    return "{}"
                with patch("writerforge.writing_assist.local_chat_completion",
                           side_effect=saved_author):
                    with self.assertRaisesRegex(
                            WritingExecutionError,"WF96_SCENE_TURN_REJECTED_"):
                        AutonomousWriting(assist).run(
                            outline=scene["outline"],
                            chapter_goals=[scene["goal"]],
                            output_dir=root/"work",
                            draft_mode="continuity_guard",
                            bootstrap_unified_core=True,
                            narrative_memory_backend="local",
                            g_rolling_author_planning=True,
                            self_edit_rounds=0,
                            xuehai_methods_enabled=False,
                            xuehai_readings_enabled=True)
                self.assertEqual(len(packets),4)
                self.assertIn("【完整阅读】",packets[0].prompt)
                self.assertIn("【原文】",packets[0].prompt)
                self.assertIn("【心得】",packets[0].prompt)
                # This was the TRUE 0.BZ author error: top-level SKIP is
                # a reading selector, not the character's story decision.
                # WF must not propagate it as plot in turn planning/prose.
                self.assertNotIn('"decision": "SKIP"',packets[1].prompt)
                self.assertNotIn('"decision": "SKIP"',packets[2].prompt)
                self.assertIn("人物决定仍需作者在正文中自行完成",packets[1].prompt)
                jobs=list((root/"work").glob("auto-*"))
                self.assertEqual(len(jobs),1)
                job=jobs[0]
                self.assertEqual(
                    (job/"chapter-001-raw-author-plan-misplaced.json").read_text("utf8"),
                    fixed_originals[0])
                self.assertTrue((job/"chapter-001-turn-01-raw.json").is_file())
                self.assertEqual(
                    (job/"chapter-001-turn-01-raw.json").read_text("utf8"),
                    fixed_originals[2])
                self.assertFalse(list(job.rglob("candidate.md")))
                self.assertFalse(list(job.rglob("job_manifest.json")))
                failure=json.loads((job/"chapter-001-rejected.json").read_text("utf8"))
                self.assertEqual(failure["candidate_chapter_completed"],False)
                self.assertEqual(failure["canonical_fact_writes"],0)
                self.assertEqual(failure["previous_valid_turn_count"],1)
                self.assertEqual(failure["automatic_repair_attempts"],0)
                partial=job/"chapter-001-partial-unaccepted-prose.txt"
                self.assertTrue(partial.is_file())
                self.assertEqual(partial.read_text("utf8"),
                                 json.loads(fixed_originals[2])["prose"].strip())
                self.assertEqual(
                    failure["partial_unaccepted_source_sha256"],
                    sha256(partial.read_bytes()).hexdigest())
                self.assertEqual(failure["partial_unaccepted_turns"],1)
                self.assertTrue(
                    failure["partial_unaccepted_requires_author_review"])
                self.assertFalse(
                    failure["partial_unaccepted_eligible_for_canon"])
                self.assertFalse(
                    failure["partial_unaccepted_causal_truth_proven"])
            finally:
                rt.exit()
                db.close()

    def test_real_invalid_first_turn_leaves_no_phantom_partial_manuscript(self):
        """0.BZ mountain prose never started: no fake recovered candidate."""
        from tempfile import TemporaryDirectory
        from unittest.mock import patch
        from writerforge import WriterForgeDB,RuntimeEngine,XuehaiStore
        from writerforge.writing_assist import InvisibleWritingAssist,AutonomousWriting
        from writerforge.verified_flow import WritingExecutionError
        from test_v26_invisible_writer import make_db
        from experiments.wf_0bz_real_local_literary_three_arm_once import SCENES
        scene=SCENES[1]
        originals=[real_reply("mountain-array","wf_g",1),
                   real_reply("mountain-array","wf_g",2)]
        with TemporaryDirectory() as tmp:
            root=Path(tmp)
            dbfile=root/"disposable-source.sqlite"
            sid=make_db(dbfile)
            db=WriterForgeDB(dbfile)
            rt=RuntimeEngine()
            rt.enter_learn()
            # This disposable source must be relevant to the real scenario.
            # Otherwise original WF correctly rejects missing source BEFORE
            # seeing any of the two saved model replies.
            book=json.loads((
                ROOT/"experiments/wf_0bu_remaining_sixteen_original_close_readings_20261028.json"
            ).read_text("utf8"))
            row=next(r for r in book["items"]
                     if r["id"]=="original-read-bq-03")
            src=book["sources"][row["source_key"]]
            full=(f"【出处】{row['work']}·{row['chapter']}｜{src['url']}\n"
                  f"【原文】\n{row['original']}\n【批注】\n"+
                  "\n".join(f"{j}. {x}" for j,x in enumerate(row["annotation"],1))+
                  "\n【心得】\n"+row["reflection"])
            store=XuehaiStore(db,rt)
            child=store.create_staging_snapshot(parent_id=sid)
            store.add_entry(child,work_id="book-original",text=full,
                            source_role="original_annotation_reflection",
                            library_class="原创小说原文＋批注＋心得",
                            culture="中国",genre="玄幻",
                            function="护山阵阵井与铜钉结霜",
                            effect=row["title"],method_cluster=row["id"])
            store.publish(child)
            rt.exit();rt.enter_write(child)
            calls=[]
            def replay(packet,*,model,api_base,max_tokens):
                calls.append(packet.prompt_sha256)
                return originals[len(calls)-1]
            try:
                assist=InvisibleWritingAssist(
                    db,rt,"wf0cb-source-replay","mountain-array",scene["goal"],
                    model="saved-Qwen25-replay-NO-INFERENCE",
                    api_base="http://127.0.0.1:1/v1",source_genre="玄幻")
                with patch("writerforge.writing_assist.local_chat_completion",
                           side_effect=replay):
                    with self.assertRaisesRegex(
                        WritingExecutionError,
                        "WF96_SCENE_TURN_REJECTED_WF96_JSON_INVALID_OR_DUPLICATE_KEYS"):
                        AutonomousWriting(assist).run(
                            outline=scene["outline"],chapter_goals=[scene["goal"]],
                            output_dir=root/"work",
                            draft_mode="continuity_guard",
                            bootstrap_unified_core=True,
                            narrative_memory_backend="local",
                            g_rolling_author_planning=True,
                            self_edit_rounds=0)
                self.assertEqual(len(calls),2)
                jobs=list((root/"work").glob("auto-*"))
                self.assertEqual(len(jobs),1)
                job=jobs[0]
                failure=json.loads((job/"chapter-001-rejected.json").read_text("utf8"))
                self.assertEqual(failure["previous_valid_turn_count"],0)
                self.assertNotIn("partial_unaccepted_source_path",failure)
                self.assertFalse(list(job.glob("*partial-unaccepted-prose.txt")))
                self.assertFalse(list(job.rglob("candidate.md")))
            finally:
                rt.exit()
                db.close()

    def test_original_model_still_is_not_claimed_to_have_used_a_reading(self):
        for scene in ("medicine-rights","mountain-array"):
            answer=real_reply(scene,"wf_g_reading",1)
            if answer.startswith("```json"):
                answer=answer.split("\n",1)[1].rsplit("```",1)[0]
            doc=json.loads(answer)
            self.assertIn(doc["decision"],("USE","SKIP"))
            self.assertNotIn("reading_choice",doc)


if __name__=="__main__":
    unittest.main()
