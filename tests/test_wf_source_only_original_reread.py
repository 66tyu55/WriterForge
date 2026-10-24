"""WF genuine prior-model-source replay: no prompt diagnosis, no extra memory.

All tests offline. These synthetic test identities cannot be used as live
source: the real workflow must download and SHA-verify the genuine prior
provider artifact from GH Actions #40094106486 before charging anything.
"""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from writerforge.writing_assist import (
    _source_only_writer_replay_index, _ai_decides_when_to_revisit,
)
from writerforge.verified_flow import WritingExecutionError
from experiments import wf_real_deepseek_blind_source_replay_20261024 as real

PROSE=(
    "阿宁看见小舟已经靠近岸边，船夫陈七正在水边等着人回来。"
    "她看着灯笼晃了一下，陈七抬手去解绳结，又放下。"
    "\n\n"
    "陈七上船，把船篙放在脚边，阿宁并未阻拦他的离开。"
    "到了夜里，阿宁独自站在渡口，不知道对岸是否还有人。"
)
CAST=("阿宁","陈七")

def answer(action,*,quote=None):
    return json.dumps({
        "decision":action,
        "target_turn":"current",
        "source_sha256":real.digest(PROSE),
        "evidence_quote":quote if action=="LOOK_BACK_NOW" else None,
        "focus":"sentence" if action=="LOOK_BACK_NOW" else None,
        "why_now":"我认为这段情节仍需要从人物自己的行动出发，不能靠凭空转场交代结果。",
        "what_goes_wrong_if_unchanged":(
            "我担心如果保持原样，后段的事件承接会缺少可观察的动作证据。"
            if action=="LOOK_BACK_NOW" else None),
        "intended_reader_effect":(
            "希望读者能在动作节奏与人物犹豫之间体会选择的代价。"
            if action=="LOOK_BACK_NOW" else None),
    },ensure_ascii=False)

