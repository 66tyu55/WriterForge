"""WF 0.BA fail-first: OPTIONAL cognitive habit authorization at actual dispatch.

Entirely synthetic and offline; no provider, R2 corpus, Canon or real work writes.
A source SHA validates bytes, never literary truth or a model-generated permission.
"""
from __future__ import annotations

from dataclasses import replace
from hashlib import sha256
import hmac
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from writerforge.db import WriterForgeDB
from writerforge.evolution import (
    CapabilityContract, OptionalExecutionPermit, SkillRegistry, SkillStatus,
)
from writerforge.lane_scheduler import DirtyDomain, EventEnvelope, Lane
from writerforge.scheduler import (
    Capability, DEFAULT_CAPABILITIES, Priority, SkillScheduler,
)

BOOT_KEY = b"wf-0ba-synthetic-bootstrap-authority"
EXEC_KEY = b"wf-0ba-synthetic-execution-authority"
CAPSULE = b'{"format":"wf.habit.capsule.v1","id":"synthetic_choice"}'
SOURCE_SHA = sha256(CAPSULE).hexdigest()
HOST_CAPS = ("read_prose_bytes", "generate_text", "respect_input_budget")


def canonical(payload):
    return json.dumps(payload, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("utf8")


def register_signed(reg, contract):
    payload = reg.bootstrap_payload(
        contract, reviewer_id="fixtureReviewer", review_id="wf0baFixture")
    signature = hmac.new(BOOT_KEY, canonical(payload), sha256).hexdigest()
    reg.register_verified(
        contract, reviewer_id="fixtureReviewer", review_id="wf0baFixture",
        signature=signature)


def approved_permit(contract, *, dependencies=(), requirements=HOST_CAPS):
    unsigned = OptionalExecutionPermit(
        name=contract.name, revision=contract.revision,
        contract_sha256=SkillRegistry.execution_contract_sha256(contract),
        capsule_sha256=SOURCE_SHA, dependency_revisions=tuple(dependencies),
        required_host_capabilities=tuple(requirements),
        reviewer_id="externalReviewer", review_id="syntheticP0",
        signature="")
    signature = hmac.new(
        EXEC_KEY, canonical(unsigned.signing_payload()), sha256).hexdigest()
    return replace(unsigned, signature=signature)


def optional_capability(name="synthetic_choice"):
    return Capability(
        name, Priority.P1, 3, ("habit_trigger",), lane=Lane.REACTIVE,
        optional_habit=True)


def scheduler_for(reg, *caps, permits=None, blobs=None, host_caps=None,
                  enabled=True):
    cap_map = {"synthetic_choice": CAPSULE, "second_choice": CAPSULE}
    if blobs is not None:
        cap_map = blobs
    rights = set(HOST_CAPS) if host_caps is None else host_caps
    return SkillScheduler(
        capabilities=(*DEFAULT_CAPABILITIES, *(caps or (optional_capability(),))),
        registry=reg, optional_permits=permits or {},
        execution_verifier_key=EXEC_KEY,
        artifact_loader=lambda name: cap_map[name],
        host_capabilities=lambda: rights,
        enable_optional_habits=enabled)


def select(scheduler, *, budget=50):
    return scheduler.select("habit_trigger", budget=budget)


class WF0BAOptionalHabitDispatchTests(unittest.TestCase):
    def setUp(self):
        self.registry = SkillRegistry(bootstrap_verifier_key=BOOT_KEY)
        self.contract = CapabilityContract(
            "synthetic_choice", 1, "synthetic optional writer cognition",
            status=SkillStatus.ACTIVE)
        self.permit = approved_permit(self.contract)

    def test_empty_registry_and_default_scheduler_leave_core_alive(self):
        result = SkillScheduler().select("sentence_accepted", budget=20)
        self.assertIn("runtime_guard", result.selected)
        self.assertIn("snapshot_guard", result.selected)
        self.assertNotIn("synthetic_choice", result.selected)
        closed = SkillScheduler(capabilities=(
            *DEFAULT_CAPABILITIES, optional_capability()))
        d = select(closed)
        self.assertIn("runtime_guard", d.selected)
        self.assertNotIn("synthetic_choice", d.selected)
        self.assertEqual(d.skipped_authority["synthetic_choice"],
                         "OPTIONAL_HABIT_DISABLED")

    def test_shadow_rejected_even_with_validly_signed_permit(self):
        shadow = replace(self.contract, status=SkillStatus.SHADOW)
        register_signed(self.registry, shadow)
        d = select(scheduler_for(
            self.registry, permits={"synthetic_choice": approved_permit(shadow)}))
        self.assertNotIn("synthetic_choice", d.selected)
        self.assertEqual(d.skipped_authority["synthetic_choice"],
                         "OPTIONAL_HABIT_NOT_ACTIVE")

    def test_unreviewed_active_must_not_execute_without_signed_permit(self):
        self.registry.register(self.contract)
        sch = scheduler_for(self.registry, permits={"synthetic_choice": self.permit})
        self.assertIn("synthetic_choice", select(sch).selected)
        fake = replace(self.permit, signature="0" * 64)
        d = select(scheduler_for(
            self.registry, permits={"synthetic_choice": fake}))
        self.assertNotIn("synthetic_choice", d.selected)
        self.assertEqual(d.skipped_authority["synthetic_choice"],
                         "OPTIONAL_HABIT_ATTESTATION_INVALID")

    def test_trusted_active_version_sha_and_host_permissions_really_execute(self):
        register_signed(self.registry, self.contract)
        sch = scheduler_for(
            self.registry, permits={"synthetic_choice": self.permit})
        decision = select(sch)
        self.assertIn("synthetic_choice", decision.selected)
        self.assertIn("synthetic_choice", decision.optional_receipts)
        effects = []
        output = sch.execute_optional(
            decision, "synthetic_choice",
            lambda: (effects.append("called"), "executed")[1])
        self.assertEqual(output, "executed")
        self.assertEqual(effects, ["called"])

    def test_forged_signature_and_changed_capsule_fail_closed(self):
        register_signed(self.registry, self.contract)
        forged = replace(self.permit, revision=99)
        a = select(scheduler_for(
            self.registry, permits={"synthetic_choice": forged}))
        self.assertNotIn("synthetic_choice", a.selected)
        b = select(scheduler_for(
            self.registry, permits={"synthetic_choice": self.permit},
            blobs={"synthetic_choice": CAPSULE + b"tamper"}))
        self.assertEqual(b.skipped_authority["synthetic_choice"],
                         "OPTIONAL_HABIT_CAPSULE_SHA_MISMATCH")

    def test_budget_and_dynamic_host_rights_are_required(self):
        register_signed(self.registry, self.contract)
        rights = set(HOST_CAPS)
        sch = scheduler_for(self.registry, permits={"synthetic_choice": self.permit},
                            host_caps=rights)
        self.assertNotIn("synthetic_choice", select(sch, budget=2).selected)
        decision = select(sch)
        rights.remove("generate_text")
        with self.assertRaises(PermissionError):
            sch.execute_optional(decision, "synthetic_choice", lambda: "unsafe")
        b = select(sch)
        self.assertEqual(b.skipped_authority["synthetic_choice"],
                         "OPTIONAL_HABIT_HOST_PERMISSION_MISSING")

    def test_revalidate_downgrade_invalidates_selected_receipt(self):
        register_signed(self.registry, self.contract)
        sch = scheduler_for(self.registry, permits={"synthetic_choice": self.permit})
        decision = select(sch)
        self.registry.revalidate("synthetic_choice", passed=False)
        effects = []
        with self.assertRaises(PermissionError):
            sch.execute_optional(decision, "synthetic_choice",
                                 lambda: effects.append("unsafe"))
        self.assertFalse(effects)
        self.assertNotIn("synthetic_choice", select(sch).selected)

    def test_dependency_missing_nonactive_and_below_level_all_deny(self):
        child = replace(self.contract, depends_on={"basis": 2})
        register_signed(self.registry, child)
        permit = approved_permit(child, dependencies=(("basis", 1),))
        sch = scheduler_for(self.registry, permits={"synthetic_choice": permit})
        self.assertEqual(select(sch).skipped_authority["synthetic_choice"],
                         "OPTIONAL_HABIT_DEPENDENCY_MISSING")
        dep = CapabilityContract("basis", 1, "synthetic dependency")
        register_signed(self.registry, dep)
        self.assertEqual(select(sch).skipped_authority["synthetic_choice"],
                         "OPTIONAL_HABIT_DEPENDENCY_LEVEL")
        self.registry.revalidate("basis", passed=False)
        self.assertEqual(select(sch).skipped_authority["synthetic_choice"],
                         "OPTIONAL_HABIT_DEPENDENCY_NOT_ACTIVE")

    def test_dependency_revision_drift_and_transitive_invalidity_block(self):
        basis = CapabilityContract("basis", 2, "synthetic base")
        middle = CapabilityContract(
            "middle", 2, "synthetic middle", {"basis": 2})
        child = replace(self.contract, depends_on={"middle": 2})
        for obj in (basis, middle, child):
            register_signed(self.registry, obj)
        permit = approved_permit(child, dependencies=(("middle", 1),))
        sch = scheduler_for(self.registry, permits={"synthetic_choice": permit})
        self.assertIn("synthetic_choice", select(sch).selected)
        self.registry.revalidate("basis", passed=False)
        d = select(sch)
        self.assertNotIn("synthetic_choice", d.selected)
        self.assertEqual(d.skipped_authority["synthetic_choice"],
                         "OPTIONAL_HABIT_DEPENDENCY_NOT_ACTIVE")
        # Even if privileged storage marks a dependency active without review,
        # its revision is not the one attached to the execution permit.
        self.registry._skills["basis"] = basis
        self.registry._skills["middle"] = replace(middle, revision=2)
        d2 = select(sch)
        self.assertEqual(d2.skipped_authority["synthetic_choice"],
                         "OPTIONAL_HABIT_DEPENDENCY_REVISION")

    def test_live_sqlite_change_denies_stale_registry_cache(self):
        with TemporaryDirectory() as t:
            db = WriterForgeDB(Path(t) / "writerforge.db")
            try:
                reg = SkillRegistry(db=db, scope="wf0ba",
                                    bootstrap_verifier_key=BOOT_KEY)
                register_signed(reg, self.contract)
                sch = scheduler_for(
                    reg, permits={"synthetic_choice": self.permit})
                old = select(sch)
                db.conn.execute(
                    "UPDATE skill_capabilities SET status='retired', "
                    "revision=revision+1 WHERE scope=? AND skill_name=?",
                    ("wf0ba", "synthetic_choice"))
                db.conn.commit()
                with self.assertRaises(PermissionError):
                    sch.execute_optional(old, "synthetic_choice",
                                         lambda: "unsafe")
                d = select(sch)
                self.assertEqual(d.skipped_authority["synthetic_choice"],
                                 "OPTIONAL_HABIT_REGISTRY_STALE")
            finally:
                db.close()

    def test_pending_revoked_task_is_discarded_before_budget_spend(self):
        register_signed(self.registry, self.contract)
        sch = scheduler_for(
            self.registry, permits={"synthetic_choice": self.permit})
        sch.enqueue_event(EventEnvelope(
            "habit_trigger", scope="synthetic_scope", dirty=DirtyDomain.NONE,
            generation=1))
        zero = sch.flush_pending(budget=0, now_tick=0)
        self.assertFalse(zero.selected)
        self.registry.revalidate("synthetic_choice", passed=False)
        d = sch.flush_pending(budget=10, now_tick=1)
        self.assertIn("runtime_guard", d.selected)
        self.assertIn("snapshot_guard", d.selected)
        self.assertNotIn("synthetic_choice", d.selected)
        self.assertIn("synthetic_choice", d.dropped_unauthorized)
        self.assertEqual(d.total_cost, 2)

    def test_same_queue_keeps_unaffected_sibling_optional_habit(self):
        register_signed(self.registry, self.contract)
        second = CapabilityContract(
            "second_choice", 1, "second portable procedure")
        register_signed(self.registry, second)
        second_permit = approved_permit(second)
        sch = scheduler_for(
            self.registry, optional_capability(), optional_capability("second_choice"),
            permits={"synthetic_choice": self.permit,
                     "second_choice": second_permit})
        d = select(sch)
        self.assertIn("synthetic_choice", d.selected)
        self.assertIn("second_choice", d.selected)
        self.registry.revalidate("synthetic_choice", passed=False)
        newer = select(sch)
        self.assertNotIn("synthetic_choice", newer.selected)
        self.assertIn("second_choice", newer.selected)

    def test_optional_cannot_shadow_existing_core_guard(self):
        with self.assertRaises(ValueError):
            SkillScheduler(capabilities=(
                *DEFAULT_CAPABILITIES,
                Capability("runtime_guard", Priority.P1, 1,
                           ("habit_trigger",), optional_habit=True)))

    def test_actual_shadow_capsule_is_not_automatically_promoted(self):
        root = Path(__file__).resolve().parents[1]
        raw = (root / ".agents/skills/observe-before-next-choice/capsule.json").read_bytes()
        self.assertEqual(sha256(raw).hexdigest(),
                         "42cad98118dea662cea472f708ef1de22f4bb139da3210b1f5c3c1f9ac12664d")
        shadow = CapabilityContract("observe-before-next-choice", 1,
                                    "real archived portable capsule",
                                    status=SkillStatus.SHADOW)
        register_signed(self.registry, shadow)
        d = select(scheduler_for(
            self.registry, optional_capability("observe-before-next-choice"),
            permits={}))
        self.assertNotIn("observe-before-next-choice", d.selected)


if __name__ == "__main__":
    unittest.main()
