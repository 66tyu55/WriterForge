"""WF reader-first model literary choice vs host mechanical SHA provenance.

REAL run #40110957161: treatment model chose MOVE_ON but returned null source
SHA. A null identity is not a model assertion that the manuscript differs.
ONLY explicitly enabled current-source binding can supply the cryptographic
digest of the exact prose the host has *already* provided. Model's original
wire, rationale and action remain unedited. Wrong hashes, past-turn nulls,
nonunique quotations and malicious schema remain INVALID_SIGNAL.

This test uses offline scripted replies; it claims no literary improvement.
"""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import Mock

from test_wf_ai_writer_chooses_when_and_why import (
    PROSE,QUOTE,digest,old_turn,proposed,WriterChoosesWhen
)
from writerforge.verified_flow import GroundedDraftPacket,WritingExecutionError
from writerforge.writing_assist import _ai_decides_when_to_revisit


class HostBindsNullOnlyFromExactCurrentSource(TestCase):
    def setUp(self):
        self.temp=TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.dir=Path(self.temp.name)
        self.beat={
            "id":"t01","kind":"quiet","actor":"秦真",
            "goal":"秦真根据实际灯塔原文决定是否继续或修改",
            "causal_parent":None,"craft_focus":[]}
        msg="真正小说的事件只能来自已实际写出的正文。"
        self.packet=GroundedDraftPacket(
            project_id="source-bound-identity",
            scene_id="current-author-turn",
            snapshot_id=1,evidence=(),craft_ids=(),
            prompt=msg,prompt_sha256=digest(msg))

    def run_signal(self,item,*,bound=False,previous=None):
        raw=json.dumps(item,ensure_ascii=False,separators=(",",":"))
        captures=[]
        def writer(packet,*,model,api_base,max_tokens):
            captures.append((packet.prompt,max_tokens))
            return raw
        decision=_ai_decides_when_to_revisit(
            raw=old_turn(),beat=self.beat,
            accepted=(
                ({"prose":previous,"effect_quote":None},)
                if previous is not None else ()),
            turn_packet=self.packet,
            ask_model=writer,
            directory=self.dir/f"decision-{len(list(self.dir.iterdir()))}",
            source_identity_contract=(
                "bind_null_current" if bound else "model_sha"))
        return decision,raw,captures

    def test_real_move_on_null_sha_requires_optin_and_preserves_raw_reply(self):
        response=json.loads(proposed("MOVE_ON"))
        response["source_sha256"]=None
        response["type"]="json_object"
        strict,raw,queries=self.run_signal(response)
        self.assertEqual(strict["decision"],"INVALID_SIGNAL")
        self.assertEqual(len(queries),1)
        found,original,queries=self.run_signal(response,bound=True)
        self.assertEqual(found["decision"],"MOVE_ON")
        self.assertEqual(found["target_prose_sha256"],digest(PROSE))
        self.assertEqual(found["receipt"]["original_decision_sha256"],
                         digest(original))
        self.assertTrue(found["receipt"]["null_source_sha256_bound_from_current_source"])
        self.assertTrue(found["receipt"]["source_sha256_original_model_value_not_changed"])
        self.assertTrue(found["receipt"]["model_original_source_sha256_was_null"])
        self.assertEqual(found["receipt"]["source_identity_contract"],"bind_null_current")
        self.assertEqual(found["receipt"]["format_wrapper_type_only_removed"],True)
        self.assertIsNone(json.loads(original)["source_sha256"])
        self.assertEqual(found["model_calls"],1)
        self.assertFalse(found["receipt"]["literary_quality_verified"])
        self.assertEqual(len(queries),1)
        self.assertIn(PROSE,queries[0][0])
        # The exact raw reply survives in private evidence without host
        # claiming it came with a matching SHA.
        files=list(self.dir.glob("decision-*/ai-when-and-why-original.json"))
        self.assertEqual(len(files),2)
        self.assertTrue(all(f.read_text("utf8")==raw for f in files))

    def test_valid_author_source_quote_can_be_null_bound_without_autorewrite(self):
        item=json.loads(proposed("LOOK_BACK_NOW",quote=QUOTE))
        item["source_sha256"]=None
        yes,raw,_=self.run_signal(item,bound=True)
        self.assertEqual(yes["decision"],"LOOK_BACK_NOW")
        self.assertEqual(yes["source_quote"],QUOTE)
        self.assertEqual(yes["target_prose_sha256"],digest(PROSE))
        self.assertTrue(yes["receipt"]["null_source_sha256_bound_from_current_source"])
        self.assertEqual(json.loads(raw)["evidence_quote"],QUOTE)

    def test_wrong_supplied_sha_or_fake_quote_never_bound(self):
        for change in (
            {"source_sha256":"0"*64},
            {"source_sha256":""},
            {"source_sha256":False},
            {"source_sha256":None,"evidence_quote":"完全不存在的引文"},
            {"source_sha256":None,"bogus_fact_verified":True},
        ):
            with self.subTest(change=change):
                item=json.loads(proposed("LOOK_BACK_NOW",quote=QUOTE))
                item.update(change)
                d,_,_=self.run_signal(item,bound=True)
                self.assertEqual(d["decision"],"INVALID_SIGNAL")
                self.assertNotIn("null_source_sha256_bound_from_current_source",
                                 d["receipt"])

    def test_null_previous_target_must_not_be_bound_from_current_source(self):
        prev=("秦真先前从灯塔出去，在水边看着晚霞，"
              "她和巡夜人保持距离，并没有向他透露钥匙的来历。")*2
        item=json.loads(proposed("LOOK_BACK_NOW",quote=QUOTE))
        item["target_turn"]="previous"
        item["source_sha256"]=None
        item["evidence_quote"]=None
        item["focus"]="scene"
        decision,_,_=self.run_signal(item,bound=True,previous=prev)
        self.assertEqual(decision["decision"],"INVALID_SIGNAL")

    def test_unrecognized_binding_mode_rejected_before_any_model_request(self):
        with self.assertRaisesRegex(
                WritingExecutionError,"SOURCE_IDENTITY_MODE_INVALID"):
            _ai_decides_when_to_revisit(
                raw=old_turn(),beat=self.beat,accepted=(),
                turn_packet=self.packet,ask_model=Mock(),
                directory=self.dir/"invalid-mode",
                source_identity_contract="trust_every_model_hash")
        self.assertFalse((self.dir/"invalid-mode").exists())
