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

    def test_ebook_contents_list_cannot_masquerade_as_reference(self):
        contents=("第1章 目录一\n第2章 目录二\n第3章 目录三\n")
        real=("第一章 正文一\n"+"真"*320+"\n第二章 正文二\n"+
              "实"*330+"\n第三章 正文三\n"+"章"*340)
        self.assertEqual(exp.source_windows(contents+real),
                         ("真"*230,"实"*230))

    def test_existing_private_r2_fallback_is_read_only(self):
        """Fake R2 protocol only: no book source or paid provider in this test."""
        from pathlib import Path
        from types import SimpleNamespace
        from unittest.mock import patch
        from scripts.learn_archived_modern_r2 import WORKS
        pinned=WORKS["fanrenxiuxian"]
        self.assertEqual(pinned.source_bytes,15079878)
        self.assertEqual(pinned.source_sha256,
            "2fc1698410418bf136448807335c6359bf515b75e6f9c1e1d1f443a1c928e6cc")
        source=("第一章 开端\n"+"甲"*380+"\n第二章 转机\n"+
                "乙"*380+"\n第三章 前行\n"+"丙"*380)
        calls=[]
        class FakeVault:
            def __init__(self):
                self.client=self
            def verify_existing_single_work(self):
                calls.append("verify")
                return {"source_integrity_verified":True,
                        "already_archived":True,
                        "utf8_sha256":pinned.source_sha256,
                        "utf8_bytes":pinned.source_bytes}
            def _blob_key(self,work_id,digest):
                calls.append("blob-key")
                return "frozen/private/source"
            def download_file(self,bucket,key,path):
                calls.append("download")
                Path(path).write_text(source,encoding="utf8")
        with patch("writerforge.r2_storage.R2Config.from_environment",
                   return_value=SimpleNamespace(bucket="writerforge-private-library")), \
             patch("writerforge.single_work_runner.SingleWorkVault",
                   return_value=FakeVault()), \
             patch("writerforge.r2_storage._digest",
                   return_value=(pinned.source_sha256,pinned.source_bytes)):
            windows,info=exp.download_existing_pinned_r2()
        self.assertEqual(windows,("甲"*230,"乙"*230))
        self.assertEqual(calls,["verify","blob-key","download"])
        self.assertEqual(info["reading_channel"],"existing_single_work_R2_read_only")
        self.assertFalse(info["source_uploaded_or_rewritten"])

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
