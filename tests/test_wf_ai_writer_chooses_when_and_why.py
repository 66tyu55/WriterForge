"""Tests of AI-owned literary dissatisfaction, NOT tests of literary taste.

The WF host only offers a scene-boundary checkpoint; the writing model
chooses MOVE_ON / LOOK_BACK_NOW and gives a source-backed why. No Python
heuristics decide a sentence is boring or has to be deleted.
All sample prose is synthetic; no model/R2 requests and no Canon writes.
"""
import hashlib
import inspect
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from writerforge.verified_flow import GroundedDraftPacket,WritingExecutionError
from writerforge.writing_assist import (
    _ai_decides_when_to_revisit,AutonomousWriting,SELF_EDIT_MOMENT_TOKENS,
)
from writerforge.studio_server import StudioService,StudioError
from test_v26_invisible_writer import make_db

PROSE=(
    "秦真在灯塔的石阶前等到夜半，听见楼上传来三次敲击。"
    "她原本想立刻推开门，却发现门把手下有一枚新的铜钉。"
    "屋里的灯忽然熄了。秦真把手收回来，决定先去问值夜人。"
    "她没有贸然断定那个声音是鬼魂，也没有忘记渡口还在等她。"
)
QUOTE="秦真把手收回来，决定先去问值夜人。"


def digest(text):
    return hashlib.sha256(text.encode("utf8")).hexdigest()


def old_turn():
    return json.dumps({
        "prose":PROSE,
        "trace":{"action_quote":None,"effect_quote":None,
                 "parent_effect_quote":None}
    },ensure_ascii=False)


def proposed(action,*,quote=None,sha_override=None):
    extra={
        "decision":action,"source_sha256":sha_override or digest(PROSE),
        "evidence_quote":quote,"focus":"sentence" if quote else
            "scene" if action=="LOOK_BACK_NOW" else None,
        "why_now":("眼前仍然有未解的危险，继续写可以保持悬念和人物谨慎。"
                   if action=="MOVE_ON" else
                   "前面曾说行动会改变人物立场，但实际只让她重复等待。"),
        "what_goes_wrong_if_unchanged":(
            None if action=="MOVE_ON" else
            "再往下写会让人物的决定显得毫无代价，读者看不到可信的变化。"),
        "intended_reader_effect":(
            None if action=="MOVE_ON" else
            "让读者从实际选择看见她害怕又不愿放弃，而不是被解释说服。"),
    }
    return json.dumps(extra,ensure_ascii=False,separators=(",",":"))


