"""0.AL RED: the REAL 0.AJ DeepSeek SciFi WF-author wire has ONE fullwidth
JSON field separator outside its valid authored prose string.

Source: Actions #40205342567 provider-originals/scifi_airlock_WF-author.json
raw provider SHA256 61b61ec1c651735e07a01df91b2836d859d98d6dcc397879ef3118afd8755548.
The source is genuine and unmodified. This is an interface repair, not
regenerating literature, rewriting prose or asserting literary causality.
"""
from __future__ import annotations
from hashlib import sha256
import json
import unittest

from writerforge.deepseek_flash_model import DeepSeekFlashModel,FlashBudget,DeepSeekFlashError
from writerforge.v96_causal_turns import check_turn

REAL_PROSE=(
    "唐弦把手掌从舱门观察窗上移开。玻璃内侧的薄霜被体温化出一小块清晰，外面仍是深黑的通道，压力表的红针停在低压侧，纹丝不动。"
    "\n\n“后舱，读到我的声音没有？”他对着头戴送话器说。"
    "\n\n三秒后，喇叭里才响起小林的回答：“读到——你那边舱门怎么样？”延迟是单向三秒，他早算过，但真正等的时候，三秒比想象长。"
    "\n\n“门没动，我这边没有机械卡死的迹象。”他侧耳贴住门框，只能听到自己呼吸在金属里的回响，风一样的声音一点也没有。远处林薇从对讲机那头插话，她的通道要绕中继，回音迟了将近七秒：“我这边读数和你对不上，别急着开。”"
    "\n\n他不知道锁扣后是卡死了还是压差了。两个读数都可能是对的，也可能有一个坏了。他没钱修，也没有别的仪器。“小林，你再报一遍你的表盘。”他说。只有再听一遍，他才能知道该信谁的一半。"
)
REAL_TRACE={
    "action_quote":"“小林，你再报一遍你的表盘。”他说。",
    "effect_quote":None,
    "parent_effect_quote":None,
}
PROSE_SHA="713534247a7071accb8852ee5e72133d3420ceeaabecf92cf1a542d5626edf35"
CONTENT_SHA="bab2b02e7afe6084febf2ca51088ac873887683faa4c5b340152a7b4e9e705a6"


def original_content():
    return (
        '{"prose":'+json.dumps(REAL_PROSE,ensure_ascii=False)
        +'，"trace":'+json.dumps(REAL_TRACE,ensure_ascii=False,
                                  separators=(",",":"))+"}"
    )


def fake_provider(content):
    return json.dumps({
        "id":"test-real-source-envelope",
        "model":"deepseek-flash",
        "choices":[{
            "index":0,"finish_reason":"stop",
            "message":{"role":"assistant","content":content}}],
        "usage":{"prompt_tokens":1,"completion_tokens":400},
    },ensure_ascii=False,separators=(",",":")).encode("utf8")


def ask(content,role="self_scene_writing"):
    wire=fake_provider(content)
    saved=[]
    adapter=DeepSeekFlashModel(
        api_key="synthetic-test-key-16characters",
        budget=FlashBudget(max_calls=1,max_reserved_output_tokens=1000),
        transport=lambda request:wire,
        timeout_seconds=2,
        on_response_wire=lambda raw:saved.append(raw),
    )
    result=adapter.ask_json(
        role=role,
        system="你正在用原始字节来源核验中文小说 JSON，绝不补写文学正文。",
        user="仅检查原作者返回的完整 JSON 结构。",
        max_tokens=500)
    return result,adapter.last_response_format_recovery,saved,wire


class OriginalFullwidthTopLevelSeparator(unittest.TestCase):
    def test_real_recovered_fullwidth_separator_and_zero_changed_prose(self):
        content=original_content()
        self.assertEqual(len(REAL_PROSE),342)
        self.assertEqual(sha256(REAL_PROSE.encode()).hexdigest(),PROSE_SHA)
        self.assertEqual(sha256(content.encode()).hexdigest(),CONTENT_SHA)
        output,receipt,preserved,provider_wire=ask(content)
        self.assertEqual(output["prose"],REAL_PROSE)
        self.assertEqual(output["trace"],REAL_TRACE)
        self.assertEqual(len(preserved),1)
        self.assertEqual(preserved[0],provider_wire)
        self.assertEqual(receipt["original_content_sha256"],CONTENT_SHA)
        self.assertEqual(receipt["original_prose_sha256"],PROSE_SHA)
        self.assertTrue(receipt["single_external_separator_only"])
        self.assertTrue(receipt["original_prose_unchanged"])
        self.assertTrue(receipt["original_provider_wire_preserved"])
        self.assertTrue(receipt["trace_still_requires_wf_source_validation"])
        self.assertEqual(receipt["extra_model_calls"],0)

        beat={
            "id":"t01","kind":"decision","actor":"唐弦",
            "goal":"以舱门压差和通讯延迟决定下一步动作，不宣布未知结果",
            "causal_parent":None,"craft_focus":[],
        }
        checked=check_turn(json.dumps(output,ensure_ascii=False),
                           beat,mode="causal_guard",
                           max_prose_chars=1024)
        self.assertEqual(checked["prose"],REAL_PROSE)
        self.assertIsNone(checked["effect_quote"])
        self.assertTrue(checked["receipt"]["outcome_pending_source_only"])
        self.assertFalse(checked["receipt"]["causal_relation_verified"])
        self.assertFalse(checked["receipt"]["eligible_for_factjournal_KNOWN"])

    def test_wide_comma_inside_valid_story_is_never_changed(self):
        prose="她说：“我有一件事，明天再谈。”屋里人都还没有作答。"*3
        doc=json.dumps({"prose":prose,"trace":REAL_TRACE},ensure_ascii=False)
        output,receipt,_,_=ask(doc)
        self.assertEqual(output["prose"],prose)
        self.assertIsNone(receipt)

    def test_do_not_guess_other_syntax_corruptions_or_provider_roles(self):
        malformed=[
            original_content().replace('，"trace":','，"tracé":',1),
            original_content().replace('，"trace":','，"trace":null,',1),
            original_content().replace('，"trace":','，，"trace":',1),
            original_content().replace('，"trace":','，"trace":{"action_quote":null}',1),
        ]
        for doc in malformed:
            with self.subTest(doc=doc[-30:]):
                with self.assertRaises(DeepSeekFlashError):
                    ask(doc)
        with self.assertRaises(DeepSeekFlashError):
            ask(original_content(),role="craft_analysis")


if __name__=="__main__":
    unittest.main()
