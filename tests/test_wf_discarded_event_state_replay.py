"""Failure-first checks: a discarded event is not a surviving story fact.

All writer replies below are deterministic synthetic fixtures, not evidence
of a real author's literary preference. Uses existing pinned MIT reducer,
V117 signed receipts, one unified graph, and no paid model / external R2.
"""
import json
import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from writerforge import WriterForgeDB, RuntimeEngine
from writerforge.writing_assist import AutonomousWriting, InvisibleWritingAssist
from writerforge.v114_external_story_state import (
    external_temporal_step, temporal_prompt,
)
from writerforge.v116_state_delta import preflight_next_prose
from writerforge.v117_continuity_trace import (
    make_resume, read_resume, preflight_continuation,
)
from writerforge.narrative_core import (
    advance_graph, record_chapter_memory, knows, propose_source_interactions,
    audit_candidate, read_core_from_resume,
)
from test_v116_state_delta import SOURCE, CAST, cells
from test_v26_invisible_writer import PLAN, make_db
from test_unified_narrative_core import (
    P, S, intro, update, annotation,
)
from test_wf_ai_writer_previous_turn_rewind import digest, moment

FRUIT_KEY=("item","火髓果","holder","author_plan")
ARM_KEY=("character","沈砚","右臂可用性","author_plan")
BURN_KEY=("character","沈砚","右臂伤情","author_plan")
HANDOFF="沈砚把火髓果从左手心递给唐蜃。"


