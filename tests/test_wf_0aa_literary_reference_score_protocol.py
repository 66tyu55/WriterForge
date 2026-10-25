"""0.AA zero-paid judge protocol regressions: numbers not made up by WF."""
import unittest
from pathlib import Path
from unittest.mock import patch
from experiments import wf_0aa_literary_reference_score_20261025 as probe


def answer(labels=("甲","乙","丙"),score=15):
    return {"ratings":[{
        "id":label,
        "scores":{k:score for k in probe.CRITERIA},
        "evidence_reason":"叙述由可见动作和具体细节推动，语句基本自然。",
        "most_visible_weakness":"节奏和人物动机仍有可以强化的地方。"}
        for label in labels]}


class FrozenLiteraryBenchmarkProtocol(unittest.TestCase):
    def test_frozen_source_sha_and_two_chapters(self):
        self.assertEqual(probe.RUN,40163959949)
        self.assertEqual(len(probe.SRC_WINDOWS),2)
        self.assertEqual(len(probe.WIRES),4)
        self.assertEqual(probe.MAX_JUDGE_CALLS,4)
        self.assertEqual(probe.MAX_RESERVED_OUTPUT_TOKENS,8000)
        self.assertEqual(len(probe.STAGE_ORDERS),2)
        self.assertEqual(set(probe.CRITERIA),{
            "语言自然与节制","细节的叙事作用","动作与场景可信",
            "节奏与信息取舍","人物真实感"})

    def test_excerpt_does_not_generate_text_and_balances_length(self):
        x=("林栖在堤坝上反复记录水尺，目光不由自主地落到木桩上。"*10)
        v=probe.sample_window(x)
        self.assertLessEqual(len(v),230)
        self.assertGreaterEqual(len(v),170)
        self.assertIn(v,x)

    def test_three_objects_five_axes_no_novel_prose_returned(self):
        valid=probe.parse_ratings(answer(),probe.LABELS)
        self.assertEqual(sum(valid["甲"]["scores"].values()),75)
        self.assertEqual(set(valid),set(probe.LABELS))
        self.assertNotIn("prose",str(valid))

    def test_missing_fields_fabricated_scores_and_duplicates_refused(self):
        for bad in (
            {"ratings":[]},
            answer(("甲","甲","丙")),
            answer(score=21),
            answer(score=-1),
        ):
            with self.subTest(case=bad):
                with self.assertRaises(RuntimeError):
                    probe.parse_ratings(bad,probe.LABELS)
        c=answer()
        c["ratings"][0]["scores"]["语言自然与节制"]=True
        with self.assertRaises(RuntimeError):
            probe.parse_ratings(c,probe.LABELS)

    def test_published_reason_must_not_echo_book_text(self):
        r=probe.parse_ratings(answer(),probe.LABELS)
        sample="这是一段用于模拟隐私检查的短小原著引用片段，长度超过十二个字符。"
        r["甲"]["evidence_reason"]=sample
        self.assertTrue(probe.response_exposed_copy(r,sample))
        r["甲"]["evidence_reason"]="叙述自然地显露环境和人物的生存压力。"
        self.assertFalse(probe.response_exposed_copy(r,sample))

    def test_counterbalance_two_passes_and_relative_anchor_not_hardcoded(self):
        def mock(vals):
            return {name:{
                "id":name,
                "scores":{criterion:score for criterion in probe.CRITERIA},
                "evidence_reason":"场面完整且具有明确叙述行动和信息取舍。",
                "most_visible_weakness":"句式变化可以更灵活，人物动机略显单薄。"}
                for name,score in vals.items()}
        result=probe.compare_benchmark(1,[
            mock({"R":16,"A":14,"B":13}),
            mock({"R":15,"A":13,"B":14})])
        self.assertEqual(result["R"]["score_out_of_100"],77.5)
        self.assertEqual(result["A"]["score_out_of_100"],67.5)
        self.assertEqual(result["B"]["score_out_of_100"],67.5)
        self.assertEqual(result["A"]["gap_from_reference_points"],-10)
        self.assertAlmostEqual(result["A"]["reference_ratio_percent"],87.1)
        self.assertEqual(result["R"]["order_sensitivity_range"],5)

    def test_no_blind_score_is_a_WF_mandatory_literary_verdict(self):
        import inspect
        s=inspect.getsource(probe.main)
        self.assertIn("load_prior_originals()",s)
        self.assertIn("download_existing_pinned_r2()",s)
        self.assertLess(s.index("load_prior_originals()"),s.index("BoundJudge(key)"))
        self.assertLess(s.index("download_existing_pinned_r2()"),s.index("BoundJudge(key)"))
        self.assertNotIn("record_chapter_memory(",s)
        self.assertNotIn("put_object(",s)

    @unittest.skipUnless((probe.PAIR/"STATUS.json").exists(),
                         "Old original provider artifact not mounted outside one-shot job")
    def test_old_writer_prose_verified_against_actual_provider_wires(self):
        x=probe.load_prior_originals()
        self.assertEqual(len(x),4)
        self.assertEqual(
            x[("B",2)]["source_sha256"],
            "eacda836547a0e3576c16be85e44ce7bbb4dbafb1a74096cbc5465b8b99af4b0")
        self.assertTrue(all(170<=len(r["text"])<=230 for r in x.values()))


if __name__=="__main__":
    unittest.main()
