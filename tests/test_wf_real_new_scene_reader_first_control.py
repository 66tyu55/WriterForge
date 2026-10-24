"""Offline preflight for once-only genuine new-scene G writer A/B experiment.

Synthetic provider fixtures ONLY. This verifies actual G pipeline, SAME
first-turn source in both arms, no host-created literary revision and call cap.
The real workflow must use the DeepSeek server and save its original wire.
"""
from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch
import json
import os

from experiments import wf_real_new_scene_reader_first_control_20261025 as run
from test_v26_invisible_writer import PLAN
from writerforge.v96_causal_turns import check_turn


BEATS={
    "turns":[
        {"id":"t01","kind":"quiet","actor":"江遥",
         "goal":"江遥在戏楼门内犹豫是否要把票据取出来给人看",
         "causal_parent":None,"craft_focus":[]},
        {"id":"t02","kind":"quiet","actor":"宋易",
         "goal":"宋易在夜鼓声中决定自己应守护的后门是否仍能安全",
         "causal_parent":None,"craft_focus":[]},
    ]
}
PROSE_1=(
    "江遥停在戏楼的南廊口，听见上面的鼓声隔了一阵又响起。"
    "她的左脚踝肿了，站久了就疼，于是握着门边的栏杆，没有朝裂开的木板迈步。"
    "藏在袖中的赎身票据被她手心的汗浸得发软，宋易还不知道这张纸的存在。"
    "她听见宋易敲了一下铜锣，又忍住了要喊他的念头，先从门后看向看台。"
    "夜风吹动戏台前的旧幕布，没有人露面，她仍不能确认是谁在击鼓。"
)
PROSE_2=(
    "宋易把灯放在戏楼后门边，隔着一条长廊听见脚步声，却不敢说是谁。"
    "他记得二楼第三块木板早已裂开，也知道江遥的脚受了伤，不适合独自跑过看台。"
    "他低下头，摸了摸手里的后门钥匙，决定暂时不把门从里面闩死。"
    "那声音似乎又近了一点，宋易并没有因此推定走来的是好人或坏人。"
    "他先轻轻敲了两下门框，给对方留下一个说话的机会，仍不愿走上锁住的北楼梯。"
)


def envelope(text):
    return {
        "prose":text,
        "trace":{"action_quote":None,"effect_quote":None,
                 "parent_effect_quote":None},
    }


def self_choice(prose,decision="MOVE_ON"):
    revisit=decision=="LOOK_BACK_NOW"
    return {
        "decision":decision,
        "target_turn":"current",
        "source_sha256":run.h(prose),
        "evidence_quote":(
            "江遥停在戏楼的南廊口" if revisit else None),
        "focus":"sentence" if revisit else None,
        "why_now":(
            "我认为这段仍有未落实的动作衔接，是否修改要以我自己的叙事目的为准。"
            if revisit else
            "这里的动作与犹豫已提供当下必要的信息，暂时保留未见之人的身份更自然。"),
        "what_goes_wrong_if_unchanged":(
            "如果继续沿着省略的动作发展，下一段可能误以为人物已经离开南廊。"
            if revisit else None),
        "intended_reader_effect":(
            "希望保留人物谨慎和夜里未知的氛围，而不是为了填字强行转折。"
            if revisit else None),
    }


def reader(prose):
    return {
        "observed":[{
            "quote":prose[:22],
            "actor":"江遥",
            "visible_action":"读者只能从实际原文知道她此时留在南廊附近。",
        }],
        "inferred_links":[],
        "reader_uncertainty":"没有必须猜测的过渡，不能要求作家为了展示修改而加句。",
    }


class FakeFlashWriter:
    messages=[]
    call_count=0
    def __init__(self,*,api_key,budget,timeout_seconds,on_response_wire):
        self.budget=budget
        self.wire=on_response_wire
    def ask_json(self,*,role,system,user,max_tokens):
        if not self.messages:
            raise AssertionError("offline actual writer fixture exhausted")
        item=self.messages.pop(0)
        self.call_count+=1
        self.budget.reserve(role,max_tokens,len(user.encode("utf8")))
        reply=json.dumps(item,ensure_ascii=False,separators=(",",":"))
        wire=json.dumps({
            "choices":[{"finish_reason":"stop",
                        "message":{"content":reply}}],
            "usage":{"prompt_tokens":200,"completion_tokens":110},
        },ensure_ascii=False).encode("utf8")
        self.wire(wire)
        return item


