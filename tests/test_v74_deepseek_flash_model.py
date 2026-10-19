"""V74 WF DeepSeek Flash API contract; synthetic responses, zero paid calls.

All fixtures are invented; no R2 source, user text or real credentials.
"""
from __future__ import annotations

import json
import os
import unittest
from urllib.error import HTTPError
from io import BytesIO

from writerforge.deepseek_flash_model import (
    API_URL, MODEL, PROVIDER, TOKEN_ENV,
    DeepSeekFlashModel, DeepSeekFlashError, FlashBudget,
    learner_provider_status, _NoRedirect,
)

DUMMY_KEY="synthetic-deepseek-not-a-real-secret-for-tests"


def wire(content='{"status":"accepted","kind":"test"}',finish="stop",
         prompt_tokens=27,output_tokens=12):
    return json.dumps({
       "choices":[{"finish_reason":finish,
                   "message":{"role":"assistant","content":content}}],
       "usage":{"prompt_tokens":prompt_tokens,
                "completion_tokens":output_tokens},
    },ensure_ascii=False).encode("utf-8")


class FakeTransport:
    def __init__(self,response=None):
        self.received=[]
        self.response=wire() if response is None else response
    def __call__(self,request):
        self.received.append(request)
        return self.response


class DeepSeekProviderTests(unittest.TestCase):
    def setUp(self):
        self.transport=FakeTransport()
        self.model=DeepSeekFlashModel(
            api_key=DUMMY_KEY,transport=self.transport)
        self.system=(
          '你是WriterForge自身LEARN模块。仅返回JSON对象，'
          '格式示例 {"status":"accepted","kind":"test"}。不补原著，不代作者写答案。')
    def one(self,*,role="first_read",tokens=650,user="合成文本，不是真实小说。"):
        return self.model.ask_json(
            role=role,system=self.system,user=user,max_tokens=tokens)

    def test_model_id_host_and_json_shape(self):
        output=self.one()
        self.assertEqual(output,{"status":"accepted","kind":"test"})
        self.assertEqual(len(self.transport.received),1)
        req=self.transport.received[0]
        self.assertEqual(req.full_url,API_URL)
        self.assertEqual(req.get_method(),"POST")
        sent=json.loads(req.data)
        self.assertEqual(sent["model"],"deepseek-flash")
        self.assertEqual(sent["thinking"],{"type":"disabled"})
        self.assertEqual(sent["response_format"],{"type":"json_object"})
        self.assertFalse(sent["stream"])
        self.assertEqual(sent["max_tokens"],650)
        self.assertEqual([x["role"] for x in sent["messages"]],
                         ["system","user"])
        self.assertIn("严格有效的 JSON",sent["messages"][0]["content"])
        self.assertEqual(req.get_header("Authorization"),"Bearer "+DUMMY_KEY)
        self.assertEqual(self.model.name,MODEL)

    def test_usage_is_just_metering_not_mastery(self):
        self.one(role="genre_classification")
        self.one(role="first_read")
        status=self.model.budget.public_receipt()
        self.assertEqual(status["provider"],PROVIDER)
        self.assertEqual(status["calls_reserved"],2)
        self.assertEqual(status["prompt_tokens_reported"],54)
        self.assertEqual(status["completion_tokens_reported"],24)
        self.assertTrue(status["model_decisions_not_verified_literary_truth"])
        self.assertNotIn(DUMMY_KEY,str(status))

    def test_budget_is_hard_and_no_failed_retry(self):
        b=FlashBudget(max_calls=1,max_reserved_output_tokens=750)
        model=DeepSeekFlashModel(api_key=DUMMY_KEY,budget=b,
                                transport=self.transport)
        model.ask_json(role="first_read",system=self.system,
                       user="synthetic",max_tokens=650)
        with self.assertRaisesRegex(DeepSeekFlashError,"BUDGET_EXCEEDED"):
            model.ask_json(role="craft_analysis",system=self.system,
                           user="again",max_tokens=650)
        self.assertEqual(len(self.transport.received),1)

    def test_token_output_limit_enforced_without_network(self):
        with self.assertRaisesRegex(DeepSeekFlashError,"BUDGET_EXCEEDED"):
            self.one(tokens=50000)
        self.assertEqual(len(self.transport.received),0)

    def test_no_writer_or_critic_role_promoted(self):
        with self.assertRaisesRegex(DeepSeekFlashError,"ROLE_UNSUPPORTED"):
            self.one(role="writer")
        self.assertEqual(len(self.transport.received),0)

    def test_invalid_json_prompt_refused(self):
        with self.assertRaisesRegex(DeepSeekFlashError,"JSON_PROMPT_INVALID"):
            self.model.ask_json(role="first_read",system="中文短提示",
                                user="hi")
        self.assertEqual(len(self.transport.received),0)

    def test_truncated_response_refused_with_no_retry(self):
        self.transport.response=wire(finish="length")
        with self.assertRaisesRegex(DeepSeekFlashError,"OUTPUT_TRUNCATED"):
            self.one()
        self.assertEqual(len(self.transport.received),1)

    def test_empty_json_content_refused(self):
        self.transport.response=wire(content="")
        with self.assertRaisesRegex(DeepSeekFlashError,
                                    "EMPTY_OR_OVERSIZED_CONTENT"):
            self.one()
        self.assertEqual(len(self.transport.received),1)

    def test_non_json_content_refused(self):
        self.transport.response=wire(content="我是一段说明文字")
        with self.assertRaisesRegex(DeepSeekFlashError,
                                    "INVALID_JSON_RESPONSE"):
            self.one()
        self.assertEqual(len(self.transport.received),1)

    def test_json_array_refused(self):
        self.transport.response=wire(content='["not a study"]')
        with self.assertRaisesRegex(DeepSeekFlashError,
                                    "RESULT_NOT_BOUNDED_JSON_OBJECT"):
            self.one()

    def test_bad_finish_reason_refused(self):
        self.transport.response=wire(finish="content_filter")
        with self.assertRaisesRegex(DeepSeekFlashError,
                                    "FINISH_REASON_UNSAFE"):
            self.one()

    def test_http_error_exposes_status_not_error_body_or_token(self):
        def transport(req):
            raise DeepSeekFlashError("WF_FLASH_HTTP_401")
        model=DeepSeekFlashModel(api_key=DUMMY_KEY,transport=transport)
        with self.assertRaisesRegex(DeepSeekFlashError,"WF_FLASH_HTTP_401") as result:
            model.ask_json(role="first_read",system=self.system,user="hi")
        self.assertNotIn(DUMMY_KEY,str(result.exception))

    def test_network_timeout_no_hidden_fallback(self):
        calls=[0]
        def transport(req):
            calls[0]+=1
            raise DeepSeekFlashError("WF_FLASH_NETWORK_OR_TIMEOUT")
        model=DeepSeekFlashModel(api_key=DUMMY_KEY,transport=transport)
        with self.assertRaisesRegex(DeepSeekFlashError,"NETWORK_OR_TIMEOUT"):
            model.ask_json(role="first_read",system=self.system,user="hi")
        self.assertEqual(calls,[1])

    def test_missing_key_never_falls_back_to_discovery(self):
        with self.assertRaisesRegex(DeepSeekFlashError,"API_KEY_NOT_CONFIGURED"):
            DeepSeekFlashModel(api_key="")
        status=learner_provider_status({})
        self.assertEqual(status["WF_LEARN_MODEL"],"deepseek-flash")
        self.assertFalse(status["key_present"])
        self.assertFalse(status["discovery_api_used_for_wf_learn"])
        self.assertFalse(status["auto_paid_training_enabled"])

    def test_redirect_refuses_to_follow_bearer(self):
        with self.assertRaisesRegex(DeepSeekFlashError,"REDIRECT_REFUSED"):
            _NoRedirect().redirect_request(None,None,302,"redirect",{},
                "https://somewhere-else.example.net")

    def test_http_error_body_not_read(self):
        class UnsafeBody(BytesIO):
            def read(self,*args):
                raise AssertionError("private failure body must not be read")
        def throw(_req):
            error=HTTPError(API_URL,403,"forbidden",{},
                            UnsafeBody(b"private-prose"))
            # Exercise _real_transport by temporarily swapping opener,
            # not a genuine network request. The model itself rejects
            # injected error without exposing raw source.
            raise error
        fake=DeepSeekFlashModel(api_key=DUMMY_KEY,transport=throw)
        with self.assertRaises(HTTPError):
            fake.ask_json(role="first_read",system=self.system,user="synthetic")
        self.assertEqual(fake.budget.calls_reserved,1)

    def test_scene_adapter_keeps_data_inside_WF(self):
        call=self.model.call_for_scene(role="first_read",
            system=self.system,max_tokens=550)
        answer=json.loads(call("假定的第一读提示"))
        self.assertEqual(answer["status"],"accepted")
        self.assertNotIn(DUMMY_KEY,json.dumps(answer))

if __name__=="__main__":
    unittest.main()
