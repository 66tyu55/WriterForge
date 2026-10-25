"""0.AE: zero-cost replay of actual ten 0.AD model wires before paying for new ratings."""
import unittest
from pathlib import Path

from experiments import wf_0ae_replay_original_multigenre_real_scores_20261025 as probe
from experiments.wf_0ad_multigenre_real_paired_writing_20261025 import GENRES

class ForensicGenreReplayTests(unittest.TestCase):
    def test_new_job_cannot_regenerate_the_eight_existing_literary_paragraphs(self):
        self.assertEqual(probe.FROZEN_RUN,40190602528)
        self.assertEqual(probe.MAX_NEW_CALLS,6)
        self.assertEqual(probe.MAX_NEW_RESERVED_TOKENS,10300)
        self.assertEqual(len(GENRES),4)
        import inspect
        source=inspect.getsource(probe.main)
        self.assertNotIn("author_pair(",source)
        self.assertNotIn("record_chapter_memory(",source)
        self.assertIn("replay_first_real_run()",source)
        self.assertIn("original,existing,events",source)

    def test_frozen_author_prompts_byte_identical_to_previous_pilot(self):
        from experiments.wf_0ad_multigenre_real_paired_writing_20261025 import (
            scene_prompt,make_turn_instructions)
        for item in GENRES:
            base=scene_prompt(item)
            bare=base+'仅输出 JSON: {"prose":"你真正创作的小说原文"}。'
            self.assertEqual(probe.author_prompt(item,"bare-author"),bare)
            self.assertIn("WF原有V96候选来源契约",
                          probe.author_prompt(item,"WF-author"))

    def test_scores_merge_without_promoting_WF_source_truth(self):
        def item(total):
            return {"scores":{axis:total for axis in (
                "语言自然与节制","具体细节的叙事作用",
                "动作与因果可信度","人物心理与动机",
                "类型目标完成程度")},
                "reason":"这一次人物动作与实际情绪关联清晰。",
                "weakness":"故事的局部信息还可以更克制。"}
        o=probe.merge_scores(
            {"裸模型":item(12),"WF辅助":item(15)},
            {"裸模型":item(13),"WF辅助":item(14)})
        self.assertEqual(o["裸模型"]["score_out_of_100"],62.5)
        self.assertEqual(o["WF辅助"]["score_out_of_100"],72.5)
        self.assertEqual(o["WF_minus_bare_points"],10.0)
        self.assertNotIn("literary_truth_verified",o)

    @unittest.skipUnless((probe.PRIOR/"STATUS.json").exists(),
                         "Real GitHub source artifact is mounted only in dedicated one-shot replay workflow")
    def test_all_ten_authentic_provider_wires_and_old_bug_cases(self):
        passages,first_ratings,events=probe.replay_first_real_run()
        self.assertEqual(len(events),10)
        self.assertEqual(len(passages),4)
        self.assertEqual(set(first_ratings),{"fantasy","scifi"})
        self.assertEqual(passages["realism"]["WF_provenance"]["V96_status"],
                         "SOURCE_TRACE_VERIFIED")
        self.assertIsNotNone(
            passages["realism"]["WF_provenance"]["V96_normalization_receipt"])
        self.assertEqual(passages["mystery"]["WF_provenance"]["V96_status"],
                         "HELD_TRACE_UNVERIFIED")
        self.assertEqual(passages["mystery"]["WF_provenance"]["V96_failure_code"],
                         "WF96_ACTION_EFFECT_OVERLAP_OR_REVERSED")
        self.assertEqual(first_ratings["fantasy"]["裸模型"]["id"],"甲")
        self.assertEqual(first_ratings["fantasy"]["WF辅助"]["id"],"乙")
        self.assertEqual(passages["scifi"]["WF_provenance"]["V116_hard_findings"],[])

if __name__=="__main__":
    unittest.main()
