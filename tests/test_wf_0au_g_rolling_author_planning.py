"""0.AU: G opt-in V98 uses signed source, never review-only as plot truth."""
import unittest
from writerforge.v98_rolling_causal_planner import g_source_replan_eligibility
from writerforge.v96_causal_turns import check_turn,review_only_model_turn,canonical,digest,V96CausalDraftError
from writerforge.verified_flow import WritingExecutionError
from test_v96_causal_turns import prose1,ACTION1,EFFECT1,response,plan

class GWriterRollingGate(unittest.TestCase):
    def test_real_action_effect_is_a_provisional_replan_basis(self):
        turn=check_turn(response(prose1(),ACTION1,EFFECT1),plan()[0],mode="causal_guard")
        doc=g_source_replan_eligibility((turn,))
        self.assertTrue(doc["eligible"])
        self.assertFalse(doc["causal_truth_verified"])
    def test_review_only_cannot_be_relabelled_as_real_cause(self):
        turn=review_only_model_turn(response(prose1(),ACTION1,ACTION1),plan()[0],
             failure_code="WF96_ACTION_EFFECT_OVERLAP_OR_REVERSED")
        doc=g_source_replan_eligibility((turn,))
        self.assertFalse(doc["eligible"])
        self.assertEqual(doc["reason"],"PREVIOUS_TRACE_REVIEW_ONLY")
        tampered={**turn,"prose":turn["prose"]+"伪造"}
        with self.assertRaises(Exception):
            g_source_replan_eligibility((tampered,))
    def test_G_requires_explicit_opt_in_parameter(self):
        from writerforge.writing_assist import AutonomousWriting
        import inspect
        self.assertIn("g_rolling_author_planning",inspect.signature(AutonomousWriting.run).parameters)
