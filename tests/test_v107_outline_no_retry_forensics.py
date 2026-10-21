"""V107 offline unmodified outline diagnostics and paid-call forensic gates."""
from __future__ import annotations
from copy import deepcopy
from pathlib import Path
import unittest

from writerforge.v107_outline_observation import observe_shared_two_turns
from writerforge.v96_causal_turns import parse_turn_outline
from wf_railway_v106_real_e_f_smoke_once import (
    EXAM,freeze,make_outline_request,PLANNER_SYS,ROLE,
)
import wf_railway_v107_v106_readonly_forensic as read_only


def valid():
    return {"turns":[
        {"id":"t01","kind":"action","actor":"林薇",
         "goal":"工程师先查清B舱气路和供电状态",
         "causal_parent":None,"craft_focus":["detail","action"]},
        {"id":"t02","kind":"decision","actor":"王崇年",
         "goal":"站长根据查验到的真实后果决定是否封门",
         "causal_parent":"t01","craft_focus":["dialogue"]},
    ]}

class V107NoTamperTests(unittest.TestCase):
    def test_correct_original_pass_and_no_literary_grade(self):
        item=valid()
        before=deepcopy(item)
        r=observe_shared_two_turns(item)
        self.assertTrue(r["exact_v96_valid"])
        self.assertEqual(r["violations"],[])
        self.assertEqual(item,before)
        self.assertFalse(r["semantic_story_quality_checked"])
        self.assertFalse(r["auto_retry_permitted"])
        self.assertFalse(r["model_calls_for_diagnostics"])
        self.assertEqual(parse_turn_outline(
             __import__("json").dumps(item,ensure_ascii=False))[1]["id"],
            "t02")

    def test_craft_field_scalar_stays_invalid_no_model_repair(self):
        item=valid();item["turns"][1]["craft_focus"]="dialogue"
        frozen=deepcopy(item)
        r=observe_shared_two_turns(item)
        self.assertFalse(r["exact_v96_valid"])
        self.assertTrue(any(x["failure_kind"]=="INVALID_CRAFT_FOCUS"
                            for x in r["violations"]))
        self.assertEqual(item,frozen)
        self.assertEqual(r["raw_decoded_model_json_sha256"],
                         observe_shared_two_turns(frozen)[
                             "raw_decoded_model_json_sha256"])
        self.assertNotIn("dialogue",str(r["violations"]))

    def test_malformed_roles_goals_and_parent_are_located(self):
        item=valid();item["turns"][0]["kind"]="fantasy"
        item["turns"][1]["goal"]="短"
        item["turns"][1]["causal_parent"]="t99"
        r=observe_shared_two_turns(item)
        issues={x["failure_kind"] for x in r["violations"]}
        self.assertTrue({"INVALID_EVENT_KIND","GOAL_LENGTH_OR_UNICODE",
                         "PARENT_MISSING_NOT_PRIOR_ACTION"}<=issues)
        self.assertFalse(r["exact_v96_valid"])

    def test_missing_wrong_shape_does_not_claim_success(self):
        for obj in [None,{},{"turns":[]}]:
            self.assertFalse(observe_shared_two_turns(obj)["exact_v96_valid"])
        item=valid();item["turns"][0].pop("goal")
        x=observe_shared_two_turns(item)
        self.assertFalse(x["exact_v96_valid"])
        self.assertIn("TURN_FIELDS_NOT_EXACT",
                      [p["failure_kind"] for p in x["violations"]])

    def test_original_V106_precommit_unchanged_and_model_not_rerun(self):
        self.assertEqual(EXAM,"WF-V106-E-VS-F-REAL-1-CASE-20261021")
        self.assertEqual(freeze()["max_actual_provider_calls"],9)
        self.assertTrue(freeze()["no_retry_even_if_incomplete"])
        self.assertIn("JSON",PLANNER_SYS)
        self.assertIn("两个叙事事件",make_outline_request())
        self.assertEqual(ROLE,"self_scene_writing")

    def test_instrumentation_always_logs_raw_answer_sha_before_parsing(self):
        source=(Path(__file__).parents[1]/
                "wf_railway_v106_real_e_f_smoke_once.py").read_text("utf8")
        log=source.index('"WF107_RAW_MODEL_REPLY_R2_SEALED_BEFORE_VALIDATION"')
        parse=source.index("outline=parse_turn_outline(")
        self.assertLess(log,parse)
        self.assertIn('"WF107_SINGLE_REQUEST_INTENT_R2_SEALED"',source)
        self.assertIn('"WF107_STRICT_SHARED_OUTLINE_REJECTED_WITH_EVIDENCE"',source)
        self.assertIn("raw_reply_cas_sha256",source)
        self.assertEqual(source.count("wf_model.ask_json("),1)
        self.assertNotIn("retry_on_parse",source)
        self.assertNotIn("accept_draft(",source)

    def test_readonly_forensic_contains_zero_model_provider_call(self):
        source=Path(read_only.__file__).read_text("utf8")
        self.assertIn("WF107_V106_ORIGINAL_PRECOMMIT_AND_REQUEST_COLD_VERIFIED",source)
        self.assertIn("original_provider_response_cas_sha256",source)
        self.assertIn("SHA_NOT_LOGGED_BEFORE_V96_EXCEPTION",source)
        self.assertNotIn("ask_json(",source)
        self.assertNotIn("_put_content(",source)
        self.assertIn("read_only=True",source)
        self.assertIn('os.environ.pop(k,None)',source)


if __name__=="__main__":unittest.main()
