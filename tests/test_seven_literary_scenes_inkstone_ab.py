"""Zero-provider protocol checks before the real InkStone writing batch."""
import json
import unittest
from unittest.mock import patch

from experiments.seven_literary_scenes_inkstone_ab import (
    scenarios,make_packet,diagnose,sha,GENRES,stream_chat,
    FREE_CANDIDATES,MAX_COMPLETIONS,MAX_PROBES,
)


class SevenScenarioBatchProtocolTests(unittest.TestCase):
    def test_fixed_seven_distinct_chinese_categories(self):
        data=scenarios()
        self.assertEqual(tuple(c["genre"] for c in data),GENRES)
        self.assertEqual(len({c["id"] for c in data}),7)
        self.assertEqual(len(data),7)
        self.assertTrue(all(len(c["seed"])>=60 for c in data))
        self.assertEqual(MAX_COMPLETIONS,14)
        self.assertEqual(MAX_PROBES,3)
        self.assertEqual(FREE_CANDIDATES[:2],
                         ("intern-s2","Atria-Dawn-Preview"))

    def test_prompts_are_actual_wf_guarded_packets_and_share_origin(self):
        for case in scenarios():
            with self.subTest(category=case["genre"]):
                bare,guided,temporal,graph,receipt=make_packet(case)
                self.assertIn(case["seed"],bare)
                self.assertIn(case["seed"],guided)
                self.assertIn(case["goal"],bare)
                self.assertIn(case["goal"],guided)
                self.assertIn("原创",guided)
                self.assertIn("【本章当前事件】",guided)
                self.assertTrue(receipt["wf_prompt_verified_hard_context"])
                self.assertNotEqual(sha(bare),sha(guided))
                self.assertEqual(graph["chapter_index"],1)
                self.assertEqual(graph["model_calls"],0)
                self.assertEqual(graph["canon_writes"],0)
                self.assertLessEqual(len(guided),10000)
                self.assertEqual(
                    receipt["bare_prompt_sha256"],sha(bare))
                self.assertEqual(
                    receipt["wf_prompt_sha256"],sha(guided))
                self.assertEqual(
                    temporal["reducer_result"]["model_calls"],0
                    if "model_calls" in temporal["reducer_result"]
                    else 0)

    def test_fake_real_sse_transport_collects_visible_prose_only(self):
        class Stream:
            def __init__(self,finish="stop",done=True):
                self.finish=finish
                self.done=done
            def __enter__(self):
                return self
            def __exit__(self,*args):
                pass
            def __iter__(self):
                chunks=[
                    {"choices":[{"delta":{"reasoning_content":"隐含推理",
                                           "content":None},
                                 "finish_reason":None}]},
                    {"choices":[{"delta":{"content":"沈砚向前走去。"},
                                 "finish_reason":None}]},
                    {"choices":[{"delta":{"content":"风停了。"},
                                 "finish_reason":self.finish}]},
                    {"choices":[],"usage":{
                        "prompt_tokens":22,"completion_tokens":100,
                        "total_tokens":122}},
                ]
                raw=[("data: "+json.dumps(z,ensure_ascii=False)+"\n\n"
                      ).encode() for z in chunks]
                if self.done:
                    raw.append(b"data: [DONE]\n\n")
                return iter(raw)
        class FakeOpener:
            def __init__(self,finish="stop",done=True):
                self.finish=finish
                self.done=done
            def open(self,request,timeout):
                self.url=request.full_url
                payload=json.loads(request.data)
                assert payload["stream"] is True
                assert payload["stream_options"]=={"include_usage":True}
                assert timeout>120
                return Stream(self.finish,self.done)
        with patch(
            "experiments.seven_literary_scenes_inkstone_ab.build_opener",
            return_value=FakeOpener()):
            got=stream_chat("synthetic-test-token","Atria-Dawn-Preview",
                            "请写正文",3100)
        self.assertTrue(got["ok"],got)
        self.assertEqual(got["text"],"沈砚向前走去。风停了。")
        self.assertEqual(got["reasoning_characters"],len("隐含推理"))
        self.assertEqual(got["usage"]["total_tokens"],122)
        self.assertTrue(got["done_seen"])
        self.assertEqual(got["finish_reason"],"stop")
        with patch(
            "experiments.seven_literary_scenes_inkstone_ab.build_opener",
            return_value=FakeOpener(finish="length")):
            truncated=stream_chat("synthetic-test-token",
                                  "Atria-Dawn-Preview","请写正文",3100)
        self.assertFalse(truncated["ok"])
        self.assertEqual(truncated["kind"],"FINISH_length")
        self.assertEqual(truncated["text"],"")
        self.assertIn("沈砚",truncated["partial_text"])
        with patch(
            "experiments.seven_literary_scenes_inkstone_ab.build_opener",
            return_value=FakeOpener(done=False)):
            interrupted=stream_chat("synthetic-test-token",
                                    "Atria-Dawn-Preview","请写正文",3100)
        self.assertFalse(interrupted["ok"])
        self.assertEqual(interrupted["kind"],"STREAM_UNFINISHED")

    def test_synthetic_body_receipts_never_claim_human_judgment(self):
        for case in scenarios():
            _,_,source,graph,_=make_packet(case)
            result=diagnose(
                case,"沈砚望着门外的旧雨，没有贸然行动。"*28,
                source,graph,variant="bare",usage={},
                finish_reason="stop")
            self.assertFalse(result["literary_quality_blind_judged"])
            self.assertTrue(result["prose_in_saved_private_artifact"])
            self.assertTrue(result["output_sha256"])
            self.assertIn("source_mechanics_clean",result)


if __name__=="__main__":
    unittest.main()
