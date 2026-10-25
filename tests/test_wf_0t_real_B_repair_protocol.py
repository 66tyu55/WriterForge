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


class CompactSourceReaderBudget(TestCase):
    """A limited same-writer reader profile, no new reviewer model."""
    def test_compact_output_schema_exact_quotes_and_concise_model_prompt(self):
        from writerforge.writing_assist import _reader_separates_written_and_inferred
        from writerforge.verified_flow import GroundedDraftPacket
        prior=("昨日程满把那截麻绳递给林栖，让他绑在桩头作测潮记号。"
               "他重新摸了一遍结，随后领人收工回镇。")
        now=("天亮前林栖重新登上潮堤，绳结仍系在木桩上。"
             "奇怪的是那条绳子已经被人解下来，绕在一块石头旁。"
             "他查看留下的瓦片，并把所有细节记录在自己的潮簿里。"
             "午后他准备带着这一页记录去询问测潮人程满。")
        self.assertGreaterEqual(len(now),80)
        first="绳结仍系在木桩上"
        second="那条绳子已经被人解下来"
        older="昨日程满把那截麻绳递给林栖"
        reply={
            "observed":[{"quote":first,"actor":"林栖",
                         "visible_action":"观察木桩上的绳结"}],
            "inferred_links":[{"before_quote":first,"after_quote":second,
                               "reader_imagined_step":"中间可能缺少绳结状态的说明"}],
            "cross_source_links":[{"previous_quote":older,
                                   "current_quote":second,
                                   "reader_imagined_step":"从昨日交付到当前解绑存在未写出的动作"}],
            "reader_uncertainty":"不确定绳结与绳子是否为同一个被系住的对象",
        }
        prompts=[]
        def same_novelist(packet,*,model,api_base,max_tokens):
            self.assertIsNone(model)
            self.assertIsNone(api_base)
            self.assertEqual(max_tokens,1000)
            self.assertIn("最多三处",packet.prompt)
            self.assertIn("最多一处",packet.prompt)
            self.assertNotIn("最多八处",packet.prompt)
            self.assertNotIn("PRIVATE AUTHOR OUTLINE",packet.prompt)
            prompts.append(packet.prompt)
            return json.dumps(reply,ensure_ascii=False)
        prompt="PRIVATE AUTHOR OUTLINE - cannot pass into source-only reader"
        packet=GroundedDraftPacket(
            project_id="source-profile-project",
            scene_id="source-profile-scene",snapshot_id=0,
            evidence=(),craft_ids=(),prompt=prompt,
            prompt_sha256=exp.sha(prompt))
        with TemporaryDirectory() as d:
            result=_reader_separates_written_and_inferred(
                raw=json.dumps({"prose":now,"trace":{
                    "action_quote":None,"effect_quote":None,
                    "parent_effect_quote":None}},ensure_ascii=False),
                turn_packet=packet,ask_model=same_novelist,
                directory=Path(d)/"compact",
                earlier_source=prior,
                earlier_source_sha256=exp.sha(prior),
                compact_source_review=True)
            self.assertEqual(result["status"],
                             "SOURCE_ANCHORED_READER_HYPOTHESES",result)
            self.assertEqual(len(result["report"]["inferred_links"]),1)
            self.assertEqual(len(result["report"]["cross_source_links"]),1)
            self.assertEqual(len(prompts),1)
            self.assertTrue(result["receipt"]["compact_source_review"])
            self.assertFalse(result["receipt"]["literary_quality_verified"])
            self.assertEqual(result["receipt"]["canon_writes"],0)

    def test_compact_reader_refuses_extra_observations_without_force_accept(self):
        from writerforge.writing_assist import _reader_separates_written_and_inferred
        from writerforge.verified_flow import GroundedDraftPacket
        source=("林栖查看海堤的刻度，发现昨日留下的绳结已在另一个地方。"
                "他看见有人从远处走来，却没有立刻走过去说出全部疑虑。"
                "他决定先把亲眼所见的每一项刻度抄进潮簿，留作明日比照。")
        clause="林栖查看海堤的刻度"
        reply={"observed":[{"quote":clause,"actor":"林栖",
                          "visible_action":"记录自己的观察"}]*4,
               "inferred_links":[],"reader_uncertainty":"无法确定"}
        pkt=GroundedDraftPacket(
            project_id="source-profile-test",scene_id="solo",snapshot_id=0,
            evidence=(),craft_ids=(),prompt="never-leak-plan",
            prompt_sha256=exp.sha("never-leak-plan"))
        with TemporaryDirectory() as d:
            out=_reader_separates_written_and_inferred(
                raw=json.dumps({"prose":source,"trace":{
                    "action_quote":None,"effect_quote":None,
                    "parent_effect_quote":None}},ensure_ascii=False),
                turn_packet=pkt,
                ask_model=lambda *args,**kwargs:json.dumps(
                    reply,ensure_ascii=False),
                directory=Path(d)/"invalid",
                compact_source_review=True)
            self.assertEqual(out["status"],"INVALID_READER_SOURCE")
            self.assertIsNone(out["report"])
            self.assertTrue(out["receipt"]["compact_source_review"])



if __name__=="__main__":
    import unittest
    unittest.main()
