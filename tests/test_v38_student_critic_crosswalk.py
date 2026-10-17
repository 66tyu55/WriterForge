"""No-text-leak pure offsets for V38 original reviewer vs WF self-clue."""
import unittest
from scripts.audit_v38_l2_student_vs_critics import exact_sentence_at
from scripts.forensic_v37_xiyouji_L2 import sentence_menu

TEXT=("一位药童在出门时发现了药包上的旧铜扣，并把它藏回袋子里。"
      "她犹豫许久，不知道为什么商贩总在提起某个从未见过的老人。"
      "章节结束时，她回头看铜扣，才想起老人的话。")*6

class CrosswalkTests(unittest.TestCase):
    def test_each_real_character_offset_maps_to_exact_unique_sentence(self):
        rows=sentence_menu(TEXT,"R")
        self.assertGreater(len(rows),5)
        for sentence in rows:
            if sentence["end"]-sentence["start"]<=2:continue
            actual=exact_sentence_at(rows,sentence["start"]+1)
            self.assertEqual(actual["id"],sentence["id"])
            self.assertEqual(TEXT[sentence["start"]:sentence["end"]],
                             sentence["text"])
    def test_uncovered_offset_cannot_be_guessed_into_quote(self):
        rows=sentence_menu(TEXT,"R")
        with self.assertRaisesRegex(ValueError,"UNIQUE_REAL_SENTENCE"):
            exact_sentence_at(rows,len(TEXT)+40)
    def test_ambiguous_overlapping_ranges_rejected(self):
        rows=sentence_menu(TEXT,"R")
        altered=[dict(rows[0]),dict(rows[0])]
        altered[1]["id"]="R00"
        with self.assertRaisesRegex(ValueError,"UNIQUE_REAL_SENTENCE"):
            exact_sentence_at(altered,rows[0]["start"]+1)

if __name__=="__main__":
    unittest.main()
