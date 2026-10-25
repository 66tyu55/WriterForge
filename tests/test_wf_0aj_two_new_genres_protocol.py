"""0.AJ third two-genre original microfiction preflight: zero provider calls."""
from __future__ import annotations
import inspect
import unittest

from experiments import wf_0ag_diverse_micro_paired_20261025 as original
from experiments import wf_0ah_diverse_micro_paired_20261025 as second
from experiments import wf_0aj_diverse_micro_paired_20261025 as trial


class ThirdTwoGenreFailureFirstProtocol(unittest.TestCase):
    def test_only_two_new_frozen_scenes_never_repeat_first_six(self):
        self.assertEqual(trial.BATCH,("romance_photos","scifi_airlock"))
        self.assertEqual(trial.GENRES,original.GENRES)
        self.assertEqual(trial.GENRES,second.GENRES)
        self.assertTrue(set(trial.BATCH).isdisjoint(original.BATCH))
        self.assertTrue(set(trial.BATCH).isdisjoint(second.BATCH))
        self.assertEqual([trial.SCENE_BY_ID[i]["genre"] for i in trial.BATCH],
                         ["言情","科幻灾难"])
        self.assertEqual(trial.SCENE_BY_ID["romance_photos"]["kind"],"dialogue")
        self.assertEqual(trial.SCENE_BY_ID["scifi_airlock"]["kind"],"decision")
        self.assertEqual(trial.MAX_CALLS,8)
        self.assertEqual(trial.OUTPUT_RESERVATION_CAP,12000)
        self.assertEqual(trial.AUTHOR_OUTPUT_TOKENS,1400)
        self.assertEqual(trial.RATER_OUTPUT_TOKENS,1600)

    def test_literary_prompt_is_frozen_but_decision_may_report_pending_effect(self):
        for scene in trial.BATCH:
            item=trial.SCENE_BY_ID[scene]
            common=trial.scene_prompt(item)
            bare=trial.prompt(item,"bare")
            wf=trial.prompt(item,"WF")
            self.assertTrue(bare.startswith(common))
            self.assertTrue(wf.startswith(common))
            self.assertIn("200至350",common)
            self.assertEqual(trial.h(common),original.h(original.scene_prompt(item)))
        scifi=trial.SCENE_BY_ID["scifi_airlock"]
        wf=trial.prompt(scifi,"WF")
        self.assertIn("effect_quote 可填 JSON null",wf)
        self.assertIn("引句先后不证明因果",wf)

    def test_frozen_provider_wire_and_complete_but_not_overclaimed_grades(self):
        source=inspect.getsource(trial.Model)
        run=inspect.getsource(trial.main)
        audit=inspect.getsource(trial.check_source)
        self.assertIn("on_response_wire=self.save_wire",source)
        self.assertIn("WF0AJ_DUPLICATE_PROVIDER_WIRE_NO_OVERWRITE",source)
        self.assertNotIn("retry(",source.lower()+run.lower())
        self.assertIn("case[arm+\"_source_sha256\"]",run)
        self.assertIn("case[arm+\"_within_200_350\"]",run)
        self.assertIn("lengths_comparable_within_15pct",run)
        self.assertIn("NOT_COMPARABLE",run)
        self.assertIn('"Canon_writes":0',run)
        self.assertIn('"Railway_deployments":0',run)
        self.assertIn("candidate_accepted_into_Canon",audit)
        self.assertIn('"model_or_WF_literary_truth_verified":False',audit)
        self.assertEqual(len(trial.JUDGEMENTS),2)
        self.assertEqual(len(trial.CRITERIA),5)

    def test_reuses_real_lossless_score_decoder_not_a_second_judge(self):
        self.assertIs(trial.parse_micro_judge,second.parse_micro_judge)
        data={"ratings":{
            "甲":{"scores":[15,16,17,16,16],
                 "reason":"情节有节奏，也保留两位人物各自未知的信息。",
                 "weakness":"人物语气仍有点趋同，需留更多空间。"},
            "乙":{"scores":[16,16,16,16,16],
                 "reason":"通讯延时与环境限制实际影响角色抉择。",
                 "weakness":"物理压力的危险程度尚不够清楚。"},
        }}
        result,receipt=trial.parse_micro_judge(data)
        self.assertEqual(sum(result["甲"]["scores"].values()),80)
        self.assertEqual(sum(result["乙"]["scores"].values()),80)
        self.assertTrue(receipt["numeric_scores_unchanged"])
        self.assertEqual(receipt["extra_model_calls"],0)


if __name__=="__main__":
    unittest.main()