class WriterSourceReplayUnit(TestCase):
    def test_literal_offsets_are_complete_without_host_literary_labels(self):
        evidence=_source_only_writer_replay_index(PROSE,cast=CAST)
        self.assertEqual(evidence["source_sha256"],real.digest(PROSE))
        self.assertTrue(evidence["literary_quality_verified"] is False)
        self.assertFalse(evidence["literary_error_found_by_host"])
        self.assertFalse(evidence["auto_revision_requested"])
        self.assertEqual(
            "".join(x["source_quote"] for x in evidence["units"]),PROSE)
        for x in evidence["units"]:
            self.assertEqual(PROSE[x["start"]:x["end"]],x["source_quote"])
            self.assertEqual(x["explicit_names"],
                             [n for n in CAST if n in x["source_quote"]])
        self.assertTrue(any(x["source_quote"]=="\n"
                            for x in evidence["units"]))
        self.assertFalse(
            any(any(y in x for y in (
                "character_position", "wrong", "contradiction",
                "suggested_edit","error_score"))
                for x in evidence["units"]))

    def test_v116_existing_source_layer_emits_places_without_any_error_verdict(self):
        from writerforge.v116_state_delta import source_only_character_place_mentions
        text=(
            "程九蹲在船头，手指摸到松开的绳扣。"
            "顾翎跨上船，回头望见雾里的人影。"
            "程九已经坐进船里，手里拿着竹篙。"
            "程九仍蹲在桩边，指尖还在摸绳子的毛刺。"
        )
        report=source_only_character_place_mentions(
            text,cast=("顾翎","程九"))
        self.assertEqual(report["source_sha256"],real.digest(text))
        self.assertFalse(report["literary_error_detected_by_software"])
        self.assertFalse(report["automatically_request_revision"])
        self.assertTrue(report["spatial_consistency_judged_by_model_not_host"])
        self.assertTrue(report["source_mentions_are_not_reducer_state"])
        self.assertEqual(
            [r["literal_place_phrase"] for r in report["entries"]],
            ["船头","船","船里","桩边"])
        self.assertEqual(
            [r["actor"] for r in report["entries"]],
            ["程九","顾翎","程九","程九"])
        for r in report["entries"]:
            self.assertEqual(text[r["start"]:r["end"]],
                             r["source_quote"])
            self.assertEqual(r["source_assertion_status"],
                             "LITERAL_MENTION_NOT_VERIFIED_FACT")
        self.assertEqual(report["model_calls"],0)
        self.assertEqual(report["canon_writes"],0)

    def test_v116_spoken_or_negated_place_claim_not_host_inferred_as_fact(self):
        from writerforge.v116_state_delta import source_only_character_place_mentions
        source=(
            "“程九站在岸边。”顾翎这样猜测。"
            "听说程九跑到渡口，众人都不敢相信。"
            "程九没有站在岸边，只是看着渡口。"
            "程九蹲在船头，握着破裂的船篙。"
        )
        record=source_only_character_place_mentions(
            source,cast=("顾翎","程九"))
        self.assertEqual([e["literal_place_phrase"] for e in
                          record["entries"]],["船头"])
        self.assertFalse(record["automatically_request_revision"])

    def test_source_index_fails_closed_outside_bounded_source(self):
        for prose,cast in [
            ("",CAST),("a"*20000,CAST),(PROSE,()),
            (PROSE,("阿宁","阿宁")),(PROSE,("a"*80,)),
        ]:
            with self.subTest(chars=len(prose),cast=cast):
                with self.assertRaises(WritingExecutionError):
                    _source_only_writer_replay_index(prose,cast=cast)

    def test_model_can_keep_in_blind_and_choose_recheck_after_literal_index(self):
        import json
        from writerforge.writing_assist import _decode_json
        raw=json.dumps({
            "prose":PROSE,
            "trace":{"action_quote":None,"effect_quote":None,
                     "parent_effect_quote":None}},
            ensure_ascii=False)
        beat={
            "id":"t01","kind":"quiet","actor":"阿宁",
            "goal":"阿宁根据现实信息判断是否需要等待",
            "causal_parent":None,"craft_focus":[]}
        with TemporaryDirectory() as temp:
            root=Path(temp)
            observations=[]
            responses=[
                answer("MOVE_ON"),
                answer("LOOK_BACK_NOW",quote="陈七上船，把船篙放在脚边"),
            ]
            def fake_model(packet,*,model,api_base,max_tokens):
                self.assertIsNone(model)
                self.assertIsNone(api_base)
                self.assertEqual(max_tokens,600)
                observations.append(packet.prompt)
                return responses.pop(0)
            blind=_ai_decides_when_to_revisit(
                raw=raw,beat=beat,accepted=(),
                turn_packet=real.packet_for_review(),
                ask_model=fake_model,directory=root/"blind")
            self.assertEqual(blind["decision"],"MOVE_ON")
            self.assertNotIn("逐句原文来源目录",observations[0])
            index=_source_only_writer_replay_index(PROSE,cast=CAST)
            appendix="\n【同一稿件逐句原文来源目录】"+json.dumps(
                index,ensure_ascii=False)
            evidence=_ai_decides_when_to_revisit(
                raw=raw,beat=beat,accepted=(),
                turn_packet=real.packet_for_review(appendix),
                ask_model=fake_model,directory=root/"source-index")
            self.assertEqual(evidence["decision"],"LOOK_BACK_NOW")
            self.assertIn("逐句原文来源目录",observations[1])
            self.assertEqual(len(responses),0)
            self.assertEqual(len(observations),2)
            self.assertEqual(
                _decode_json((root/"blind"/
                    "ai-when-and-why-original.json").read_text("utf8"))["decision"],
                "MOVE_ON")
            self.assertTrue((root/"source-index"/
                             "ai-when-and-why-original.json").exists())

