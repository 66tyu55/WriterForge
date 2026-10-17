"""WF general CloudAB absolute output range opt-in, no network or novel source."""
import unittest
from test_v28_cloud_ab import FakeModel,PLANNER,CRITIC
from writerforge.reverse_cloud_ab import CloudABTrial,ABTrialError
from writerforge.reverse_real_training import raw_hash

SOURCE=("合成文本只用于测试人物在风雨之中的有限视角，与任何原著无关。"+chr(10))*20
UNIT="少年在雨后的古镇街巷里看见一张被风吹落的纸，决定先去寻找主人。"
TASK="原创小说的一个完整开篇：学徒在雨夜发现被遗落的信，误判造成真实后果，留有可回查的具体悬念。"
def story(n):return (UNIT*((n+len(UNIT)-1)//len(UNIT)))[:n]

class Writer:
    provider="synthetic"
    name="bounded-writer"
    def __init__(self,lengths):self.lengths=lengths;self.calls=[]
    def ask(self,system,user,*,num_predict):
        self.calls.append((system,user,num_predict))
        return {"scene":story(self.lengths[len(self.calls)-1])}

class GeneralLengthGateTests(unittest.TestCase):
    def models(self,lengths):
        p=FakeModel("planner",PLANNER,"p")
        w=Writer(lengths)
        c=FakeModel("critic",CRITIC,"c")
        return p,w,c
    def go(self,p,w,c,**kwargs):
        requested_target=kwargs.pop("target",1120)
        return CloudABTrial(planner=p,writer=w,critic=c).run(
            SOURCE,"合成后续"*90,source_sha="a"*64,
            window_hash=raw_hash(SOURCE),common_target_chars=requested_target,
            role_tokens=(5500,7500,7000),writing_task=TASK,**kwargs)
    def test_relative_equal_but_absolute_invalid_still_unscorable(self):
        p,w,c=self.models([1000,1010])
        with self.assertRaisesRegex(ABTrialError,"AB_ABSOLUTE_LENGTH_VIOLATION"):
            self.go(p,w,c,absolute_char_bounds=(1100,1300))
        self.assertEqual(len(w.calls),2)
        self.assertEqual(len(c.calls),0)
    def test_absolute_invalid_forces_equal_edits_even_if_relatively_fair(self):
        p,w,c=self.models([1000,1005,1140,1170])
        r=self.go(p,w,c,absolute_char_bounds=(1100,1300),
                  symmetric_length_revision=True)
        self.assertEqual(r["symmetric_revision_calls"],2)
        self.assertEqual(r["absolute_char_bounds_opt_in"],[1100,1300])
        self.assertTrue(r["both_drafts_meet_absolute_bounds"])
        self.assertEqual(len(c.calls),1)
        self.assertIn("own_actual_character_count",w.calls[2][1])
        self.assertNotIn(SOURCE,w.calls[2][1])
    def test_fail_after_symmetry_never_grades_out_of_bounds(self):
        # After symmetric edit the drafts are relatively comparable but
        # both remain below the enforced 1100 hard minimum.
        p,w,c=self.models([1000,1005,1050,1080])
        with self.assertRaisesRegex(ABTrialError,"AB_ABSOLUTE_LENGTH_AFTER_SYMMETRIC_REVISION"):
            self.go(p,w,c,absolute_char_bounds=(1100,1300),
                    symmetric_length_revision=True)
        self.assertEqual(len(c.calls),0)
    def test_invalid_bounds_rejected_before_any_calls(self):
        p,w,c=self.models([])
        with self.assertRaisesRegex(ABTrialError,"INVALID_ABSOLUTE_CHAR_BOUNDS"):
            self.go(p,w,c,absolute_char_bounds=(1300,900))
        self.assertEqual(len(p.calls),0)
        self.assertEqual(len(w.calls),0)
    def test_custom_larger_user_requested_target_hard_checked(self):
        p,w,c=self.models([1920,2030])
        r=self.go(p,w,c,target=2000,absolute_char_bounds=(1800,2200))
        self.assertTrue(r["both_drafts_meet_absolute_bounds"])
        self.assertEqual(r["neutral_common_target_chars"],2000)
        self.assertEqual(r["absolute_char_bounds_opt_in"],[1800,2200])
        self.assertEqual(len(c.calls),1)

    def test_old_default_relative_only_does_not_change(self):
        p,w,c=self.models([1000,1010])
        r=self.go(p,w,c)
        self.assertIsNone(r["absolute_char_bounds_opt_in"])
        self.assertEqual(len(w.calls),2)
        self.assertEqual(len(c.calls),1)
if __name__=="__main__":
    unittest.main()
