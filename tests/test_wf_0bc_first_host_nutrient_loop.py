"""WF 0.BC: first HOST work -> verified observations -> host-derived SHADOW habit.

No paid model calls or real provider replay here: only synthetic host callback
and verifiable source bytes. Existing 0.AY original wire is replayed separately
by 0.AZ after those historical provider bytes have been verified.
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
    HostNutrientObservation, FirstHostNutrientLoop, PortableHabitCandidatePool,
    SkillStatus,
)
from writerforge.scheduler import (
    OptionalHostResourceLease, OptionalHostResourceUnavailable,
)

ROOT_SHA = "42cad98118dea662cea472f708ef1de22f4bb139da3210b1f5c3c1f9ac12664d"
VERIFY_KEY = b"0bc-synthetic-verified-provider-source"
HOLDOUT = sha256(b"unseen hard cases, never passed to proposer").hexdigest()
SOURCE = (
    "一名巡查者先看见灯塔连续闪了两次，又听到值班者说机器没有动作。"
    "她尚未确认是谁控制了开关，因此不能把计划当作已经执行的行动。"
).encode("utf-8")


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def wire(prose, model="synthetic-writer"):
    return canonical({
        "model": model,
        "choices": [{"finish_reason": "stop", "message": {
            "content": json.dumps({
                "prose": prose, "chosen_step": "Keep the ambiguity",
                "still_unknown": "who switched the relay",
            }, ensure_ascii=False)}}],
    })


def observed(event_id, *, arm="control", host="synthetic-app",
             task="light-failure", experiment="first-host-demo",
             status="SUCCESS", failure=None, source=SOURCE):
    request = canonical({
        "task": task, "arm": arm, "model": "synthetic-writer",
        "source_sha256": sha256(source).hexdigest(),
    })
    prose = ("她重新检查灯塔的记录，但仍未知道开关是谁拨动的。"
             if arm == "control" else
             "她先查阅电路日志，随后选择等待一次新的信号。")
    provider = wire(prose) if status == "SUCCESS" else None
    answer = prose.encode("utf-8") if status == "SUCCESS" else None
    record = HostNutrientObservation(
        observation_id=event_id, experiment_id=experiment, host_id=host,
        model_id="synthetic-writer", task_id=task, arm=arm,
        source_sha256=sha256(source).hexdigest(),
        request_sha256=sha256(request).hexdigest(),
        provider_wire_sha256=(sha256(provider).hexdigest()
                              if provider is not None else None),
        prose_sha256=(sha256(answer).hexdigest()
                      if answer is not None else None),
        status=status, failure_code=failure,
        verification_origin=("archived_provider_wire" if status == "SUCCESS"
                             else "host_resource_error_receipt"),
        signature="")
    record = replace(record, signature=hmac.new(
        VERIFY_KEY, canonical(record.signing_payload()), sha256).hexdigest())
    return record, source, request, provider, answer


def model_habit_reply(challenge):
    return canonical({
        "format": "wf.host-nutrient-proposal.v1",
        "task_id": challenge["task_id"],
        "source_observation_ids": challenge["source_observation_ids"],
        "target_skill": "observe-before-next-choice",
        "parent_capsule_sha256": ROOT_SHA,
        "procedure_index": 1,
        "procedure_replacement": (
            "Before deciding the next step, inspect actual authored action and "
            "consequences separately from unexecuted plans and character beliefs; "
            "retain ambiguity and allow deliberate attempts without forcing any correction."
        ),
        "falsifier_index": 0,
        "falsifier_replacement": (
            "This observed-step procedure fails when independent fresh matched "
            "tasks produce no stronger choices than the control while consuming "
            "more authorized host resources, or when it suppresses lawful repetition."
        ),
        "reason": "The host observed two different viable next choices; do not claim one is superior.",
    })


class WF0BCFirstHostNutrientTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.db = WriterForgeDB(Path(self.temp.name) / "wf.db")
        self.raw = (Path(__file__).resolve().parents[1] /
                    ".agents/skills/observe-before-next-choice/capsule.json").read_bytes()
        self.assertEqual(sha256(self.raw).hexdigest(), ROOT_SHA)
        self.pool = PortableHabitCandidatePool(
            pinned_roots={ROOT_SHA: self.raw},
            reviewer_verifier_key=b"synthetic-0bc-separate-independent-evaluator",
            frozen_heldout_sha256=HOLDOUT)
        self.loop = FirstHostNutrientLoop(
            db=self.db, scope="first-host-synthetic",
            verifier_key=VERIFY_KEY, root_capsule_bytes=self.raw,
            expected_capsule_sha256=ROOT_SHA, candidate_pool=self.pool)

    def tearDown(self):
        self.db.close()
        self.temp.cleanup()

    def record(self, event_id, **changes):
        rec, source, request, provider, answer = observed(event_id, **changes)
        self.loop.ingest(
            rec, source_bytes=source, request_bytes=request,
            provider_wire_bytes=provider, authored_prose_bytes=answer)
        return rec

    def pair(self):
        self.record("obs-control", arm="control")
        self.record("obs-habit", arm="habit")

    def lease(self, calls=1):
        return OptionalHostResourceLease(
            authorization_id="explicit-synthetic-host-authorization",
            allowances={"nutrient_acquisition": calls})

    def window(self):
        return {
            "source": SOURCE,
            "control": observed("unused-control", arm="control")[4],
            "habit": observed("unused-habit", arm="habit")[4],
        }

    def test_model_needs_actual_verified_work_not_only_hashes(self):
        self.pair()
        calls = []
        budget = self.lease()
        no_context = self.loop.acquire_once(
            experiment_id="first-host-demo", task_id="light-failure",
            host_id="synthetic-app",
            host_call=lambda obj: calls.append(obj), host_lease=budget)
        self.assertEqual(no_context["status"], "DORMANT_SOURCE_NOT_DELIVERED")
        self.assertEqual(calls, [])
        self.assertEqual(budget.remaining("nutrient_acquisition"), 1)

    def test_untrusted_or_edited_work_window_never_reaches_host(self):
        self.pair()
        invalid = self.window()
        invalid["habit"] += b"fabricated action"
        calls = []
        out = self.loop.acquire_once(
            experiment_id="first-host-demo", task_id="light-failure",
            host_id="synthetic-app", source_window=invalid,
            host_call=lambda x: calls.append(x), host_lease=self.lease())
        self.assertEqual(out["status"], "DORMANT_SOURCE_WINDOW_MISMATCH")
        self.assertEqual(calls, [])

    def test_real_work_observation_metadata_is_persistent_not_novel_memory(self):
        self.pair()
        receipt = self.loop.disposition("first-host-demo")
        self.assertEqual(receipt["status"], "OBSERVED_NEEDS_META_PROPOSAL")
        self.assertEqual(receipt["verified_successes"], 2)
        self.assertEqual(receipt["host_requests_in_this_read"], 0)
        rows = self.db.conn.execute(
            "SELECT * FROM host_nutrient_observations ORDER BY observation_id"
        ).fetchall()
        self.assertEqual(len(rows), 2)
        combined = repr([dict(r) for r in rows])
        self.assertNotIn("灯塔", combined)
        self.assertNotIn("source_text", combined)
        self.assertIn("provider_wire_sha256", rows[0].keys())
        self.assertEqual(sha256(self.raw).hexdigest(), ROOT_SHA)

    def test_source_bytes_signature_and_provider_wire_cannot_be_forged(self):
        rec, source, request, provider, answer = observed("obs-one")
        fake = replace(rec, source_sha256="0" * 64)
        with self.assertRaises((ValueError, PermissionError)):
            self.loop.ingest(fake, source_bytes=source, request_bytes=request,
                             provider_wire_bytes=provider,
                             authored_prose_bytes=answer)
        with self.assertRaises(ValueError):
            self.loop.ingest(rec, source_bytes=source, request_bytes=request,
                             provider_wire_bytes=provider + b"x",
                             authored_prose_bytes=answer)
        with self.assertRaises(ValueError):
            self.loop.ingest(rec, source_bytes=source + b"x", request_bytes=request,
                             provider_wire_bytes=provider,
                             authored_prose_bytes=answer)
        self.assertEqual(self.loop.disposition("first-host-demo")["verified_successes"], 0)

    def test_429_record_is_failure_not_fake_body_and_blocks_resource_iteration(self):
        self.pair()
        self.record("obs-third", arm="control", host="second-api",
                    status="SUCCESS")
        self.record("obs-fourth", arm="habit", host="second-api",
                    status="HTTP_429", failure="HTTP_429")
        self.assertEqual(self.loop.disposition("first-host-demo")["status"],
                         "DORMANT_HOST_RESOURCE")
        host_calls = []
        budget = self.lease()
        result = self.loop.acquire_once(
            experiment_id="first-host-demo", task_id="light-failure",
            host_id="synthetic-app", host_call=lambda packet: host_calls.append(packet),
            host_lease=budget)
        self.assertEqual(result["status"], "DORMANT_HOST_RESOURCE")
        self.assertEqual(host_calls, [])
        self.assertEqual(budget.remaining("nutrient_acquisition"), 1)

    def test_one_arm_and_cross_host_pair_cannot_manufacture_matched_evidence(self):
        self.record("obs-control", arm="control")
        self.record("other-habit", arm="habit", host="independent-other")
        result = self.loop.acquire_once(
            experiment_id="first-host-demo", task_id="light-failure",
            host_id="synthetic-app", host_call=lambda packet: self.fail("no calls"),
            host_lease=self.lease())
        self.assertEqual(result["status"], "DORMANT_UNMATCHED_ARMS")

    def test_first_host_model_supplies_new_procedure_then_shadow_persists(self):
        self.pair()
        calls = []
        lease = self.lease()
        result = self.loop.acquire_once(
            experiment_id="first-host-demo", task_id="light-failure",
            host_id="synthetic-app",
            source_window=self.window(),
            host_call=lambda packet: (calls.append(packet), model_habit_reply(packet))[1],
            host_lease=lease)
        self.assertEqual(result["status"], "SHADOW_NEEDS_INDEPENDENT_EVIDENCE")
        self.assertEqual(len(calls), 1)
        self.assertEqual([x["label"] for x in calls[0]["observed_work_data"]],
                         ["source", "control", "habit"])
        self.assertIn("灯塔", calls[0]["observed_work_data"][0]["literal_text"])
        self.assertEqual(lease.remaining("nutrient_acquisition"), 0)
        sha = result["candidate_sha256"]
        self.assertEqual(self.pool.status(sha), "SHADOW")
        self.assertNotEqual(sha, ROOT_SHA)
        receipt = self.loop.read_shadow_candidate(sha)
        self.assertEqual(sha256(receipt["capsule_bytes"]).hexdigest(), sha)
        self.assertEqual(receipt["source_observation_ids"],
                         ("obs-control", "obs-habit"))
        self.assertNotIn("灯塔", receipt["capsule_bytes"].decode())
        self.assertEqual(receipt["parent_sha256"], ROOT_SHA)
        self.assertEqual(receipt["model_proposal_sha256"],
                         sha256(model_habit_reply(calls[0])).hexdigest())
        self.assertEqual(self.loop.disposition("first-host-demo")["shadow_candidates"], 1)
        self.assertFalse(result["literary_improvement_proven"])
        self.assertFalse(result["activated"])

        # A NEW run/process can recover candidate bytes without the original
        # host model, prompt, provider secrets or original prose.
        reopened = WriterForgeDB(self.db.path)
        try:
            other = FirstHostNutrientLoop(
                db=reopened, scope="first-host-synthetic",
                verifier_key=VERIFY_KEY, root_capsule_bytes=self.raw,
                expected_capsule_sha256=ROOT_SHA, candidate_pool=None)
            loaded = other.read_shadow_candidate(sha)
            self.assertEqual(loaded["capsule_bytes"], receipt["capsule_bytes"])
            self.assertFalse(loaded["activated"])
        finally:
            reopened.close()

    def test_no_authorized_lease_no_model_call_or_proposal(self):
        self.pair()
        result = self.loop.acquire_once(
            experiment_id="first-host-demo", task_id="light-failure",
            host_id="synthetic-app", host_call=lambda packet: self.fail("no calls"),
            host_lease=None)
        self.assertEqual(result["status"], "HOST_RESOURCES_NOT_AUTHORIZED")
        self.assertEqual(self.loop.disposition("first-host-demo")["shadow_candidates"], 0)

    def test_no_model_reply_as_fiction_is_not_a_cognitive_habit(self):
        self.pair()
        result = self.loop.acquire_once(
            experiment_id="first-host-demo", task_id="light-failure",
            host_id="synthetic-app",
            source_window=self.window(),
            host_call=lambda packet: canonical({"prose": "一段小说", "chosen_step": "重来"}),
            host_lease=self.lease())
        self.assertEqual(result["status"], "REJECTED_HOST_HABIT_PROPOSAL")
        self.assertEqual(self.loop.disposition("first-host-demo")["shadow_candidates"], 0)
        with self.assertRaises(PermissionError):
            self.loop.acquire_once(
                experiment_id="first-host-demo", task_id="light-failure",
                host_id="synthetic-app", host_call=lambda packet: self.fail("no retry"),
                host_lease=self.lease())

    def test_schema_cannot_change_authority_or_claim_cross_host_proven(self):
        self.pair()
        def forged(packet):
            obj = json.loads(model_habit_reply(packet))
            obj["auto_promotion"] = True
            return canonical(obj)
        out = self.loop.acquire_once(
            experiment_id="first-host-demo", task_id="light-failure",
            host_id="synthetic-app",
            source_window=self.window(), host_call=forged, host_lease=self.lease())
        self.assertEqual(out["status"], "REJECTED_HOST_HABIT_PROPOSAL")
        self.assertEqual(self.db.conn.execute(
            "SELECT COUNT(*) FROM host_nutrient_candidates").fetchone()[0], 0)

    def test_duplicate_signed_observation_is_immutable(self):
        original = self.record("obs-control")
        with self.assertRaises((ValueError, RuntimeError)):
            self.record("obs-control")
        self.assertEqual(self.loop.disposition("first-host-demo")["verified_successes"], 1)
        with self.assertRaises(Exception):
            self.db.conn.execute(
                "UPDATE host_nutrient_observations SET host_id='forged' "
                "WHERE observation_id=?", ("obs-control",))
        self.db.conn.rollback()

    def test_host_429_during_new_proposal_burns_budget_and_stops(self):
        self.pair()
        called = []
        budget = self.lease(calls=2)
        def callback(challenge):
            called.append("attempt")
            raise OptionalHostResourceUnavailable("HTTP_429")
        out = self.loop.acquire_once(
            experiment_id="first-host-demo", task_id="light-failure",
            host_id="synthetic-app",
            source_window=self.window(), host_call=callback, host_lease=budget)
        self.assertEqual(out["status"], "DORMANT_HOST_RESOURCE")
        self.assertEqual(called, ["attempt"])
        self.assertEqual(budget.remaining("nutrient_acquisition"), 1)
        with self.assertRaises(PermissionError):
            self.loop.acquire_once(
                experiment_id="first-host-demo", task_id="light-failure",
                host_id="synthetic-app", host_call=callback, host_lease=budget)
        self.assertEqual(called, ["attempt"])

    def test_changed_or_malicious_recovery_bytes_are_rejected(self):
        self.pair()
        out = self.loop.acquire_once(
            experiment_id="first-host-demo", task_id="light-failure",
            host_id="synthetic-app",
            source_window=self.window(), host_call=model_habit_reply,
            host_lease=self.lease())
        sha = out["candidate_sha256"]
        self.db.conn.execute(
            "UPDATE host_nutrient_candidates SET capsule_bytes=? "
            "WHERE candidate_sha256=?", (b'{"forged":true}', sha))
        self.db.conn.commit()
        with self.assertRaises(ValueError):
            self.loop.read_shadow_candidate(sha)


if __name__ == "__main__":
    unittest.main()
