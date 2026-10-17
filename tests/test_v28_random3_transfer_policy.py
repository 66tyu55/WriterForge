"""Cross-context evidence-first quarantine test with synthetic R2-style results."""
import unittest
from hashlib import sha256
from writerforge.r2_storage import _canonical
from writerforge.reverse_transfer_policy import (
    policy_from_immutable_random3,should_withhold_opt_in,TransferPolicyError)
from scripts.audit_wudong_random3_v7_r2 import collect
from test_v28_random3_aggregation import FakePrivateR2
from test_v28_cloud_ab import FakeModel,CRITIC
from writerforge.reverse_cloud_ab import CloudABTrial,ABTrialError
from writerforge.reverse_real_training import raw_hash


def fixture(scores):
    report=collect(FakePrivateR2(scores),persist=False)
    return report,sha256(_canonical(report)).hexdigest()


class PolicyTests(unittest.TestCase):
    def test_three_negative_different_chapters_triggers_only_candidate_pair(self):
        report,h=fixture([70,71,72])
        policy=policy_from_immutable_random3(report,report_sha256=h)
        self.assertEqual(policy["second_window"],"LOCKED")
        self.assertFalse(policy["legacy_host_mechanisms_deleted"])
        pair=report["results"][0]["mechanism_ids_unreviewed"]
        self.assertTrue(should_withhold_opt_in(pair,policy))
        self.assertFalse(should_withhold_opt_in(["WITHHOLD_CAUSE_SHOW_CLUE"],policy))
        self.assertEqual(policy["states"][0]["distinct_windows"],3)

    def test_mixed_results_does_not_auto_block(self):
        report,h=fixture([70,95,72])
        policy=policy_from_immutable_random3(report,report_sha256=h)
        pair=report["results"][0]["mechanism_ids_unreviewed"]
        self.assertFalse(should_withhold_opt_in(pair,policy))
    def test_forged_receipt_or_duplicate_chapter_rejected(self):
        report,h=fixture([70,71,72])
        report["results"][1]["chapter"]=3
        with self.assertRaises(TransferPolicyError):
            policy_from_immutable_random3(report,report_sha256=h)
        fixed_h=sha256(_canonical(report)).hexdigest()
        with self.assertRaises(TransferPolicyError):
            policy_from_immutable_random3(report,report_sha256=fixed_h)
    def test_guard_stops_writer_and_critic_but_preserves_old_default(self):
        report,h=fixture([70,71,72])
        policy=policy_from_immutable_random3(report,report_sha256=h)
        selected=report["results"][0]["mechanism_ids_unreviewed"]
        source="这是用于合成实验的故事背景，与任何真实原著无关。\n"*16
        plan={"selections":[
            {"id":name,"evidence_ids":["P"+str(i)]}
            for i,name in enumerate(selected)
        ]}
        p=FakeModel("planner",plan,"p")
        w=FakeModel("writer",{},"w")
        critic=FakeModel("critic",CRITIC,"c")
        with self.assertRaisesRegex(ABTrialError,"MULTI_WINDOW_NEGATIVE"):
            CloudABTrial(planner=p,writer=w,critic=critic,
                         evidence_first=True,transfer_policy=policy).run(
                         source,"合成后续"*90,source_sha="a"*64,
                         window_hash=raw_hash(source))
        self.assertEqual(len(w.calls),0)
        self.assertEqual(len(critic.calls),0)
        # Legacy mode cannot silently pretend it applied an opt-in policy.
        with self.assertRaisesRegex(ABTrialError,"UNSAFE_POLICY_WITH_LEGACY"):
            CloudABTrial(planner=p,writer=w,critic=critic,transfer_policy=policy)
        CloudABTrial(planner=p,writer=w,critic=critic)

if __name__=="__main__":
    unittest.main()
