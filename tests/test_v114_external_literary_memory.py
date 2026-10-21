"""V114 pinned licensed Novel Studio temporal memory compatibility tests.

No internet, no model, no DB. Upstream pristine temporal reducer runs in
Node subprocess; Python WF character/scene sources remain unmodified.
"""
from __future__ import annotations
import json
from pathlib import Path
import shutil
import subprocess
from hashlib import sha256
from unittest import TestCase

ROOT=Path(__file__).parents[1]/"experiments"/"v114_fallback_novel_studio"
BRIDGE=ROOT/"bridge.mjs"

def candidate_event(event_id,prose,quote,item,prev,value):
    start=prose.index(quote)
    assert start>=0 and prose.count(quote)==1
    return {
        "id":event_id,
        "evidence":{"quote":quote,"start":start,"end":start+len(quote),
                    "narrative":"present"},
        "ops":[{
            "type":"set",
            "cell":{"domain":"item","entityId":item,"predicate":"holder",
                    "scope":"author_plan"},
            "expected":({"kind":"missing"} if prev is None
                        else {"kind":"value","value":prev}),
            "value":value,
        }]
    }

def invoke(source,events,prior=None):
    if not shutil.which("node"):
        raise RuntimeError("V114_EXPLICIT_FALLBACK_NEEDS_NODE_20_OR_NEWER")
    payload={
        "format":"wf.fallback.novel-studio.input.v114",
        "source_prose":source,"events":events,
        "prior_state":prior or {},
    }
    result=subprocess.run(
        ["node",str(BRIDGE)],input=json.dumps(payload,ensure_ascii=False),
        capture_output=True,text=True,timeout=10,check=False)
    if result.returncode!=0:
        raise RuntimeError("FALLBACK_STDERR:"+result.stderr[:200])
    return json.loads(result.stdout)

from writerforge.v114_external_story_state import (
    external_temporal_step,temporal_prompt,actual_item_events,
    V114ExternalMemoryError,
)