class SourceDeletionDoesNotRecreateFacts(unittest.TestCase):
    def test_v114_item_handoff_removed_from_new_history_and_signed_v117(self):
        # The prior source already established an exact palm holder.
        # Exercise the licensed reducer's time-ordered handoff in a
        # subsequent event, instead of inventing an impossible atomic batch.
        initial=external_temporal_step(SOURCE,cast=CAST)
        old=external_temporal_step(
            HANDOFF+"唐蜃握着火髓果。",cast=CAST,prior=initial)
        old_cells=cells(old["reducer_result"]["candidate_state"])
        self.assertEqual(old_cells[FRUIT_KEY],"唐蜃手中",old_cells)
        # Simulate the writing model deleting the precise source sentence.
        revised=SOURCE
        new=external_temporal_step(revised,cast=CAST,prior=None)
        new_cells=cells(new["reducer_result"]["candidate_state"])
        self.assertEqual(new_cells[FRUIT_KEY],"沈砚左手心",new_cells)
        self.assertNotIn("唐蜃手中",str(new["reducer_result"]["candidate_state"]))
        self.assertNotEqual(old["receipt_sha256"],new["receipt_sha256"])
        original_next="唐蜃握着火髓果，沿墙向后退去。"
        new_next="沈砚握住左手心的火髓果，靠在墙边仔细听雨。"
        self.assertFalse(preflight_next_prose(new_next,
            previous_candidate_state=new["reducer_result"]["candidate_state"])[
                "blocked"])
        self.assertTrue(preflight_next_prose(original_next,
            previous_candidate_state=new["reducer_result"]["candidate_state"],
            cast=CAST)["blocked"])
        signed=make_resume(
            project_id="rewind-items",scene_id="sealed-chapter",
            chapter_index=1,checkpoint=new)
        restored=read_resume(signed,project_id="rewind-items",
                             scene_id="sealed-chapter")
        self.assertEqual(restored["receipt_sha256"],new["receipt_sha256"])
        self.assertEqual(cells(restored["reducer_result"]["candidate_state"])[
            FRUIT_KEY],"沈砚左手心")
        self.assertNotIn("唐蜃手中",temporal_prompt(restored))
        self.assertFalse(preflight_continuation(
            new_next,restored,project_id="rewind-items",chapter_index=2,
            cast=CAST)["blocked"])
        self.assertEqual(signed["canon_writes"],0)
        self.assertFalse(signed["author_accepted"])

    def test_v114_injury_deleted_not_preserved_through_old_reduce(self):
        prefix=(
            "沈砚沿断墙查找逃生小路，追兵尚未看见他。"
            "唐蜃站在旧钟下，没有选择替他引路。"
        )
        injury="沈砚右臂垂着，手指不听使唤，他只好停在雨水里。"
        end="沈砚看见远处灯火再次亮起，却仍不知道来者是谁。"
        before=external_temporal_step(prefix+injury+end,cast=CAST)
        self.assertEqual(cells(before["reducer_result"]["candidate_state"])[
            ARM_KEY],"受限")
        after=external_temporal_step(prefix+end,cast=CAST,prior=None)
        self.assertNotIn(ARM_KEY,
                         cells(after["reducer_result"]["candidate_state"]))
        future="沈砚右臂挥剑砍断缠在门外的绳索，唐蜃远远看着。"
        self.assertTrue(preflight_next_prose(
            future,previous_candidate_state=before["reducer_result"][
                "candidate_state"])["blocked"])
        self.assertFalse(preflight_next_prose(
            future,previous_candidate_state=after["reducer_result"][
                "candidate_state"])["blocked"])
        self.assertNotIn("右臂受限",temporal_prompt(after))
        self.assertNotEqual(before["source_sha256"],after["source_sha256"])

    def test_v117_old_unverified_tassel_debt_removed_from_replayed_source(self):
        seed="沈渡腰间挂着旧剑穗。"
        leak=("叶青梧跌下栈道，沈渡猛地抽回长索。"
              "索头回落，钩尖上挂着湿透的旧剑穗。")
        old=external_temporal_step(seed+leak,cast=("叶青梧","沈渡"))
        self.assertTrue(any(x["kind"]=="UNPROVEN_ITEM_TRANSFER" for x in
                        old["v117_open_continuity_debts"]))
        revised=external_temporal_step(seed+"叶青梧扶住岩石，没有改变剑穗的位置。",
                                       cast=("叶青梧","沈渡"),prior=None)
        self.assertFalse(any(x["kind"]=="UNPROVEN_ITEM_TRANSFER" for x in
                         revised["v117_open_continuity_debts"]))
        self.assertNotIn("UNPROVEN_ITEM_TRANSFER",temporal_prompt(revised))
        signed=make_resume(project_id="debt-rewind",scene_id="old-bridge",
                           chapter_index=1,checkpoint=revised)
        self.assertEqual(read_resume(signed,project_id="debt-rewind",
            scene_id="old-bridge")["receipt_sha256"],revised["receipt_sha256"])

    def test_deleted_narrated_secret_does_not_become_graph_knowledge_or_hot_memory(self):
        graph=intro()
        missing="叶青梧尚不知道密令藏在井底。"
        graph=update(graph,missing,[annotation(
            missing,missing,"UNKNOWN",id="unknown",
            actor="叶青梧",fact_id="secret-letter")])
        witness="沈砚亲眼看见密令藏在井底。"
        graph=update(graph,witness,[annotation(
            witness,witness,"WITNESS",id="witness",
            actor="沈砚",fact_id="secret-letter")])
        self.assertEqual(knows(graph,character="叶青梧",
                               fact_id="secret-letter"),
                         "AUTHOR_ASSERTED_UNKNOWN")
        old_scene=(
            "沈砚告诉叶青梧密令藏在井底。"
            "叶青梧默默记下这句话，却没问谁把信藏在那里。"
        )
        removed="沈砚告诉叶青梧密令藏在井底。"
        revised=(
            "沈砚走到叶青梧面前，却没有开口说出密令的下落。"
            "叶青梧见他神情不安，只问是不是有人追来了。"
        )
        old_proposed=propose_source_interactions(
            graph,project_id=P,scene_id=S,prose=old_scene,
            cast=("沈砚","叶青梧"))
        self.assertEqual(len(old_proposed["source_disclosure_proposals"]),1)
        new_proposed=propose_source_interactions(
            graph,project_id=P,scene_id=S,prose=revised,
            cast=("沈砚","叶青梧"))
        self.assertEqual(new_proposed["source_disclosure_proposals"],[])
        # Neither candidate may change FACT/UNKNOWN without author review.
        self.assertFalse(audit_candidate(
            graph,project_id=P,scene_id=S,prose=revised)["blocked"])
        next_graph=advance_graph(
            graph,project_id=P,scene_id=S,chapter_index=4,
            prose=revised,events=())
        with tempfile.TemporaryDirectory() as tmp:
            saved=Path(tmp)/"candidate.md"
            saved.write_text(revised,encoding="utf8")
            buffered=record_chapter_memory(
                next_graph,project_id=P,scene_id=S,chapter_index=4,
                source_path=str(saved),prose=revised)
        self.assertEqual(knows(buffered,character="叶青梧",
                               fact_id="secret-letter"),
                         "AUTHOR_ASSERTED_UNKNOWN")
        self.assertNotIn(removed,str(buffered["memory"]["hot"]))
        self.assertEqual(buffered["memory"]["hot"][-1]["source_sha256"],
                         digest(revised))
        # Signed resume must still point only to the retained graph.
        checkpoint=external_temporal_step(
            "沈砚在空院里等待叶青梧，没有取走任何物件。")
        signed=make_resume(project_id=P,scene_id=S,chapter_index=4,
                           checkpoint=checkpoint,
                           unified_narrative_core=buffered)
        cold=read_core_from_resume(signed,project_id=P,scene_id=S)
        self.assertEqual(knows(cold,character="叶青梧",
                               fact_id="secret-letter"),
                         "AUTHOR_ASSERTED_UNKNOWN")
        self.assertEqual(cold["receipt_sha256"],buffered["receipt_sha256"])


