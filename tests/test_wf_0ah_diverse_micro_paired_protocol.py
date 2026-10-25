"""0.AH offline preregistration tests: do not call DeepSeek or read originals."""
from __future__ import annotations

import inspect
import unittest

from experiments import wf_0ag_diverse_micro_paired_20261025 as prev
from experiments import wf_0ah_diverse_micro_paired_20261025 as trial


class TestSecondThreeDifferentLiteraryScenes(unittest.TestCase):
    def test_only_next_three_frozen_nonrepeated_scenes(self):
        self.assertEqual(trial.BATCH,(
            "xianxia_plant","history_message","comedy_breakfast"))
        self.assertTrue(set(trial.BATCH).isdisjoint(prev.BATCH))
        self.assertEqual(trial.GENRES,prev.GENRES)
        self.assertEqual(len(trial.GENRES),10)
        self.assertEqual(trial.MAX_CALLS,12)
        self.assertEqual(len(trial.BATCH),3)
        roles=[trial.SCENE_BY_ID[key]["role"] for key in trial.BATCH]
        self.assertEqual(len(set(roles)),3)
        self.assertEqual(
            [trial.SCENE_BY_ID[x]["genre"] for x in trial.BATCH],
            ["仙侠","历史","喜剧"])
        self.assertNotEqual(trial.OUT,prev.OUT)
        self.assertIn("batch2",str(trial.OUT))
        self.assertTrue(all(x not in str(trial.OUT) for x in prev.BATCH))

    def test_same_writer_model_budget_scope_and_true_prose_lengths(self):
        self.assertEqual(trial.AUTHOR_OUTPUT_TOKENS,1400)
        self.assertEqual(trial.RATER_OUTPUT_TOKENS,1600)
        self.assertEqual(trial.OUTPUT_RESERVATION_CAP,18000)
        for key in trial.BATCH:
            item=trial.SCENE_BY_ID[key]
            bare=trial.prompt(item,"bare")
            assisted=trial.prompt(item,"WF")
            shared=trial.scene_prompt(item)
            self.assertTrue(bare.startswith(shared))
            self.assertTrue(assisted.startswith(shared))
            self.assertIn("200至350",bare)
            self.assertIn("200至350",assisted)
            self.assertEqual(trial.h(shared),prev.h(prev.scene_prompt(item)))
            self.assertEqual(trial.beat(item),prev.beat(item))
        code=inspect.getsource(trial.main)
        self.assertIn("AUTHOR_OUTPUT_TOKENS)",code)
        self.assertIn("RATER_OUTPUT_TOKENS",inspect.getsource(trial.judge_one))
        self.assertIn('case[arm+"_source_sha256"]',code)
        self.assertIn("case[arm+\"_within_200_350\"]",code)
        self.assertIn("lengths_comparable_within_15pct",code)
        self.assertIn("NOT_COMPARABLE",code)
        self.assertIn("LOW_CONFIDENCE",code)

    def test_no_retry_source_overwrite_or_literary_judge_promoted_as_fact(self):
        code=inspect.getsource(trial.Model)
        main=inspect.getsource(trial.main)
        self.assertIn("on_response_wire=self.save_wire",code)
        self.assertIn("WF0AH_DUPLICATE_PROVIDER_WIRE_NO_OVERWRITE",code)
        self.assertIn("original_wire_preserved",code)
        self.assertNotIn("retry(",code.lower()+main.lower())
        self.assertNotIn("time.sleep",code.lower()+main.lower())
        self.assertIn('"R2_reads":0',main)
        self.assertIn('"Canon_writes":0',main)
        self.assertIn('"Railway_deployments":0',main)
        check=inspect.getsource(trial.check_source)
        self.assertIn("normalize_model_source_citations",check)
        self.assertIn("check_turn",check)
        self.assertIn("preflight_next_prose",check)
        self.assertIn("external_temporal_step",check)
        self.assertIn('"model_or_WF_literary_truth_verified":False',check)
        self.assertIn('"candidate_accepted_into_Canon":False',check)
        self.assertIn('"false_positive_count_confirmed":None',check)

    def test_first_batch_real_rater_shape_fixes_still_available(self):
        self.assertIsNot(trial.parse_micro_judge,prev.parse_micro_judge)
        valid={"ratings":{
            "甲":{"scores":[17,16,15,18,17],
                 "reason":"人物行为与已知资料保持一致，细节有作用。",
                 "weakness":"意图尚可以表达得更自然一些。"},
            "乙":{"scores":[15,15,16,15,15],
                 "reason":"空间状态有意保留，节奏没有强迫反转。",
                 "weakness":"部分场景过渡暂时还不够自然。"},
        }}
        parsed,receipt=trial.parse_micro_judge(valid)
        self.assertEqual(sum(parsed["甲"]["scores"].values()),83)
        self.assertEqual(sum(parsed["乙"]["scores"].values()),76)
        self.assertEqual(receipt["labelled_map_rows_losslessly_rekeyed"],2)
        self.assertEqual(receipt["score_arrangement_recovered"],2)
        self.assertTrue(receipt["numeric_scores_unchanged"])
        self.assertTrue(receipt["model_reason_and_weakness_unchanged"])
        self.assertEqual(receipt["extra_model_calls"],0)

    def test_natural_quiet_comedy_does_not_require_forced_action_trace(self):
        self.assertEqual(trial.SCENE_BY_ID["comedy_breakfast"]["kind"],"dialogue")
        self.assertEqual(trial.SCENE_BY_ID["xianxia_plant"]["kind"],"decision")
        self.assertEqual(trial.SCENE_BY_ID["history_message"]["kind"],"decision")
        self.assertNotIn("new literary memory",inspect.getsource(trial))
        self.assertEqual(len(trial.JUDGEMENTS),2)


if __name__=="__main__":
    unittest.main()