class LicensedTemporalReducerTests(TestCase):
    def test_vendored_source_is_exact_and_has_mit_notice(self):
        src=(ROOT/"schema.mjs").read_text("utf8")
        reducer=(ROOT/"reducer.mjs").read_text("utf8")
        license_text=(ROOT/"LICENSE").read_text("utf8")
        self.assertIn("MIT License",license_text)
        self.assertIn("Novel Studio contributors",license_text)
        self.assertIn("reduceBatchInPlace",reducer)
        self.assertIn("canonicalJson",src)
        self.assertIn("PRECONDITION_FAILED",reducer)
        self.assertNotIn("axios",src+reducer)

    def test_known_holder_first_event_accepted_only_as_candidate(self):
        prose="沈渡腰间挂着旧剑穗。"
        event=candidate_event("e01",prose,prose,"剑穗",None,"沈渡")
        result=invoke(prose,[event])
        self.assertEqual(result["format"],"wf.fallback.novel-studio.result.v114")
        self.assertEqual(result["verified_events"],1)
        self.assertEqual(result["risks"],[])
        self.assertFalse(result["literary_semantics_verified"])
        self.assertEqual(result["canon_writes"],0)
        self.assertIn("沈渡",str(result["candidate_state"]))
        self.assertEqual(result["network_calls"],0)

    def test_sword_tassel_teleport_stays_pending_not_marked_transferred(self):
        first="沈渡腰间挂着旧剑穗。"
        p1=candidate_event("e01",first,first,"剑穗",None,"沈渡")
        m1=invoke(first,[p1])
        late="钩尖上挂着一截湿透的旧剑穗。"
        p2=candidate_event("e02",late,late,"剑穗","沈渡","索钩")
        m2=invoke(late,[p2],m1["candidate_state"])
        self.assertEqual(m2["verified_events"],0)
        self.assertEqual(m2["risks"][0]["kind"],"UNPROVEN_ITEM_TRANSFER")
        self.assertEqual(m2["candidate_state"],m1["candidate_state"])
        self.assertEqual(m2["canon_writes"],0)

    def test_observable_handoff_updates_candidate_holder_state(self):
        first="沈渡腰间挂着旧剑穗。"
        m1=invoke(first,[candidate_event("e01",first,first,
                                         "剑穗",None,"沈渡")])
        second="沈渡扯下旧剑穗，把旧剑穗挂到索钩上。"
        proposal=candidate_event("e02",second,second,"剑穗","沈渡","索钩")
        m2=invoke(second,[proposal],m1["candidate_state"])
        self.assertEqual(m2["verified_events"],1)
        self.assertEqual(m2["risks"],[])
        self.assertIn("索钩",str(m2["candidate_state"]))
        self.assertNotEqual(m1["candidate_state_sha256"],
                            m2["candidate_state_sha256"])

    def test_wrong_actor_or_missing_evidence_does_not_launder_truth(self):
        first="沈渡腰间挂着旧剑穗。"
        m1=invoke(first,[candidate_event("e01",first,first,"剑穗",None,"沈渡")])
        second="沈渡扯下旧剑穗，挂到索钩上。"
        wrong=candidate_event("e02",second,second,"剑穗","叶青梧","索钩")
        invalid=invoke(second,[wrong],m1["candidate_state"])
        self.assertEqual(invalid["error_code"],"PRECONDITION_FAILED")
        self.assertEqual(invalid["candidate_state"],m1["candidate_state"])
        quote_event=candidate_event("e03",second,second,"剑穗","沈渡","索钩")
        quote_event["evidence"]["quote"]="不存在的原文"
        self.assertEqual(invoke(second,[quote_event],m1["candidate_state"])["risks"][0]["kind"],
                         "UNANCHORED_EVENT")

    def test_WF_python_adapter_invokes_real_Novel_Studio_reducer_not_native_fix(self):
        before=("沈渡偏头一避。就这一瞬，她看清他腰间还挂着旧剑穗，"
                "那是三年前亲手编的。")
        late=("沈渡追至崖边，锁魂索没入水雾。"
              "他收住脚，索头回落，钩尖上挂着湿透的旧剑穗。")
        a=external_temporal_step(before,cast=("叶青梧","沈渡"))
        self.assertIn("沈渡",str(a["reducer_result"]["candidate_state"]))
        b=external_temporal_step(late,cast=("叶青梧","沈渡"),prior=a)
        self.assertEqual(b["sequence"],2)
        self.assertEqual(b["previous_checkpoint_sha256"],a["receipt_sha256"])
        self.assertIn("UNPROVEN_ITEM_TRANSFER",
                      [r["kind"] for r in b["reducer_result"]["risks"]])
        self.assertEqual(b["reducer_result"]["candidate_state"],
                         a["reducer_result"]["candidate_state"])
        self.assertIn("沈渡",temporal_prompt(b))
        self.assertFalse(b["semantic_truth_verified"])
        self.assertEqual(b["canon_writes"],0)

    def test_real_handoff_is_accepted_by_reducer_even_if_native_false_alarm(self):
        before="沈渡腰间悬着旧剑穗。"
        after=("沈渡从腰间取下旧剑穗，把它挂到索钩上。"
               "索头回落，钩尖上挂着旧剑穗。")
        one=external_temporal_step(before,cast=("沈渡",))
        two=external_temporal_step(after,cast=("沈渡",),prior=one)
        self.assertFalse(any(r["kind"]=="UNPROVEN_ITEM_TRANSFER"
                             for r in two["reducer_result"].get("risks",[])))
        self.assertIn("索钩",str(two["reducer_result"]["candidate_state"]))
        self.assertNotEqual(one["reducer_result"]["candidate_state_sha256"],
                            two["reducer_result"]["candidate_state_sha256"])

if __name__=="__main__":
    import unittest
    unittest.main()
