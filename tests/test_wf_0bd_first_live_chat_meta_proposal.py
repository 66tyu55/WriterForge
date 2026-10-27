"""WF 0.BD source-first real archived writer A/B -> ChatGPT-origin SHADOW only.

Tests intentionally require the original immutable 0.AY Actions artifact. They
never ask a model; a preauthored ChatGPT text is explicitly UNAUTHENTICATED
as provider wire, and can only become an ungraded SHADOW hypothesis.
"""
from __future__ import annotations

from contextlib import ExitStack
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import json
import shutil
import unittest

from experiments import wf_0bd_chatgpt_first_host_source_reanalysis_20261027 as exp
from writerforge.evolution import PortableHabitCandidatePool
from writerforge.db import WriterForgeDB


class WF0BDFirstLiveChatHypothesisTests(unittest.TestCase):
    def setUp(self):
        if not exp.ORIGINAL.exists():
            self.fail("WF0BD_ORIGINAL_0AY_ARTIFACT_REQUIRED_NO_SYNTHETIC_FALLBACK")
        self.temp=TemporaryDirectory()
        self.output=Path(self.temp.name)/"out"

    def tearDown(self):
        self.temp.cleanup()

    def _proposal_copy(self, change):
        candidate=json.loads(exp.PROPOSAL.read_text("utf8"))
        change(candidate)
        temp_path=Path(self.temp.name)/"proposal.json"
        temp_path.write_text(json.dumps(candidate,ensure_ascii=False),encoding="utf8")
        return temp_path

    def test_live_chatgpt_authored_hypothesis_comes_from_real_writer_pairs(self):
        before=exp.ROOT.read_bytes()
        with patch("urllib.request.urlopen",side_effect=AssertionError(
                "no extra model API call or network")):
            status=exp.run(output=self.output)
        self.assertEqual(status["source_pair_original_wires_verified"],2)
        self.assertTrue(status["chatgpt_meta_reply_authenticated_provider_wire"] is False)
        self.assertEqual(status["source_writer_host"],"deepseek")
        self.assertEqual(status["proposal_author_kind"],
                         "INTERACTIVE_CHATGPT_SELF_ATTRIBUTED")
        self.assertFalse(status["quality_improvement_proven"])
        self.assertFalse(status["actual_independent_heldout_suite"])
        self.assertEqual(status["new_paid_provider_calls"],0)
        self.assertEqual(status["replayed_host_model_callbacks"],0)
        self.assertEqual(status["candidate_state"],"SHADOW")
        self.assertEqual(status["original_experiment_state"],
                         "DORMANT_HOST_RESOURCE_UNCHANGED")
        self.assertEqual(exp.ROOT.read_bytes(),before)
        capsule=(self.output/"source_bound_candidate_capsule.json").read_bytes()
        self.assertEqual(exp.digest(capsule),status["candidate_sha256"])
        actual=json.loads(capsule)
        old=json.loads(before)
        self.assertEqual(actual["revision"],old["revision"]+1)
        self.assertEqual(actual["lifecycle"],"SHADOW")
        self.assertEqual(actual["transfer"],old["transfer"])
        self.assertEqual(actual["authority"],old["authority"])
        self.assertEqual(actual["provenance"],old["provenance"])
        self.assertEqual(actual["stopping"],old["stopping"])
        self.assertNotEqual(actual["procedure"][1],old["procedure"][1])
        self.assertEqual(actual["procedure"][:1],old["procedure"][:1])
        self.assertNotIn("阮知",capsule.decode("utf8"))
        self.assertNotIn("沈闻",capsule.decode("utf8"))
        db=WriterForgeDB(self.output/"first_host_source_sha_only.sqlite")
        try:
            rows=db.conn.execute(
                "SELECT host_id,status,provider_wire_sha256 FROM "
                "host_nutrient_observations ORDER BY observation_id").fetchall()
            self.assertEqual(len(rows),2)
            self.assertEqual([r["host_id"] for r in rows],["deepseek","deepseek"])
            self.assertTrue(all(r["status"]=="SUCCESS" for r in rows))
            self.assertEqual(db.conn.execute(
                "SELECT COUNT(*) FROM host_nutrient_candidates").fetchone()[0],0)
        finally:
            db.close()

    def test_no_independent_grade_no_fake_approved_candidate(self):
        exp.run(output=self.output)
        manifest=json.loads((self.output/"portable_manifest.json").read_text("utf8"))
        self.assertEqual(len(manifest["candidates"]),1)
        self.assertEqual(manifest["competition_evidence"],[])
        self.assertEqual(manifest["quarantine_attestations"],[])
        self.assertEqual(manifest["auto_execution_or_promotion"],False)
        self.assertEqual(manifest["cross_host_literary_benefit_proven"],False)
        self.assertEqual(manifest["candidates"][0]["proposer_skill"],
                         "chatgpt-interactive")
        self.assertEqual(manifest["candidates"][0]["target_skill"],
                         "observe-before-next-choice")
        self.assertEqual(manifest["candidates"][0]["parent_sha256"],exp.ROOT_SHA)
        status=json.loads((self.output/"STATUS.json").read_text("utf8"))
        self.assertEqual(status["candidate_sha256"],manifest["candidates"][0]["capsule_sha256"])
        self.assertEqual(status["manifest_sha256"],
                         exp.digest((self.output/"portable_manifest.json").read_bytes()))

    def test_wrong_source_edition_is_rejected_without_consuming_model(self):
        with TemporaryDirectory() as directory:
            folder=Path(directory)/"copied_original"
            shutil.copytree(exp.ORIGINAL,folder)
            path=folder/"original-provider-wires"/"deepseek"/"flood-radio-habit.json"
            path.write_bytes(path.read_bytes()+b"x")
            with patch.object(exp,"ORIGINAL",folder):
                with self.assertRaisesRegex(ValueError,"WIRE_SHA_MISMATCH"):
                    exp.run(output=self.output)
        self.assertFalse(self.output.exists())

    def test_glm_429_cannot_be_silently_filled_for_this_proposal(self):
        with TemporaryDirectory() as directory:
            folder=Path(directory)/"copied_original"
            shutil.copytree(exp.ORIGINAL,folder)
            path=folder/"original-provider-wires"/"discovery"/"flood-radio-habit.json"
            path.parent.mkdir(parents=True,exist_ok=True)
            path.write_bytes(b'{"forged_glm_response":true}')
            with patch.object(exp,"ORIGINAL",folder):
                with self.assertRaisesRegex(ValueError,"429_RESPONSE_FABRICATED"):
                    exp.run(output=self.output)
        self.assertFalse(self.output.exists())

    def test_untrusted_chat_claiming_signed_provider_wire_fails_closed(self):
        proposal=self._proposal_copy(lambda x: x["meta_proposal_origin"].update(
            {"verified_meta_provider_wire_sha256":"0"*64,
             "trusted_host_signed_completion":True}))
        with patch.object(exp,"PROPOSAL",proposal):
            with self.assertRaisesRegex(ValueError,"CHAT_WIRE_MISREPRESENTED"):
                exp.run(output=self.output)
        self.assertFalse(self.output.exists())

    def test_source_original_prose_copying_to_habit_rejected(self):
        source=json.loads(
            (exp.ORIGINAL/"frozen-new-tasks"/"flood-radio.json").read_text("utf8"))
        leaked=source["prior_prose"][0]["prose"][:52]
        proposal=self._proposal_copy(lambda x: x["proposal"].update(
            procedure_replacement="An external model should memorize "+leaked+
            " and reuse that line whenever planning the next chapter."))
        with patch.object(exp,"PROPOSAL",proposal):
            with self.assertRaisesRegex(ValueError,"COPIED_HOST_STORY"):
                exp.run(output=self.output)
        self.assertFalse(self.output.exists())

    def test_source_pair_hash_cannot_be_detached_from_chat_reply(self):
        proposal=self._proposal_copy(lambda x: x["proposal"].update(
            {"source_observation_ids":["other-source-control","other-source-habit"]}))
        with patch.object(exp,"PROPOSAL",proposal):
            with self.assertRaisesRegex(ValueError,"CAUSAL_BINDING_INVALID"):
                exp.run(output=self.output)
        self.assertFalse(self.output.exists())

    def test_existing_result_is_immutable_not_overwritten(self):
        exp.run(output=self.output)
        first_sha=exp.digest((self.output/"portable_manifest.json").read_bytes())
        with self.assertRaisesRegex(ValueError,"NEVER_OVERWRITE"):
            exp.run(output=self.output)
        self.assertEqual(first_sha,
                         exp.digest((self.output/"portable_manifest.json").read_bytes()))


if __name__=="__main__":
    unittest.main()
