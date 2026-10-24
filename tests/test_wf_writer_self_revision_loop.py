"""WF core writes, hesitates, deletes and rewrites its OWN drafts.

These tests are structural adversarial fixtures, NOT real model writing,
independent literary review, or training. They check V119 byte-accurate
edits, original rollback, G-only opt-in, bounded same-model attempts and
preservation of V96 causal quoted prose.
"""
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from test_v96_causal_turns import (
    ACTION1,EFFECT1,prose1,response,plan,
)
from writerforge.verified_flow import GroundedDraftPacket,WritingExecutionError
from writerforge.writing_assist import (
    _self_edit_one_turn,WriterDraftCancelled,
    AutonomousWriting,SELF_EDIT_MODEL_MAX_TOKENS,
    SELF_EDIT_MAX_PROVIDER_CALLS_PER_RUN,
)
from writerforge.v96_causal_turns import check_turn


def sha(src):
    return hashlib.sha256(src.encode("utf8")).hexdigest()


def advice(text,*,decision="KEEP",start=None,end=None,
           replacement=None,scope=None,trace=None,
           source_sha_override=None):
    edit=decision!="KEEP"
    return json.dumps({
        "decision":decision,
        "scope":scope if edit else None,
        "source_sha256":source_sha_override or sha(text),
        "start":start if edit else None,
        "end":end if edit else None,
        "expected_original":text[start:end] if edit else None,
        "replacement":replacement if edit else None,
        "trace":trace if edit else None,
        "reason":"原稿实际行动和后果已经可观察，此轮如有重复则局部处理。",
    },ensure_ascii=False,separators=(",",":"))


