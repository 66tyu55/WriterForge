"""V28 cloud adapter and A/B no-network regressions. All manuscript text synthetic."""
from __future__ import annotations

from io import BytesIO
import json
import unittest

from writerforge.reverse_cloud_models import (
    CloudCallBudget, CloudModel, ModelUnavailable,
    configured_cloud_roles, safe_cloud_readiness, PROVIDER_ENDPOINTS,
)
from writerforge.reverse_cloud_ab import CloudABTrial, ABTrialError

class FakeTransport:
    def __init__(self, response):
        self.response=response
        self.requests=[]
    def __call__(self, request, size):
        self.requests.append(request)
        return json.dumps(self.response,ensure_ascii=False).encode("utf-8")

class AdapterTests(unittest.TestCase):
    def model(self, name="premium",provider="moonshot",transport=None,budget=None):
        return CloudModel(role="planner",provider=provider,name=name,
                          key="fixture-not-a-live-key",budget=budget or CloudCallBudget(),
                          input_usd_per_m=0.5,output_usd_per_m=2.0,transport=transport)
    def test_https_allowlist_and_no_key_in_response(self):
        t=FakeTransport({"choices":[{"message":{"content":'{"ok":true}'}}],
                         "usage":{"prompt_tokens":25,"completion_tokens":5}})
        m=self.model(transport=t)
        self.assertEqual(m.ask("Return JSON","hello"),{"ok":True})
        r=t.requests[0]
        self.assertEqual(r.full_url,PROVIDER_ENDPOINTS["moonshot"])
        self.assertNotIn(b"fixture-not-a-live-key",r.data)
        self.assertEqual(m.budget.observed_input_tokens,25)
        self.assertEqual(m.budget.observed_output_tokens,5)

    def test_fail_closed_invalid_endpoint_or_bad_key_or_price(self):
        with self.assertRaises(ModelUnavailable):
            self.model(provider="http://example.local")
        with self.assertRaises(ModelUnavailable):
            CloudModel(role="critic",provider="moonshot",name="x",key="",
                       budget=CloudCallBudget(),input_usd_per_m=1,output_usd_per_m=1)
        self.assertFalse(safe_cloud_readiness(environ={})["ready"])

    def test_price_and_call_cap_prevent_paid_request(self):
        t=FakeTransport({"choices":[{"message":{"content":'{"ok":true}'}}]})
        m=self.model(transport=t,budget=CloudCallBudget(max_calls=1,max_usd=0.02))
        m.ask("json","short")
        with self.assertRaisesRegex(ModelUnavailable,"call budget"):
            m.ask("json","short")
        self.assertEqual(len(t.requests),1)

    def test_body_and_response_caps_refuse_without_evidence(self):
        t=FakeTransport({"choices":[{"message":{"content":'{"ok":true}'}}]})
        m=self.model(transport=t)
        with self.assertRaises(ModelUnavailable):
            m.ask("json","x"*14000)
        self.assertEqual(len(t.requests),0)
        m=self.model(transport=lambda request,size:b"x"*(size+1))
        with self.assertRaisesRegex(ModelUnavailable,"unbounded"):
            m.ask("json","small")

    def test_three_role_wiring_requires_explicit_different_critic(self):
        env={"WF_V28_MAX_USD":"0.5","WF_V28_MAX_CALLS":"7"}
        for role,model in (("PLANNER","planner-v1"),("WRITER","writer-v1"),("CRITIC","critic-v1")):
            env.update({
                f"WF_V28_{role}_PROVIDER":"deepseek",
                f"WF_V28_{role}_MODEL":model,
                f"WF_V28_{role}_API_KEY":"testfixturekey",
                f"WF_V28_{role}_INPUT_USD_PER_M":"0.5",
                f"WF_V28_{role}_OUTPUT_USD_PER_M":"1",
            })
        roles,budget=configured_cloud_roles(environ=env,transport=FakeTransport({}))
        self.assertIs(roles["planner"].budget,roles["writer"].budget)
        self.assertIs(roles["critic"].budget,budget)
        self.assertTrue(safe_cloud_readiness(environ=env)["ready"])
        env["WF_V28_CRITIC_MODEL"]="writer-v1"
        with self.assertRaisesRegex(ModelUnavailable,"different model"):
            configured_cloud_roles(environ=env)

