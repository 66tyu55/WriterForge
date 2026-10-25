"""Genuine-opera follow-up guard rails without author-model or fiction calls.

Cross-source report is a MODEL hypothesis, only exact source quotes are
verified by WF. Deterministic source SHA binding for missing current-source
identity must never reinterpret the literary choice, silently rewrite
previous prose, or elevate item-movement guesses into saved story truth.
"""
import os
import json
from tempfile import TemporaryDirectory
from pathlib import Path
import unittest
from unittest import TestCase
from unittest.mock import patch

from writerforge.verified_flow import GroundedDraftPacket,WritingExecutionError
from writerforge.writing_assist import (
    _reader_separates_written_and_inferred,
    _ai_decides_when_to_revisit,
)
from experiments import wf_real_opera_cross_source_reader_followup_20261025 as exp
from experiments.wf_real_opera_source_sha_replay_20261025 import (
    ORIGINAL_SOURCE_SHA
)
from test_wf_ai_writer_chooses_when_and_why import digest

SEED=exp.SEED
SOURCE=(
    "鼓声第三下敲完，江遥把后背抵在廊柱上，左踝一阵一阵地跳疼。"
    "她咬了咬牙，不去想打鼓的是谁，眼下更要紧的是后台那口旧箱子，"
    "票据还压在箱底一件戏服底下，今夜不取出来就未必有机会了。"
    "她扶着廊壁往南挪，脚下尽量放轻。"
    "宋易仍在后门听着声音，并不知道那张票据的真正来历。"
)
OLD_QUOTE="衣袖里藏着一张尚未交出去的赎身票据。"
NEW_QUOTE="票据还压在箱底一件戏服底下"
assert SEED.count(OLD_QUOTE)==1 and SOURCE.count(NEW_QUOTE)==1


def raw_original():
    return json.dumps({
        "prose":SOURCE,
        "trace":{"action_quote":None,"effect_quote":None,
                 "parent_effect_quote":None}},ensure_ascii=False)


def packet():
    text="写作 AI 拥有所有小说修改权；工作台只能核验真实来源。"
    return GroundedDraftPacket(
        project_id="source-genuine-case",
        scene_id="opera-reader-source",
        snapshot_id=1,evidence=(),craft_ids=(),
        prompt=text,prompt_sha256=digest(text))


def reader_answer(*,wrong_quote=False):
    return json.dumps({
        "observed":[],"inferred_links":[],
        "cross_source_links":[{
            "previous_quote":OLD_QUOTE,
            "current_quote":(
                "完全没有存在于当前正文的虚构位置来源"
                if wrong_quote else NEW_QUOTE),
            "reader_imagined_step":(
                "读者需要推测票据如何从旧原文描述的位置"
                "出现在新章节的另一地点，叙述中暂时没有写明转换。"),
        }],
        "reader_uncertainty":"我不知道是否存在省略的动作，此处只是读者推测。",
    },ensure_ascii=False)