class GenuineArtifactProvenanceGate(TestCase):
    @staticmethod
    def local_evidence(root):
        source_dir=root/"evidence"
        source_dir.mkdir()
        (source_dir/"ai-moment").mkdir()
        original_raw=json.dumps({
            "prose":PROSE,
            "trace":{"action_quote":None,"effect_quote":None,
                     "parent_effect_quote":None}},
            ensure_ascii=False,separators=(",",":"))
        original_decision=answer("MOVE_ON")
        (source_dir/"ORIGINAL_MODEL_PROSE.md").write_text(
            PROSE,encoding="utf8")
        (source_dir/"01-write-model-answer.json").write_text(
            original_raw,encoding="utf8")
        (source_dir/"02-decide-model-answer.json").write_text(
            original_decision,encoding="utf8")
        (source_dir/"ai-moment"/"ai-when-and-why-original.json").write_text(
            original_decision,encoding="utf8")
        calls=[]
        for i,stage,reply in ((1,"write",original_raw),
                              (2,"decide",original_decision)):
            wire=json.dumps({"choices":[{"message":{"content":reply}}]},
                            ensure_ascii=False).encode("utf8")
            (source_dir/f"{i:02d}-{stage}-provider-wire.json").write_bytes(
                wire)
            calls.append({
                "stage":stage,"wire_sha256":real.digest(wire),
                "response_sha256":real.digest(reply),
                "wire_preserved":True})
        status={
            "status":"REAL_MODEL_EVALUATED","model":"deepseek-flash",
            "provider":"deepseek","calls_attempted":2,
            "ai_choice":"MOVE_ON",
            "original_prose_sha256":real.digest(PROSE),
            "original_new_scenario_sha256":real.digest(real.SEED),
            "calls":calls}
        (source_dir/"STATUS.json").write_text(
            json.dumps(status,ensure_ascii=False),encoding="utf8")
        return source_dir
    def test_source_is_byte_anchored_to_original_artifact_and_prior_reply(self):
        with TemporaryDirectory() as tmp:
            evidence=self.local_evidence(Path(tmp))
            obj=real.verified_prior_source(
                evidence,expected=real.digest(PROSE))
            self.assertEqual(obj["source"],PROSE)
            self.assertEqual(obj["previous_decision"]["decision"],"MOVE_ON")
            (evidence/"01-write-provider-wire.json").write_bytes(
                b"not actual old wire")
            with self.assertRaisesRegex(
                RuntimeError,"WF_ORIGINAL_PROVIDER_WIRE_TAMPERED"):
                real.verified_prior_source(
                    evidence,expected=real.digest(PROSE))
    def test_changed_old_prose_fails_before_any_model_work(self):
        with TemporaryDirectory() as tmp:
            evidence=self.local_evidence(Path(tmp))
            (evidence/"ORIGINAL_MODEL_PROSE.md").write_text(
                PROSE+"私自改写",encoding="utf8")
            with self.assertRaisesRegex(
                RuntimeError,"WF_ORIGINAL_PROVIDER_PROSE_SHA_INVALID"):
                real.verified_prior_source(
                    evidence,expected=real.digest(PROSE))


class GenuinePriorTwoReadProof(TestCase):
    def test_old_two_valid_move_on_wires_have_immutable_source_and_hashes(self):
        from experiments import wf_real_deepseek_v116_place_reread_20261024 as followup
        with TemporaryDirectory() as tmp:
            root=Path(tmp)
            (root/"blind").mkdir()
            (root/"source-index").mkdir()
            (root/"ORIGINAL_PROVIDER_PROSE_READONLY.md").write_text(
                PROSE,encoding="utf8")
            events=[]
            for i,stage,directory in (
                    (1,"BLIND_SELF_READ","blind"),
                    (2,"SOURCE_INDEX_SELF_READ","source-index")):
                reply=answer("MOVE_ON")
                wire=b'{"choices":[]}' + bytes([i])
                (root/f"{i:02d}-{stage}-decoded-model.json").write_text(
                    reply,encoding="utf8")
                (root/f"{i:02d}-{stage}-original-wire.json").write_bytes(wire)
                (root/directory/"ai-when-and-why-original.json").write_text(
                    reply,encoding="utf8")
                events.append({
                    "stage":stage,"decoded_sha256":real.digest(reply),
                    "wire_sha256":real.digest(wire),
                    "wire_preserved_before_model_parse":True})
            status={
                "source_sha256":real.digest(PROSE),
                "status":"REAL_REVIEW_STAGES_COMPLETED",
                "old_original_model_decision":"MOVE_ON",
                "blind_decision":"MOVE_ON",
                "source_index_decision":"MOVE_ON",
                "actual_provider_calls":2,
                "source_actually_changed":False,
                "source_index_model_offered":True,
                "model_request_evidence":events}
            (root/"STATUS.json").write_text(
                json.dumps(status),encoding="utf8")
            found=followup.previous_two_real_reviews(
                root,expected=real.digest(PROSE))
            self.assertEqual(found["source"],PROSE)
            self.assertEqual(found["status"]["blind_decision"],"MOVE_ON")
            (root/"blind"/"ai-when-and-why-original.json").write_text(
                answer("LOOK_BACK_NOW",
                       quote="陈七上船，把船篙放在脚边"),encoding="utf8")
            with self.assertRaisesRegex(RuntimeError,
                                         "WF_V116_PRIOR_REAL_REPLY_OR_WIRE_INVALID"):
                followup.previous_two_real_reviews(
                    root,expected=real.digest(PROSE))

if __name__=="__main__":
    import unittest
    unittest.main()
