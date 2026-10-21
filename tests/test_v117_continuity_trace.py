"""V117 real pinned MIT general longform context and cross-run isolation.

No provider, no database, no network, no R2, no original private prose.
"""
from __future__ import annotations
import hashlib
import json
import unittest
from pathlib import Path

from writerforge.v114_external_story_state import external_temporal_step
from writerforge.v117_continuity_trace import (
    audit_continuity,compact_context,preflight_continuation,
    make_resume,read_resume,ContinuityTraceError,
)

ROOT=Path(__file__).resolve().parents[1]
OSS=ROOT/"experiments/v117_novel_studio"
# Exact upstream GIT blob hashes, not merely "same-looking version".
PINNED={
    "prop-chain.mjs":"551db5a197890c0dc6e5cee529294e3e65e59551",
    "state-query.mjs":"e6c01669d7cf24630a5d34b516e605f9e01b73fc",
    "knowledge.mjs":"25b716a3f7c458f1a82a8b0315708a91e7aed784",
    "timeline.mjs":"57e87e6aa9fadd9ad50cc1d10b047bac431fa0e9",
    "LICENSE":"a106e3ecc789d6ac79f7c7797a4d234e09a71afc",
}
SOURCE=("沈砚看见火髓果发热。"
        "沈砚没应声，把果子往齿间一咬。"
        "他右手撑住炉沿要翻身，半空里忽然一麻——锁脉诀到了。"
        "灵力从肘弯往下被截断，手指头瞬间不听使唤。"
        "炉壁里的丹火忽然舔上他右前臂，烧出焦臭。"
        "沈砚把果子从齿间吐到左手心。")
def checked():
    return external_temporal_step(SOURCE,cast=("沈砚","唐蜃"))

def reference():
    return {
        "facts":[
            {"id":"old","status":"confirmed","chapter_index":0,
             "scope":"canon","domain":"world_fact","entity_id":"矿道",
             "predicate":"出口","value":"东侧石梯"},
            {"id":"future","status":"confirmed","chapter_index":9,
             "scope":"canon","entity_id":"唐蜃","predicate":"结局","value":"失去修为"},
            {"id":"actor_a","status":"confirmed","chapter_index":0,
             "scope":"character","holder_id":"沈砚","entity_id":"密令",
             "predicate":"内容","value":"甲"},
            {"id":"actor_b","status":"confirmed","chapter_index":0,
             "scope":"character","holder_id":"唐蜃","entity_id":"密令",
             "predicate":"内容","value":"乙"},
            {"id":"reader","status":"confirmed","chapter_index":0,
             "scope":"reader","disclosed":False,"entity_id":"皇帝",
             "predicate":"真实身份","value":"沈砚的父亲"},
            {"id":"future_plan","status":"candidate","chapter_index":0,
             "scope":"author_plan","entity_id":"血祭","predicate":"结果",
             "value":"秘密生效"},
        ],
        "timeline":[
            {"id":1,"chapter_index":0,"seq":1,"label":"沈砚进入矿道"},
            {"id":2,"chapter_index":9,"seq":0,"label":"唐蜃失去修为"},
            {"id":3,"chapter_index":0,"seq":2,"label":"火髓果开始发热",
             "after_event_id":1},
        ],
        "knowledge":[
            {"character_id":"沈砚","character_name":"沈砚",
             "fact_key":"密令的真正作者",
             "scope":"CHARACTER_KNOWLEDGE","state":"unknown",
             "learned_chapter_index":5},
            {"character_id":"唐蜃","character_name":"唐蜃",
             "fact_key":"丹火暗号",
             "scope":"CHARACTER_KNOWLEDGE","state":"known",
             "learned_chapter_index":0},
        ],
        "prop_chains":[{
            "entity":"火髓果",
            "expected_state":"沈砚左手心",
            "chain":[{
                "state":"沈砚齿间",
                "evidence_quote":"沈砚没应声，把果子往齿间一咬。",
            },{
                "state":"沈砚左手心",
                "evidence_quote":"沈砚把果子从齿间吐到左手心。",
            }],
        }],
        "pov_character_id":"沈砚",
    }

