"""Bounded AI-chosen previous-turn rewind: all model replies are synthetic.

No paid provider, repeated literary training, R2, Canon, or deployment.
The model fixture makes every artistic decision and supplies every new prose
byte. WF only verifies source identity and rolls back provisional state.
"""
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from writerforge import RuntimeEngine, WriterForgeDB
from writerforge.writing_assist import (
    AutonomousWriting, InvisibleWritingAssist,
    _ai_decides_when_to_revisit, _rewind_unaccepted_turn_suffix,
)
from writerforge.verified_flow import GroundedDraftPacket, WritingExecutionError
from writerforge.v114_external_story_state import external_temporal_step as real_temporal_step
from test_v26_invisible_writer import make_db, PLAN
from test_v96_causal_turns import (
    ACTION1, EFFECT1, ACTION2, EFFECT2,
    prose1, prose2, response, turns,
)


def digest(src):
    return hashlib.sha256(src.encode("utf8")).hexdigest()


def moment(decision, source, *, target="current", quote=None):
    reviewing = decision == "LOOK_BACK_NOW"
    return json.dumps({
        "decision":decision, "target_turn":target,
        "source_sha256":digest(source),
        "evidence_quote":quote if reviewing else None,
        "focus":"sentence" if reviewing and quote else
                "scene" if reviewing else None,
        "why_now":("上一段的开场环境交代妨碍人物行动的具体张力，应该调整。"
                   if reviewing else
                   "这里保留真实行动的后果和必要留白，更自然地接到下一场。"),
        "what_goes_wrong_if_unchanged":(
            "如果保留旧开场，下一段的天气和时间因果会让读者误解。"
            if reviewing else None),
        "intended_reader_effect":(
            "希望人物行动主导气氛变化，让下一个场景由结果生长。"
            if reviewing else None),
    },ensure_ascii=False)


