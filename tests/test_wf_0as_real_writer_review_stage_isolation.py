"""0.AS: real writer self-review must be an independent AUTHOR decision task.

0.AQ original DeepSeek Flash run 40264287305 preserved six true responses.
Four of six returned another {"prose","trace"} instead of review decision,
while two chose MOVE_ON. Provenance SHA of those original responses:
01 c6bab8b37c16a4fe33789b2db5f70e24f0126d604e0eee22a812fe4fd9dda663
02 c2ce29bd95563b32a820f63944bbbfdf6916a7952178da1c27501acfcf0f57c8
05 b54a5878573b839713499e9600c15b11a13a3ba54b326f5acd1a030ec899d116
06 babc87004ca1aea82acc29bb95c88394f6b95de075e56d209b5899d5619c9df7

The previous WF "review" prompt actually started with "write novel prose"
and a conflicting JSON {prose,trace} schema. No host literary judgment.
Fixtures below NEVER claim their prose comes from a new real model call.
"""
from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from writerforge.writing_assist import _ai_decides_when_to_revisit
from writerforge.verified_flow import GroundedDraftPacket
from test_v96_causal_turns import (
    prose1,prose2,ACTION2,EFFECT2,EFFECT1,turns,response,
)
from test_wf_ai_writer_previous_turn_rewind import moment


def digest(src):
    return sha256(src.encode("utf8")).hexdigest()


class IndependentAuthorReviewStage(TestCase):
    def setUp(self):
        self.folder=TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.root=Path(self.folder.name)
        self.real_prose=prose2()
        self.prior_prose=prose1()
        self.raw=response(self.real_prose,ACTION2,EFFECT2,EFFECT1)
        self.beat=turns()["turns"][1]
        self.WRITER_PROMPT=(
            "【小说正文生成任务】请创作原创小说正文。请先根据六事件规划续写，"
            "只返回严格 JSON {\"prose\":\"新的原创故事\","
            "\"trace\":{\"action_quote\":null,\"effect_quote\":null,"
            "\"parent_effect_quote\":null}}。"
            "不得返回审稿判断；优先续写场景中的道具。"
        )
        self.packet=GroundedDraftPacket(
            scene_id="wf-as-stage-separation-source",
            project_id="wf-as-stage-separation-project",
            snapshot_id=1,evidence=(),craft_ids=(),
            prompt=self.WRITER_PROMPT,
            prompt_sha256=digest(self.WRITER_PROMPT))

    def run_author(self,model_result,*,prior=True,contract="model_sha"):
        queries=[]
        def ask_model(packet,*,model,api_base,max_tokens):
            queries.append(packet.prompt)
            self.assertEqual(packet.prompt_sha256,digest(packet.prompt))
            self.assertTrue(packet.prompt.startswith(
                "【WriterForge 独立写后审稿阶段 / ONLY_REVIEW_DECISION】"))
            self.assertNotIn("【小说正文生成任务】",packet.prompt)
            self.assertNotIn("只返回严格 JSON {\"prose\"",packet.prompt)
            self.assertNotIn("优先续写场景中的道具",packet.prompt)
            self.assertIn(self.real_prose,packet.prompt)
            self.assertIn(digest(self.real_prose),packet.prompt)
            self.assertIn("decision(MOVE_ON 或 LOOK_BACK_NOW)",packet.prompt)
            return model_result
        accepted=({"prose":self.prior_prose,
                   "effect_quote":EFFECT1},) if prior else ()
        decision=_ai_decides_when_to_revisit(
            raw=self.raw,beat=self.beat,
            accepted=accepted,turn_packet=self.packet,
            ask_model=ask_model,directory=self.root/
                ("review-"+str(len(list(self.root.iterdir())))),
            source_identity_contract=contract)
        self.assertEqual(len(queries),1)
        self.assertTrue(
            decision["receipt"]["review_prompt_stage_isolated_from_prose_generation"])
        self.assertTrue(
            decision["receipt"]["review_writer_source_prose_unchanged"])
        self.assertTrue(
            decision["receipt"]["review_writer_not_forced_to_revise"])
        self.assertEqual(
            decision["receipt"]["review_prompt_sha256"],digest(queries[0]))
        return decision,queries[0]

    def test_author_may_keep_without_host_coercion_or_literary_grade(self):
        original=moment("MOVE_ON",self.real_prose)
        result,prompt=self.run_author(original)
        self.assertEqual(result["decision"],"MOVE_ON")
        self.assertEqual(result["reason"],json.loads(original)["why_now"])
        self.assertFalse(result["receipt"]["literary_quality_verified"])
        self.assertEqual(result["receipt"]["no_canon_writes"],True)
        self.assertIn(self.prior_prose,prompt)
        self.assertIn(digest(self.prior_prose),prompt)

    def test_previous_source_choice_and_evidence_remain_model_owned(self):
        quote="黄昏最后一点天光落到桥头时，"
        author=moment("LOOK_BACK_NOW",self.prior_prose,
                      target="previous",quote=quote)
        result,prompt=self.run_author(author)
        self.assertEqual(result["decision"],"LOOK_BACK_NOW")
        self.assertEqual(result["target_turn"],"previous")
        self.assertEqual(result["target_prose_sha256"],
                         digest(self.prior_prose))
        self.assertEqual(result["source_quote"],quote)

    def test_real_old_prose_echo_is_not_relabelled_as_a_review_decision(self):
        old_echo=self.raw
        result,prompt=self.run_author(old_echo)
        self.assertEqual(result["decision"],"INVALID_SIGNAL")
        self.assertEqual(
            result["receipt"]["failure_code"],"WF_AI_WRITER_SIGNAL_SCHEMA_OR_SOURCE")
        self.assertTrue(any(self.root.rglob("ai-when-and-why-original.json")))
        self.assertFalse(result["receipt"]["literary_quality_verified"])
        self.assertNotIn("当前文本应该删除",prompt)

    def test_wrong_sha_does_not_become_valid_even_in_isolated_stage(self):
        wrong=json.loads(moment("MOVE_ON",self.real_prose))
        wrong["source_sha256"]="0"*64
        result,_=self.run_author(json.dumps(wrong,ensure_ascii=False))
        self.assertEqual(result["decision"],"INVALID_SIGNAL")

    def test_opt_in_null_current_sha_does_not_change_artistic_choice(self):
        author=json.loads(moment("MOVE_ON",self.real_prose))
        author["source_sha256"]=None
        result,_=self.run_author(json.dumps(author,ensure_ascii=False),
                                 contract="bind_null_current")
        self.assertEqual(result["decision"],"MOVE_ON")
        self.assertTrue(result["receipt"]["null_source_sha256_bound_from_current_source"])


if __name__=="__main__":
    import unittest
    unittest.main()
