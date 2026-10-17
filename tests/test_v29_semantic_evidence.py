"""No-network semantic evidence protocol; all source prose synthetic."""
import unittest
from writerforge.reverse_semantic_evidence import (
    semantic_proposal_prompt,validate_semantic_selections,
)
from writerforge.reverse_mechanism_boundary import (
    source_paragraphs,MechanismBoundaryError,TECHNIQUES,
)
from writerforge.reverse_real_training import raw_hash
from writerforge.reverse_cloud_ab import CloudABTrial,ABTrialError
from test_v28_cloud_ab import FakeModel,CRITIC

SOURCE=(
    "学徒抬起灯照见山岩上崭新的裂痕，才决定停止推车并向前探路。\n"
    "他很清楚暴雨已经冲毁背后的路，却不知道前面的木桥也开始松动。\n"
    "那道细响被下一阵雨声盖过，他仍记住了铃铛没有随风摇动的异样。\n"
)*7
TASK=("一个少年因大雨夜里无法归家，在旧塔发现线索后不得不作出有代价的决定。"
      "写完整第一章，留具体但尚未解释的结尾悬念。")

def payload(*,wrong_span=False,decision="SUPPORTED_FOR_TRIAL"):
    return {"selections":[{
        "id":"WITHHOLD_CAUSE_SHOW_CLUE",
        "evidence_id":"P2",
        "source_span":"那道细响被下一阵雨声盖过，他仍记住了铃铛",
        "character_knowledge":"角色只能记住铃声似乎不同寻常，但不知道造成声音的东西到底是什么。",
        "local_cause_effect":"对异样铃声的观察影响他后来的路线判断，但原因暂时没有进入角色视野。",
        "new_task_fit":"在这部新的夜间逃亡故事里，一个可以回查的小线索能服务人物判断与末尾悬念。",
        "misuse_risk":"若不断重复制造怪声而不让少年采取动作，会变成无意义的神秘名词和细节清单。",
        "decision":decision,
    }]}

class SemanticEvidenceTests(unittest.TestCase):
    def setUp(self):self.paragraphs=source_paragraphs(SOURCE)

    def test_real_exact_source_anchor_does_not_prove_meaning(self):
        proposal=semantic_proposal_prompt(self.paragraphs,writing_task=TASK)
        self.assertIn("new_task_fit",proposal)
        choices,meta=validate_semantic_selections(payload(),self.paragraphs,
                                                   writing_task=TASK)
        self.assertEqual(choices[0]["id"],"WITHHOLD_CAUSE_SHOW_CLUE")
        self.assertEqual(meta["selected_count"],1)
        self.assertTrue(meta["observed"][0]["source_span_exact_match"])
        self.assertFalse(meta["observed"][0]["semantic_truth_independently_verified"])
        self.assertFalse(meta["observed"][0]["task_fit_independently_verified"])
        self.assertNotIn("那道细响",str(meta))
        self.assertNotIn("学徒抬起灯",str(meta))

    def test_hallucinated_anchor_fails_closed(self):
        doc=payload()
        doc["selections"][0]["source_span"]="绝对不存在于原本引用段落的一小段虚构陈述"
        with self.assertRaisesRegex(MechanismBoundaryError,"SEMANTIC_EVIDENCE_NOT_IN_SOURCE"):
            validate_semantic_selections(doc,self.paragraphs,writing_task=TASK)

    def test_risky_task_explicitly_abstains_without_writer(self):
        choices,meta=validate_semantic_selections(payload(decision="RISK_IN_THIS_TASK"),
                                    self.paragraphs,writing_task=TASK)
        self.assertEqual(choices,())
        p=FakeModel("planner",payload(decision="RISK_IN_THIS_TASK"),"p")
        w=FakeModel("writer",{},"w")
        critic=FakeModel("critic",CRITIC,"c")
        with self.assertRaisesRegex(ABTrialError,"NO_VERIFIED_TRANSFERABLE_MECHANISM"):
            CloudABTrial(planner=p,writer=w,critic=critic,evidence_first=True,
                         semantic_evidence_first=True).run(
                SOURCE,"合成下段"*70,source_sha="a"*64,
                window_hash=raw_hash(SOURCE),writing_task=TASK)
        self.assertEqual(len(p.calls),1)
        self.assertEqual(len(w.calls),0)
        self.assertEqual(len(critic.calls),0)

    def test_good_candidate_writer_receives_only_host_technique(self):
        p=FakeModel("planner",payload(),"p")
        w=FakeModel("writer",{},"w")
        critic=FakeModel("critic",CRITIC,"c")
        outcome=CloudABTrial(planner=p,writer=w,critic=critic,
                      evidence_first=True,semantic_evidence_first=True).run(
            SOURCE,"合成后续"*60,source_sha="a"*64,
            window_hash=raw_hash(SOURCE),writing_task=TASK)
        self.assertEqual(len(w.calls),2)
        self.assertTrue(outcome["semantic_evidence_first_opt_in"])
        self.assertEqual(outcome["semantic_evidence_candidate"]["selected_count"],1)
        self.assertFalse(outcome["core_automatically_promoted"])
        self.assertNotIn("那道细响",w.calls[1][1])
        self.assertNotIn("local_cause_effect",w.calls[1][1])
        self.assertNotIn("source_span",w.calls[1][1])
        self.assertIn("WITHHOLD_CAUSE_SHOW_CLUE",w.calls[1][1])

    def test_legacy_behavior_and_requires_explicit_opt_in(self):
        p=FakeModel("planner",payload(),"p")
        w=FakeModel("writer",{},"w")
        c=FakeModel("critic",CRITIC,"c")
        with self.assertRaisesRegex(ABTrialError,"SEMANTIC_GATE_MUST_BE_EVIDENCE_FIRST"):
            CloudABTrial(planner=p,writer=w,critic=c,semantic_evidence_first=True)
        self.assertEqual(len(p.calls),0)

if __name__=="__main__":
    unittest.main()