class MITNovelStudioIntegrated(unittest.TestCase):
    def test_exact_upstream_sources_mit_licensed(self):
        for name,blob in PINNED.items():
            data=(OSS/name).read_bytes()
            header=(b"blob "+str(len(data)).encode()+b"\0")
            self.assertEqual(hashlib.sha1(header+data).hexdigest(),blob)
        self.assertIn("MIT License",(OSS/"LICENSE").read_text("utf8"))

    def test_original_source_anchored_item_chain_automatically_available(self):
        frame=audit_continuity(checked(),project_id="novel-z",
                               chapter_index=1,boundary="before")
        prop=[p for p in frame["prop_verdicts"]
              if p["entity"]=="火髓果"]
        self.assertEqual(len(prop),1)
        self.assertTrue(prop[0]["ok"])
        self.assertEqual(prop[0]["latest_state"],"沈砚左手心")
        self.assertFalse(frame["coverage"]["knowledge_coverage_proven"])
        self.assertEqual(frame["no_model_call"],True)

    def test_state_as_of_chapter_avoids_future_and_other_pov_leaks(self):
        prior=checked()
        frame=audit_continuity(
           prior,project_id="novel-z",chapter_index=1,
           reference=reference(),boundary="before")
        self.assertEqual(frame["format"],"wf.continuity.v117.pinned-oss-temporal-view")
        visible={x["id"] for x in frame["confirmed_visible"]}
        self.assertIn("old",visible)
        self.assertIn("actor_a",visible)
        self.assertNotIn("future",visible)
        self.assertNotIn("actor_b",visible)
        self.assertNotIn("reader",visible)
        self.assertNotIn("future_plan",visible)
        self.assertIn("密令的真正作者",
                      {x["fact_key"] for x in frame["knowledge"]["unknown"]})
        self.assertNotIn("丹火暗号",
                      {x["fact_key"] for x in frame["knowledge"]["known"]})
        self.assertGreaterEqual(frame["chronology"]["future_hidden_count"],1)
        self.assertEqual(frame["prop_verdicts"][0]["code"],"PROP_STATE_OK")
        text=compact_context(frame)
        self.assertIn("火髓果",text)
        self.assertIn("密令的真正作者",text)
        self.assertNotIn("失去修为",text)
        self.assertNotIn("沈砚的父亲",text)
        self.assertEqual(frame["coverage"]["knowledge_rows_received"],2)
        self.assertTrue(frame["no_model_call"])

    def test_knowledge_match_is_review_not_false_hard_failure(self):
        prose="沈砚知道密令的真正作者，忙转身攀上石梯。"
        report=preflight_continuation(
            prose,checked(),project_id="novel-z",chapter_index=1,
            reference=reference())
        self.assertTrue(report["needs_review"])
        self.assertIn("KNOWLEDGE_VIOLATION",
                      {x["code"] for x in report["knowledge_needs_review"]})
        self.assertFalse(report["blocked"])
        self.assertEqual(report["canon_writes"],0)
        self.assertEqual(report["no_model_call"],True)

    def test_unresolved_sword_tassel_debt_survives_two_new_chapters(self):
        first_text=("沈渡腰间挂着旧剑穗。"
                    "叶青梧疾行数丈，他挥起锁魂索。"
                    "索头回落，钩尖上挂着湿透的旧剑穗。")
        first=external_temporal_step(first_text,cast=("沈渡","叶青梧"))
        self.assertIn("UNPROVEN_ITEM_TRANSFER",
            [r["kind"] for r in first["reducer_result"]["risks"]])
        second=external_temporal_step(
            "叶青梧避过风雨，沈渡仍在桥上疾追。",
            cast=("沈渡","叶青梧"),prior=first)
        third=external_temporal_step(
            "两人先后望见飞瀑，栈道已被山洪吞没。",
            cast=("沈渡","叶青梧"),prior=second)
        self.assertEqual(third["reducer_result"]["risks"],[])
        open_debts=third["v117_open_continuity_debts"]
        self.assertTrue(any(r["kind"]=="UNPROVEN_ITEM_TRANSFER"
                            for r in open_debts))
        frame=audit_continuity(third,project_id="tassel-story",
                               chapter_index=2)
        text=compact_context(frame)
        self.assertIn("UNPROVEN_ITEM_TRANSFER",text)
        self.assertGreater(len(open_debts),0)
        self.assertEqual(frame["no_model_call"],True)

    def test_wrong_arm_return_is_blocked_with_pinned_source_state(self):
        unsafe="沈砚右臂挥剑刺出，果子依然还在齿间。"
        report=preflight_continuation(
            unsafe,checked(),project_id="novel-z",chapter_index=1,
            reference=reference())
        self.assertTrue(report["blocked"])
        self.assertIn("WF116_ARM_USED_WITHOUT_RECOVERY",report["state_findings"])
        self.assertEqual(report["no_model_call"],True)

    def test_cold_restart_requires_exact_project_and_digest(self):
        prior=checked()
        saved=make_resume(project_id="novel-z",scene_id="chapter-stream",
                          chapter_index=5,checkpoint=prior)
        restored=json.loads(json.dumps(saved,ensure_ascii=False))
        reloaded=read_resume(restored,project_id="novel-z",
                           scene_id="chapter-stream")
        self.assertEqual(reloaded,prior)
        later=audit_continuity(reloaded,project_id="novel-z",chapter_index=6)
        self.assertIn("火髓果",compact_context(later))
        self.assertFalse(later["coverage"]["knowledge_coverage_proven"])
        self.assertEqual(saved["author_accepted"],False)
        with self.assertRaises(ContinuityTraceError):
            read_resume(saved,project_id="different-book",
                        scene_id="chapter-stream")
        bad=json.loads(json.dumps(saved))
        bad["chapter_index"]=100
        with self.assertRaises(ContinuityTraceError):
            read_resume(bad,project_id="novel-z",
                        scene_id="chapter-stream")

    def test_unregistered_knowledge_not_misreported_as_consistency_pass(self):
        frame=audit_continuity(checked(),project_id="novel-z",chapter_index=2)
        self.assertFalse(frame["coverage"]["knowledge_coverage_proven"])
        self.assertFalse(frame["coverage"]["time_coverage_proven"])
        self.assertIn("尚未全面登记",compact_context(frame))
        self.assertFalse(frame["literary_truth_verified"])

    def test_prop_chain_older_quote_cannot_claim_new_manuscript_proof(self):
        r=reference()
        r["prop_chains"][0]["recheck_prose"]=True
        current="火髓果落进沈砚掌中，再无别的动作。"
        frame=audit_continuity(checked(),project_id="novel-z",
                  chapter_index=1,reference=r,next_prose=current)
        self.assertEqual(frame["prop_verdicts"][0]["code"],"PROP_EVIDENCE_LOST")
        self.assertFalse(frame["prop_verdicts"][0]["ok"])

if __name__=="__main__":
    unittest.main()
