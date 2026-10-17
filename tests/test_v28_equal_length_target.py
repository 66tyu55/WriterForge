"""Offline regression for neutral equal-length A/B, backwards compatible."""
import unittest
from test_v28_cloud_ab import FakeModel,PLANNER,CRITIC
from writerforge.reverse_cloud_ab import CloudABTrial,ABTrialError
from writerforge.reverse_real_training import raw_hash

class NeutralLengthTests(unittest.TestCase):
    def test_both_arms_get_identical_length_target_without_source(self):
        p=FakeModel("planner",PLANNER,"p")
        w=FakeModel("writer",{},"w")
        c=FakeModel("critic",CRITIC,"c")
        source=("第一段合成材料。"+chr(10))*32
        trial=CloudABTrial(planner=p,writer=w,critic=c)
        report=trial.run(source,"下一段合成材料"*48,
            source_sha="a"*64,window_hash=raw_hash(source),
            common_target_chars=1100,role_tokens=(5500,8500,7000))
        self.assertEqual(report["neutral_common_target_chars"],1100)
        self.assertFalse(report["manuscripts_cropped_or_padded"])
        self.assertEqual(len(w.calls),2)
        self.assertIn("1100",w.calls[0][1])
        self.assertIn("1100",w.calls[1][1])
        self.assertNotIn(source,w.calls[0][1])
        self.assertNotIn(source,c.calls[0][1])
    def test_legacy_mode_remains_unchanged(self):
        p=FakeModel("planner",PLANNER,"p")
        w=FakeModel("writer",{},"w")
        c=FakeModel("critic",CRITIC,"c")
        source=("第二个合成段落。"+chr(10))*36
        report=CloudABTrial(planner=p,writer=w,critic=c).run(
            source,"下一段合成材料"*42,source_sha="a"*64,
            window_hash=raw_hash(source))
        self.assertIsNone(report["neutral_common_target_chars"])
        self.assertNotIn("共同严格篇幅要求",w.calls[0][1])
    def test_invalid_size_fails_before_network(self):
        p=FakeModel("planner",PLANNER,"p")
        w=FakeModel("writer",{},"w")
        c=FakeModel("critic",CRITIC,"c")
        with self.assertRaisesRegex(ABTrialError,"INVALID_COMMON_AB_LENGTH_TARGET"):
            CloudABTrial(planner=p,writer=w,critic=c).run(
                "合成来源文本。"*50,"合成下一段"*40,source_sha="a"*64,
                window_hash="b"*64,common_target_chars=2000)
        self.assertEqual(len(p.calls),0)
        self.assertEqual(len(w.calls),0)

if __name__=="__main__":
    unittest.main()