class SourceTargetAndRewindTests(TestCase):
    def setUp(self):
        self.temp=TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base=Path(self.temp.name)
        self.beat=turns()["turns"][1]
        self.packet=GroundedDraftPacket(
            scene_id="rewind-scene",project_id="rewind-project",
            snapshot_id=1,evidence=(),craft_ids=(),
            prompt="这一任务的主模型负责创造小说，工作台只提供实际前文。",
            prompt_sha256=digest("这一任务的主模型负责创造小说，工作台只提供实际前文。"))

    def invoke(self, reply, *, previous=None, source=None):
        model_calls=[]
        def model(packet, **kwargs):
            model_calls.append(packet.prompt)
            return reply
        answer=_ai_decides_when_to_revisit(
            raw=source or response(prose2(),ACTION2,EFFECT2,EFFECT1),
            beat=self.beat,accepted=(
                ({"prose":previous,"effect_quote":EFFECT1},)
                if previous is not None else ()),
            turn_packet=self.packet,ask_model=model,
            directory=self.base/("moment-"+str(len(list(self.base.iterdir())))))
        return answer,model_calls

    def test_ai_can_choose_previous_source_without_code_literary_scoring(self):
        quote="黄昏最后一点天光落到桥头时，"
        selected, calls=self.invoke(
            moment("LOOK_BACK_NOW",prose1(),
                   target="previous",quote=quote),
            previous=prose1())
        self.assertEqual(selected["decision"],"LOOK_BACK_NOW")
        self.assertEqual(selected["target_turn"],"previous")
        self.assertEqual(selected["target_prose_sha256"],digest(prose1()))
        self.assertEqual(selected["source_quote"],quote)
        self.assertIn(prose1(),calls[0])
        self.assertIn(prose2(),calls[0])
        self.assertIn("不要返回 prose/trace",calls[0])
        self.assertFalse(selected["receipt"]["literary_quality_verified"])

    def test_previous_must_exist_and_old_json_decisions_stay_compatible(self):
        invalid,_=self.invoke(moment(
            "LOOK_BACK_NOW",prose1(),target="previous",
            quote="黄昏最后一点天光落到桥头时，"))
        self.assertEqual(invalid["decision"],"INVALID_SIGNAL")
        legacy=json.loads(moment("MOVE_ON",prose2()))
        legacy.pop("target_turn")
        old,_=self.invoke(json.dumps(legacy,ensure_ascii=False))
        self.assertEqual(old["decision"],"MOVE_ON")
        self.assertEqual(old["target_turn"],"current")

    def test_wrong_source_or_nonunique_previous_quote_cannot_edit(self):
        quote="黄昏最后一点天光落到桥头时，"
        forged=json.loads(moment("LOOK_BACK_NOW",prose1(),
                                 target="previous",quote=quote))
        forged["source_sha256"]="0"*64
        result,_=self.invoke(json.dumps(forged,ensure_ascii=False),
                             previous=prose1())
        self.assertEqual(result["decision"],"INVALID_SIGNAL")
        duplicate=prose1()+quote
        result,_=self.invoke(moment("LOOK_BACK_NOW",duplicate,
                                   target="previous",quote=quote),
                             previous=duplicate)
        self.assertEqual(result["decision"],"INVALID_SIGNAL")

    def test_rewind_invalidates_source_dependent_arrays_not_prior_state(self):
        first=prose1()
        accepted=[{"prose":first}]
        plans=[{"id":"t01"}]
        notifications=[{"old_lamp":True}]
        tracked=(accepted,plans,notifications)
        prior_external={"source":"initial-signed-chapter"}
        stale_external={"source":"now-abandoned-event"}
        snapshots=[
            {"counts":(0,0,0),"continuity":None,
             "external":prior_external,"lamp":None},
            {"counts":(1,1,1),"continuity":{"old":True},
             "external":stale_external,"lamp":{"old":True}},
        ]
        snapshot=_rewind_unaccepted_turn_suffix(
            accepted=accepted,source_sha256=digest(first),
            snapshots=snapshots,tracked=tracked)
        self.assertEqual(snapshot["external"],prior_external)
        self.assertEqual(accepted,[])
        self.assertEqual(plans,[])
        self.assertEqual(notifications,[])
        self.assertEqual(snapshots,[])

    def test_stale_source_causes_no_partial_rollback(self):
        a=[{"prose":prose1()}]
        b=[1]
        snaps=[{"counts":(0,0)},{"counts":(1,1)}]
        with self.assertRaisesRegex(WritingExecutionError,
                                    "WF_WRITER_REWIND_STALE_SOURCE"):
            _rewind_unaccepted_turn_suffix(
                accepted=a,source_sha256="0"*64,
                snapshots=snaps,tracked=(a,b))
        self.assertEqual(len(a),1)
        self.assertEqual(b,[1])
        self.assertEqual(len(snaps),2)


