"""Mock-only GLM low-effort opt-in transport test; no source or model calls."""
import json,unittest
from writerforge.reverse_discovery_models import DiscoveryModel,DiscoveryCallBudget,DiscoveryError


class GLMEffortTests(unittest.TestCase):
    def test_low_effort_is_explicit_for_glm_writer_only(self):
        outbound=[]
        prose="这是一个与任何原著无关的虚构小城。主人公仔细观察天气和行人的动作，决定改变回家路线。"*10
        def wire(req):
            outbound.append(json.loads(req.data))
            return json.dumps({"choices":[{"message":{"content":prose},
                      "finish_reason":"stop"}],"usage":{"completion_tokens":300,"prompt_tokens":100}},
                      ensure_ascii=False).encode()
        model=DiscoveryModel(name="glm-5.3",role="writer",api_key="dummy-not-a-real-key",
             budget=DiscoveryCallBudget(),transport=wire,reasoning_effort="low")
        self.assertIn("scene",model.ask("写小说","虚构",num_predict=2500))
        self.assertEqual(outbound[0]["reasoning_effort"],"low")
        self.assertNotIn("thinking",outbound[0])
        self.assertEqual(len(outbound),1)
    def test_unverified_effort_is_rejected(self):
        for name,role,effort in [
            ("glm-5.3","writer","none"),
            ("glm-5.3","writer","high"),
            ("glm-5.3","planner","low"),
            ("deepseek-v4-flash-0731","critic","low"),
        ]:
            with self.subTest(name=name,role=role,effort=effort):
                with self.assertRaisesRegex(DiscoveryError,"UNVERIFIED_REASONING"):
                    DiscoveryModel(name=name,role=role,api_key="not-a-real-key",
                         budget=DiscoveryCallBudget(),reasoning_effort=effort)
    def test_default_never_sends_unverified_extra_parameter(self):
        outbound=[]
        def wire(req):
            outbound.append(json.loads(req.data))
            return json.dumps({"choices":[{"message":{"content":json.dumps({"valid":True})},
                                            "finish_reason":"stop"}]}).encode()
        model=DiscoveryModel(name="deepseek-v4-flash-0731",role="planner",
             api_key="dummy-not-a-real-key",budget=DiscoveryCallBudget(),transport=wire)
        model.ask("system","user",num_predict=2500)
        self.assertNotIn("reasoning_effort",outbound[0])

if __name__=="__main__":
    unittest.main()
