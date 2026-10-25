"""No-model preflight for authentic 0.T B second-turn repair continuation."""
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase, skipUnless
from unittest.mock import patch
import inspect
import json
import shutil

from experiments import wf_0t_real_B_reader_repair_downstream_20261025 as exp


class ReadBeforeAnyProvider(TestCase):
    def test_provider_source_and_contract_are_not_replaced_with_fake(self):
        self.assertEqual(exp.MAX_CALLS,6)
        self.assertLessEqual(exp.MAX_OUTPUT,8000)
        self.assertEqual(exp.PRIOR_RUN,40163959949)
        self.assertEqual(len(exp.PRIOR_WIRES),2)
        for phrase in exp.COMPETING_SPANS:
            self.assertGreater(len(phrase),6)
        main=inspect.getsource(exp.main)
        self.assertLess(main.index("read_old_real_sources()"),
                        main.index("SameWriter(key)"))
        self.assertIn('choice["decision"]=="MOVE_ON"',main)
        self.assertIn("return",main)
        self.assertIn("changed_source_sha256",main)
        self.assertIn("no_external_critic",main)
        self.assertNotIn("source_windows(",main)
        self.assertNotIn("download_existing_pinned_r2(",main)
        self.assertNotIn("WF_FORCE_REWRITE",main)

    def test_next_beat_is_model_chosen_not_host_fiction(self):
        class Fake:
            def call(self,stage,packet,*,max_tokens):
                selfouter.assertEqual(stage,"new-third-plan")
                return json.dumps({"turn":{
                    "id":"t03","kind":"quiet","actor":"林栖",
                    "goal":"在上一段已经发生的结果之后自行选择谨慎观察，不使秘密凭空被知晓",
                    "causal_parent":"t02","craft_focus":[]}},
                    ensure_ascii=False)
        selfouter=self
        dummy=[
            {"prose":"前段已发生且已写明的散文。"*9,
             "effect_quote":"前段已发生且已写明的散文。"},
            {"prose":"后段作者新写出的动作与后果。"*9,
             "effect_quote":"后段作者新写出的动作与后果。"}
        ]
        result=exp.new_third_beat(Fake(),dummy)
        self.assertEqual(result["id"],"t03")
        self.assertEqual(result["causal_parent"],"t02")

    @skipUnless(Path("wf0t_prior_paired_originals/STATUS.json").exists(),
                "Authentic prior artifact not mounted outside dedicated workflow")
    def test_actual_prior_real_wire_and_scene_recheck(self):
        first,second,one,two,cp1,cp2=exp.read_old_real_sources()
        self.assertEqual(exp.sha(one["prose"]),exp.PRIOR_B_FIRST)
        self.assertEqual(exp.sha(two["prose"]),exp.PRIOR_B_SECOND)
        self.assertEqual(one["receipt"]["causal_check"],
                         "EXACT_OBSERVABLE_ANCHORS_ONLY")
        self.assertEqual(two["receipt"]["causal_check"],
                         "EXACT_OBSERVABLE_ANCHORS_ONLY")
        self.assertEqual(cp2["previous_checkpoint_sha256"],
                         cp1["receipt_sha256"])
        self.assertEqual(cp1["canon_writes"],0)
        self.assertEqual(cp2["canon_writes"],0)
        self.assertNotEqual(first,second)

    @skipUnless(Path("wf0t_prior_paired_originals/STATUS.json").exists(),
                "Authentic prior artifact not mounted outside dedicated workflow")
    def test_corrupted_authentic_source_always_fails_before_any_model(self):
        if not shutil.which("node"):
            self.skipTest("No upstream Novel Studio Node reducer")
        with TemporaryDirectory() as d:
            new=Path(d)
            src=Path("wf0t_prior_paired_originals")
            shutil.copytree(src,new/"pair")
            victim=new/"pair"/"B"/"stage-02-real-author-prose.md"
            victim.write_text(victim.read_text("utf8")+"伪",encoding="utf8")
            with patch.object(exp,"PRIOR",new/"pair"):
                with self.assertRaisesRegex(
                    RuntimeError,"WF0T_PINNED_WRITER_PROSE_CHANGED"):
                    exp.read_old_real_sources()


if __name__=="__main__":
    import unittest
    unittest.main()
