"""Offline safety/logic verification of ONE-SHOT real-model comparison.

No provider keys or network. Synthetic fixtures ONLY and not literary proof.
"""
import json
import tempfile
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

from writerforge.verified_flow import GroundedDraftPacket
from experiments import wf_three_existing_writer_models_real_20261024 as pilot

SCENE=(
    "顾翎把带血的旧税簿按在船板上，发现那张纸已经被河水浸湿一角。"
    "程九抬头看了看摇晃的渡索，没有答应立刻开船，而是先用竹篙试探水深。"
    "雾里又有人喊了一声，顾翎刚想追问，左手的伤口却疼得握不住刀鞘。"
    "她没再拿账簿质问程九，只把那页纸挪到避雨的船篷下面。"
    "程九从她肩上的血迹看出她已经撑不住，却仍不知道这张纸是哪一夜留下的。"
    "渡索猛地绷响，两人都停住手里的动作，先看那盏快被雨打熄的河灯。"
)
QUOTE="她没再拿账簿质问程九，只把那页纸挪到避雨的船篷下面。"
REPLACE="她没有揭开旧税簿的来历，只用手背压住纸角，避免河水再毁掉剩下的墨字。"


def h(t):
    return pilot.h(t)


def wire(content):
    return json.dumps({
        "prose":content,
        "trace":{"action_quote":None,"effect_quote":None,
                 "parent_effect_quote":None},
    },ensure_ascii=False)


def decision(action):
    return json.dumps({
        "decision":action,"target_turn":"current",
        "source_sha256":h(SCENE),
        "evidence_quote":QUOTE if action=="LOOK_BACK_NOW" else None,
        "focus":"sentence" if action=="LOOK_BACK_NOW" else None,
        "why_now":"我认为这里需要保留人物先谨慎观察的片刻，不能凭空给出谜底。",
        "what_goes_wrong_if_unchanged":(
            "如果照旧往下写，纸张可能无缘无故被保存完整，给后续调查造成破绽。"
            if action=="LOOK_BACK_NOW" else None),
        "intended_reader_effect":(
            "希望读者意识到保存线索也要付出代价，同时不替人物解释全部原因。"
            if action=="LOOK_BACK_NOW" else None),
    },ensure_ascii=False)


def edit():
    return json.dumps({
        "decision":"REVISE","scope":"sentence",
        "source_sha256":h(SCENE),"start":SCENE.index(QUOTE),
        "end":SCENE.index(QUOTE)+len(QUOTE),
        "expected_original":QUOTE,"replacement":REPLACE,
        "trace":{"action_quote":None,"effect_quote":None,
                 "parent_effect_quote":None},
        "reason":"该句没有说明人物如何保护正在被水打湿的线索。",
    },ensure_ascii=False)


class FakeOriginalWriter:
    """Fake only in off-line unit tests, never in live runner."""
    scripted=[]
    def __init__(self,name,provider,secret,output):
        self.name=name
        self.provider=provider
        self.output=output
        self.calls=0
        self.reserved=0
        self.usage={"prompt_tokens":0,"completion_tokens":0}
        self.events=[]
    def ask(self,packet,*,model,api_base,max_tokens):
        if not self.scripted:
            raise RuntimeError("OFFLINE_MODEL_FIXTURE_EXHAUSTED")
        assert isinstance(packet,GroundedDraftPacket)
        assert max_tokens in (1450,600,1800)
        self.calls+=1
        self.reserved+=max_tokens
        self.events.append({"stage":str(max_tokens),
                            "wire_preserved":True})
        return self.scripted.pop(0)


class RealWriterCompareOfflineLimits(TestCase):
    def test_exact_three_existing_allowlisted_models_no_dynamic_selection(self):
        self.assertEqual(pilot.MODELS,(
            ("deepseek-flash","deepseek"),
            ("glm-5.3","discovery"),
            ("kimi-k2.6","discovery"),
        ))
        self.assertEqual(pilot.PER_MODEL_MAX_CALLS,3)
        self.assertEqual(pilot.PER_MODEL_MAX_REQUESTED_TOKENS,3850)
        self.assertEqual(set(pilot.SYSTEM_BY_TOKENS),{1450,600,1800})
        self.assertNotIn("沈砚从父亲遗信",pilot.SEED)
        self.assertNotIn("来源于用户",pilot.SEED)

    def _pilot(self,script):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(pilot,"OUTPUT",Path(tmp)/"private"),patch.object(
                pilot,"ActualModel",FakeOriginalWriter):
                pilot.OUTPUT.mkdir()
                FakeOriginalWriter.scripted=list(script)
                state=pilot.test_one_model(
                    "deepseek-flash","deepseek","fake-unit-only")
                self.assertEqual(FakeOriginalWriter.scripted,[])
                output=pilot.OUTPUT/"deepseek-flash"
                self.assertTrue((output/"ORIGINAL_MODEL_PROSE.md").is_file())
                self.assertEqual((output/"ORIGINAL_MODEL_PROSE.md").read_text("utf8"),
                                 SCENE)
                self.assertTrue((output/"STATUS.json").is_file())
                return state,(output/"FINAL_UNACCEPTED_CANDIDATE.md").read_text("utf8")

    def test_move_on_is_same_writer_choice_and_does_not_request_edit(self):
        state,final=self._pilot([wire(SCENE),decision("MOVE_ON")])
        self.assertEqual(state["status"],"REAL_MODEL_EVALUATED")
        self.assertEqual(state["v96_original_source_validation"],"PASS")
        self.assertEqual(state["ai_choice"],"MOVE_ON")
        self.assertEqual(state["calls_attempted"],2)
        self.assertFalse(state["changed_source"])
        self.assertEqual(final,SCENE)
        self.assertEqual(state["canon_writes"],0)

    def test_model_chosen_lookback_goes_through_existing_v119(self):
        state,final=self._pilot([
            wire(SCENE),decision("LOOK_BACK_NOW"),edit()])
        self.assertEqual(state["status"],"REAL_MODEL_EVALUATED")
        self.assertEqual(state["calls_attempted"],3)
        self.assertEqual(state["ai_choice"],"LOOK_BACK_NOW")
        self.assertEqual(state["ai_self_edit_statuses"],[
            "PROVISIONALLY_REVISED"])
        self.assertTrue(state["changed_source"])
        self.assertIn(REPLACE,final)
        self.assertNotIn(QUOTE,final)
        self.assertEqual(final,SCENE.replace(QUOTE,REPLACE))

    def test_invalid_author_decision_cannot_trigger_billable_edit(self):
        state,final=self._pilot([wire(SCENE),"{}"])
        self.assertEqual(state["status"],"REAL_MODEL_EVALUATED")
        self.assertEqual(state["ai_choice"],"INVALID_SIGNAL")
        self.assertEqual(state["calls_attempted"],2)
        self.assertEqual(final,SCENE)
        self.assertFalse(state["changed_source"])
