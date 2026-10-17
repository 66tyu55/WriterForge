"""No-network retry-budget profile regression, preserving existing default."""
import unittest
from test_v28_cloud_ab import FakeModel,PLANNER,CRITIC
from writerforge.reverse_cloud_ab import CloudABTrial,ABTrialError
from writerforge.reverse_real_training import raw_hash


class RetryProfileTests(unittest.TestCase):
    def fake_roles(self):
        return FakeModel("planner",PLANNER,"p"),FakeModel("writer",{},"w"),FakeModel("critic",CRITIC,"c")

    def test_retry_profile_reserves_two_extra_writer_attempts(self):
        p,w,c=self.fake_roles()
        source=("纯合成的安全叙事片段。"+chr(10))*30
        profile=(5500,8500,7000)
        trial=CloudABTrial(planner=p,writer=w,critic=c)
        result=trial.run(source,"合成下一段"*70,source_sha="a"*64,
                         window_hash=raw_hash(source),role_tokens=profile)
        self.assertEqual(result["role_output_token_profile"],list(profile))
        self.assertEqual(p.calls[0][2],5500)
        self.assertEqual(w.calls[0][2],8500)
        self.assertEqual(w.calls[1][2],8500)
        self.assertEqual(c.calls[0][2],7000)
        self.assertLessEqual(profile[0]+4*profile[1]+profile[2],50000)

    def test_custom_oversubscribed_budget_blocked_before_model_calls(self):
        p,w,c=self.fake_roles()
        with self.assertRaisesRegex(ABTrialError,"RETRY_RESILIENT"):
            CloudABTrial(planner=p,writer=w,critic=c).run(
                "合成原著片段。"*90,"合成下一段"*70,
                source_sha="a"*64,window_hash="b"*64,
                role_tokens=(6500,10500,8000))
        self.assertEqual(len(p.calls),0)
        self.assertEqual(len(w.calls),0)

if __name__=="__main__":
    unittest.main()
