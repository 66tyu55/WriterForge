"""0.CN: real author selector rejected a two-sentence quiet-care craft request.

Frozen observation in GitHub Actions #40881414726: first source returned NONE,
while new Rulin mother-son complete reading was available. This tests
the loss of a linked writing request, not a literary scoring target.
"""
import unittest
from writerforge.xuehai import _author_craft_scope

class LinkedAuthorProblem(unittest.TestCase):
    def test_short_craft_question_followed_by_concrete_narrative_delivery(self):
        s=_author_craft_scope(
            "怎样写不多言的照顾？用饭菜、衣着、劳作和省下的零碎钱带出人物之间的感情。")
        self.assertIn("不多言的照顾",s)
        self.assertIn("饭菜、衣着、劳作",s)
        self.assertIn("人物之间的感情",s)

    def test_only_generic_writing_request_without_a_subject_still_abstains(self):
        self.assertEqual(_author_craft_scope(
            "怎样写得更好？请使用更多更漂亮的词语。"),"")

    def test_technical_artifact_not_injected_via_narrative_nouns(self):
        self.assertEqual(_author_craft_scope(
            "如何处理小说人物的数据？用JSON字段与CSS样式输出完整代码。"),"")

    def test_factual_technical_explanation_not_literature(self):
        self.assertEqual(_author_craft_scope(
            "如何解释雨水测量误差？用Python公式计算浓度及单位换算。"),"")

if __name__=="__main__":
    unittest.main()
