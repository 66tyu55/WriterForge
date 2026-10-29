"""0.CJ explicit writing-problem routing tests, unrelated to model intelligence.

The new 0.CJ real R2 holdout exposed generic how-to questions being treated
as literary craft. These source-only checks fail before the WF fix, and use
no model/R2/Canon. Do not add training data or new Skill/memory DB.
"""
import unittest
from writerforge.xuehai import _author_craft_scope


class AuthorWritingProblemScope(unittest.TestCase):
    def test_want_to_make_a_scene_unsettling_is_author_craft(self):
        scope=_author_craft_scope(
            "想让原本安静的房间一点点变得不安全，每过一道门声音都更近，"
            "结尾留着怪事的真相不说破。")
        self.assertIn("原本安静的房间",scope)
        self.assertIn("怪事的真相",scope)

    def test_consequence_and_cause_in_two_clauses_stay_together(self):
        scope=_author_craft_scope(
            "想写出当事人的转述未必可靠；行动之后出现的报复，"
            "并非已经证实的因果。")
        self.assertIn("转述未必可靠",scope)
        self.assertIn("报复",scope)

    def test_narrative_craft_questions_still_work(self):
        for problem in (
            "如何让对手的误判引出下一步设局并造成代价？",
            "怎样把妖物变形与绳索松紧、捉者分神放到同一动作里？",
            "不要让三名修士凭一句志向就结成联盟，交代资源与风险。",
        ):
            with self.subTest(problem=problem):
                self.assertNotEqual(_author_craft_scope(problem),"")

    def test_css_implementation_is_not_novel_craft(self):
        self.assertEqual(_author_craft_scope(
            "如何实现CSS悬停按钮的键盘焦点样式，"
            "要求触控设备也兼容且所有变量命名采用kebab-case。"),"")

    def test_programming_help_is_not_novel_craft_even_with_fantasy_goal(self):
        self.assertEqual(_author_craft_scope(
            "请解释如何配置Apache HTTP服务的跨域请求头，并提供"
            "可执行的Nginx配置；这不是文学写作技法问题。"),"")

    def test_json_schema_request_is_not_literary_method(self):
        self.assertEqual(_author_craft_scope(
            "怎样构造严格符合JSON Schema Draft 2020-12的对象，"
            "逐一设置integer字段的minimum值，"
            "输出合法JSON结构并由验证器检查。"),"")

    def test_generic_write_better_is_not_concrete_transfer(self):
        # An empty scope is preferable to treating this as a specific
        # mechanics problem, but a generic nonempty scope is also safe
        # when the retriever finds no matching source.
        self.assertNotIn("原文",_author_craft_scope("希望这一章写得更好"))

    def test_only_technical_question_after_literary_scene_is_not_craft(self):
        self.assertEqual(_author_craft_scope(
            "鬼王落在玄幻书院塔顶。如何设置Nginx的HTTP响应头？"),"")


if __name__=="__main__":
    unittest.main()
