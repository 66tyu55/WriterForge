"""Offline contract: both writer arms reuse exact first-turn real source.

No model calls, no fabricated comparison result or score. Verify only the
host's gated adapter mechanics; actual prose enters through live experiment.
"""
import inspect
import unittest

from experiments import wf_same_first_turn_literary_ab as trial


class FakeModel:
    def __init__(self):
        self.calls=0
        self.last_response_format_recovery={"stale":"must not leak"}
        self._on_response_wire=None

    def ask_json(self,*,role,system,user,max_tokens):
        self.calls+=1
        assert max_tokens==1450
        return {"prose":"真实模型下一段只在实跑时生成",
                "trace":{"action_quote":None,"effect_quote":None,
                         "parent_effect_quote":None}}


class SharedProseExperiment(unittest.TestCase):
    def test_first_is_original_replay_and_only_second_hits_model(self):
        old={"prose":"实际旧模型返回的完整第一段原文。",
             "trace":{"action_quote":None,"effect_quote":None,
                      "parent_effect_quote":None}}
        model=FakeModel()
        client=trial.SharedRealFirstTurn(old,model)
        client._on_response_wire=lambda raw:None
        self.assertIs(client._on_response_wire,model._on_response_wire)
        first=client.ask_json(role="self_scene_writing",
                              system="JSON",user="anything",max_tokens=1450)
        self.assertEqual(first,old)
        first["prose"]="试图篡改"
        self.assertEqual(old["prose"],"实际旧模型返回的完整第一段原文。")
        self.assertEqual(model.calls,0)
        self.assertIsNone(client.last_response_format_recovery)
        next_value=client.ask_json(role="self_scene_writing",
                                   system="JSON",user="new",max_tokens=1450)
        self.assertIn("prose",next_value)
        self.assertEqual(model.calls,1)
        self.assertEqual(client.replay_count,1)
        self.assertEqual(client.live_count,1)
        with self.assertRaisesRegex(RuntimeError,
                                    "WF_SHARED_TURN_CALLS_OUT_OF_BOUNDS"):
            client.ask_json(role="self_scene_writing",
                            system="JSON",user="again",max_tokens=1450)

    def test_exact_prespecified_original_provenance(self):
        self.assertEqual(trial.MAX_REAL_PROVIDER_CALLS,2)
        self.assertEqual(trial.OUTPUT_LIMIT,2900)
        self.assertEqual(set(trial.EXACT_SHA),{"plot","climax","horror"})
        for case,entries in trial.EXACT_SHA.items():
            self.assertEqual(len(entries),3)
            self.assertTrue(all(len(x)==64 for x in entries.values()))
        self.assertIn("same_first_turn_json_and_both_wf_prompts",
                      inspect.getsource(trial.main))
        self.assertIn("same_first_turn",trial.__doc__.lower().replace("-","_"))

if __name__=="__main__":
    unittest.main()
