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
        with self.assertRaisesRegex(DiscoveryError,"STRUCTURED_OUTPUT_FAILED"):
            m.ask("system","synthetic test",num_predict=300)

    def test_writer_accepts_plain_prose_without_enforcing_json(self):
        prose=("原创山岭中，年轻旅人追着风雪寻找同伴。"
               "他看到谷底结冰的河流，便决定沿着脚印往北走。")*12
        t=DummyTransport({"choices":[{
            "message":{"content":prose},"finish_reason":"stop"
        }],"usage":{"prompt_tokens":50,"completion_tokens":480}})
        model=self.create(model="deepseek-v4-pro-0813",role="writer",transport=t)
        result=model.ask("只输出正文","创作故事",num_predict=1200)
        self.assertEqual(result,{"scene":prose})
        sent=json.loads(t.requests[0].data)
        self.assertNotIn("response_format",sent)
        self.assertIn("只输出原创小说正文",sent["messages"][0]["content"])
        self.assertEqual(model.budget.calls,1)

    def test_writer_continues_actual_partial_prose_instead_of_restarting(self):
        first=("陌生行人在冰冷山路上感到风向骤变。"
               "他想起必须带回的重要消息，决定查看积雪。")*11
        ending=("脚印通向林间废屋，他放下行囊查找线索。"
                "得知危险来自暗道之后，他决定返回村庄报信。")*10
        class TwoCallTransport:
            def __init__(self):
                self.requests=[]
            def __call__(self,request):
                self.requests.append(request)
                text=first if len(self.requests)==1 else ending
                finish="length" if len(self.requests)==1 else "stop"
                return json.dumps({"choices":[{"message":{"content":text},
                                                "finish_reason":finish}]}).encode("utf-8")
        t=TwoCallTransport()
        m=self.create(model="deepseek-v4-pro-0813",role="writer",transport=t)
        result=m.ask("原创小说","新场景",num_predict=1200)
        self.assertEqual(result["scene"],first+ending)
        self.assertEqual(m.budget.calls_by_role,{"writer":2})
        self.assertEqual([x["finish_reason"] for x in m.budget.response_observations],
                         ["length","stop"])
        continuation=json.loads(t.requests[1].data)
        self.assertEqual(continuation["messages"][2]["role"],"assistant")
        self.assertEqual(continuation["messages"][2]["content"],first)
        self.assertIn("只续写",continuation["messages"][3]["content"])
        self.assertNotIn("response_format",continuation)

    def test_writer_rejects_truncated_text_after_bounded_retry(self):
        prose=("山路上的旅人发现雪层下有奇怪足迹。"
               "他考虑风险并决定返回营地通知同伴。")*14
        t=DummyTransport({"choices":[{
            "message":{"content":prose},"finish_reason":"length"
        }]})
        model=self.create(model="deepseek-v4-pro-0813",role="writer",transport=t)
        with self.assertRaisesRegex(DiscoveryError,"OUTPUT_TRUNCATED"):
            model.ask("写作","原创",num_predict=1200)
        self.assertEqual(len(t.requests),2)

    def test_different_model_roles_with_real_listed_names(self):
        self.assertEqual(set(ROLE_MODELS),{"planner","writer","critic"})
        self.assertNotEqual(ROLE_MODELS["writer"], ROLE_MODELS["critic"])
        for role,model in ROLE_MODELS.items():
            self.assertEqual(self.create(model=model,role=role).name,model)
        with self.assertRaises(DiscoveryError):
            self.create(model="arbitrary-not-verified-model")
