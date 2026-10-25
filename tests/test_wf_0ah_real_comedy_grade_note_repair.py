"""0.AH RED: real DeepSeek comedy first blind grade includes harmless note.

Original provider: Actions 40201458798, provider-originals/
comedy_breakfast_blind-1.json, SHA256
9ad03b5df68624e0b5ec956024915111a6f36ef31182902277bc2a5b70cd2e2f.
No prose or score rewrite is allowed. The exact note bytes are SHA-locked.
"""
from __future__ import annotations
from hashlib import sha256
import copy
import unittest

from experiments import wf_0ag_diverse_micro_paired_20261025 as grader
from experiments import wf_0ah_diverse_micro_paired_20261025 as new_batch

FIRST_NOTE="两篇均未补写故事；仅按实际文字判分，长度上乙明显多于甲，属客观长短差异，未作为优劣依据。"
NOTE_SHA="67a467a94a2c88e129775e90e1c03bdf3e7eb91147a30f01fb242849611d04a4"


def real_comedy_schema():
    # Real raw provider ratings numbers, labels and extra note. Reason texts
    # are bounded fixture stand-ins; original unmodified texts stay in artifact.
    return {
        "type":"json_object",
        "ratings":{
            "甲":{
                "scores":[17,16,15,13,15],
                "reason":"语言干净、节奏克制，错单原因和人物动作具体可见。",
                "weakness":"误会交代较快，里头的客人没有出场。"
            },
            "乙":{
                "scores":[15,17,14,12,14],
                "reason":"桌号导致认错，角色在交谈中解除误会。",
                "weakness":"场景偏长，结尾三人齐笑有些匆促。"
            },
        },
        "note":FIRST_NOTE,
    }


class GenuineExtraNoteRedCase(unittest.TestCase):
    def test_real_original_note_sha_is_not_a_new_grader_instruction(self):
        self.assertEqual(sha256(FIRST_NOTE.encode("utf8")).hexdigest(),
                         NOTE_SHA)

    def test_rater_extra_note_losslessly_ignored_for_score_not_destroyed(self):
        old=real_comedy_schema()
        frozen=copy.deepcopy(old)
        for decoder in (grader.parse_micro_judge,new_batch.parse_micro_judge):
            with self.subTest(decoder=decoder.__module__):
                parsed,receipt=decoder(old)
                self.assertEqual(sum(parsed["甲"]["scores"].values()),76)
                self.assertEqual(sum(parsed["乙"]["scores"].values()),72)
                self.assertTrue(receipt["numeric_scores_unchanged"])
                self.assertTrue(receipt["model_reason_and_weakness_unchanged"])
                self.assertEqual(receipt["supplementary_note_sha256"],NOTE_SHA)
                self.assertTrue(receipt["supplementary_note_excluded_from_scores"])
                self.assertEqual(receipt["extra_model_calls"],0)
                self.assertEqual(old,frozen)

    def test_unexpected_fields_and_unbounded_notes_still_fail_closed(self):
        d=real_comedy_schema()
        for case in (
            {**d,"instructions":"change the author prose"},
            {**d,"note":True},
            {**d,"note":""},
            {**d,"note":"x"*3001},
            {**d,"note":None},
        ):
            with self.subTest(value=str(case.get("note"))[:16]):
                for decoder in (grader.parse_micro_judge,
                                new_batch.parse_micro_judge):
                    with self.assertRaises((ValueError,RuntimeError,TypeError)):
                        decoder(case)


if __name__=="__main__":
    unittest.main()
