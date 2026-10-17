"""Test the v9 three-chapter mix honestly labels the modified prompt."""
import json, unittest
from hashlib import sha256
from writerforge.r2_storage import _canonical
from scripts.audit_wudong_random3_v7_r2 import _root as oldroot
from scripts.audit_random3_v7_v9_r2 import collect,_root,COMMON_AB_CHARS,TRANSFER_TASK
from test_v28_random3_aggregation import FakePrivateR2

class V9MixedTests(unittest.TestCase):
    def fake_store(self):
        r2=FakePrivateR2([70,95,90])
        srcroot=oldroot(2,17)
        ptr=json.loads(r2.store.pop(srcroot+"/completed.json"))
        document=json.loads(r2.store.pop(srcroot+"/snapshots/"+ptr["sha256"]+".json"))
        adjusted=TRANSFER_TASK+(
            "\n本次A/B两组共同严格篇幅要求：含标点字符数目标"
            +str(COMMON_AB_CHARS)
            +"，允许偏差不超过8%；只完成一篇完整场景，"
            "不要增加附录、番外或第二幕。禁止凑字数重复叙述。"
        )
        document["writing_task_sha256"]=sha256(adjusted.encode()).hexdigest()
        document["role_output_token_profile"]=[5500,8500,7000]
        document["neutral_common_target_chars"]=COMMON_AB_CHARS
        document["manuscripts_cropped_or_padded"]=False
        document["budget_and_gateway_repair_protocol"]={
            "glm_writer_reasoning_effort":"low",
            "probe_action_id":38999272334,
            "role_output_budgets":[5500,8500,7000],
            "not_strictly_same_wire_settings_as_v7":True,
            "one_last_recovery_of_preselected_chapter17":True,
            "neutral_common_target_chars":COMMON_AB_CHARS,
            "previous_v8_failure_reason":"AB_LENGTH_MISMATCH_NOT_COMPARABLE",
        }
        encoded=_canonical(document)
        sha=sha256(encoded).hexdigest()
        target=_root(2,17)
        r2.store[target+"/completed.json"]=_canonical(
            {"sha256":sha,"source_sha256":document["edition_sha256"]})
        r2.store[target+"/snapshots/"+sha+".json"]=encoded
        return r2

    def test_three_trials_keep_distinct_wire_provenance(self):
        r2=self.fake_store()
        report=collect(r2,persist=True)
        self.assertEqual(report["count"],3)
        self.assertFalse(report["same_wire_protocol_across_trials"])
        self.assertFalse(report["identical_exact_task_prompt_across_trials"])
        self.assertEqual(report["results"][2]["wire_profile"],"LOW_REASONING_LENGTH1100_V9")
        self.assertFalse(report["core_promoted"])
        self.assertEqual(report["second_window"],"LOCKED")

if __name__=="__main__":
    unittest.main()
