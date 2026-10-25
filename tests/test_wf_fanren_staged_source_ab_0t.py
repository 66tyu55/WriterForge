"""Model-free isolation and real-source mechanics for 0.T staged A/B.

The tests use synthetic tiny chapter placeholders only. They MUST NOT imply
that the paid DeepSeek A/B ran or that literary quality was independently graded.
"""
import json
import unittest

from experiments import wf_fanren_staged_source_ab_0t as exp
from writerforge.v96_causal_turns import check_turn


class ProgressiveSourceVisibility(unittest.TestCase):
    def setUp(self):
        self.refs=("甲"*exp.EXCERPT_CHARS,"乙"*exp.EXCERPT_CHARS)

    def test_two_real_early_chapter_bounds_no_entire_book_sent(self):
        source=("本书仅为合成测试内容。\n第1章 甲\n"+
                "初"*350+"\n第2章 乙\n"+"继"*360+
                "\n第3章 丙\n"+"终"*350)
        result=exp.source_windows(source)
        self.assertEqual(result,("初"*230,"继"*230))
        self.assertNotIn("终",result[0]+result[1])

    def test_missing_real_chapters_fails_closed(self):
        with self.assertRaisesRegex(RuntimeError,"WF0T_CANNOT_VERIFY_TWO_CHAPTER_BOUNDS"):
            exp.source_windows("假"*1500)

    def test_A_never_sees_reference_and_B_gets_only_current_window(self):
        a=exp.build_prompt("A",0)
        b=exp.build_prompt("B",0,reference=self.refs[0])
        self.assertNotIn("甲"*30,a)
        self.assertNotIn("乙"*30,a)
        self.assertNotIn("凡人修仙传",a)
        self.assertIn(self.refs[0],b)
        self.assertNotIn(self.refs[1],b)
        self.assertEqual(a.count(exp.OUTLINE),1)
        self.assertEqual(b.count(exp.OUTLINE),1)
        prior="林栖在海堤上的测量并不顺利。"*8
        later=exp.build_prompt(
            "B",1,previous_prose=prior,previous_effect="堤尺掉进淤泥。",
            reference=self.refs[1])
        self.assertIn(self.refs[1],later)
        self.assertNotIn(self.refs[0],later)
        self.assertIn(prior,later)
        self.assertIn("堤尺掉进淤泥。",later)

    def test_arm_A_reference_argument_is_refused(self):
        with self.assertRaisesRegex(RuntimeError,"WF0T_REFERENCE_ISOLATION_FAILED"):
            exp.build_prompt("A",0,reference=self.refs[0])
        with self.assertRaisesRegex(RuntimeError,"WF0T_REFERENCE_ISOLATION_FAILED"):
            exp.build_prompt("B",0,reference=None)

    def test_no_staged_continuation_without_actual_written_previous(self):
        with self.assertRaisesRegex(RuntimeError,"WF0T_PREVIOUS_REAL_PROSE_REQUIRED"):
            exp.build_prompt("A",1)

    def test_never_publish_long_literary_verbatim_match(self):
        self.assertTrue(exp.original_enough("另一个完全不同的原创场景。",self.refs))
        with self.assertRaisesRegex(RuntimeError,"WF0T_REFERENCE_VERBATIM_COPY_HELD"):
            exp.original_enough("这是一段"+"甲"*31+"完成了的中文段落。",self.refs)

    def test_sentence_statistics_are_descriptive_only(self):
        info=exp.sentence_lengths("他没有回头。第二句话略微长一些，因为要交代行动的后果。")
        self.assertEqual(info["sentences"],2)
        self.assertTrue(info["no_automatic_literary_grade"])
        self.assertNotIn("quality_score",info)

    def test_actual_v96_source_validation_of_two_short_turns(self):
        a1="清晨的潮沟里，林栖摸到一枚刻度偏斜的旧铜尺。"
        a2="林栖把旧铜尺轻轻抬起，放到堤沿上让程满看个清楚。"
        a3="铜尺底下露出一道新刻痕，比昨夜记下的潮线高出三分。"
        a=(a1+a2+a3+
           "程满没有立刻回答，只把账页向前翻了一格，"
           "又让林栖把刚看见的数字重新记一遍。")
        first=json.dumps({
            "prose":a,
            "trace":{"action_quote":"林栖把旧铜尺轻轻抬起",
                     "effect_quote":"铜尺底下露出一道新刻痕",
                     "parent_effect_quote":None}},ensure_ascii=False)
        one=check_turn(first,exp.BEATS[0],mode="causal_guard",
                       accepted=(),max_prose_chars=1024)
        b=("林栖看着铜尺底下露出的新刻痕，想起家里尚欠的修堤债。"
           "他把抄好的潮数推到程满面前，请程满在账页上署名。"
           "程满皱着眉签下了名字，却把另一页空白账纸留在自己袖中。"
           "林栖没有追问，他只是重新检查被潮水浸湿的鞋。")
        two=check_turn(json.dumps({
            "prose":b,"trace":{
                "action_quote":"他把抄好的潮数推到程满面前",
                "effect_quote":"程满皱着眉签下了名字",
                "parent_effect_quote":one["effect_quote"]}},ensure_ascii=False),
            exp.BEATS[1],mode="causal_guard",
            accepted=(one,),max_prose_chars=1024)
        self.assertEqual(one["receipt"]["causal_check"],"EXACT_OBSERVABLE_ANCHORS_ONLY")
        self.assertEqual(two["receipt"]["parent_effect_sha256"],
                         exp.sha(one["effect_quote"]))
        self.assertNotEqual(one["receipt"]["prose_sha256"],
                            two["receipt"]["prose_sha256"])


