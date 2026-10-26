"""0.AZ: offline Evolution must distinguish a host outage from a habit falsifier.

Real source: 0.AY Actions #40354436598, Discovery GLM-5.3 HTTP 429 after
3 valid real fiction wires and 4 attempted/reserved calls; the habit arm's
GLM response DOES NOT EXIST. Re-running a model is not a fix for this RED.
No host may promote/retire this portable habit from incomplete literary A/B.
"""
from dataclasses import replace
import unittest

from writerforge.evolution import (
    SkillStatus, HabitTrialEvidence, HabitTrialDisposition,
    assess_habit_trial_continuation,
)


def actual_429():
    return HabitTrialEvidence(
        habit_id="observe-before-next-choice",
        current_status=SkillStatus.SHADOW,
        verified_source_receipts=True,
        expected_pairs=4,
        completed_pairs=1,
        attempted_model_calls=4,
        completed_model_responses=3,
        provider_failure_code="WF0AY_SECOND_HOST_HTTP_429",
        independent_literary_review=False,
        confirmed_literary_benefit=False,
        independently_confirmed_contamination=False,
        repeated_no_benefit_evidence=False,
    )


class RealProviderBackpressureIsNotHabitFalsification(unittest.TestCase):
    def test_real_429_keeps_capsule_shadow_and_pauses_not_auto_retries(self):
        decision=assess_habit_trial_continuation(actual_429())
        self.assertIsInstance(decision,HabitTrialDisposition)
        self.assertEqual(decision.disposition,"DORMANT_HOST_RESOURCE")
        self.assertEqual(decision.registry_status,SkillStatus.SHADOW)
        self.assertEqual(decision.new_provider_calls_authorized,0)
        self.assertEqual(decision.literary_conclusion,"NOT_TESTED_INCOMPLETE")
        self.assertFalse(decision.habit_falsified)
        self.assertFalse(decision.habit_promoted)
        self.assertTrue(decision.requires_external_restart_approval)

    def test_partial_429_must_not_be_marked_contamination(self):
        decision=assess_habit_trial_continuation(
            replace(actual_429(),independently_confirmed_contamination=False))
        self.assertNotIn("QUARANTINE",decision.disposition)
        self.assertNotIn("RETIRED",decision.disposition)

    def test_no_429_but_missing_arms_still_stops_as_unmatched(self):
        decision=assess_habit_trial_continuation(
            replace(actual_429(),provider_failure_code=None))
        self.assertEqual(decision.disposition,"DORMANT_UNMATCHED_ARMS")
        self.assertFalse(decision.habit_falsified)

    def test_full_comparable_pairs_not_a_literary_win_without_readers(self):
        decision=assess_habit_trial_continuation(
            replace(actual_429(),expected_pairs=4,completed_pairs=4,
                    attempted_model_calls=8,completed_model_responses=8,
                    provider_failure_code=None))
        self.assertEqual(decision.disposition,"SHADOW_NEEDS_READER_EVIDENCE")
        self.assertFalse(decision.habit_promoted)
        self.assertEqual(decision.literary_conclusion,"NOT_ESTABLISHED")

    def test_proven_benefit_only_routes_to_manual_promotion_review(self):
        decision=assess_habit_trial_continuation(
            replace(actual_429(),expected_pairs=4,completed_pairs=4,
                    attempted_model_calls=8,completed_model_responses=8,
                    provider_failure_code=None,independent_literary_review=True,
                    confirmed_literary_benefit=True))
        self.assertEqual(decision.disposition,"REVIEW_MANUAL_PROMOTION_ONLY")
        self.assertEqual(decision.new_provider_calls_authorized,0)
        self.assertFalse(decision.habit_promoted)

    def test_stable_negative_evidence_can_stop_useless_iterations(self):
        decision=assess_habit_trial_continuation(
            replace(actual_429(),expected_pairs=4,completed_pairs=4,
                    attempted_model_calls=8,completed_model_responses=8,
                    provider_failure_code=None,independent_literary_review=True,
                    repeated_no_benefit_evidence=True))
        self.assertEqual(decision.disposition,"DORMANT_NO_PROVEN_VALUE")
        self.assertFalse(decision.habit_falsified)
        self.assertEqual(decision.registry_status,SkillStatus.SHADOW)

    def test_confirmed_poison_is_not_self_declared_retirement(self):
        decision=assess_habit_trial_continuation(
            replace(actual_429(),independently_confirmed_contamination=True))
        self.assertEqual(decision.disposition,"REVIEW_QUARANTINE_LINEAGE")
        self.assertEqual(decision.registry_status,SkillStatus.SHADOW)
        self.assertFalse(decision.habit_promoted)
        self.assertTrue(decision.requires_external_restart_approval)

    def test_unsigned_sources_cannot_trigger_skill_state_change(self):
        decision=assess_habit_trial_continuation(
            replace(actual_429(),verified_source_receipts=False))
        self.assertEqual(decision.disposition,"REFUSE_UNVERIFIED_EVIDENCE")
        self.assertEqual(decision.new_provider_calls_authorized,0)
        self.assertEqual(decision.registry_status,SkillStatus.SHADOW)

    def test_never_guess_from_invalid_or_fabricated_paired_counts(self):
        with self.assertRaisesRegex(ValueError,"WF_HABIT"):
            assess_habit_trial_continuation(
                replace(actual_429(),completed_pairs=5))
        with self.assertRaisesRegex(ValueError,"WF_HABIT"):
            assess_habit_trial_continuation(
                replace(actual_429(),completed_model_responses=5))
        with self.assertRaisesRegex(ValueError,"WF_HABIT"):
            assess_habit_trial_continuation(
                replace(actual_429(),attempted_model_calls=-1))


if __name__=="__main__":
    unittest.main()