class OriginalGControlTreatmentTest(TestCase):
    def _run_fake(self,items):
        with TemporaryDirectory() as tmp:
            root=Path(tmp)
            path=root/"case"
            with patch.object(run,"OUT",path),patch.object(
                run,"DeepSeekFlashModel",FakeFlashWriter),patch.dict(
                os.environ,{"DEEPSEEK_API_KEY":"offline-unit-fake-secret-key"}):
                FakeFlashWriter.messages=list(items)
                FakeFlashWriter.call_count=0
                result=run.run()
                record=json.loads((path/"STATUS.json").read_text("utf8"))
                produced={p.name:p.read_text("utf8") for p in
                          path.glob("BLIND_*.md")}
                originals=(path/"TRUE_IDENTICAL_FIRST_TURN_SOURCE.md")
                original=originals.read_text("utf8") if originals.exists() else None
                written=sorted(p.name for p in
                    (path/"provider-wires").glob("*provider-wire.json"))
                return result,record,produced,original,written,list(
                    FakeFlashWriter.messages)

    def test_genuine_g_pipeline_can_save_same_prose_for_two_independent_review_arms(self):
        scripted=[
            json.loads(PLAN),BEATS,envelope(PROSE_1),envelope(PROSE_2),
            self_choice(PROSE_1),
            reader(PROSE_1),self_choice(PROSE_1),
        ]
        _,status,variants,original,wires,remain=self._run_fake(scripted)
        self.assertEqual(remain,[])
        self.assertEqual(status["status"],
                         "G_REAL_SOURCE_AND_TWO_AUTHENTIC_REVIEW_ARMS_SAVED",
                         status.get("error_code"))
        self.assertTrue(status["actual_wf_G_original_generated"])
        self.assertTrue(status["actual_wf_G_source_trace_passed"])
        self.assertEqual(status["actual_provider_calls"],7)
        self.assertEqual(len(wires),7)
        self.assertEqual(status["max_real_model_requests"],9)
        self.assertEqual(status["max_output_tokens_reserved"],10800)
        self.assertEqual(status["single_source_for_control_and_treatment"],
                         run.h(PROSE_1))
        self.assertEqual(original,PROSE_1)
        self.assertEqual(status["control"]["author_decision"],"MOVE_ON")
        self.assertEqual(status["reader_first_treatment"]["author_decision"],"MOVE_ON")
        self.assertFalse(status["control"]["approved_as_provisional_source"])
        self.assertFalse(status["reader_first_treatment"]["approved_as_provisional_source"])
        self.assertEqual(status["true_different_candidate_count"],1)
        self.assertEqual(set(variants.values()),{PROSE_1})
        self.assertEqual(status["accepted_prose_rows_at_end"],0)
        self.assertFalse(status["literary_quality_verified"])

    def test_failure_of_first_g_model_prose_preserves_original_wires_and_no_blind_artifacts(self):
        wrong=envelope(PROSE_1)
        wrong["trace"]["parent_effect_quote"]="一段并不存在的旧事"
        replies=[json.loads(PLAN),BEATS,wrong]
        _,status,variants,original,wires,remain=self._run_fake(replies)
        self.assertEqual(status["status"],
                         "REAL_G_OR_REVIEW_BLOCKED_SOURCE_PRESERVED")
        self.assertGreaterEqual(status["actual_provider_calls"],3)
        self.assertEqual(variants,{})
        self.assertIsNone(original)
        self.assertEqual(len(wires),3)
        self.assertTrue(status["no_model_retries_or_literary_scoring"])
        self.assertFalse(status["literary_quality_verified"])

    def test_one_real_model_adapter_enforces_stage_order_and_hard_cap(self):
        self.assertEqual(run.MAX_CALLS,9)
        self.assertEqual(run.FULL_MAX_RESERVED,10800)
        self.assertEqual(len(run.G_STAGES),4)
        self.assertEqual(run.G_STAGES,
                         ("CHAPTER_PLAN","SELF_BEAT_PLAN","PROSE_1","PROSE_2"))
        self.assertIn("reader_first",run.try_review_arm.__code__.co_varnames)
        self.assertNotIn("沈砚",run.SEED)
        self.assertNotIn("程九",run.SEED)
        self.assertNotIn("火髓果",run.SEED)
        self.assertNotIn("R2",run.GOAL)

if __name__=="__main__":
    import unittest
    unittest.main()
