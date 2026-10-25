"""0.AG score-only recovery: auth frozen 9 paid wires, never regenerate authors."""
from __future__ import annotations
import inspect
import unittest

from experiments import wf_0ag_replay_three_real_micro_scores_only_20261025 as p
from experiments import wf_0ag_diverse_micro_paired_20261025 as e


class ScoreOnlySourceReplay(unittest.TestCase):
    def test_first_real_blind_five_scores_recovered_in_frozen_order(self):
        if not (p.PRIOR/"STATUS.json").exists():
            self.skipTest("Nine old true provider wires only in dedicated zero-author replay job")
        verified,manifest,calls=p.replay_old_first_once()
        self.assertEqual(len(verified),3)
        self.assertEqual(len(calls),9)
        frozen={
            "wuxia_bridge":(84,80),
            "horror_flashlight":(86,83),
            "strategy_ledger":(73,75),
        }
        for k,(bare,wf) in frozen.items():
            row=verified[k]
            self.assertEqual(row["first_ratings"]["裸模型"]["score"],bare)
            self.assertEqual(row["first_ratings"]["WF辅助"]["score"],wf)
            self.assertEqual(row["first_ratings"]["裸模型"][
                "score_representation_receipt"][
                "score_arrangement_recovered"],2)
            self.assertFalse(row[
                "source_verified_again_without_model"][
                "model_or_WF_literary_truth_verified"])
            self.assertTrue(row["score_schema_issue_confirmed_from_provider_wire"])
        self.assertEqual(manifest["actual_model_calls"],9)

    def test_second_judge_can_only_be_blind_reverse_and_budgeted(self):
        src=inspect.getsource(p.OnlyReverseJudge)
        self.assertIn('task=="blind-2"',src)
        self.assertIn('role=="craft_analysis"',src)
        self.assertIn('max_tokens==RATER_OUTPUT_TOKENS',src)
        self.assertIn('on_response_wire=self.on_original',src)
        self.assertIn("target.write_bytes(raw)",src)
        self.assertEqual(p.MAX_NEW_CALLS,3)
        self.assertEqual(p.RESERVED_NEW_OUTPUT_TOKENS,4800)
        self.assertEqual(p.FROZEN_RUN,40198761026)
        self.assertEqual(p.BATCH,("wuxia_bridge","horror_flashlight",
                                  "strategy_ledger"))
        run=inspect.getsource(p.main)
        self.assertIn("replay_old_first_once()",run)
        self.assertNotIn('role="self_scene_writing"',run)
        self.assertIn('new_writer_requests":0',run)

    def test_all_score_recovery_is_math_not_literary_promotion(self):
        values={
            "裸模型":{"score":84,"dimensions":dict(zip(e.CRITERIA,
                                [17,18,17,16,16]))},
            "WF辅助":{"score":80,"dimensions":dict(zip(e.CRITERIA,
                                [16,17,15,17,15]))},
        }
        back={
            "裸模型":{"score":80,"dimensions":dict(zip(e.CRITERIA,
                                [16,16,16,16,16]))},
            "WF辅助":{"score":82,"dimensions":dict(zip(e.CRITERIA,
                                [16,17,17,16,16]))},
        }
        scores,diff=p.combine(values,back)
        self.assertEqual(scores["裸模型"]["score_100"],82)
        self.assertEqual(scores["WF辅助"]["score_100"],81)
        self.assertEqual(diff,-1)
        self.assertEqual(scores["裸模型"]["two_blind_order_scores"],[84,80])
        self.assertEqual(scores["WF辅助"]["two_blind_order_scores"],[80,82])


if __name__=="__main__":
    unittest.main()
