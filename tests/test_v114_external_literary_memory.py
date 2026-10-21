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

if __name__=="__main__":
    import unittest
    unittest.main()