class WriterSelfCritiqueAndDiscard(TestCase):
    def setUp(self):
        self.tmp=TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.source=prose1()
        self.raw=response(self.source,ACTION1,EFFECT1)
        prompt="【前文必须继续】守桥人的告示已取下，少年尚未渡桥。"
        self.packet=GroundedDraftPacket(
            scene_id="test-self-writer-chapter-001",
            project_id="writerforge-synthetic-self",
            snapshot_id=1,evidence=(),craft_ids=(),
            prompt=prompt,prompt_sha256=sha(prompt))
        self.beat=plan()[0]
        self.provider_requests=0

    def execute(self,reply,rounds=1,*,directory="scratch",allowance=8,
                cancel_check=None):
        replies=[reply] if isinstance(reply,str) else list(reply)
        self.provider_requests=0
        def fake_model(packet,*,model,api_base,max_tokens):
            self.assertEqual(max_tokens,SELF_EDIT_MODEL_MAX_TOKENS)
            self.assertEqual(packet.project_id,self.packet.project_id)
            self.provider_requests+=1
            self.assertLessEqual(self.provider_requests,len(replies))
            return replies[self.provider_requests-1]
        return _self_edit_one_turn(
            raw=self.raw,beat=self.beat,accepted=(),
            project_id=self.packet.project_id,
            scene_id=self.packet.scene_id,
            turn_packet=self.packet,ask_model=fake_model,
            round_limit=rounds,call_allowance=allowance,
            directory=self.root/directory,
            cancel_check=cancel_check)

    def test_no_edit_if_writer_thinks_original_already_works(self):
        final,receipt=self.execute(advice(self.source))
        self.assertEqual(final,self.raw)
        self.assertEqual(self.provider_requests,1)
        self.assertEqual(receipt["model_calls"],1)
        self.assertEqual(receipt["rounds"][0]["status"],"KEEP_BY_WRITER")
        self.assertTrue((self.root/"scratch"/"first-original.md").exists())
        self.assertFalse(list((self.root/"scratch").glob("*discarded*")))
        self.assertFalse(receipt["literary_quality_verified"])

    def test_writer_can_delete_sentence_not_rewrite_unrelated_action(self):
        suffix="同伴问他是否反悔，他只是把地图重新摊在船板上。"
        self.assertIn(suffix,self.source)
        start=self.source.index(suffix)
        proposed=advice(self.source,decision="DELETE",scope="sentence",
                        start=start,end=start+len(suffix),
                        replacement="",trace={
                          "action_quote":ACTION1,
                          "effect_quote":EFFECT1,
                          "parent_effect_quote":None})
        final,r=self.execute(proposed)
        actual=json.loads(final)["prose"]
        self.assertNotIn(suffix,actual)
        self.assertTrue(actual.startswith(self.source[:start]))
        self.assertEqual(actual,self.source[:start])
        self.assertEqual(r["rounds"][0]["status"],"PROVISIONALLY_REVISED")
        self.assertEqual(
            check_turn(final,self.beat,mode="causal_guard")[
                "receipt"]["causal_check"],"EXACT_OBSERVABLE_ANCHORS_ONLY")
        self.assertEqual(
            (self.root/"scratch"/"round-01-discarded-draft.md").read_text("utf8"),
            self.source)
        self.assertEqual(
            (self.root/"scratch"/"round-01-selected-draft.md").read_text("utf8"),
            actual)
        self.assertFalse(r["all_revisions_are_unaccepted_candidates"] is False)

    def test_writer_can_rework_part_of_paragraph_and_keep_causal_links(self):
        original="黄昏最后一点天光落到桥头时，"
        start=self.source.index(original)
        correction="山间落起细雨时，"
        reply=advice(self.source,decision="REVISE",scope="paragraph",
                     start=start,end=start+len(original),
                     replacement=correction,trace={
                        "action_quote":ACTION1,"effect_quote":EFFECT1,
                        "parent_effect_quote":None})
        final,r=self.execute(reply)
        next_prose=json.loads(final)["prose"]
        self.assertIn(correction,next_prose)
        self.assertNotIn(original,next_prose)
        self.assertEqual(self.source[len(original):],
                         next_prose[len(correction):])
        self.assertEqual(r["model_calls"],1)

    def test_writer_can_abandon_whole_scene_for_genuine_new_scene(self):
        revised=(
            "雨后无人渡桥。"+ACTION1+
            "。少年追着铁链撞响的方位走近，发现水位比早晨高了一尺。"
            "同伴劝他立刻上桥，他却看见桥柱正在摇晃。"
            "他把备用木筏推向河湾，"+EFFECT1+
            "。药箱仍在他手里，众人等待下一步应对。")
        proposed=advice(
            self.source,decision="REPLACE_SCENE",scope="scene",
            start=0,end=len(self.source),replacement=revised,trace={
                "action_quote":ACTION1,"effect_quote":EFFECT1,
                "parent_effect_quote":None})
        final,r=self.execute(proposed)
        self.assertEqual(json.loads(final)["prose"],revised)
        self.assertEqual(
            (self.root/"scratch"/"round-01-discarded-draft.md").read_text("utf8"),
            self.source)
        self.assertEqual(r["discarded_drafts_preserved_locally_only"],1)
        self.assertEqual(r["model_calls"],1)

    def test_stale_or_wrong_source_hash_fails_closed_without_retry(self):
        start=self.source.index("黄昏")
        bad=advice(self.source,decision="REVISE",scope="sentence",
                   start=start,end=start+2,
                   replacement="黎明",source_sha_override="0"*64,
                   trace={"action_quote":ACTION1,
                          "effect_quote":EFFECT1,
                          "parent_effect_quote":None})
        final,r=self.execute(bad)
        self.assertEqual(final,self.raw)
        self.assertEqual(r["rounds"][0]["status"],
                         "REJECTED_AND_ROLLED_BACK")
        self.assertEqual(self.provider_requests,1)
        self.assertFalse(list((self.root/"scratch").glob("*selected-draft*")))

    def test_illogical_trace_or_excluded_fact_reverts_to_original(self):
        to_remove="黄昏最后一点天光落到桥头时，"
        start=self.source.index(to_remove)
        bad=advice(self.source,decision="REVISE",scope="paragraph",
                   start=start,end=start+len(to_remove),
                   replacement="黎明的台阶上，",trace={
                    "action_quote":"模型捏造并没有在小说出现的动作",
                    "effect_quote":EFFECT1,"parent_effect_quote":None})
        final,r=self.execute(bad)
        self.assertEqual(final,self.raw)
        self.assertEqual(r["rounds"][0]["status"],
                         "REJECTED_AND_ROLLED_BACK")
        self.assertEqual(self.provider_requests,1)

    def test_two_rounds_model_controls_further_changes_without_user_resend(self):
        head="黄昏最后一点天光落到桥头时，"
        start=self.source.index(head)
        new="天色渐晚时，"
        actual=self.source.replace(head,new,1)
        first=advice(self.source,decision="REVISE",scope="sentence",
                     start=start,end=start+len(head),
                     replacement=new,trace={
                        "action_quote":ACTION1,"effect_quote":EFFECT1,
                        "parent_effect_quote":None})
        second=advice(actual,decision="KEEP")
        final,r=self.execute([first,second],rounds=2)
        self.assertEqual(json.loads(final)["prose"],actual)
        self.assertEqual(self.provider_requests,2)
        self.assertEqual([x["status"] for x in r["rounds"]],
                         ["PROVISIONALLY_REVISED","KEEP_BY_WRITER"])

    def test_provider_allowance_zero_does_not_call_model(self):
        final,r=self.execute([],rounds=2,allowance=0)
        self.assertEqual(final,self.raw)
        self.assertEqual(self.provider_requests,0)
        self.assertEqual(r["model_calls"],0)

    def test_cancelled_writer_does_not_finalize_prose(self):
        with self.assertRaises(WriterDraftCancelled):
            self.execute(
                advice(self.source),cancel_check=lambda:
                (_ for _ in ()).throw(WriterDraftCancelled(
                    "WF_STUDIO_DRAFT_CANCELLED")))
        self.assertEqual(self.provider_requests,0)

    def test_default_writer_still_uses_only_original_calls_without_self_editor(self):
        self.assertEqual(SELF_EDIT_MAX_PROVIDER_CALLS_PER_RUN,8)
        with self.assertRaisesRegex(
                WritingExecutionError,"WF_SELF_EDIT_REQUIRES_G_MODE"):
            class Stub:
                project_id="p"
                scene_id="s"
            AutonomousWriting(Stub()).run(
                outline="真实的悬疑小说大纲，具有独立人物和长期故事矛盾。",
                chapter_goals=["作者写出的剧情必须有因果后果"],
                output_dir=self.root/"bad",
                draft_mode="single",self_edit_rounds=1)
        self.assertFalse((self.root/"bad").exists())


if __name__=="__main__":
    import unittest
    unittest.main()
