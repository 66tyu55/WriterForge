"""Future original-draft review marks: offset exactness, safe digest output."""
import unittest
from writerforge.reverse_draft_review_marks import review_marks,DraftReviewError

class ReviewMarksTests(unittest.TestCase):
    def setUp(self):
        self.drafts={
            "baseline":"学徒走进雨夜里，决定去寻找停在山脚下的灯火。"*13,
            "skill":"少年觉得林子有异样，听见落叶响，迟疑后追赶林间亮光。"*13,
        }
        self.one={
            "arm":"skill","dimension":"information",
            "category":"DISCONNECTED_CLUE",
            "start":3,"end":20,
            "observation":"这个发现与人物下一步行动之间缺少可以直接回查的因果桥梁。",
            "revision_hint":"需要重新检查人物当前能看到的事实与行动目标是否有可追踪联系。",
        }
    def test_hash_only_no_sensitive_draft_in_summary(self):
        info=review_marks(self.drafts,[self.one],draft_receipt_sha256="a"*64)
        self.assertEqual(info["annotated_count"],1)
        self.assertEqual(info["marks"][0]["start"],3)
        self.assertFalse(info["eligible_for_core_promotion"])
        self.assertFalse(info["marks"][0]["independently_literary_verified"])
        self.assertNotIn("林子有异样",str(info))
        self.assertNotIn("学徒走进",str(info))
        self.assertNotIn("缺少可以直接",str(info))
    def test_forged_bounds_not_reviewable(self):
        bad={**self.one,"end":9000}
        with self.assertRaisesRegex(DraftReviewError,"REVIEW_SPAN"):
            review_marks(self.drafts,[bad],draft_receipt_sha256="a"*64)
        bad={**self.one,"start":True}
        with self.assertRaisesRegex(DraftReviewError,"REVIEW_SPAN"):
            review_marks(self.drafts,[bad],draft_receipt_sha256="a"*64)
        bad={**self.one,"category":"FAKE_90_PERCENT_PASS"}
        with self.assertRaisesRegex(DraftReviewError,"REVIEW_DIMENSION"):
            review_marks(self.drafts,[bad],draft_receipt_sha256="a"*64)

if __name__=="__main__":
    unittest.main()
