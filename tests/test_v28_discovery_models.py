"""V28 Discovery endpoint budget/key and role regression: no external traffic."""
import json
import unittest

from writerforge.reverse_discovery_models import (
    DiscoveryModel,DiscoveryCallBudget,DiscoveryError,ROLE_MODELS,ENDPOINT,
)

class DummyTransport:
    def __init__(self,response):
        self.response=response
        self.requests=[]
    def __call__(self,req):
        self.requests.append(req)
        return json.dumps(self.response,ensure_ascii=False).encode("utf-8")

class DiscoveryAdapterTests(unittest.TestCase):
    def create(self,model="glm-5.3", role="planner", transport=None, budget=None):
        return DiscoveryModel(name=model,role=role,api_key="fictional-probe-credential",
            budget=budget or DiscoveryCallBudget(),transport=transport)

    def test_uses_fixed_approved_endpoint_and_no_loggable_credentials(self):
        t=DummyTransport({"choices":[{"message":{"content":'{"trigger":"okay"}'}}],
                          "usage":{"prompt_tokens":14,"completion_tokens":8}})
        m=self.create(transport=t)
        out=m.ask("Return JSON","synthetic prompt",num_predict=300)
        self.assertEqual(out,{"trigger":"okay"})
        self.assertEqual(t.requests[0].full_url,ENDPOINT)
        self.assertNotIn(b"fictional-probe-credential",t.requests[0].data)
        self.assertEqual(m.budget.total_prompt_tokens,14)
        self.assertEqual(m.budget.total_completion_tokens,8)

    def test_shared_output_and_request_limits_stop_before_call(self):
        t=DummyTransport({"choices":[{"message":{"content":'{"ok":true}'}}]})
        cap=DiscoveryCallBudget(max_calls=1,max_reserved_output_tokens=450)
        m=self.create(transport=t,budget=cap)
        self.assertEqual(m.ask("system","test",num_predict=400),{"ok":True})
        with self.assertRaisesRegex(DiscoveryError,"BUDGET"):
            m.ask("system","again",num_predict=100)
        self.assertEqual(len(t.requests),1)

    def test_non_json_and_empty_text_are_blocked(self):
        t=DummyTransport({"choices":[{"message":{"content":""}}]})
        m=self.create(transport=t)
        with self.assertRaisesRegex(DiscoveryError,"EMPTY_VISIBLE"):
            m.ask("system","synthetic test",num_predict=300)
        t.response={"choices":[{"message":{"content":"not json"}}]}
        with self.assertRaisesRegex(DiscoveryError,"JSON_CONTRACT"):
            m.ask("system","synthetic test",num_predict=300)

    def test_different_model_roles_with_real_listed_names(self):
        self.assertEqual(set(ROLE_MODELS),{"planner","writer","critic"})
        self.assertEqual(len(set(ROLE_MODELS.values())),3)
        for role,model in ROLE_MODELS.items():
            self.assertEqual(self.create(model=model,role=role).name,model)
        with self.assertRaises(DiscoveryError):
            self.create(model="arbitrary-not-verified-model")
