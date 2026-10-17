"""Offline tests: symmetric A/B length repair must not privilege one arm."""
import unittest
from test_v28_cloud_ab import FakeModel,PLANNER,CRITIC
from writerforge.reverse_cloud_ab import CloudABTrial,ABTrialError
from writerforge.reverse_real_training import raw_hash

SOURCE=("纯合成来源事件，绝不带任何著作权保护原著情节。"+chr(10))*20
PART="雪后驿站的灯火渐弱，学徒比较索道刻痕，决定通知值夜师傅。"

class FourReplyWriter:
    provider="synthetic"
    name="sym-editor"
    def __init__(self,fail=False):
        self.calls=[]
        self.fail=fail
    def ask(self,system,user,*,num_predict):
        self.calls.append((system,user,num_predict))
        turn=len(self.calls)
        multiplier=40 if turn==1 else 70 if turn==2 else 65 if turn==3 else 66
        if self.fail and turn==4:multiplier=100
        return {"scene":PART*multiplier}

class SymmetricRevisionTests(unittest.TestCase):
    def test_two_edits_same_target_own_draft_only(self):
        p=FakeModel("planner",PLANNER,"plan")
        w=FourReplyWriter()
        c=FakeModel("critic",CRITIC,"critic")
        result=CloudABTrial(planner=p,writer=w,critic=c).run(
            SOURCE,"合成后续"*100,source_sha="a"*64,
            window_hash=raw_hash(SOURCE),common_target_chars=1100,
            role_tokens=(5500,8500,7000),symmetric_length_revision=True)
        self.assertEqual(result["symmetric_revision_calls"],2)
        self.assertTrue(result["symmetric_length_revision_opt_in"])
        self.assertEqual(len(w.calls),4)
        self.assertEqual(len(c.calls),1)
        self.assertTrue(result["length_gate"]["comparable"])
        self.assertFalse(result["manuscripts_cropped_or_padded"])
        self.assertIn("own_draft_to_rewrite",w.calls[2][1])
        self.assertIn("own_draft_to_rewrite",w.calls[3][1])
        self.assertNotIn(SOURCE,w.calls[2][1])
        self.assertNotIn(SOURCE,c.calls[0][1])
    def test_failed_equalization_stops_critic_and_preserves_locks(self):
        p=FakeModel("planner",PLANNER,"plan")
        w=FourReplyWriter(fail=True)
        c=FakeModel("critic",CRITIC,"critic")
        with self.assertRaisesRegex(ABTrialError,"AB_LENGTH_MISMATCH_AFTER_SYMMETRIC_REVISION"):
            CloudABTrial(planner=p,writer=w,critic=c).run(
                SOURCE,"合成后续"*100,source_sha="a"*64,
                window_hash=raw_hash(SOURCE),common_target_chars=1100,
                role_tokens=(5500,8500,7000),symmetric_length_revision=True)
        self.assertEqual(len(w.calls),4)
        self.assertEqual(len(c.calls),0)
    def test_symmetric_mode_rejects_missing_target_without_calls(self):
        p=FakeModel("planner",PLANNER,"plan")
        w=FourReplyWriter()
        c=FakeModel("critic",CRITIC,"critic")
        with self.assertRaisesRegex(ABTrialError,"SYMMETRIC_LENGTH_REVISION_BUDGET_INVALID"):
            CloudABTrial(planner=p,writer=w,critic=c).run(
                SOURCE,"合成后续"*100,source_sha="a"*64,
                window_hash=raw_hash(SOURCE),role_tokens=(5500,8500,7000),
                symmetric_length_revision=True)
        self.assertEqual(len(p.calls),0)
        self.assertEqual(len(w.calls),0)
if __name__=="__main__":
    unittest.main()
