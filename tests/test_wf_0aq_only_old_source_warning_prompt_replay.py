"""0.AQ immutable old novelist answer under exactly one WF guide correction.

The saved writer's T04 and timing-response prompts (original 0.AO #7,#8)
differ from today's G prompts only by the unverified-parent source warning.
This test never asks a model to regenerate them. A changed literary task,
changed quote, changed budget or extra text is a source error, not a new
"equivalent" answer. Real 8-wire hashes are separately verified by 0.AP/0.AQ.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from experiments import wf_0aq_resume_eight_real_writer_turns_then_new_once_20261026 as e


@dataclass
class Packet:
    prompt: str


class SingleBoundedPromptException(TestCase):
    def make(self,index):
        old="【已有的角色行为】"+e.OLD_REVIEW_GUIDANCE+"【真正要写的动作目标】"
        new=old.replace(e.OLD_REVIEW_GUIDANCE,e.NEW_REVIEW_GUIDANCE)
        events=[]
        for n in range(8):
            prompt=(old if n in (6,7) else
                    "这一段旧情节来自实际作家写作，人物动作和消息时间都保持不变。"*3+str(n))
            events.append(("真实模型先前写好的JSON回答"+str(n),
                          {"prompt_sha256":e.h(prompt),
                           "max_completion_tokens_reserved":600},
                          {"prompt":prompt}))
        temporary=TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        sandbox=Path(temporary.name)/"isolated-model-test-only"
        with patch.object(e,"DeepSeekFlashModel") as m:
            obj=e.RealPaidHistoryThenWriter(
                "旧章节实际计划JSON",{
                    "prompt_sha256":e.h("旧章节计划的同一题"),
                    "max_completion_tokens_reserved":650},
                events,"offline-fake-key-without-network",
                output_root=sandbox)
        obj.replayed=index
        return obj,old,new,m

    def test_six_earlier_calls_must_be_same_prompt_and_token_budget(self):
        obj,_,__,provider=self.make(1)
        previous=obj.old_eight[0][2]["prompt"]
        result=obj.ask(Packet(previous),model="deepseek-flash",
                       api_base="irrelevant",max_tokens=600)
        self.assertTrue(result.endswith("0"))
        self.assertTrue(obj.prompt_comparisons[-1]["same_prompt_and_budget"])
        self.assertEqual(obj.budget.calls_reserved,0)
        provider.return_value.ask_json.assert_not_called()
        with self.assertRaisesRegex(RuntimeError,
                                    "WF0AQ_UNEXPECTED_OLD_AUTHOR_PROMPT_DRIFT"):
            obj.ask(Packet("人物行为已经发生了一个改变，但文学目标和消息时间被额外附加了未授权的解释。"*3),
                    model="deepseek-flash",api_base="irrelevant",
                    max_tokens=600)

    def test_only_seventh_and_eighth_source_warning_may_differ(self):
        obj,old,new,provider=self.make(7)
        value=obj.ask(Packet(new),model="deepseek-flash",
                      api_base="irrelevant",max_tokens=600)
        self.assertEqual(value,"真实模型先前写好的JSON回答6")
        receipt=obj.prompt_comparisons[-1]
        self.assertFalse(receipt["same_prompt_and_budget"])
        self.assertTrue(receipt["only_wf_source_warning_changed"])
        self.assertTrue(receipt["old_writer_answer_cannot_prove_new_guidance_followed"])
        self.assertEqual(obj.budget.calls_reserved,0)
        provider.return_value.ask_json.assert_not_called()

        for invalid in (
            new+"追加了人物已经知道秘密",
            new.replace("来源/因果引句被拒绝","来源引句已证明"),
        ):
            candidate,_,__,provider=self.make(7)
            with self.assertRaisesRegex(
                RuntimeError,"WF0AQ_SOURCE_WARNING_ONLY_PROMPT_DRIFT_NOT_EXACT"):
                candidate.ask(Packet(invalid),model="deepseek-flash",
                              api_base="irrelevant",max_tokens=600)
            provider.return_value.ask_json.assert_not_called()
        obj2,_,__,provider=self.make(8)
        self.assertTrue(obj2.ask(Packet(new),model="deepseek-flash",
                                 api_base="irrelevant",max_tokens=600).endswith("7"))
        provider.return_value.ask_json.assert_not_called()

    def test_mocked_source_mismatch_never_poisons_real_live_output(self):
        # Regression for Actions 40263390051: earlier test runs wrote
        # mocked old/new prompts into the real one-shot output directory.
        # The live job then correctly refused to overwrite that directory
        # before any paid writer call. Keep the guard; fix test isolation.
        self.assertFalse(e.OUT.exists())
        obj,old,new,provider=self.make(7)
        with self.assertRaisesRegex(
                RuntimeError,"WF0AQ_SOURCE_WARNING_ONLY_PROMPT_DRIFT_NOT_EXACT"):
            obj.ask(Packet(new+"错误扩展原作家对主帅的已知信息"),
                    model="deepseek-flash",api_base="irrelevant",
                    max_tokens=600)
        stored=obj.output_root/"original-vs-current-prompts"/"07.json"
        self.assertTrue(stored.is_file())
        self.assertFalse(e.OUT.exists())
        provider.return_value.ask_json.assert_not_called()

    def test_source_warning_only_cannot_hide_revised_author_budget(self):
        obj,_,new,provider=self.make(7)
        with self.assertRaisesRegex(
            RuntimeError,"WF0AQ_SOURCE_WARNING_ONLY_PROMPT_DRIFT_NOT_EXACT"):
            obj.ask(Packet(new),model="deepseek-flash",
                    api_base="irrelevant",max_tokens=601)
        provider.return_value.ask_json.assert_not_called()


if __name__=="__main__":
    import unittest
    unittest.main()
