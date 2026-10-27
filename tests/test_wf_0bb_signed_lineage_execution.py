"""WF 0.BB fail-first: signed SHADOW provenance MUST gate optional ACTIVE execution.

Offline synthetic curator/test signer only. The original archived portable v1
remains SHADOW. No model/provider, Canon, R2, external host or real promotion.
"""
from __future__ import annotations
from dataclasses import replace
from hashlib import sha256
import hmac
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

from writerforge.evolution import (
    CapabilityContract, SkillRegistry, SkillStatus, OptionalExecutionPermit,
    PortableHabitCandidatePool, PortableHabitReleaseAttestation,
    PortableHabitActivationAttestation, TrustedPortableHabitLineage,
    HabitQuarantineAttestation,
)
from writerforge.scheduler import (
    Capability, DEFAULT_CAPABILITIES, Priority, SkillScheduler,
    OptionalHostResourceLease,
)
from writerforge.lane_scheduler import DirtyDomain, EventEnvelope, Lane
from writerforge.db import WriterForgeDB

BOOT_KEY = b"wf0bb-synthetic-trusted-registry-bootstrap"
EXEC_KEY = b"wf0bb-synthetic-execution-permission-key"
REVIEW_KEY = b"wf0bb-synthetic-independent-reviewer"
ROOT_SHA = "42cad98118dea662cea472f708ef1de22f4bb139da3210b1f5c3c1f9ac12664d"
HOLDOUT = sha256(b"wf0bb frozen synthetic suite").hexdigest()
EVIDENCE = sha256(b"wf0bb synthetic contamination evidence").hexdigest()
NAME = "observe-before-next-choice"
CURATOR = "externalCurator"


