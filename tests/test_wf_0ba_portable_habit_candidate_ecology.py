"""WF 0.BA/P1 fail-first: actual offline cross-Skill proposals/lineage quarantine.

No model calls, live corpus, Canon writes, upgraded registry or real hosts.
Score fixtures are synthetic and must never certify literary uplift.
"""
from __future__ import annotations

from dataclasses import replace
from hashlib import sha256
import hmac
import json
from pathlib import Path
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
import unittest

from writerforge.evolution import (
    HabitCompetitionEvidence, HabitQuarantineAttestation,
    PortableHabitCandidatePool,
    PortableHabitReleaseAttestation, verify_portable_habit_release,
)

KEY = b"wf0ba-p1-synthetic-independent-reviewer"
HOLDOUT_SHA = sha256(b"immutable synthetic withheld cases").hexdigest()
EVIDENCE_SHA = sha256(b"authentic-looking synthetic offline evidence").hexdigest()
ROOT_SHA = "42cad98118dea662cea472f708ef1de22f4bb139da3210b1f5c3c1f9ac12664d"
TARGET = "observe-before-next-choice"


def canonical(payload):
    return json.dumps(payload, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("utf8")


def proposal_bytes(old_raw, *, text, revise=lambda x: x):
    document = json.loads(old_raw.decode("utf8"))
    document["revision"] += 1
    document["lifecycle"] = "SHADOW"
    document["procedure"][1] += " " + text
    revise(document)
    return canonical(document)


def competition(sha, *, successes=2, regressions=0, cost=8,
                evaluator="independentReviewer", holdout=HOLDOUT_SHA):
    draft = HabitCompetitionEvidence(
        candidate_sha256=sha, evaluator_id=evaluator,
        holdout_suite_sha256=holdout,
        matched_pairs=4, observed_success=successes,
        regression_cases=regressions, cost_units=cost,
        independent_reader_count=0, signature="")
    mac = hmac.new(KEY, canonical(draft.signing_payload()), sha256).hexdigest()
    return replace(draft, signature=mac)


def contamination(root, *, evidence=EVIDENCE_SHA, reviewer="independentReviewer"):
    unsigned = HabitQuarantineAttestation(
        ancestor_sha256=root, evidence_sha256=evidence,
        reason_code="VERIFIED_CANDIDATE_CONTAMINATION",
        reviewer_id=reviewer, signature="")
    signature = hmac.new(KEY, canonical(unsigned.signing_payload()), sha256).hexdigest()
    return replace(unsigned, signature=signature)


class WF0BAPortableHabitCandidateEcologyTests(unittest.TestCase):
    def setUp(self):
        root = Path(__file__).resolve().parents[1]
        self.original = (
            root / ".agents/skills/observe-before-next-choice/capsule.json").read_bytes()
        self.assertEqual(sha256(self.original).hexdigest(), ROOT_SHA)
        self.pool = PortableHabitCandidatePool(
            pinned_roots={ROOT_SHA: self.original},
            reviewer_verifier_key=KEY,
            frozen_heldout_sha256=HOLDOUT_SHA)

    def propose(self, parent=ROOT_SHA, *, proposal_id="patch-alpha",
                prose="Remember lawful uncertainty before next choice.",
                proposer="companion-reasoner", revise=lambda obj: obj):
        source = self.original if parent == ROOT_SHA else self.pool.export_candidate(
            parent)["capsule_utf8"].encode("utf8")
        return self.pool.propose(
            proposer_skill=proposer,
            target_skill=TARGET,
            parent_sha256=parent,
            candidate_bytes=proposal_bytes(source, text=prose, revise=revise),
            evidence_sha256=EVIDENCE_SHA, proposal_id=proposal_id)

    def test_two_independent_candidate_bytes_do_not_change_archived_v1(self):
        root_snapshot = self.original
        first = self.propose()
        second = self.propose(proposal_id="patch-beta",
                              prose="Respect meaningful action repetitions.")
        self.assertNotEqual(first.candidate_sha256, second.candidate_sha256)
        self.assertEqual(self.original, root_snapshot)
        self.assertEqual(self.pool.status(first.candidate_sha256), "SHADOW")
        self.assertEqual(self.pool.status(second.candidate_sha256), "SHADOW")
        self.assertEqual(first.parent_sha256, ROOT_SHA)
        self.assertIn("procedure", first.changed_fields)
        self.assertFalse(self.pool.has_execution_authority)

    def test_proposer_cannot_mutate_authority_evaluator_or_transfer(self):
        for key, replace_value in (
            ("authority", {"auto_skill_promotion": True}),
            ("transfer", {"tested_host_count": 2, "cross_host_quality_proven": True}),
            ("provenance", {"independently_graded": True}),
            ("stopping", {"automatic_rewrite_or_promotion": True}),
        ):
            with self.subTest(protected=key):
                def bad(doc):
                    doc[key] = replace_value
                with self.assertRaises(ValueError):
                    self.propose(proposal_id="unsafe-" + key, revise=bad)

    def test_undeclared_root_wrong_revision_or_fake_active_is_rejected(self):
        with self.assertRaises(ValueError):
            PortableHabitCandidatePool(
                pinned_roots={ROOT_SHA: b"tampered"},
                reviewer_verifier_key=KEY,
                frozen_heldout_sha256=HOLDOUT_SHA)
        for k in ("revision", "lifecycle"):
            def bad(doc):
                doc[k] = 99 if k == "revision" else "ACTIVE"
            with self.subTest(k=k), self.assertRaises(ValueError):
                self.propose(proposal_id="invalid-" + k, revise=bad)
        with self.assertRaises(ValueError):
            self.pool.propose(
                proposer_skill="companion-reasoner", target_skill=TARGET,
                parent_sha256="0" * 64,
                candidate_bytes=proposal_bytes(self.original, text="untrusted parent"),
                evidence_sha256=EVIDENCE_SHA, proposal_id="untrusted-parent")

    def test_proposer_cannot_evaluate_own_candidate_or_forge_signature(self):
        a = self.propose()
        forged = replace(
            competition(a.candidate_sha256, successes=2), signature="0" * 64)
        with self.assertRaises(PermissionError):
            self.pool.record_competition(forged)
        self_signed = competition(a.candidate_sha256, evaluator="companion-reasoner")
        with self.assertRaises(PermissionError):
            self.pool.record_competition(self_signed)
        with self.assertRaises(ValueError):
            self.pool.record_competition(
                competition(a.candidate_sha256, holdout="0"*64))
        self.assertEqual(self.pool.status(a.candidate_sha256), "SHADOW")

    def test_competition_can_prefer_candidate_but_cannot_promote(self):
        first = self.propose()
        second = self.propose(proposal_id="patch-beta",
                              prose="Let the author freely choose the repetition.")
        self.pool.record_competition(
            competition(first.candidate_sha256, successes=1, regressions=2, cost=15))
        self.pool.record_competition(
            competition(second.candidate_sha256, successes=3, regressions=0, cost=6))
        d = self.pool.compare_candidates(TARGET)
        self.assertEqual(d["provisional_leader_sha256"], second.candidate_sha256)
        self.assertIn(first.candidate_sha256, d["dormant_review_candidates"])
        self.assertEqual(d["automatic_promotion"], False)
        self.assertEqual(d["independent_literary_improvement_proven"], False)
        self.assertEqual(self.pool.status(first.candidate_sha256), "SHADOW")
        self.assertEqual(self.pool.status(second.candidate_sha256), "SHADOW")

    def test_competition_same_suite_no_partial_or_missing_source_masquerade(self):
        first = self.propose()
        self.pool.record_competition(
            competition(first.candidate_sha256, successes=2))
        comparison = self.pool.compare_candidates(TARGET)
        self.assertEqual(comparison["status"], "INSUFFICIENT_COMPARABLE_CANDIDATES")
        with self.assertRaises(ValueError):
            self.pool.record_competition(
                competition("0"*64, successes=3))

    def test_signed_contamination_quarantines_descendants_not_siblings(self):
        a = self.propose()
        b = self.propose(proposal_id="patch-beta",
                         prose="Preserve motivated repetition.")
        child = self.propose(
            a.candidate_sha256, proposal_id="patch-alpha-child",
            prose="Preserve bounded-POV uncertainty after failures.")
        fake = replace(contamination(a.candidate_sha256), signature="0"*64)
        with self.assertRaises(PermissionError):
            self.pool.quarantine_lineage(fake)
        affected = self.pool.quarantine_lineage(
            contamination(a.candidate_sha256))
        self.assertEqual(set(affected), {a.candidate_sha256, child.candidate_sha256})
        self.assertEqual(self.pool.status(a.candidate_sha256),
                         "REVIEW_QUARANTINE_LINEAGE")
        self.assertEqual(self.pool.status(child.candidate_sha256),
                         "REVIEW_QUARANTINE_LINEAGE")
        self.assertEqual(self.pool.status(b.candidate_sha256), "SHADOW")
        with self.assertRaises(PermissionError):
            self.propose(a.candidate_sha256, proposal_id="grandchild-unsafe")

    def test_signed_root_poison_propagates_through_all_descendants(self):
        a = self.propose()
        b = self.propose(proposal_id="patch-beta", prose="Avoid false certainty.")
        child = self.propose(
            a.candidate_sha256, proposal_id="patch-alpha-child",
            prose="Do not promote character beliefs to known fact.")
        affected = self.pool.quarantine_lineage(contamination(ROOT_SHA))
        self.assertEqual(set(affected),
                         {ROOT_SHA, a.candidate_sha256,
                          b.candidate_sha256, child.candidate_sha256})
        self.assertEqual(self.pool.status(b.candidate_sha256),
                         "REVIEW_QUARANTINE_LINEAGE")

    def test_pinned_manifest_replays_candidate_lineage_without_erasing_quarantine(self):
        a = self.propose()
        b = self.propose(proposal_id="patch-beta",
                         prose="Permit motivated repetition in the next action.")
        child = self.propose(a.candidate_sha256,
                             proposal_id="patch-alpha-child",
                             prose="Keep a character's wrong inference provisional.")
        self.pool.record_competition(
            competition(b.candidate_sha256, successes=3))
        self.pool.quarantine_lineage(contamination(a.candidate_sha256))
        bundle = self.pool.export_manifest()
        manifest_raw = canonical(bundle)
        pinned = sha256(manifest_raw).hexdigest()
        self.assertNotIn(b"DEEPSEEK_API_KEY", manifest_raw)
        self.assertNotIn("provider_wire", bundle)
        self.assertTrue(all(
            json.loads(entry["capsule_utf8"])["provenance"]
            ["original_provider_wires_outside_capsule"]
            for entry in bundle["candidates"]))
        restored = PortableHabitCandidatePool.from_manifest(
            bundle, pinned_roots={ROOT_SHA: self.original},
            reviewer_verifier_key=KEY, frozen_heldout_sha256=HOLDOUT_SHA,
            expected_manifest_sha256=pinned)
        self.assertEqual(restored.export_manifest(), bundle)
        self.assertEqual(restored.status(a.candidate_sha256),
                         "REVIEW_QUARANTINE_LINEAGE")
        self.assertEqual(restored.status(child.candidate_sha256),
                         "REVIEW_QUARANTINE_LINEAGE")
        self.assertEqual(restored.status(b.candidate_sha256), "SHADOW")
        self.assertFalse(restored.has_execution_authority)

    def test_manifest_pin_rejects_removed_quarantine_and_changed_candidate(self):
        a = self.propose()
        self.pool.quarantine_lineage(contamination(a.candidate_sha256))
        bundle = self.pool.export_manifest()
        pinned = sha256(canonical(bundle)).hexdigest()
        options = dict(pinned_roots={ROOT_SHA: self.original},
                       reviewer_verifier_key=KEY,
                       frozen_heldout_sha256=HOLDOUT_SHA)
        with self.assertRaises(ValueError):
            PortableHabitCandidatePool.from_manifest(
                bundle, expected_manifest_sha256="0"*64, **options)
        def corrupt(edit):
            value = json.loads(json.dumps(bundle))
            edit(value)
            with self.assertRaises(ValueError):
                PortableHabitCandidatePool.from_manifest(
                    value, expected_manifest_sha256=pinned, **options)
        corrupt(lambda data: data["quarantine_attestations"].clear())
        corrupt(lambda data: data["candidates"][0].update(
            capsule_utf8='{"id":"forged"}'))
        with self.assertRaises(ValueError):
            PortableHabitCandidatePool.from_manifest(
                bundle, **options)

    def _signed_release(self, bundle, *, sequence=3, curator="independentCurator"):
        private = Ed25519PrivateKey.generate()
        public = private.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
        draft = PortableHabitReleaseAttestation(
            manifest_sha256=sha256(canonical(bundle)).hexdigest(),
            curator_id=curator, release_sequence=sequence, signature_hex="")
        release = replace(
            draft, signature_hex=private.sign(
                canonical(draft.signing_payload())).hex())
        return release, public, private

    def _verified_release(self, bundle, release, public_key, *,
                          sequence=3, curator="independentCurator"):
        return verify_portable_habit_release(
            bundle, release, pinned_roots={ROOT_SHA: self.original},
            trusted_public_key=public_key,
            expected_curator_id=curator,
            minimum_release_sequence=sequence,
            expected_manifest_sha256=release.manifest_sha256)

    def test_external_agent_reads_signed_habit_history_with_public_key_only(self):
        a = self.propose()
        b = self.propose(proposal_id="patch-beta",
                         prose="Preserve meaningful deliberate repetition.")
        child = self.propose(a.candidate_sha256,
                             proposal_id="patch-alpha-child",
                             prose="Keep character belief uncertainty separate.")
        self.pool.quarantine_lineage(contamination(a.candidate_sha256))
        bundle = self.pool.export_manifest()
        release, public_key, private = self._signed_release(bundle)
        self.assertEqual(len(public_key), 32)
        self.assertNotIn("private_key", bundle)
        self.assertNotIn("private_key", release.signing_payload())
        self.assertNotIn(private.private_bytes_raw().hex(),
                         json.dumps(bundle, ensure_ascii=False))
        imported = self._verified_release(bundle, release, public_key)
        self.assertEqual(imported["candidate_count"], 3)
        self.assertEqual(set(imported["quarantined_candidate_shas"]),
                         {a.candidate_sha256, child.candidate_sha256})
        self.assertNotIn(b.candidate_sha256,
                         imported["quarantined_candidate_shas"])
        self.assertFalse(imported["can_execute"])
        self.assertEqual(imported["new_provider_calls"], 0)
        self.assertFalse(imported["literary_improvement_proven"])

    def test_signed_release_rejects_changed_candidate_and_omitted_quarantine(self):
        a = self.propose()
        self.pool.quarantine_lineage(contamination(a.candidate_sha256))
        bundle = self.pool.export_manifest()
        release, public_key, private = self._signed_release(bundle)
        for mutator in (
            lambda x: x["quarantine_attestations"].clear(),
            lambda x: x["candidates"][0].update(capsule_utf8='{"forged":true}'),
            lambda x: x["candidates"][0].update(lifecycle="SHADOW"),
        ):
            tampered = json.loads(json.dumps(bundle))
            mutator(tampered)
            with self.assertRaises(ValueError):
                self._verified_release(tampered, release, public_key)

        # Even a fresh curator signature on structurally inconsistent lineage
        # must not override the actual signed ancestor/child SHA graph.
        changed = json.loads(json.dumps(bundle))
        changed["candidates"][0]["capsule_sha256"] = "0" * 64
        unsigned = replace(
            release, manifest_sha256=sha256(canonical(changed)).hexdigest(),
            signature_hex="")
        fresh = replace(
            unsigned, signature_hex=private.sign(
                canonical(unsigned.signing_payload())).hex())
        with self.assertRaises(ValueError):
            self._verified_release(changed, fresh, public_key)

    def test_release_requires_independently_trusted_public_key_and_curator(self):
        self.propose()
        bundle = self.pool.export_manifest()
        release, public_key, _ = self._signed_release(bundle)
        another = Ed25519PrivateKey.generate().public_key().public_bytes(
            Encoding.Raw, PublicFormat.Raw)
        with self.assertRaises(PermissionError):
            self._verified_release(bundle, release, another)
        with self.assertRaises(PermissionError):
            self._verified_release(bundle, release, public_key,
                                   curator="impersonatedCurator")
        with self.assertRaises(PermissionError):
            self._verified_release(bundle, replace(release, signature_hex="0"*128),
                                   public_key)

    def test_signed_old_manifest_must_not_roll_back_quarantine_history(self):
        a = self.propose()
        old, pub_old, old_signer = self._signed_release(
            self.pool.export_manifest(), sequence=1)
        self.pool.quarantine_lineage(contamination(a.candidate_sha256))
        newest, current_public, current_signer = self._signed_release(
            self.pool.export_manifest(), sequence=2)
        self.assertEqual(self._verified_release(
            self.pool.export_manifest(), newest, current_public,
            sequence=2)["candidate_count"], 1)
        with self.assertRaises(PermissionError):
            self._verified_release(
                {**self.pool.export_manifest(),
                 "quarantine_attestations": []}, old, pub_old, sequence=2)
        with self.assertRaises(PermissionError):
            self._verified_release(
                self.pool.export_manifest(), newest, current_public,
                sequence=3)

    def test_release_verifies_capsule_sha_even_with_valid_curator_signature(self):
        a = self.propose()
        bundle = self.pool.export_manifest()
        candidate = bundle["candidates"][0]
        candidate["capsule_sha256"] = "0"*64
        release, key, _ = self._signed_release(bundle)
        with self.assertRaises(ValueError):
            self._verified_release(bundle, release, key)
        self.assertEqual(sha256(self.original).hexdigest(), ROOT_SHA)

    def test_export_is_sha_pinned_but_is_not_an_independent_host_test(self):
        candidate = self.propose()
        exported = self.pool.export_candidate(candidate.candidate_sha256)
        self.assertEqual(sha256(exported["capsule_utf8"].encode()).hexdigest(),
                         candidate.candidate_sha256)
        self.assertEqual(exported["parent_sha256"], ROOT_SHA)
        self.assertEqual(exported["lifecycle"], "SHADOW")
        self.assertFalse(exported["cross_host_quality_proven"])
        self.assertFalse(exported["auto_execute"])


if __name__ == "__main__":
    unittest.main()
