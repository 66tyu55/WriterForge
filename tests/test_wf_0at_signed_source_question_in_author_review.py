"""0.AT genuine G improvement: source-first author choice, not auto-criticism.

A real 0.AQ six-turn DeepSeek chapter wrote a booklet being carried away,
then possibly the same geography booklet being sealed by its old holder.
V114/V122 now carries this uncertainty with literal provider source anchors.
The original writer must SEE those quoted sources at the self-review moment
and decide autonomously, including a legal MOVE_ON/intentional ellipsis.
Do not turn these claims into known holder cells or host literary grades.
"""
from __future__ import annotations

from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
import json

from writerforge.writing_assist import (
    _signed_previous_author_source_question,
    _ai_decides_when_to_revisit,
)
from writerforge.verified_flow import GroundedDraftPacket,WritingExecutionError
from writerforge.v114_external_story_state import (
    external_temporal_step,temporal_prompt,
)
from test_wf_0ar_real_document_custody_source import (
    OUTGOING,REAPPEARING,RETURNED,DIFFERENT,QUIET,
)
from test_wf_ai_writer_previous_turn_rewind import moment


def digest(s):
    return sha256(s.encode("utf8")).hexdigest()


AFTER=(
    "门外残雪已暗，秦渊仍不敢断言主帅读了几封旧信。"
    "他举灯看了看那张按站换马的纸，城门钟声从深巷传来。"
    "笔下那些没有来源的数目仍空着，他没有借着回忆编造敌情。"
    "他指了指案边未封好的新纸，吩咐守夜人暂且不动，"
    "等实际能传回的消息到了再做决定。"
)
PREVIOUS=REAPPEARING+QUIET


class SignedContinuityQuestionForSameAuthor(TestCase):
    def make_checkpoint(self,*,return_seen=False,different=False):
        old=external_temporal_step(OUTGOING,cast=("秦渊","周卒"))
        if return_seen:
            old=external_temporal_step(RETURNED,cast=("秦渊","周卒"),prior=old)
        prose=DIFFERENT+QUIET if different else PREVIOUS
        now=external_temporal_step(prose,cast=("秦渊","周卒"),prior=old)
        return now,prose

    def test_signed_original_two_quotes_actually_reach_separate_review(self):
        signed,earlier=self.make_checkpoint()
        text,origin=_signed_previous_author_source_question(
            signed,({"prose":earlier},))
        self.assertIn("周卒把册子揣进贴身的油布囊",text)
        self.assertIn("地形册子一并纳入",text)
        self.assertIn("可能是另一本",text)
        self.assertIn("你作为原作者判断",text)
        self.assertIn("也可以明确选择不改",text)
        self.assertEqual(origin,signed[
            "v122_physical_relation_source_receipt"]["receipt_sha256"])
        self.assertEqual(signed["canon_writes"],0)

        with TemporaryDirectory() as root:
            seen=[]
            packet=GroundedDraftPacket(
                scene_id="wf-0at-real-src",
                project_id="wf-0at-real-g",
                snapshot_id=1,evidence=(),craft_ids=(),
                prompt='【旧创作指令】只输出小说正文 JSON {"prose":...}',
                prompt_sha256=digest('【旧创作指令】只输出小说正文 JSON {"prose":...}'))
            def model(p,*,model,api_base,max_tokens):
                seen.append(p.prompt)
                return moment("MOVE_ON",AFTER)
            raw=json.dumps({
                "prose":AFTER,
                "trace":{"action_quote":None,"effect_quote":None,
                         "parent_effect_quote":None}},
                ensure_ascii=False)
            beat={"id":"t05","kind":"quiet","actor":"秦渊",
                  "goal":"先保持马蹄来路不明并审慎核对消息",
                  "causal_parent":"t04","craft_focus":[]}
            review=_ai_decides_when_to_revisit(
                raw=raw,beat=beat,
                accepted=({"prose":earlier},),
                turn_packet=packet,ask_model=model,
                source_checkpoint=signed,
                directory=Path(root)/"real-source-stage")
            self.assertEqual(review["decision"],"MOVE_ON")
            self.assertEqual(len(seen),1)
            self.assertNotIn("【旧创作指令】",seen[0])
            self.assertIn("周卒把册子揣进",seen[0])
            self.assertIn("与地形册子一并纳入",seen[0])
            self.assertTrue(review["receipt"][
                "signed_prior_document_source_question_delivered"])
            self.assertTrue(review["receipt"][
                "no_host_mandated_revision_from_source_question"])
            self.assertFalse(review["receipt"]["literary_quality_verified"])
            self.assertEqual(review["receipt"]["no_canon_writes"],True)

    def test_explicit_return_and_different_copy_do_not_manufacture_question(self):
        for var in ("return_seen","different"):
            k={var:True}
            cp,previous=self.make_checkpoint(**k)
            guidance,receipt=_signed_previous_author_source_question(
                cp,({"prose":previous},))
            self.assertEqual(guidance,"")
            self.assertIsNone(receipt)

    def test_signed_checkpoint_must_match_previous_literal_prose(self):
        checkpoint,_=self.make_checkpoint()
        with self.assertRaisesRegex(
                WritingExecutionError,"WF_WRITER_REVIEW_OLD_SOURCE_NOT_PREVIOUS_TURN"):
            _signed_previous_author_source_question(
                checkpoint,({"prose":AFTER},))

    def test_changed_source_receipt_is_rejected_before_author_model(self):
        checkpoint,previous=self.make_checkpoint()
        checkpoint["v122_physical_relation_source_receipt"][
            "document_custody_open_source_reviews"][0][
                "later_source_quote"]="原稿并没有这一句"
        with self.assertRaisesRegex(
                WritingExecutionError,"WF_WRITER_REVIEW_OLD_SOURCE_CHECKPOINT_NOT_SIGNED"):
            _signed_previous_author_source_question(
                checkpoint,({"prose":previous},))


if __name__=="__main__":
    import unittest
    unittest.main()
