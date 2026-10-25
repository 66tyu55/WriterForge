"""Writer literary KEEP and what was literally written are separate facts.

Deterministic zero-provider fixtures. Same author model chooses literary
MOVE_ON/LOOK_BACK independently; cross-source attribution only proves that
a byte-exact earlier quote exists. It NEVER proves the quote semantically
records an item transfer or forces V119, and cannot mutate signed story Canon.
"""
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import Mock
import inspect
import json

from writerforge.verified_flow import GroundedDraftPacket,WritingExecutionError
from writerforge.writing_assist import (
    _ai_decides_when_to_revisit,
    _validate_author_prior_source_claims,AutonomousWriting,
    SELF_EDIT_ATTRIBUTION_TOKENS,SELF_EDIT_MOMENT_TOKENS,
)

EARLIER=(
    "寒夜戏楼的后门已经上了锁，宋易站在门旁握着钥匙。"
    "江遥把一张赎身票据藏进衣袖，还没有交给任何人。"
    "戏台上方传来三声鼓点，两人都不知道谁敲的鼓。"
    "楼上南廊的一块木板已经裂开，宋易担心人从那里摔下去。"
)
CURRENT=(
    "江遥握着南廊的栏杆，左脚还在隐隐作痛。"
    "她忽然想起后台那口旧箱子，票据还压在箱底一件戏服底下。"
    "她听见第四声鼓，却没有看见鼓手的脸。"
    "宋易还在后门边，没有察觉江遥已经决定不从正门出去。"
    "月光从屋顶漏洞照进来，落在廊板破损的地方。"
)
PRIOR_QUOTE="江遥把一张赎身票据藏进衣袖，还没有交给任何人。"
NEW_QUOTE="票据还压在箱底一件戏服底下"
assert EARLIER.count(PRIOR_QUOTE)==1
assert CURRENT.count(NEW_QUOTE)==1


def h(v):
    return sha256(v.encode("utf8")).hexdigest()


def env():
    return json.dumps({
        "prose":CURRENT,
        "trace":{"action_quote":None,"effect_quote":None,
                 "parent_effect_quote":None}},ensure_ascii=False)


def report(earlier=EARLIER):
    return {
        "source_sha256":h(CURRENT),
        "earlier_source_sha256":h(earlier),
        "observed":[],"inferred_links":[],
        "reader_uncertainty":"读者需要补出一处没有明确写出的过渡。",
        "cross_source_links":[{
            "previous_quote":PRIOR_QUOTE,
            "current_quote":NEW_QUOTE,
            "reader_imagined_step":"可能有尚未描写的票据转移，不能说前章一定已经交代。",
            "earlier_original_source_offset":earlier.index(PRIOR_QUOTE),
            "current_source_offset":CURRENT.index(NEW_QUOTE),
            "inference_not_an_accepted_change":True,
        }],
        "all_semantics_are_model_generated_not_verified":True,
        "no_host_literary_error_decision":True,
    }


def writer_reply(claims=None,*,choice="MOVE_ON",add_claims=True):
    data={
        "type":"json_object",
        "decision":choice,"target_turn":"current",
        "source_sha256":None,
        "evidence_quote":None if choice=="MOVE_ON" else NEW_QUOTE,
        "focus":None if choice=="MOVE_ON" else "sentence",
        "why_now":"这个场景中的犹豫和沉默对人物的生活压力有意义，即使缺少一次明说的动作，我仍可能选择保留。",
        "what_goes_wrong_if_unchanged":None if choice=="MOVE_ON" else
            "我担心票据的位置变化会令读者误解人物的真实行动和后续选择。",
        "intended_reader_effect":None if choice=="MOVE_ON" else
            "我希望让疑问由人物可信的行为自然生出，而不是靠解释填满所有空白。",
    }
    if add_claims:
        data["source_attributions"]=claims
    return json.dumps(data,ensure_ascii=False,separators=(",",":"))


def claim(basis,quote=None,reason="这一段是否留白应由我自己根据人物真实选择来决定。"):
    return [{
        "link_index":0,
        "basis":basis,
        "prior_transition_quote":quote,
        "literary_reason":reason,
    }]


