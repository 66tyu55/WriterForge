"""No-network invariants for executing a G novelist's genuine LOOK_BACK_NOW.

Tests are synthetic and do not prove real provider literary competence.
A successful first-turn patch does NOT bless the old second G turn; only
a new downstream author continuation can yield another full signed resume.
"""
import inspect
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from experiments import wf_real_opera_author_selected_v119_once_20261025 as task
from writerforge.writing_assist import _self_edit_one_turn,SELF_EDIT_MODEL_MAX_TOKENS
from writerforge.verified_flow import GroundedDraftPacket

MODEL_EDITED_SENTENCE="她先退半步用脚尖轻点板沿，木板吃住片刻，她知道有风险仍决定探身。"
SOURCE=(
    "江遥扶着戏楼的廊柱，左脚疼得挪不动步子。"
    "她看着南廊第三块板，木边裂开一道细口。"
    "她刚要把重心全压上去，板缘猛地往上一翻。"
    "膝头磕在栏杆上，疼得她眼前一黑，她仍揪住帘边不松手。"
    "宋易握着后门钥匙，楼梯尽头又传来了一次鼓声。"
)
QUOTE="她刚要把重心全压上去，板缘猛地往上一翻。"


class NoAutomaticApproval(TestCase):
    def test_one_real_provider_call_only_and_raw_wire_is_kept(self):
        class MockDeepSeek:
            def __init__(self,*,api_key,budget,timeout_seconds,on_response_wire):
                self.wire=on_response_wire
                self.calls=0
            def ask_json(self,*,role,system,user,max_tokens):
                self.calls+=1
                self.wire(b'{"choices":[{"finish_reason":"stop"}]}')
                return {"decision":"KEEP","source_sha256":"test_only"}
        with TemporaryDirectory() as td,patch.object(
                task,"DeepSeekFlashModel",MockDeepSeek):
            original=task.OneOriginalWriterV119("fake-test-secret-only",Path(td))
            pkt=GroundedDraftPacket(
                project_id=task.PROJECT,scene_id=task.SCENE,
                snapshot_id=0,evidence=(),craft_ids=(),
                prompt="这个文本测试属于离线模拟",prompt_sha256=task.h(
                    "这个文本测试属于离线模拟"))
            data=original.ask(pkt,model=None,api_base=None,
                              max_tokens=SELF_EDIT_MODEL_MAX_TOKENS)
            self.assertIn('"decision":"KEEP"',data)
            self.assertEqual(len(original.events),1)
            self.assertTrue(original.events[0]["wire_saved_before_parsing"])
            self.assertTrue((Path(td)/"01-AUTHOR_V119_PROVIDER_WIRE.json").exists())
            with self.assertRaisesRegex(RuntimeError,"WF_REAL_V119_ONCE_ONLY"):
                original.ask(pkt,model=None,api_base=None,
                             max_tokens=SELF_EDIT_MODEL_MAX_TOKENS)
            self.assertTrue(task.CALL_LIMIT==1)

    def test_genuine_author_lookback_required_before_any_new_model_run(self):
        program=inspect.getsource(task.prior_real_writer_decision)
        self.assertIn("REAL_OLD_ATTEST_RUN",program)
        self.assertIn("source_decision[\"decision\"]!=\"LOOK_BACK_NOW\"",program)
        self.assertIn('manifest.get("V119_called") is not False',program)
        self.assertIn("WF_AUTHENTIC_AUTHOR_LOOK_BACK_WIRE_CHANGED",program)
        production=inspect.getsource(task.main)
        self.assertLess(production.index("prior_real_writer_decision()"),
                        production.index("OneOriginalWriterV119(secret,OUTPUT)"))
        self.assertIn('old_complete_chapter_second_turn_not_reused_as_new_branch',production)
        self.assertIn('"V117_full_new_chapter_signed":False',production)
        self.assertIn('preflight_continuation(',production)
        self.assertIn('"user_accepted_source_changed"]=False',production)
        self.assertIn('V96_revised_first_turn_passed',production)

    def test_bad_synthetic_source_edit_cannot_generate_a_new_canon_narrative(self):
        # Test source-locked mechanical trace: no model-created source event
        # is accepted merely because its replacement looks plausible.
        from writerforge.writing_assist import _decode_json
        source_doc=json.dumps({
            "prose":SOURCE,
            "trace":{"action_quote":None,"effect_quote":None,
                     "parent_effect_quote":None}},ensure_ascii=False)
        pkt=GroundedDraftPacket(
            project_id="unit-only",scene_id="unit-only",
            snapshot_id=0,evidence=(),craft_ids=(),
            prompt="只读离线脚本",prompt_sha256=task.h("只读离线脚本"))
        intent=json.dumps({
            "decision":"REVISE","scope":"sentence",
            "source_sha256":task.h(SOURCE),
            "start":len(SOURCE)+2,
            "end":len(SOURCE)+2+len(QUOTE),
            "expected_original":QUOTE,
            "replacement":MODEL_EDITED_SENTENCE,
            "trace":{"action_quote":None,"effect_quote":None,
                     "parent_effect_quote":"虚构的前一段后果绝不能成为本文事实"},
            "reason":"未写出人物谨慎试探破板的动作，需要由模型自己改好人物性格衔接。",
        },ensure_ascii=False)
        with TemporaryDirectory() as td:
            result,receipts=_self_edit_one_turn(
                raw=source_doc,
                beat={"id":"t01","kind":"quiet",
                      "actor":"江遥","goal":"考虑是否要跨过裂板",
                      "causal_parent":None,"craft_focus":[]},
                accepted=(),project_id="unit-only",scene_id="unit-only",
                turn_packet=pkt,
                ask_model=lambda *args,**kwargs:intent,
                round_limit=1,call_allowance=1,
                directory=Path(td)/"bad-trace")
            self.assertEqual(result,source_doc)
            self.assertEqual(receipts["rounds"][0]["status"],
                             "REJECTED_AND_ROLLED_BACK")
            self.assertIn("WF96_",receipts["rounds"][0]["reason_code"])
            self.assertFalse(
                (Path(td)/"bad-trace"/"round-01-selected-draft.md").exists())
            self.assertTrue(
                (Path(td)/"bad-trace"/"round-01-model-proposal.json").exists())