class CrossSourceNovelEvidence(unittest.TestCase):
    def test_verified_source_only_reader_does_not_label_creative_error(self):
        with TemporaryDirectory() as tmp:
            seen=[]
            def fake(packet,*,model,api_base,max_tokens):
                self.assertEqual(max_tokens,1000)
                seen.append(packet.prompt)
                return reader_answer()
            report=_reader_separates_written_and_inferred(
                raw=raw_original(),turn_packet=packet(),
                ask_model=fake,directory=Path(tmp)/"reader",
                earlier_source=SEED,earlier_source_sha256=digest(SEED))
            self.assertEqual(report["status"],
                             "SOURCE_ANCHORED_READER_HYPOTHESES")
            self.assertEqual(len(report["report"]["cross_source_links"]),1)
            link=report["report"]["cross_source_links"][0]
            self.assertEqual(link["previous_quote"],OLD_QUOTE)
            self.assertEqual(link["current_quote"],NEW_QUOTE)
            self.assertEqual(link["earlier_original_source_offset"],
                             SEED.index(OLD_QUOTE))
            self.assertEqual(link["current_source_offset"],
                             SOURCE.index(NEW_QUOTE))
            self.assertTrue(link["inference_not_an_accepted_change"])
            self.assertTrue(report["report"]["no_host_literary_error_decision"])
            self.assertEqual(report["receipt"]["cross_source_inference_count"],1)
            self.assertIn(SEED,seen[0])
            self.assertIn(SOURCE,seen[0])
            self.assertNotIn("票据位置错误",seen[0])
            self.assertNotIn("必须删掉",seen[0])

    def test_model_can_still_keep_and_original_SHA_is_bound_without_wrong_claim(self):
        with TemporaryDirectory() as tmp:
            reader=_reader_separates_written_and_inferred(
                raw=raw_original(),turn_packet=packet(),
                ask_model=lambda *a,**k:reader_answer(),
                directory=Path(tmp)/"reader",
                earlier_source=SEED,earlier_source_sha256=digest(SEED))
            raw=json.dumps({
                "type":"json_object",
                "decision":"MOVE_ON","target_turn":"current",
                "source_sha256":None,"evidence_quote":None,
                "focus":None,
                "why_now":"我认为保留这一段的犹豫会更符合人物心理，原文已有可理解的选择，不必强制回改。",
                "what_goes_wrong_if_unchanged":None,
                "intended_reader_effect":None},ensure_ascii=False)
            seen=[]
            def author(p,*,model,api_base,max_tokens):
                self.assertEqual(max_tokens,600)
                seen.append(p.prompt)
                return raw
            beat={"id":"t01","kind":"quiet",
                  "actor":"江遥",
                  "goal":"江遥仍可以自主决定是否保持现有的故事留白",
                  "causal_parent":None,"craft_focus":[]}
            result=_ai_decides_when_to_revisit(
                raw=raw_original(),beat=beat,accepted=(),
                turn_packet=packet(),ask_model=author,
                directory=Path(tmp)/"author",
                reader_report=reader["report"],
                source_identity_contract="bind_null_current")
            self.assertEqual(result["decision"],"MOVE_ON")
            self.assertEqual(result["target_prose_sha256"],digest(SOURCE))
            self.assertTrue(result["receipt"]["null_source_sha256_bound_from_current_source"])
            self.assertTrue(result["receipt"]["unverified_reader_input_delivered"])
            self.assertEqual(result["receipt"][
                "cross_source_reader_hypotheses_unverified_count"],1)
            self.assertTrue(result["receipt"][
                "author_kept_unresolved_cross_source_hypotheses"])
            self.assertTrue(result["receipt"]["reader_hypotheses_not_source_facts"])
            self.assertTrue(result["receipt"][
                "cross_source_reader_review_did_not_confirm_fact"])
            self.assertIn(OLD_QUOTE,seen[0])
            self.assertIn(NEW_QUOTE,seen[0])
            self.assertIsNone(json.loads(raw)["source_sha256"])
            self.assertFalse(result["receipt"]["literary_quality_verified"])

    def test_fake_old_source_hash_and_forged_current_quote_are_not_reader_facts(self):
        with TemporaryDirectory() as tmp:
            model=[]
            def writer(*args,**kwargs):
                model.append(1)
                return reader_answer()
            with self.assertRaisesRegex(
                    WritingExecutionError,"WF_READER_EARLIER_SOURCE_HASH_OR_BOUNDS"):
                _reader_separates_written_and_inferred(
                    raw=raw_original(),turn_packet=packet(),
                    ask_model=writer,directory=Path(tmp)/"bad-hash",
                    earlier_source=SEED,
                    earlier_source_sha256="0"*64)
            self.assertEqual(model,[])
            result=_reader_separates_written_and_inferred(
                raw=raw_original(),turn_packet=packet(),
                ask_model=lambda *a,**k:reader_answer(wrong_quote=True),
                directory=Path(tmp)/"bad-quote",
                earlier_source=SEED,earlier_source_sha256=digest(SEED))
            self.assertEqual(result["status"],"INVALID_READER_SOURCE")
            self.assertIsNone(result["report"])
            self.assertEqual(result["receipt"]["reason_code"],
                             "WF_READER_CROSS_SOURCE_QUOTE_NOT_EXACT")


class RealFollowupProviderLimits(TestCase):
    def test_actual_provider_stages_and_budget_are_unchanged_by_model_response(self):
        self.assertEqual(exp.MAX_CALLS,3)
        self.assertEqual(exp.TOTAL_BUDGET,3400)
        self.assertEqual(list(exp.TOKENS),
                         ["CROSS_SOURCE_READER",
                          "ORIGINAL_AUTHOR_DECIDES",
                          "V119_AUTHOR_ONLY_IF_LOOK_BACK"])
        class FakeDeepSeek:
            def __init__(self,*,api_key,budget,timeout_seconds,
                         on_response_wire):
                self.events=[]
                self.on_response_wire=on_response_wire
            def ask_json(self,*,role,system,user,max_tokens):
                self.events.append(max_tokens)
                self.on_response_wire(b'{"choices":[{"finish_reason":"stop"}]}')
                return {"type":"json_object","decision":"MOVE_ON"}
        with TemporaryDirectory() as tmp,patch.dict(
                os.environ,{"DEEPSEEK_API_KEY":"nonreal-test-key-12345"}),patch.object(
                exp,"DeepSeekFlashModel",FakeDeepSeek):
            model=exp.RealOriginalWriter(Path(tmp))
            for size in (1000,600,1800):
                response=model.ask(packet(),model=None,api_base=None,
                                   max_tokens=size)
                self.assertIn("MOVE_ON",response)
            self.assertEqual(len(model.events),3)
            self.assertTrue(all(e["original_provider_wire_preserved_before_parse"]
                                for e in model.events))
            with self.assertRaisesRegex(
                    RuntimeError,"WF_OPERA_CROSS_SOURCE_BUDGET_OR_ORDER"):
                model.ask(packet(),model=None,api_base=None,max_tokens=600)
