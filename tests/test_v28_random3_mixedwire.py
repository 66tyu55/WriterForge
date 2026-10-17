"""No-network test: ch17 has a distinct low-effort gateway wire profile."""
import unittest,json
from hashlib import sha256
from writerforge.r2_storage import _canonical
from scripts.audit_wudong_random3_v7_r2 import _root as original_root
from scripts.audit_random3_mixedwire_v7_v8_r2 import collect,_root as recovered_root
from test_v28_random3_aggregation import FakePrivateR2

class MixedWireTests(unittest.TestCase):
    def make_store(self):
        r2=FakePrivateR2([70,95,90])
        oldroot=original_root(2,17)
        oldptr=r2.store.pop(oldroot+"/completed.json")
        old_sha=json.loads(oldptr)["sha256"]
        raw=r2.store.pop(oldroot+f"/snapshots/{old_sha}.json")
        d=json.loads(raw)
        d["role_output_token_profile"]=[5500,8500,7000]
        d["budget_and_gateway_repair_protocol"]={
            "glm_writer_reasoning_effort":"low",
            "probe_action_id":38999272334,
            "role_output_budgets":[5500,8500,7000],
            "not_strictly_same_wire_settings_as_v7":True,
            "one_last_recovery_of_preselected_chapter17":True,
        }
        body=_canonical(d)
        h=sha256(body).hexdigest()
        root=recovered_root(2,17)
        r2.store[root+"/completed.json"]=_canonical({"sha256":h,"source_sha256":d["edition_sha256"]})
        r2.store[root+f"/snapshots/{h}.json"]=body
        return r2
    def test_ch17_score_possible_without_claiming_same_wire_profile(self):
        r2=self.make_store()
        result=collect(r2,persist=True)
        self.assertEqual(result["count"],3)
        self.assertFalse(result["same_wire_protocol_across_trials"])
        self.assertFalse(result["strict_cross_chapter_causal_comparison_allowed"])
        self.assertTrue(result["chapter17_single_protocol_recovery"])
        self.assertEqual(result["results"][2]["wire_profile"],"LOW_REASONING_V8")
        self.assertEqual(result["results"][0]["wire_profile"],"LEGACY_V7")
        self.assertFalse(result["core_promoted"])
        self.assertEqual(r2.writes,1)
    def test_low_effort_proof_is_mandatory(self):
        r2=self.make_store()
        root=recovered_root(2,17)
        ptr=json.loads(r2.store[root+"/completed.json"])
        key=root+f"/snapshots/{ptr['sha256']}.json"
        record=json.loads(r2.store.pop(key))
        record["budget_and_gateway_repair_protocol"]["probe_action_id"]=0
        data=_canonical(record)
        newhash=sha256(data).hexdigest()
        r2.store[root+"/completed.json"]=_canonical({"sha256":newhash,"source_sha256":record["edition_sha256"]})
        r2.store[root+f"/snapshots/{newhash}.json"]=data
        with self.assertRaisesRegex(ValueError,"low-effort gateway"):
            collect(r2,persist=False)

if __name__=="__main__":
    unittest.main()