class WholeGWriterRewindMockProvider(TestCase):
    def test_ai_rewrites_previous_then_new_prose_uses_revised_source(self):
        target="黄昏最后一点天光落到桥头时，"
        replacement="山风起时，"
        original_first=prose1()
        revised_first=original_first.replace(target,replacement,1)
        original_next=prose2()
        regenerated_next=original_next.replace(
            "他们沿着旧堤走到废弃的驿站，",
            "山风渐停，他们沿着旧堤走到废弃的驿站，",1)
        previous_patch=json.dumps({
            "decision":"REVISE","scope":"sentence",
            "source_sha256":digest(original_first),
            "start":original_first.index(target),
            "end":original_first.index(target)+len(target),
            "expected_original":target,
            "replacement":replacement,
            "trace":{"action_quote":ACTION1,
                     "effect_quote":EFFECT1,
                     "parent_effect_quote":None},
            "reason":"先前的天气开场与随后段落的真实叙事节奏冲突，需要局部调整。"
        },ensure_ascii=False)
        model_responses=[
            PLAN,
            json.dumps(turns(),ensure_ascii=False),
            response(original_first,ACTION1,EFFECT1),
            moment("MOVE_ON",original_first),
            response(original_next,ACTION2,EFFECT2,EFFECT1),
            moment("LOOK_BACK_NOW",original_first,
                   target="previous",quote=target),
            previous_patch,
            response(regenerated_next,ACTION2,EFFECT2,EFFECT1),
            moment("MOVE_ON",regenerated_next),
        ]
        with TemporaryDirectory() as root:
            base=Path(root)
            dbpath=base/"fixture.sqlite3"
            snap=make_db(dbpath)
            db=WriterForgeDB(dbpath)
            try:
                rt=RuntimeEngine()
                rt.enter_write(snap)
                assist=InvisibleWritingAssist(
                    db,rt,"rewind-demo","source-rewind",
                    "根据人物真实行动写出后果，不要自动将候选当成正典。",
                    model="fixture-model",
                    api_base="http://127.0.0.1:1234/v1")
                with patch("writerforge.writing_assist.local_chat_completion",
                           side_effect=model_responses) as provider, patch(
                           "writerforge.writing_assist.external_temporal_step",
                           wraps=real_temporal_step) as temporal:
                    output=AutonomousWriting(assist).run(
                        outline="少年看见石桥异动，停下原定渡河计划；同伴调查旧账册，必须由实际事件决定行动。",
                        chapter_goals=[
                            "少年与女子在雨夜桥边调查，发现旧账册并作出新的渡河决定"],
                        draft_mode="continuity_guard",
                        bootstrap_unified_core=True,
                        self_edit_rounds=1,self_edit_timing="ai_decides",
                        output_dir=base/"drafts",
                    )
                self.assertEqual(provider.call_count,len(model_responses))
                # V114 must re-reduce the revised SOURCE from its genuine
                # pre-turn state, NOT continue from a discarded first event.
                self.assertEqual([z.kwargs["prose"] for z in
                                  temporal.call_args_list],
                                 [original_first,revised_first,regenerated_next])
                self.assertIsNone(temporal.call_args_list[1].kwargs["prior"])
                revised_state=real_temporal_step(
                    revised_first,cast=("少年","女子"),prior=None)
                self.assertEqual(
                    temporal.call_args_list[2].kwargs["prior"],revised_state)
                self.assertEqual(output["wf_self_edit_previous_turn_rewinds"],1)
                self.assertEqual(output["wf_self_edit_model_calls"],5)
                # Existing unified graph remains the sole memory owner.
                self.assertEqual(len(output["chapters"][0][
                    "unified_narrative_core_sha256"]),64)
                self.assertEqual(output["chapters"][0][
                    "unified_narrative_core_chapter"],1)
                candidate=Path(output["chapters"][0]["candidate"]).read_text("utf8")
                self.assertIn(replacement,candidate)
                self.assertIn("山风渐停",candidate)
                self.assertNotIn(target,candidate)
                evidence=json.loads(Path(output["chapters"][0]["turn_evidence"]).read_text("utf8"))
                rewinds=evidence["wf_ai_previous_turn_rewinds"]
                self.assertEqual(len(rewinds),1)
                self.assertTrue(rewinds[0]["downstream_must_be_regenerated"])
                self.assertEqual(rewinds[0]["source_sha256"],digest(original_first))
                self.assertTrue(rewinds[0]["state_rewound_before_target"])
                private=Path(output["job_dir"])
                self.assertEqual(
                    json.loads((private/"chapter-001-turn-02-invalidated-downstream-01.json").read_text("utf8"))["prose"],
                    original_next)
                self.assertTrue((private/"chapter-001-turn-01-lookback-01"/"round-01-discarded-draft.md").exists())
                self.assertEqual(output["wf_self_edit_canon_writes"],0)
            finally:
                db.close()


if __name__=="__main__":
    import unittest
    unittest.main()