def canonical(obj):
    return json.dumps(obj, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("utf8")


def sign_hmac(key, payload):
    return hmac.new(key, canonical(payload), sha256).hexdigest()


class WF0BBTrustedPortableLineageRuntime(unittest.TestCase):
    def setUp(self):
        self.v1 = (Path(__file__).resolve().parents[1] /
                   ".agents/skills/observe-before-next-choice/capsule.json").read_bytes()
        self.assertEqual(sha256(self.v1).hexdigest(), ROOT_SHA)
        self.pool = PortableHabitCandidatePool(
            pinned_roots={ROOT_SHA: self.v1}, reviewer_verifier_key=REVIEW_KEY,
            frozen_heldout_sha256=HOLDOUT)
        self.curator = Ed25519PrivateKey.generate()
        self.public = self.curator.public_key().public_bytes(
            Encoding.Raw, PublicFormat.Raw)
        self.a = self.candidate("a", "Remember actual decisions, not old proposals.")
        self.release = self.signed_release(sequence=7)
        self.lineage = self.make_lineage()

    def candidate(self, tag, instruction, parent=ROOT_SHA):
        source = self.v1 if parent == ROOT_SHA else self.pool.export_candidate(
            parent)["capsule_utf8"].encode("utf8")
        obj = json.loads(source)
        obj["revision"] += 1
        obj["lifecycle"] = "SHADOW"
        obj["procedure"][1] += " " + instruction
        return self.pool.propose(
            proposer_skill="meta-helper", target_skill=NAME,
            proposal_id=f"proposal-{tag}", parent_sha256=parent,
            candidate_bytes=canonical(obj), evidence_sha256=EVIDENCE)

    def signed_release(self, sequence):
        manifest = self.pool.export_manifest()
        att = PortableHabitReleaseAttestation(
            manifest_sha256=sha256(canonical(manifest)).hexdigest(),
            curator_id=CURATOR, release_sequence=sequence, signature_hex="")
        att = replace(att, signature_hex=self.curator.sign(
            canonical(att.signing_payload())).hex())
        return manifest, att

    def make_lineage(self):
        manifest, att = self.release
        return TrustedPortableHabitLineage(
            manifest=manifest, release_attestation=att,
            pinned_roots={ROOT_SHA: self.v1},
            trusted_public_key=self.public, expected_curator_id=CURATOR,
            minimum_release_sequence=7,
            expected_manifest_sha256=att.manifest_sha256)

    def active_capsule(self, candidate):
        shadow = self.pool.export_candidate(candidate.candidate_sha256)
        obj = json.loads(shadow["capsule_utf8"])
        obj["lifecycle"] = "ACTIVE"
        return canonical(obj)

    def activation(self, candidate, raw, release=None):
        _, published = release or self.release
        att = PortableHabitActivationAttestation(
            target_skill=NAME, candidate_sha256=candidate.candidate_sha256,
            active_capsule_sha256=sha256(raw).hexdigest(),
            manifest_sha256=published.manifest_sha256,
            release_sequence=published.release_sequence,
            curator_id=CURATOR, reviewer_id="independentReview",
            signature_hex="")
        return replace(att, signature_hex=self.curator.sign(
            canonical(att.signing_payload())).hex())

    def signed_registry(self, *, db=None):
        reg = SkillRegistry(
            db=db, scope="wf0bb", bootstrap_verifier_key=BOOT_KEY)
        c = CapabilityContract(
            NAME, 1, "synthetic externally reviewed activation only",
            status=SkillStatus.ACTIVE, revision=2)
        signed = sign_hmac(BOOT_KEY, reg.bootstrap_payload(
            c, reviewer_id="reviewer01", review_id="activation01"))
        reg.register_verified(
            c, reviewer_id="reviewer01", review_id="activation01",
            signature=signed)
        return reg, c

    def scheduler(self, raw, lineage, *, registry=None, host_lease=None):
        reg, c = (registry, registry.get(NAME)) if registry else self.signed_registry()
        permission = OptionalExecutionPermit(
            name=NAME, revision=c.revision,
            contract_sha256=SkillRegistry.execution_contract_sha256(c),
            capsule_sha256=sha256(raw).hexdigest(),
            dependency_revisions=(),
            required_host_capabilities=("generate_text", "read_prose_bytes"),
            reviewer_id="externalReviewer", review_id="manualApproval",
            signature="",
            lineage_candidate_sha256=self.a.candidate_sha256)
        permission = replace(permission, signature=sign_hmac(
            EXEC_KEY, permission.signing_payload()))
        budget = host_lease or OptionalHostResourceLease(
            authorization_id="host-authorized-two-calls",
            allowances={NAME: 2})
        sch = SkillScheduler(
            capabilities=(*DEFAULT_CAPABILITIES, Capability(
                NAME, Priority.P1, 3, ("habit_trigger",), lane=Lane.REACTIVE,
                optional_habit=True, portable_habit=True)),
            registry=reg, optional_permits={NAME: permission},
            execution_verifier_key=EXEC_KEY,
            artifact_loader=lambda _name: raw,
            host_capabilities=lambda: {"generate_text", "read_prose_bytes"},
            host_resource_lease=budget, enable_optional_habits=True,
            portable_lineage=lineage)
        return sch, budget, reg

    def approve(self, candidate=None, lineage=None):
        source = candidate or self.a
        authority = lineage or self.lineage
        raw = self.active_capsule(source)
        authority.approve_activation(self.activation(source, raw), raw)
        return raw

    def contaminate(self, parent_sha, *, sequence=8):
        record = HabitQuarantineAttestation(
            ancestor_sha256=parent_sha, evidence_sha256=EVIDENCE,
            reason_code="VERIFIED_CANDIDATE_CONTAMINATION",
            reviewer_id="independentReview", signature="")
        self.pool.quarantine_lineage(replace(record, signature=sign_hmac(
            REVIEW_KEY, record.signing_payload())))
        newer = self.signed_release(sequence=sequence)
        self.lineage.install_release(
            manifest=newer[0], release_attestation=newer[1],
            expected_manifest_sha256=newer[1].manifest_sha256)
        return newer

    def test_signed_permission_binds_exact_candidate_origin(self):
        raw = self.approve()
        sch, _, _ = self.scheduler(raw, self.lineage)
        permit = sch._optional_permits[NAME]
        self.assertEqual(permit.lineage_candidate_sha256,
                         self.a.candidate_sha256)
        self.assertIn(NAME, sch.select("habit_trigger", budget=40).selected)

    def test_signed_origin_cannot_downgrade_portable_flag_and_skip_lineage(self):
        raw = self.approve()
        sch, lease, registry = self.scheduler(raw, self.lineage)
        permit = sch._optional_permits[NAME]
        downgraded = SkillScheduler(
            capabilities=(*DEFAULT_CAPABILITIES,
                Capability(NAME, Priority.P1, 3, ("habit_trigger",),
                           lane=Lane.REACTIVE, optional_habit=True,
                           portable_habit=False)),
            registry=registry, optional_permits={NAME: permit},
            execution_verifier_key=EXEC_KEY, artifact_loader=lambda name: raw,
            host_capabilities=lambda: {"generate_text", "read_prose_bytes"},
            host_resource_lease=lease, enable_optional_habits=True)
        result = downgraded.select("habit_trigger", budget=40)
        self.assertEqual(
            result.skipped_authority[NAME],
            "OPTIONAL_HABIT_SIGNED_LINEAGE_CANNOT_DOWNGRADE")
        self.assertIn("runtime_guard", result.selected)

    def test_signed_wrong_source_and_missing_source_are_denied(self):
        raw = self.approve()
        sch, lease, _ = self.scheduler(raw, self.lineage)
        permit = sch._optional_permits[NAME]
        missing = replace(permit, lineage_candidate_sha256=None, signature="")
        missing = replace(missing, signature=sign_hmac(EXEC_KEY,
                                                      missing.signing_payload()))
        sch._optional_permits[NAME] = missing
        self.assertEqual(
            sch.select("habit_trigger", budget=40).skipped_authority[NAME],
            "OPTIONAL_HABIT_LINEAGE_SOURCE_PIN_REQUIRED")
        wrong = replace(permit, lineage_candidate_sha256=ROOT_SHA, signature="")
        wrong = replace(wrong, signature=sign_hmac(EXEC_KEY,
                                                   wrong.signing_payload()))
        sch._optional_permits[NAME] = wrong
        self.assertEqual(
            sch.select("habit_trigger", budget=40).skipped_authority[NAME],
            "OPTIONAL_HABIT_LINEAGE_SOURCE_PIN_MISMATCH")
        tampered = replace(permit, lineage_candidate_sha256=ROOT_SHA)
        sch._optional_permits[NAME] = tampered
        self.assertEqual(
            sch.select("habit_trigger", budget=40).skipped_authority[NAME],
            "OPTIONAL_HABIT_ATTESTATION_INVALID")
        self.assertEqual(lease.remaining(NAME), 2)

    def test_missing_lineage_is_denied_but_core_keeps_running(self):
        raw = self.active_capsule(self.a)
        sch, lease, reg = self.scheduler(raw, None)
        d = sch.select("habit_trigger", budget=40)
        self.assertNotIn(NAME, d.selected)
        self.assertEqual(d.skipped_authority[NAME],
                         "OPTIONAL_HABIT_LINEAGE_REQUIRED")
        self.assertIn("runtime_guard", d.selected)
        self.assertIn("snapshot_guard", d.selected)
        self.assertEqual(lease.remaining(NAME), 2)

    def test_signed_release_is_not_automatic_activation(self):
        raw = self.active_capsule(self.a)
        sch, lease, reg = self.scheduler(raw, self.lineage)
        d = sch.select("habit_trigger", budget=40)
        self.assertNotIn(NAME, d.selected)
        self.assertEqual(d.skipped_authority[NAME],
                         "OPTIONAL_HABIT_LINEAGE_ACTIVATION_MISSING")
        self.assertEqual(self.lineage.release_sequence, 7)

    def test_forged_activation_and_shadow_original_are_denied(self):
        raw = self.active_capsule(self.a)
        att = self.activation(self.a, raw)
        with self.assertRaises(PermissionError):
            self.lineage.approve_activation(replace(att, signature_hex="0"*128), raw)
        fake_root = replace(att, candidate_sha256=ROOT_SHA, signature_hex="")
        fake_root = replace(fake_root, signature_hex=self.curator.sign(
            canonical(fake_root.signing_payload())).hex())
        with self.assertRaises(ValueError):
            self.lineage.approve_activation(fake_root, raw)
        sch, _, _ = self.scheduler(self.v1, self.lineage)
        self.assertNotIn(NAME, sch.select("habit_trigger", budget=40).selected)

    def test_independently_signed_active_clone_and_original_registry_can_execute(self):
        raw = self.approve()
        sch, lease, reg = self.scheduler(raw, self.lineage)
        d = sch.select("habit_trigger", budget=40)
        self.assertIn(NAME, d.selected)
        output = sch.execute_optional(d, NAME, lambda: "synthetic-callback")
        self.assertEqual(output, "synthetic-callback")
        self.assertEqual(lease.remaining(NAME), 1)
        self.assertEqual(reg.get(NAME).status, SkillStatus.ACTIVE)
        self.assertEqual(sha256(self.v1).hexdigest(), ROOT_SHA)

    def test_active_bytes_and_unapproved_different_candidate_do_not_run(self):
        raw = self.approve()
        b = self.candidate("b", "Deliberate repetition can be meaningful.")
        wrong = self.active_capsule(b)
        sch, _, _ = self.scheduler(wrong, self.lineage)
        self.assertEqual(sch.select("habit_trigger", budget=40).skipped_authority[NAME],
                         "OPTIONAL_HABIT_LINEAGE_ACTIVE_SHA_MISMATCH")
        # Reproducing source bytes in an ACTIVE clone is an explicit content
        # change; a stolen candidate digest alone never implies approval.
        tampered = raw + b" "
        sch2, _, _ = self.scheduler(tampered, self.lineage)
        self.assertNotIn(NAME, sch2.select("habit_trigger", budget=40).selected)

    def test_signed_quarantine_stops_selected_callback_without_spending_host_budget(self):
        raw = self.approve()
        sch, lease, reg = self.scheduler(raw, self.lineage)
        selected = sch.select("habit_trigger", budget=40)
        self.assertIn(NAME, selected.selected)
        self.contaminate(self.a.candidate_sha256)
        effects = []
        with self.assertRaisesRegex(PermissionError, "LINEAGE_QUARANTINED"):
            sch.execute_optional(selected, NAME,
                                 lambda: effects.append("unsafe"))
        self.assertEqual(effects, [])
        self.assertEqual(lease.remaining(NAME), 2)
        d = sch.select("habit_trigger", budget=40)
        self.assertNotIn(NAME, d.selected)
        self.assertIn("LINEAGE_QUARANTINED", d.skipped_authority[NAME])
        self.assertEqual(reg.get(NAME).status, SkillStatus.ACTIVE)

    def test_revocation_drops_previously_queued_task_before_budget_charge(self):
        raw = self.approve()
        sch, lease, _ = self.scheduler(raw, self.lineage)
        sch.enqueue_event(EventEnvelope(
            "habit_trigger", scope="synthetic", dirty=DirtyDomain.NONE,
            generation=1))
        self.assertFalse(sch.flush_pending(budget=0, now_tick=0).selected)
        self.contaminate(self.a.candidate_sha256)
        out = sch.flush_pending(budget=40, now_tick=1)
        self.assertIn(NAME, out.dropped_unauthorized)
        self.assertEqual(out.total_cost, 2)
        self.assertIn("runtime_guard", out.selected)
        self.assertEqual(lease.remaining(NAME), 2)

    def test_quarantined_ancestor_cascades_to_descendant_but_not_sibling(self):
        b = self.candidate("b", "Deliberate repetition may still be intentional.")
        child = self.candidate(
            "child", "Preserve realistic finite perception.", parent=self.a.candidate_sha256)
        new_manifest = self.signed_release(sequence=8)
        self.lineage.install_release(
            manifest=new_manifest[0], release_attestation=new_manifest[1],
            expected_manifest_sha256=new_manifest[1].manifest_sha256)
        child_raw = self.active_capsule(child)
        self.lineage.approve_activation(self.activation(child, child_raw, new_manifest),
                                        child_raw)
        self.contaminate(self.a.candidate_sha256, sequence=9)
        self.assertEqual(self.lineage.reason(NAME, child_raw),
                         "OPTIONAL_HABIT_LINEAGE_QUARANTINED")
        b_raw = self.active_capsule(b)
        newer = self.signed_release(sequence=9)
        # Signing the sibling's activation against the latest already-installed
        # release should be allowed after independent reviewer authorizes it.
        self.lineage.approve_activation(
            self.activation(b, b_raw, newer), b_raw)
        self.assertIsNone(self.lineage.reason(NAME, b_raw))

    def test_stale_release_or_same_sequence_equivocation_never_reopens_skill(self):
        raw = self.approve()
        old_manifest, old_att = self.release
        newer = self.contaminate(self.a.candidate_sha256)
        for m, a in ((old_manifest, old_att), (newer[0], replace(
                newer[1], signature_hex="0"*128))):
            with self.assertRaises(PermissionError):
                self.lineage.install_release(
                    manifest=m, release_attestation=a,
                    expected_manifest_sha256=a.manifest_sha256)
        self.assertEqual(self.lineage.reason(NAME, raw),
                         "OPTIONAL_HABIT_LINEAGE_QUARANTINED")

    def test_wrong_public_key_and_forged_curator_cannot_approve_release(self):
        other = Ed25519PrivateKey.generate().public_key().public_bytes(
            Encoding.Raw, PublicFormat.Raw)
        manifest, att = self.release
        with self.assertRaises(PermissionError):
            TrustedPortableHabitLineage(
                manifest=manifest, release_attestation=att,
                pinned_roots={ROOT_SHA: self.v1},
                trusted_public_key=other, expected_curator_id=CURATOR,
                minimum_release_sequence=7,
                expected_manifest_sha256=att.manifest_sha256)
        forged = replace(att, curator_id="impostor")
        with self.assertRaises(PermissionError):
            TrustedPortableHabitLineage(
                manifest=manifest, release_attestation=forged,
                pinned_roots={ROOT_SHA: self.v1},
                trusted_public_key=self.public, expected_curator_id=CURATOR,
                minimum_release_sequence=7,
                expected_manifest_sha256=forged.manifest_sha256)


if __name__ == "__main__":
    unittest.main()