class ActualGPassesOnlyRevisedPhysicalState(unittest.TestCase):
    def test_no_discarded_handoff_in_g_candidate_v114_v117_and_hot_memory(self):
        first=(
            "沈砚看见火髓果已经发热。"
            "沈砚把火髓果往齿间一咬，苦味涌上舌尖。"
            "沈砚把火髓果从齿间吐到左手心，攥紧。"
            +HANDOFF+
            "雨顺着门柱落下，两人都不肯先说出自己真正担心的事。"
            "沈砚望着石阶尽头的灯，知道眼前的选择还没有确定。"
        )
        self.assertGreater(len(first),80)
        before=first.replace(HANDOFF,"")
        self.assertGreater(len(before),80)
        next_old=(
            "唐蜃握着火髓果绕着雨棚走了一圈，想到白天听到的哭声。"
            "他以为沈砚会说出密令的事，但其实双方都没有确凿线索。"
            "两人站在旧屋门外听见脚步声，仍不知道是谁故意惊动他们。"
            "唐蜃记得那天自己说过什么，但他不愿立刻承认那些话造成了误解。"
        )
        next_new=(
            "沈砚望着左手心的火髓果，一直没有松开手指。"
            "唐蜃在后门听见雨声渐渐变小，想到自己昨日说错的话。"
            "两人不急着决定去哪里，而是先把眼前的线索逐一核对。"
            "沈砚想到他们还没有找到可靠证据，所以只让两人先避开旧井旁的危险。"
        )
        self.assertGreaterEqual(len(next_old),80)
        self.assertGreaterEqual(len(next_new),80)
        turns={"turns":[
            {"id":"t01","kind":"quiet","actor":"沈砚",
             "goal":"沈砚在不确定时守住火髓果","causal_parent":None,
             "craft_focus":[]},
            {"id":"t02","kind":"quiet","actor":"唐蜃",
             "goal":"唐蜃在夜雨里重新考虑同伴的选择","causal_parent":None,
             "craft_focus":[]},
        ]}
        model_patch=json.dumps({
            "decision":"DELETE","scope":"sentence",
            "source_sha256":digest(first),
            "start":first.index(HANDOFF),
            "end":first.index(HANDOFF)+len(HANDOFF),
            "expected_original":HANDOFF,
            "replacement":"",
            "trace":{"action_quote":None,"effect_quote":None,
                     "parent_effect_quote":None},
            "reason":"这次交付武断地改变了人物的关系和后续空间，保留旧稿会破坏场面。"
        },ensure_ascii=False)
        script=[
            PLAN,json.dumps(turns,ensure_ascii=False),
            json.dumps({"prose":first,"trace":{"action_quote":None,
                "effect_quote":None,"parent_effect_quote":None}},
                ensure_ascii=False),
            moment("MOVE_ON",first),
            json.dumps({"prose":next_old,"trace":{"action_quote":None,
                "effect_quote":None,"parent_effect_quote":None}},
                ensure_ascii=False),
            moment("LOOK_BACK_NOW",first,target="previous",quote=HANDOFF),
            model_patch,
            json.dumps({"prose":next_new,"trace":{"action_quote":None,
                "effect_quote":None,"parent_effect_quote":None}},
                ensure_ascii=False),
            moment("MOVE_ON",next_new),
        ]
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            dbpath=root/"fixture.db"
            snapshot=make_db(dbpath)
            db=WriterForgeDB(dbpath)
            try:
                rt=RuntimeEngine()
                rt.enter_write(snapshot)
                assist=InvisibleWritingAssist(
                    db,rt,"rewind-physical-test","rewind-physical-scene",
                    "真正的原文事件推动两位人物继续前进。",
                    model="mock-only",
                    api_base="http://127.0.0.1:1234/v1")
                with patch("writerforge.writing_assist.local_chat_completion",
                           side_effect=script) as calls:
                    result=AutonomousWriting(assist).run(
                        outline="沈砚和唐蜃遇见不明危机；真实物件交接必须实际发生，任何过早交付都可以重写。",
                        chapter_goals=[
                            "沈砚与唐蜃先隐藏动机再逐步选择如何行动"],
                        output_dir=root/"drafts",draft_mode="continuity_guard",
                        bootstrap_unified_core=True,
                        self_edit_rounds=1,self_edit_timing="ai_decides")
                self.assertEqual(calls.call_count,len(script))
                self.assertEqual(result["wf_self_edit_previous_turn_rewinds"],1)
                chap=result["chapters"][0]
                final=Path(chap["candidate"]).read_text("utf8")
                self.assertIn(before,final)
                self.assertIn(next_new,final)
                self.assertNotIn(HANDOFF,final)
                self.assertNotIn(next_old,final)
                checkpoint=json.loads(Path(chap[
                    "v114_novel_studio_temporal_state"]).read_text("utf8"))
                state=cells(checkpoint["reducer_result"]["candidate_state"])
                self.assertEqual(state[FRUIT_KEY],"沈砚左手心",state)
                self.assertNotIn("唐蜃手中",str(state))
                self.assertNotIn(HANDOFF,str(checkpoint))
                resume=json.loads(Path(chap[
                    "v117_unreviewed_text_trace_resume"]).read_text("utf8"))
                restored=read_resume(
                    resume,project_id=assist.project_id,
                    scene_id=assist.scene_id)
                self.assertEqual(restored["receipt_sha256"],
                                 checkpoint["receipt_sha256"])
                self.assertEqual(cells(restored["reducer_result"][
                    "candidate_state"])[FRUIT_KEY],"沈砚左手心")
                self.assertNotIn(HANDOFF,str(resume[
                    "unified_narrative_core"]["memory"]))
                self.assertEqual(resume["unified_narrative_core"][
                    "memory"]["hot"][-1]["source_sha256"],digest(final))
                self.assertFalse(resume["author_accepted"])
                self.assertEqual(resume["canon_writes"],0)
                job=Path(result["job_dir"])
                self.assertEqual(json.loads((job/
                    "chapter-001-turn-02-invalidated-downstream-01.json"
                ).read_text("utf8"))["prose"],next_old)
                self.assertEqual(json.loads((job/
                    "chapter-001-turn-01-raw.json"
                ).read_text("utf8"))["prose"],first)
            finally:
                db.close()


if __name__=="__main__":
    unittest.main()
