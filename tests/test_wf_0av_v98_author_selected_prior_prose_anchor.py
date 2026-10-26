"""0.AV RED: a REAL writer replan from paid provider wire was rejected by V98.

The original 0.AV DeepSeek V98 wire (run 40294657373):
SHA256 c5f74d6bd582f12ce55250a48c22cc457aeb3e31fe68107cc5acc054289ce719
selected the unchanged countdown/hospital-unknown source, rather than the
single V96 action-effect citation (the blackout). It changed the NEXT
character decision, without claiming true causal proof or KNOWLEDGE.
Original paid wire is immutable in the GitHub artifact, not regenerated here.

This regression uses a small SYNTHETIC analogue only, no model calls.
"""
from __future__ import annotations
from copy import deepcopy
import json
import unittest

from test_v98_rolling_causal_planner import (
    first,proposed,raw,BASE_BEATS,EFFECT1,
)
from test_v96_causal_turns import (
    prose1,response,ACTION1,
)
from writerforge.v96_causal_turns import check_turn
from writerforge.v98_rolling_causal_planner import (
    validate_replan,V98RollingPlanError,
)

class RealWriterSourceSelection0AV(unittest.TestCase):
    def invoke(self,original,choice):
        return validate_replan(raw(choice),
            accepted=(original,),accepted_beats=(BASE_BEATS[0],),
            seed_next_beat=BASE_BEATS[1],
            allowed_actor_names=("少年","女子"))

    def test_real_writer_can_choose_a_different_literal_new_pressure(self):
        """Do not make the V96 *technical effect quote* decide the next plot."""
        prior=first()
        alternative="他本来答应朋友当夜入城"
        self.assertIn(alternative,prior["prose"])
        self.assertNotEqual(alternative,prior["effect_quote"])
        choice=proposed(basis=alternative)
        choice["next_turn"]["goal"]="女子不再简单要求绕路，决定核对进入城门前剩余的时间"
        beat,receipt=self.invoke(prior,choice)
        self.assertEqual(beat["goal"],choice["next_turn"]["goal"])
        self.assertTrue(receipt["changed_from_frozen_seed"])
        self.assertEqual(receipt["grounded_prior_beat_id"],"t01")
        self.assertEqual(receipt["grounded_prior_prose_sha256"],
                         prior["receipt"]["prose_sha256"])
        self.assertEqual(receipt["source_basis_kind"],
                         "AUTHOR_SELECTED_OTHER_LITERAL_SOURCE_ONLY")
        self.assertFalse(receipt["source_basis_is_observed_effect"])
        self.assertTrue(receipt["source_parent_relation_review_required"])
        self.assertFalse(receipt["source_parent_causal_relation_verified"])
        self.assertFalse(receipt["narrative_semantics_independently_verified"])
        self.assertFalse(receipt["character_knowledge_promoted_to_KNOWN"])
        self.assertEqual(receipt["canon_or_factjournal_writes"],0)

    def test_nonexistent_forged_fact_must_still_fail_without_model_retry(self):
        with self.assertRaises(V98RollingPlanError):
            self.invoke(first(),proposed(
                basis="少年已得知守桥人其实是来自官府的密探"))

    def test_alternative_repeated_source_must_not_select_arbitrary_occurrence(self):
        alt="他本来答应朋友当夜入城"
        duplicate=prose1()+"。"+alt
        a=check_turn(response(duplicate,ACTION1,EFFECT1),
                     BASE_BEATS[0],mode="causal_guard")
        with self.assertRaises(V98RollingPlanError):
            self.invoke(a,proposed(basis=alt))

    def test_original_effect_anchor_keeps_previous_contract(self):
        prior=first()
        _,receipt=self.invoke(prior,proposed())
        self.assertEqual(receipt["source_basis_kind"],"EFFECT_SOURCE_ONLY")
        self.assertTrue(receipt["source_basis_is_observed_effect"])
        self.assertFalse(receipt["source_parent_causal_relation_verified"])

if __name__=="__main__":
    unittest.main()
