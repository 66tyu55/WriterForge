"""V109: provider HTTP response captured BEFORE decoding; zero billable calls.

Bad JSON, wrong finish reason and valid JSON must all pass the same private
wire evidence callback. A network timeout has no actual bytes to persist;
its pre-request attempt slot must remain reserved by the caller instead.
"""
from __future__ import annotations
import json
import unittest
from writerforge.deepseek_flash_model import (
    DeepSeekFlashModel, DeepSeekFlashError,FlashBudget,
)
from test_v74_deepseek_flash_model import DUMMY_KEY,FakeTransport,wire


class WireFirstTests(unittest.TestCase):
    def request(self,raw,with_sink=True):
        wire_list=[]
        transport=FakeTransport(response=raw)
        budget=FlashBudget(max_calls=1,max_reserved_output_tokens=900)
        model=DeepSeekFlashModel(
            api_key=DUMMY_KEY,budget=budget,transport=transport,
            on_response_wire=(lambda content:wire_list.append(content))
                             if with_sink else None)
        return model,transport,wire_list

    def call(self,model):
        return model.ask_json(
            role="self_scene_writing",
            system="你是WriterForge模型，严格返回JSON对象，不能加其他内容。",
            user="合成占位，非真实原著，给出JSON测试。",max_tokens=850)

    def test_provider_non_json_content_still_has_unmodified_wire(self):
        raw=wire(content="这次返回的不是JSON，仍然可能已经计费。")
        model,transport,seen=self.request(raw)
        with self.assertRaisesRegex(DeepSeekFlashError,
                                    "INVALID_JSON_RESPONSE"):
            self.call(model)
        self.assertEqual(seen,[raw])
        self.assertEqual(len(transport.received),1)
        self.assertEqual(model.budget.calls_reserved,1)
        self.assertTrue(model.budget.tokens_reserved>=850)
        self.assertEqual(model.budget.completion_tokens_reported,0)
        with self.assertRaisesRegex(DeepSeekFlashError,"BUDGET_EXCEEDED"):
            self.call(model)
        self.assertEqual(len(seen),1)

    def test_truncated_json_is_still_sealed_without_resending(self):
        raw=wire(content='{"prose":"截断',finish="length")
        model,transport,seen=self.request(raw)
        with self.assertRaisesRegex(DeepSeekFlashError,"OUTPUT_TRUNCATED"):
            self.call(model)
        self.assertEqual(seen,[raw])
        self.assertEqual(model.budget.calls_reserved,1)
        self.assertEqual(len(transport.received),1)

    def test_success_callback_preserves_original_exact_bytes(self):
        raw=wire(content='{"prose":"一名守林人把钥匙留在旧屋门内。"}')
        model,transport,seen=self.request(raw)
        doc=self.call(model)
        self.assertEqual(doc,{"prose":"一名守林人把钥匙留在旧屋门内。"})
        self.assertEqual(seen,[raw])
        self.assertEqual(model.budget.completion_tokens_reported,12)

    def test_invalid_callback_not_called_until_response_exists(self):
        with self.assertRaisesRegex(DeepSeekFlashError,"WIRE_SINK_NOT_CALLABLE"):
            DeepSeekFlashModel(api_key=DUMMY_KEY,on_response_wire="not callable")
        bytes_seen=[]
        def bad_transport(req):
            raise DeepSeekFlashError("WF_FLASH_NETWORK_OR_TIMEOUT")
        model=DeepSeekFlashModel(
            api_key=DUMMY_KEY,transport=bad_transport,
            on_response_wire=lambda raw:bytes_seen.append(raw))
        with self.assertRaisesRegex(DeepSeekFlashError,"NETWORK_OR_TIMEOUT"):
            self.call(model)
        self.assertEqual(bytes_seen,[])
        self.assertEqual(model.budget.calls_reserved,1)

    def test_private_sink_failure_propagates_no_second_call(self):
        calls=[0]
        def unavailable(raw):
            calls[0]+=1
            raise RuntimeError("PRIVATE_R2_NOT_WRITABLE_STOP")
        transport=FakeTransport()
        b=FlashBudget(max_calls=1,max_reserved_output_tokens=950)
        model=DeepSeekFlashModel(
            api_key=DUMMY_KEY,budget=b,transport=transport,
            on_response_wire=unavailable)
        with self.assertRaisesRegex(RuntimeError,"PRIVATE_R2_NOT_WRITABLE_STOP"):
            self.call(model)
        self.assertEqual(calls,[1])
        self.assertEqual(len(transport.received),1)
        self.assertEqual(b.calls_reserved,1)

    def test_original_without_sink_keeps_old_api_behavior(self):
        raw=wire(content='{"status":"accepted"}')
        model,transport,seen=self.request(raw,with_sink=False)
        result=self.call(model)
        self.assertEqual(result["status"],"accepted")
        self.assertEqual(seen,[])
        self.assertEqual(len(transport.received),1)


if __name__=="__main__":
    unittest.main()