class ModelFreeEndToEndAssembly(unittest.TestCase):
    """Simulated writer only. Exercise actual unchanged WF source reducers."""

    def test_actual_v96_v114_v117_path_with_two_real_source_spans(self):
        import shutil
        from pathlib import Path
        from tempfile import TemporaryDirectory
        from unittest.mock import patch
        if not shutil.which("node"):
            self.skipTest("Node vendor reducer not available")
        first=(
            "清晨的潮沟里，林栖摸到一枚刻度偏斜的旧铜尺。"
            "林栖把旧铜尺轻轻抬起，放到堤沿上让程满看个清楚。"
            "铜尺底下露出一道新刻痕，比昨夜记下的潮线高出三分。"
            "程满没有立刻回答，只把账页向前翻了一格。"
        )
        second=(
            "林栖看着铜尺底下露出的新刻痕，想起家里尚欠的修堤债。"
            "他把抄好的潮数推到程满面前，请程满在账页上署名。"
            "程满皱着眉签下了名字，却把另一页空白账纸留在自己袖中。"
            "林栖没有追问，他只是重新检查被潮水浸湿的鞋。"
        )
        prose=[
            json.dumps({"prose":first,"trace":{
                "action_quote":"林栖把旧铜尺轻轻抬起",
                "effect_quote":"铜尺底下露出一道新刻痕",
                "parent_effect_quote":None}},ensure_ascii=False),
            json.dumps({"prose":second,"trace":{
                "action_quote":"他把抄好的潮数推到程满面前",
                "effect_quote":"程满皱着眉签下了名字",
                "parent_effect_quote":"铜尺底下露出一道新刻痕"}},ensure_ascii=False),
        ]
        class NoProviderStub:
            def call(self,arm,stage,name,packet,max_tokens,*,system):
                if name=="prose":
                    selfouter.assertEqual(max_tokens,1450)
                    return prose[stage]
                selfouter.assertEqual(name,"author-choice")
                return json.dumps({
                    "decision":"MOVE_ON","target_turn":"current",
                    "source_sha256":None,"evidence_quote":None,
                    "focus":None,
                    "why_now":"这个片段已经留下可用的行动后果，当前应当继续推进。",
                    "what_goes_wrong_if_unchanged":None,
                    "intended_reader_effect":None},ensure_ascii=False)
            def release_wires(self,arm,*,allow):
                return None
        selfouter=self
        with TemporaryDirectory() as folder:
            with patch.object(exp,"OUT",Path(folder)):
                result=exp.perform_arm(
                    "A",NoProviderStub(),("甲"*230,"乙"*230))
                self.assertEqual(
                    result["status"],
                    "COMPLETE_UNACCEPTED_TWO_STAGE_WF_CANDIDATE",
                    result)
                self.assertEqual(result["stages_completed"],2)
                self.assertFalse(result["author_revision_observed"])
                self.assertFalse(result["valid_author_revision_and_downstream"])
                self.assertTrue(result["signed_candidate_resume_sha256"])
                self.assertTrue(
                    (Path(folder)/"A"/"stage-02-real-author-prose.md").exists())


if __name__=="__main__":
    unittest.main()
