"""V76 model-call budget and DeepSeek dashboard reconciliation (synthetic)."""
from __future__ import annotations

import json
import unittest

from writerforge.deepseek_flash_model import (
    DeepSeekFlashError,FlashBudget,
)
from writerforge.wf_api_usage_supervisor import (
    MeteredDeepSeekFlashModel,WFApiUsageAuditError,
    reconcile_dashboard_snapshot,
)
from writerforge.wf_learn_model_registry import new_wf_learn_model


KEY="synthetic-deepseek-api-not-real-account-key"
SYS='只回答JSON对象 {"question":"内容"}，不提供文学等级判定。'
ORIGINAL='模拟私有小说中的合成句子，仅用来证明日志不暴露正文。'


def wire(result='{"ok":true}',usage=(30,12)):
    return json.dumps({
       "choices":[{
          "finish_reason":"stop",
          "message":{"role":"assistant","content":result},
       }],
       "usage":{"prompt_tokens":usage[0],
                "completion_tokens":usage[1]},
    }).encode("utf-8")


class MeteredWFModelTests(unittest.TestCase):
    def make(self,transport,budget=None):
        return MeteredDeepSeekFlashModel(
           api_key=KEY,transport=transport,
           budget=budget if budget is not None else
               FlashBudget(max_calls=4,max_reserved_output_tokens=2000))

    def test_private_prompt_only_sha_in_public_usage_receipt(self):
        model=self.make(lambda req:wire())
        result=model.ask_json(
            role="first_read",system=SYS,user=ORIGINAL,
            max_tokens=400)
        self.assertEqual(result,{"ok":True})
        usage=model.public_usage_report()
        self.assertEqual(usage["event_count"],1)
        self.assertEqual(usage["reserved_requests"],1)
        self.assertEqual(usage["prompt_tokens_reported"],30)
        self.assertEqual(usage["completion_tokens_reported"],12)
        self.assertEqual(usage["events"][0]["role"],"first_read")
        self.assertEqual(len(usage["events"][0]["request_sha256"]),64)
        self.assertEqual(len(usage["events"][0]["output_sha256"]),64)
        self.assertTrue(usage["usage_needs_dashboard_reconciliation"])
        self.assertNotIn(ORIGINAL,str(usage))
        self.assertNotIn(KEY,str(usage))
        self.assertNotIn('{"ok":true}',str(usage))

    def test_timeout_may_be_billed_without_received_usage(self):
        seen=[0]
        def timeout(_request):
            seen[0]+=1
            raise DeepSeekFlashError("WF_FLASH_NETWORK_OR_TIMEOUT")
        model=self.make(timeout)
        with self.assertRaisesRegex(DeepSeekFlashError,"NETWORK_OR_TIMEOUT"):
            model.ask_json(role="first_read",system=SYS,
                           user=ORIGINAL,max_tokens=400)
        self.assertEqual(seen,[1])
        report=model.public_usage_report()
        self.assertEqual(report["reserved_requests"],1)
        self.assertEqual(
            report["calls_that_may_have_billed_without_visible_usage"],1)
        self.assertEqual(report["prompt_tokens_reported"],0)
        self.assertEqual(report["completion_tokens_reported"],0)

    def test_actual_provider_key_never_printed_by_wrapper(self):
        old=new_wf_learn_model(
            api_key=KEY,
            transport=lambda _:wire(),
            budget=FlashBudget(max_calls=1,max_reserved_output_tokens=160))
        self.assertIsInstance(old,MeteredDeepSeekFlashModel)
        self.assertEqual(old.ask_json(role="genre_classification",
                      system=SYS,user=ORIGINAL,max_tokens=120),{"ok":True})
        self.assertNotIn(KEY,str(old.public_usage_report()))

    def test_dashboard_baseline_125_tokens_one_call(self):
        model=self.make(lambda req:wire(usage=(100,20)))
        model.ask_json(role="first_read",system=SYS,user=ORIGINAL,
                       max_tokens=400)
        res=reconcile_dashboard_snapshot(
            before_requests=1,after_requests=2,
            before_tokens=125,after_tokens=245,
            wf_usage_report=model.public_usage_report())
        self.assertEqual(res["status"],"COUNTS_MATCH_FOR_SPECIFIED_TIME_WINDOW")
        self.assertFalse(res["provider_billing_website_verified_by_automation"])
        # No model literary grade or training success follows from billing.
        self.assertTrue(res["literary_quality_not_implied"])

    def test_other_apps_or_different_times_prevent_reconciliation(self):
        model=self.make(lambda req:wire(usage=(100,20)))
        model.ask_json(role="first_read",system=SYS,user=ORIGINAL,
                       max_tokens=400)
        res=reconcile_dashboard_snapshot(
            before_requests=1,after_requests=5,
            before_tokens=125,after_tokens=290,
            wf_usage_report=model.public_usage_report(),
            other_apps_used=True)
        self.assertEqual(res["status"],"UNRECONCILED")

    def test_deepseek_flash_output_error_not_reported_as_free(self):
        model=self.make(lambda _:wire("nonjson response"))
        with self.assertRaisesRegex(DeepSeekFlashError,"INVALID_JSON"):
            model.ask_json(role="first_read",system=SYS,user=ORIGINAL,
                           max_tokens=400)
        log=model.public_usage_report()
        self.assertEqual(log["reserved_requests"],1)
        self.assertEqual(
            log["calls_that_may_have_billed_without_visible_usage"],1)

    def test_max_four_events_no_fifth_call(self):
        model=self.make(lambda req:wire())
        for i in range(4):
            model.ask_json(role="first_read",system=SYS,
                           user=ORIGINAL+str(i),max_tokens=400)
        with self.assertRaisesRegex(WFApiUsageAuditError,
                                    "EVENT_LIMIT_EXCEEDED"):
            model.ask_json(role="first_read",system=SYS,
                           user=ORIGINAL+"fifth",max_tokens=400)
        self.assertEqual(model.budget.calls_reserved,4)

    def test_bad_dashboard_counts_refused(self):
        with self.assertRaisesRegex(WFApiUsageAuditError,"VALUES_INVALID"):
            reconcile_dashboard_snapshot(
                before_requests=-1,after_requests=1,
                before_tokens=125,after_tokens=125,
                wf_usage_report={"provider":"deepseek"})

if __name__=="__main__":
    unittest.main()