class FakeModel:
    def __init__(self,role,answer,model):
        self.role=role
        self.answer=answer
        self.name=model
        self.provider="synthetic"
        self.calls=[]
    def ask(self,system,user,num_predict):
        self.calls.append((system,user,num_predict))
        if self.role=="writer":
            n=len(self.calls)
            return {"scene":(("陌生的山雨连着三夜，行人停下听辨脚步与水声，"
                              "觉得必须在天黑之前作出选择，否则盟约难以兑现。"
                              + ("决定先守路口。" if n==1 else "决定去河边寻找目击者。"))*17)}
        return self.answer

PLANNER={
    "selections":[
        {"id":"GOAL_FILTERS_ATTENTION","evidence_ids":["P0"]},
        {"id":"COST_VISIBLE_IN_ACTION","evidence_ids":["P1"]},
    ]
}
DIMENSIONS=("perception","causality","information","continuity","language")
CRITIC={
    "A":{k:{"score":81,"reason":"故事线索较少，人物目标还可明确"} for k in DIMENSIONS},
    "B":{k:{"score":85,"reason":"人物行为更有可信前提，节奏也较稳"} for k in DIMENSIONS},
    "uncertainty":"两份稿件仍缺少真实读者评估，不能确定优劣",
    "learned_mechanism":"叙述注意筛选要受到角色当下目标约束",
}
class ABTests(unittest.TestCase):
    def test_true_blinded_comparison_does_not_save_draft(self):
        p=FakeModel("planner",PLANNER,"p")
        w=FakeModel("writer",{},"w")
        c=FakeModel("critic",CRITIC,"c")
        source="原著窗口的合成素材仅用于研究人物因果。\n"*20
        later="后续窗口无权提供给创作模型"*30
        from writerforge.reverse_real_training import raw_hash
        result=CloudABTrial(planner=p,writer=w,critic=c).run(
            source,later,source_sha="a"*64,window_hash=raw_hash(source))
        self.assertEqual(result["model_call_count_nominal"],4)
        self.assertFalse(result["core_automatically_promoted"])
        self.assertFalse(result["literal_master_quality_90pct_verified"])
        self.assertFalse(result["second_unit_unlocked"])
        self.assertEqual(len(w.calls),2)
        self.assertEqual(len(c.calls),1)
        self.assertNotIn(source,c.calls[0][1])
        self.assertNotIn("source_context",c.calls[0][1])
        self.assertFalse(result["critic_prompt_original_source_prose"])
        self.assertNotIn(source,w.calls[0][1])
        self.assertIn("technique_operations",w.calls[1][1])
        self.assertNotIn("technique_operations",w.calls[0][1])
        self.assertNotIn("evidence_ids",w.calls[1][1])
        self.assertNotIn("P0",w.calls[1][1])
        self.assertNotIn(source,w.calls[1][1])
        self.assertIn("baseline",result["comparisons"])
        self.assertIn("skill",result["comparisons"])
        for call in w.calls:
            self.assertNotIn("林动",call[1])
        self.assertNotIn("原著窗口的合成素材",str(result))
        self.assertNotIn("陌生的山雨连着三夜",str(result))

    def test_same_model_cannot_self_critic_and_wrong_source_fails(self):
        p=FakeModel("planner",PLANNER,"p")
        w=FakeModel("writer",{},"same")
        c=FakeModel("critic",CRITIC,"same")
        with self.assertRaises(ABTrialError):
            CloudABTrial(planner=p,writer=w,critic=c)
        c.name="other"
        with self.assertRaisesRegex(ABTrialError,"no longer matches"):
            CloudABTrial(planner=p,writer=w,critic=c).run(
                "甲"*650,"乙"*650,source_sha="a"*64,window_hash="b"*64)
        self.assertEqual(len(w.calls),0)

    def test_short_exact_source_quote_does_not_survive_review(self):
        from writerforge.reverse_cloud_ab import _choice_score
        excerpt="这是仅供测试的十八个以上连续中文原文字符必须被隐藏"
        text=excerpt+"而非模型原创评论"
        scores={key: {"score": 81, "reason": text} for key in DIMENSIONS}
        output=_choice_score(scores, "假稿", excerpt)
        for value in output.values():
            self.assertTrue(value["reason"].startswith("UNVERIFIED_QUOTATION_REDACTED_"))
            self.assertNotIn(excerpt, value["reason"])


if __name__=="__main__":
    unittest.main()