class SameNovelistPriorSourceAttribution(TestCase):
    def setUp(self):
        self.tmp=TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.packet=GroundedDraftPacket(
            project_id="writer-source-claims",scene_id="opera-case",
            snapshot_id=0,evidence=(),craft_ids=(),
            prompt="一段已经写好的未接受原创小说。",
            prompt_sha256=h("一段已经写好的未接受原创小说。"))
        self.beat={
            "id":"t01","kind":"quiet","actor":"江遥",
            "goal":"江遥决定如何在未知道鼓手身份时继续自己的夜间行动",
            "causal_parent":None,"craft_focus":[]}

    def invoke(self,response,*,earlier=EARLIER,earlier_report=None,
               source_identity_contract="bind_null_current",
               source_mode=True):
        source_report=earlier_report or report(earlier)
        idx=len(list(self.root.iterdir()))
        directory=self.root/f"moment-{idx}"
        prompts=[]
        def model(packet,*,model,api_base,max_tokens):
            self.assertIsNone(model)
            self.assertIsNone(api_base)
            prompts.append((packet.prompt,max_tokens))
            return response
        result=_ai_decides_when_to_revisit(
            raw=env(),beat=self.beat,accepted=(),
            turn_packet=self.packet,ask_model=model,directory=directory,
            reader_report=source_report,
            source_identity_contract=source_identity_contract,
            earlier_source_for_attribution=earlier if source_mode else None)
        return result, prompts, directory

    def test_author_may_keep_and_declares_transition_unwritten(self):
        raw=writer_reply(claim("UNWRITTEN_OR_UNKNOWN"))
        outcome,prompts,directory=self.invoke(raw)
        self.assertEqual(outcome["decision"],"MOVE_ON")
        self.assertEqual(outcome["target_prose_sha256"],h(CURRENT))
        self.assertEqual(prompts[0][1],SELF_EDIT_ATTRIBUTION_TOKENS)
        self.assertIn(EARLIER,prompts[0][0])
        self.assertIn("原文没有明写",prompts[0][0])
        self.assertTrue(outcome["receipt"]["earlier_author_source_attribution_requested"])
        self.assertEqual(outcome["receipt"]["cross_source_reader_hypotheses_unverified_count"],1)
        claim_receipt=outcome["receipt"]["cross_source_author_attribution"]
        self.assertEqual(claim_receipt["status"],
                         "SOURCE_ATTRIBUTIONS_RECORDED_LITERAL_ONLY")
        self.assertEqual(claim_receipt["author_declared_unwritten_or_unknown_links"],1)
        self.assertEqual(claim_receipt["claimed_written_links"],0)
        self.assertTrue(claim_receipt["all_literary_meanings_still_unverified"])
        self.assertFalse(claim_receipt["author_prose_edit_forced"])
        self.assertEqual(outcome["model_calls"],1)
        self.assertEqual((directory/"ai-when-and-why-original.json"
                          ).read_text("utf8"),raw)
        self.assertFalse(outcome["receipt"]["literary_quality_verified"])

    def test_author_can_intentionally_keep_ellipsis_without_claiming_source_fact(self):
        r,_,_=self.invoke(writer_reply(claim(
            "INTENTIONAL_ELLIPSIS",
            reason="我认为人物在这里没有解释票据位置反而更能体现她的避讳，读者仍需自己想象。")))
        self.assertEqual(r["decision"],"MOVE_ON")
        self.assertEqual(r["receipt"]["cross_source_author_attribution"][
            "author_declared_intentional_ellipsis_links"],1)
        self.assertTrue(r["receipt"]["author_kept_unresolved_cross_source_hypotheses"])

    def test_quoting_only_old_sleeve_state_does_not_prove_box_transfer(self):
        r,_,_=self.invoke(writer_reply(claim(
            "WRITTEN_WITH_QUOTE",PRIOR_QUOTE,
            "我声称旧稿已经写出这次转移，实际上提供的只有它仍在衣袖的原句。")))
        self.assertEqual(r["decision"],"MOVE_ON")
        receipt=r["receipt"]["cross_source_author_attribution"]
        self.assertEqual(receipt["status"],"PRIOR_STATE_QUOTE_NOT_TRANSFER_PROOF")
        self.assertEqual(receipt["prior_state_only_citations_needing_review"],1)
        self.assertEqual(receipt["claimed_written_links"],1)
        self.assertTrue(receipt["attributions"][0][
            "source_excerpt_mechanically_verified"])
        self.assertTrue(receipt["attributions"][0][
            "quote_overlaps_questioned_prior_state"])
        self.assertTrue(receipt["attributions"][0][
            "model_semantic_transition_never_automatically_verified"])
        self.assertFalse(receipt["attributions"][0]["canonical_fact_created"])

    def test_genuine_different_old_text_quotation_is_only_literal_evidence(self):
        previous=(
            EARLIER+
            "江遥随后将袖内票据拿出来，自己悄悄放进旧箱底的戏服夹层。"
            "她没有告诉宋易她做出了这个动作，也没有让别人代交票据。"
        )
        q="江遥随后将袖内票据拿出来，自己悄悄放进旧箱底的戏服夹层。"
        r,_,_=self.invoke(writer_reply(claim(
            "WRITTEN_WITH_QUOTE",q,
            "从这一句可以找到实际行动，但软件不能仅凭引句出现就理解其中全部文学因果。")),
            earlier=previous)
        self.assertEqual(r["decision"],"MOVE_ON")
        receipt=r["receipt"]["cross_source_author_attribution"]
        self.assertEqual(receipt["status"],"SOURCE_ATTRIBUTIONS_RECORDED_LITERAL_ONLY")
        self.assertEqual(receipt["claimed_written_links"],1)
        self.assertEqual(receipt["attributions"][0]["prior_quote_sha256"],h(q))
        self.assertFalse(receipt["attributions"][0][
            "quote_overlaps_questioned_prior_state"])
        self.assertTrue(receipt["quoted_text_identity_only_not_event_proof"])

    def test_forged_old_quote_never_proves_writing_but_move_on_unmodified(self):
        raw=writer_reply(claim("WRITTEN_WITH_QUOTE",
            "原小说里根本不存在这样一段已经完成的转移动作。"))
        outcome,_,path=self.invoke(raw)
        self.assertEqual(outcome["decision"],"MOVE_ON")
        self.assertEqual(outcome["receipt"]["cross_source_author_attribution_status"],
                         "UNSUPPORTED_WRITTEN_SOURCE_QUOTE")
        self.assertFalse(outcome["receipt"]["cross_source_author_attribution"][
            "attributions"][0]["source_excerpt_mechanically_verified"])
        self.assertEqual((path/"ai-when-and-why-original.json"
                          ).read_text("utf8"),raw)
        self.assertTrue(outcome["receipt"]["author_kept_unresolved_cross_source_hypotheses"])

    def test_legacy_model_without_attributions_remains_move_on_but_unaudited(self):
        reply=writer_reply(add_claims=False)
        r,requests,_=self.invoke(reply)
        self.assertEqual(r["decision"],"MOVE_ON")
        self.assertEqual(r["receipt"]["cross_source_author_attribution_status"],
                         "MISSING_SOURCE_ATTRIBUTIONS")
        self.assertEqual(requests[0][1],SELF_EDIT_ATTRIBUTION_TOKENS)
        strict,requests,_=self.invoke(reply,source_mode=False)
        self.assertEqual(strict["decision"],"MOVE_ON")
        self.assertNotIn("cross_source_author_attribution_status",strict["receipt"])
        self.assertEqual(requests[0][1],SELF_EDIT_MOMENT_TOKENS)
        # Provenance array without enabled prior source changes the old
        # schema: it is NOT silently accepted on the default legacy path.
        extra,_,_=self.invoke(writer_reply(claim("UNWRITTEN_OR_UNKNOWN")),
                              source_mode=False)
        self.assertEqual(extra["decision"],"INVALID_SIGNAL")

    def test_malformed_claims_are_review_issue_not_a_forced_literary_rewrite(self):
        for claims in (
            [{"link_index":5,"basis":"UNWRITTEN_OR_UNKNOWN",
              "prior_transition_quote":None,"literary_reason":"本段是留白。"}],
            claim("INTENTIONAL_ELLIPSIS",quote=PRIOR_QUOTE),
            [],
            "THIS IS NOT A CREDIBLE CLAIM",
        ):
            with self.subTest(claims=claims):
                r,_,_=self.invoke(writer_reply(claims))
                self.assertEqual(r["decision"],"MOVE_ON")
                self.assertIn(r["receipt"]["cross_source_author_attribution_status"],
                              {"MALFORMED_SOURCE_ATTRIBUTIONS",
                               "UNWRITTEN_BASIS_CANNOT_CITE_TRANSFER"})
                self.assertEqual(r["model_calls"],1)

    def test_hash_swap_or_reader_forgery_blocks_provider_call(self):
        wrong=report()
        wrong["earlier_source_sha256"]="0"*64
        calls=Mock()
        with self.assertRaisesRegex(
            WritingExecutionError,"WF_AUTHOR_PRIOR_SOURCE_ATTRIBUTION_MISMATCH"):
            _ai_decides_when_to_revisit(
                raw=env(),beat=self.beat,accepted=(),
                turn_packet=self.packet,ask_model=calls,
                directory=self.root/"forged",reader_report=wrong,
                earlier_source_for_attribution=EARLIER)
        calls.assert_not_called()
        self.assertFalse((self.root/"forged").exists())
        wrong=report()
        wrong["cross_source_links"][0]["previous_quote"]="伪造完全不存在的引文"
        with self.assertRaisesRegex(
            WritingExecutionError,"WF_AUTHOR_PRIOR_SOURCE_QUOTE_UNTRUSTED"):
            _ai_decides_when_to_revisit(
                raw=env(),beat=self.beat,accepted=(),
                turn_packet=self.packet,ask_model=calls,
                directory=self.root/"forged2",reader_report=wrong,
                earlier_source_for_attribution=EARLIER)
        calls.assert_not_called()

    def test_existing_G_writing_uses_same_model_within_bounded_budget(self):
        code=inspect.getsource(AutonomousWriting.run)
        self.assertIn("SELF_EDIT_ATTRIBUTION_TOKENS",code)
        self.assertIn("earlier_source_for_attribution=(",code)
        self.assertIn('"wf_author_source_attribution_receipts"',code)
        self.assertIn('"wf_source_quote_is_not_transfer_proof"',code)
        self.assertIn('"wf_reader_first_self_review_enabled"',code)