class WriterChoosesWhen(unittest.TestCase):
    def setUp(self):
        self.tmp=TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        prompt="【已写事实】渡口无人。人物可以暂时不揭示敲击声的来源。"
        self.packet=GroundedDraftPacket(
            scene_id="writer-studio-g-scene",project_id="novel-test",
            snapshot_id=1,evidence=(),craft_ids=(),prompt=prompt,
            prompt_sha256=digest(prompt))
        self.beat={
            "id":"t01","kind":"quiet","actor":"秦真",
            "goal":"秦真在不知道敲击者身份时选择如何观察灯塔",
            "causal_parent":None,"craft_focus":[]}

    def signal(self,answer,*,source=None):
        calls=[]
        def same_model(packet,*,model,api_base,max_tokens):
            calls.append({"prompt":packet.prompt,"limit":max_tokens})
            return answer
        decision=_ai_decides_when_to_revisit(
            raw=source or old_turn(),beat=self.beat,accepted=(),
            turn_packet=self.packet,ask_model=same_model,
            directory=self.root/"moment")
        return decision,calls

    def test_model_can_deliberately_continue_and_delete_nothing(self):
        reply=proposed("MOVE_ON")
        result,calls=self.signal(reply)
        self.assertEqual(result["decision"],"MOVE_ON")
        self.assertEqual(result["model_calls"],1)
        self.assertEqual(len(calls),1)
        self.assertEqual(calls[0]["limit"],SELF_EDIT_MOMENT_TOKENS)
        self.assertIn(PROSE,calls[0]["prompt"])
        self.assertIn("你是本篇小说的作者",calls[0]["prompt"])
        self.assertTrue(result["receipt"]["only_ai_can_choose_revisit"])
        self.assertFalse(result["receipt"]["literary_quality_verified"])
        self.assertEqual((self.root/"moment"/"ai-when-and-why-original.json").read_text("utf8"),reply)

    def test_model_decides_why_now_and_quotes_exact_source(self):
        result,calls=self.signal(
            proposed("LOOK_BACK_NOW",quote=QUOTE))
        self.assertEqual(result["decision"],"LOOK_BACK_NOW")
        self.assertEqual(result["source_quote"],QUOTE)
        self.assertIn("代价",result["risk"])
        self.assertIn("读者",result["desired_effect"])
        self.assertEqual(result["receipt"]["focus"],"sentence")
        self.assertEqual(result["receipt"]["quoted_prose_sha256"],
                         digest(QUOTE))
        self.assertTrue(result["receipt"]["has_exact_model_quote"])
        self.assertEqual(len(calls),1)

    def test_missing_scene_payoff_does_not_force_a_fake_quote(self):
        result,_=self.signal(proposed("LOOK_BACK_NOW"))
        self.assertEqual(result["decision"],"LOOK_BACK_NOW")
        self.assertIsNone(result["source_quote"])
        self.assertEqual(result["focus"],"scene")

    def test_literal_json_object_type_wrapper_is_not_a_literary_decision(self):
        # The REAL provider sent exactly one redundant type='json_object'
        # on a correctly formed MOVE_ON self-assessment. Removing this
        # wrapper is parsing, never a new literary judgment by WF.
        item=json.loads(proposed("MOVE_ON"))
        item["type"]="json_object"
        result,calls=self.signal(json.dumps(item,ensure_ascii=False))
        self.assertEqual(len(calls),1)
        self.assertEqual(result["decision"],"MOVE_ON")
        self.assertTrue(result["receipt"][
            "format_wrapper_type_only_removed"])
        self.assertIn("悬念",result["reason"])
        invalid=dict(item)
        invalid["type"]="model_claims_literary_excellence"
        result,_=self.signal(json.dumps(invalid,ensure_ascii=False))
        self.assertEqual(result["decision"],"INVALID_SIGNAL")

    def test_wrong_hash_or_unseen_quote_fails_closed_without_deletion(self):
        for reply in (
            proposed("LOOK_BACK_NOW",quote=QUOTE,
                     sha_override="0"*64),
            proposed("LOOK_BACK_NOW",quote="这段根本没有的假原文"),
        ):
            with self.subTest(reply=reply):
                other=self.root/("new-moment-"+str(len(list(self.root.iterdir()))))
                result=_ai_decides_when_to_revisit(
                    raw=old_turn(),beat=self.beat,accepted=(),
                    turn_packet=self.packet,ask_model=lambda *args,**kw:reply,
                    directory=other)
                self.assertEqual(result["decision"],"INVALID_SIGNAL")
                self.assertFalse(result["receipt"]["literary_quality_verified"])
                self.assertEqual(result["receipt"]["model_calls"],1)

    def test_model_cannot_select_a_repeated_nonunique_anchor(self):
        repeated=PROSE+QUOTE
        source=json.dumps({
            "prose":repeated,
            "trace":{"action_quote":None,"effect_quote":None,
                     "parent_effect_quote":None}},ensure_ascii=False)
        reply=proposed("LOOK_BACK_NOW",quote=QUOTE,
                       sha_override=digest(repeated))
        decision,_=self.signal(reply,source=source)
        self.assertEqual(decision["decision"],"INVALID_SIGNAL")

    def test_opt_in_scope_no_secret_global_automatic_critic(self):
        from writerforge.writing_assist import _self_edit_one_turn
        method=inspect.getsource(AutonomousWriting.run)
        self.assertIn('self_edit_timing:str="always_offer"',method)
        self.assertIn('self_edit_timing=="ai_decides"',method)
        self.assertIn('_ai_decides_when_to_revisit(',method)
        self.assertIn('moment["decision"]=="LOOK_BACK_NOW"',method)
        self.assertIn('writer_attention=(',method)
        self.assertNotIn("WF_SELF_EDIT_CRITIC_SCORE_REQUIRED",method)
        self.assertIn("original",inspect.getsource(_self_edit_one_turn))
        with self.assertRaisesRegex(
            WritingExecutionError,
            "WF_AI_WRITER_TIMING_REQUIRES_ACTIVE_G_SELF_EDIT"):
            class Fake:
                project_id="test"
                scene_id="scene"
            AutonomousWriting(Fake()).run(
                outline="这是作者想要自主构思并完成原创小说的完整初始意图。",
                chapter_goals=["当前场景人物面对认知差距必须作选择"],
                output_dir=self.root/"no-model",
                draft_mode="continuity_guard",
                self_edit_rounds=0,self_edit_timing="ai_decides")
        self.assertFalse((self.root/"no-model").exists())

    def test_studio_can_choose_model_timing_only_in_G_self_edit(self):
        dbpath=self.root/"fixture.sqlite"
        make_db(dbpath)
        service=StudioService(
            db_path=dbpath,project="novel",scene="test-scene",
            goal="主体人物的愿望和现实障碍必须在原文中可见",
            model="local-mock",output_dir=self.root/"studio")
        with self.assertRaisesRegex(
            StudioError,"WF_AI_WRITER_TIMING_REQUIRES_ACTIVE_G_SELF_EDIT"):
            service.start_auto(
                "城墙外有一条没人巡看的旧路，人物在这里艰难抉择。",
                ["这一章人物需要面对实际利益冲突"],
                draft_mode="single",self_edit_rounds=0,
                self_edit_timing="ai_decides")
        self.assertEqual(service.job()["status"],"idle")

    def test_no_untrusted_creative_judgment_when_model_result_broken(self):
        decision,calls=self.signal("this is not strict JSON")
        self.assertEqual(decision["decision"],"INVALID_SIGNAL")
        self.assertEqual(len(calls),1)
        self.assertIn("failure_code",decision["receipt"])


if __name__=="__main__":
    unittest.main()
