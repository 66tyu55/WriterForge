"""V39 synthetic-only tests: no R2, no models, no literary score."""
import unittest
from scripts.forensic_v37_xiyouji_L2 import sentence_menu
from scripts.audit_v39_r39_knowledge_causality import (
    structural_timeline, CausalAuditError,
)


def manuscript():
    return "".join(
        f"第{i:02d}句里药童看见一个铜扣但暂时没有做出决定。"
        for i in range(1, 47)
    )


class V39CausalTimelineTests(unittest.TestCase):
    def setUp(self):
        self.revised = manuscript()
        self.original = manuscript().replace(
            "第39句里药童看见一个铜扣但暂时没有做出决定。",
            "第39句里药童发现一个药瓶却没有意识到区别。",
        )
        menu = sentence_menu(self.revised, "R")
        self.p = menu[38]["start"]
        self.q = menu[42]["start"]

    def test_real_positions_only_never_literary_success(self):
        result = structural_timeline(
            self.original, self.revised, self.p, self.q)
        self.assertEqual(result["setup_id"], "R39")
        self.assertEqual(result["payoff_id"], "R43")
        self.assertEqual(result["sentences_strictly_between"],
                         ["R40", "R41", "R42"])
        self.assertFalse(result["knowledge_changed_at_setup_proven"])
        self.assertFalse(result["decision_caused_by_setup_proven"])
        self.assertFalse(result["R43_resolves_R39_rather_than_earlier_clue_proven"])
        self.assertEqual(
            result["semantic_status"],
            "UNDETERMINED_REQUIRES_PRIVATE_CLOSE_READING")
        anchored = {x["sentence_id"]: x for x in
                    result["candidate_anchor_sentence_metadata"]}
        self.assertFalse(anchored["R39"][
            "found_as_exact_sentence_in_original_draft"])
        self.assertTrue(anchored["R43"][
            "found_as_exact_sentence_in_original_draft"])
        self.assertNotIn("铜扣", repr(result))

    def test_cannot_reverse_setup_and_payoff(self):
        with self.assertRaisesRegex(CausalAuditError,
                                    "V39_OFFSETS_NOT_IN_FROZEN_ORDER"):
            structural_timeline(
                self.original, self.revised, self.q, self.p)

    def test_invalid_offset_does_not_guess_sentence(self):
        with self.assertRaisesRegex(ValueError, "UNIQUE_REAL_SENTENCE"):
            structural_timeline(
                self.original, self.revised, self.p, len(self.revised)-1)
        with self.assertRaisesRegex(CausalAuditError,
                                    "V39_OFFSETS_NOT_INTEGERS"):
            structural_timeline(
                self.original, self.revised, True, self.q)

    def test_even_multiple_true_quotes_cannot_prove_character_causation(self):
        r = structural_timeline(
            self.original, self.revised, self.p, self.q)
        self.assertTrue(r["host_confirmed_sentence_identity_and_order"])
        self.assertFalse(r["same_clue_identity_proven"])
        self.assertFalse(r["knowledge_before_setup_proven"])


if __name__ == "__main__":
    unittest.main()
