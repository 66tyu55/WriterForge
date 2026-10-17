"""Offline old-vs-semantic head-to-head, no paid API requests."""
import unittest
from hashlib import sha256

from writerforge.reverse_real_training import raw_hash
from writerforge.reverse_semantic_evidence import validate_semantic_selections
from writerforge.reverse_cloud_ab import ABTrialError
from writerforge.v29_old_new_trial import (
    compare_old_vs_semantic,SemanticTrialAbstained,BUDGET_PROFILE,
    COMMON_TARGET,effective_task,
)
from writerforge.v29_fresh_holdout import chosen_ids,manifest,manifest_sha,task
from scripts.run_v29_old_new_holdout import root_for_slot,run
from writerforge.reverse_discovery_models import ROLE_MODELS,DiscoveryError

SOURCE=("少年只知道旧桥因雨损坏，伸手摸见木板松动，随即停步寻找别处道路。"+chr(10)
       +"他仍不知道是谁事先挪走一块桥板，雨水遮掩了原本可以观察的细节。"+chr(10)
       +"更远处传来一声急促铃响，少年发现响声与桥上脚步的先后顺序不一致。"+chr(10))*7
SPAN="少年只知道旧桥因雨损坏，伸手摸见木板松动"

class Planner:
    provider="test"
    name="fake-flash"
    def __init__(self,decision="SUPPORTED_FOR_TRIAL",bad=False):
        self.calls=[];self.decision=decision;self.bad=bad
    def ask(self,sys,user,*,num_predict):
        self.calls.append((sys,user,num_predict))
        if len(self.calls)==1:
            return {"selections":[{"id":"GOAL_FILTERS_ATTENTION","evidence_ids":["P0"]}]}
        return {"selections":[{
            "id":"GOAL_FILTERS_ATTENTION","evidence_id":"P0",
            "source_span":("不存在的虚假文字覆盖原著片段" if self.bad else SPAN),
            "character_knowledge":"少年只知道他眼前的木桥松动，不知道有人是否暗中挪动了桥板。",
            "local_cause_effect":"触摸木板的触觉结果让人物暂停冒险前行，从而改变下一步道路决策。",
            "new_task_fit":"新故事里人物的目标与自己有限的直接观察必须相互限制而不能突然全知。",
            "misuse_risk":"过分使用注意筛选会让人物不像慌乱中的人，而像全知的推理机器。",
            "decision":self.decision
        }]}

class Writer:
    provider="test"
    name="fake-glm"
    def __init__(self):
        self.calls=[]
    def ask(self,sys,user,*,num_predict):
        self.calls.append((sys,user,num_predict))
        text=("少年踩进湿滑的山路，发现桥板松动后选择迂回寻找村庄。"
              "他很害怕，却仍紧握随身的一封信。")*19
        if len(self.calls)==2:text=text.replace("山路","坡路")
        return {"scene":text}

class Critic:
    provider="test"
    name="fake-deepseek"
    def __init__(self):
        self.calls=[]
    def ask(self,sys,user,*,num_predict):
        self.calls.append((sys,user,num_predict))
        names=("perception","causality","information","continuity","language")
        return {"A":{n:{"score":85,"reason":"故事中的角色观察链条尚需进一步独立审稿验证"} for n in names},
                "B":{n:{"score":83,"reason":"人物行动和线索的关系仍需要人类审稿者进一步确认"} for n in names},
                "uncertainty":"这种双稿评审只是单个模型的观察，不能证明文学技能真正提高。"}
class HoldoutTests(unittest.TestCase):
    def test_three_new_prompts_fixed_before_inference(self):
        keys=chosen_ids()
        self.assertEqual(len(keys),3)
        self.assertEqual(len(set(keys)),3)
        self.assertEqual(len(manifest_sha()),64)
        self.assertEqual(manifest()["task_sha256"],
                         [raw_hash(task(i)) for i in range(3)])
        self.assertEqual(BUDGET_PROFILE,(4200,7700,6500))
        self.assertLessEqual(2*BUDGET_PROFILE[0]+4*BUDGET_PROFILE[1]+BUDGET_PROFILE[2],
                             50000)
        self.assertEqual(ROLE_MODELS["writer"],"glm-5.3")
    def test_real_structure_uses_two_planners_two_writers_one_critic(self):
        p,w,c=Planner(),Writer(),Critic()
        report=compare_old_vs_semantic(
            planner=p,writer=w,critic=c,first=SOURCE,second="后续合成场景"*100,
            source_sha="a"*64,source_window_sha=raw_hash(SOURCE),writing_task=task(0))
        self.assertEqual(len(p.calls),2)
        self.assertEqual(len(w.calls),2)
        self.assertEqual(len(c.calls),1)
        self.assertEqual(report["model_roles"]["writer"],"fake-glm")
        self.assertTrue(report["same_host_mechanisms_selected"])
        self.assertFalse(report["core_promoted"])
        self.assertFalse(report["human_independent_review"])
        self.assertFalse(report["source_sent_to_writer_or_critic"])
        self.assertNotIn(SOURCE,w.calls[0][1])
        self.assertNotIn(SPAN,w.calls[1][1])
        self.assertNotIn(SOURCE,c.calls[0][1])
        self.assertNotIn("legacy",c.calls[0][1])
        self.assertNotIn("semantic",c.calls[0][1])
        self.assertEqual(set(report["comparisons"]),{"legacy","semantic"})
        self.assertIsInstance(report["semantic_minus_legacy_model_mean"],float)
    def test_model_abstention_means_no_writer_no_score(self):
        p,w,c=Planner(decision="RISK_IN_THIS_TASK"),Writer(),Critic()
        with self.assertRaises(SemanticTrialAbstained) as caught:
            compare_old_vs_semantic(
                planner=p,writer=w,critic=c,first=SOURCE,second="合成"*120,
                source_sha="a"*64,source_window_sha=raw_hash(SOURCE),
                writing_task=task(1))
        self.assertEqual(len(p.calls),2)
        self.assertEqual(len(w.calls),0)
        self.assertEqual(len(c.calls),0)
        self.assertIsNone(caught.exception.safe_candidate["literary_quality_score"])
    def test_hallucinated_source_span_fails_before_generation(self):
        p,w,c=Planner(bad=True),Writer(),Critic()
        with self.assertRaises(Exception):
            compare_old_vs_semantic(
                planner=p,writer=w,critic=c,first=SOURCE,second="合成"*120,
                source_sha="a"*64,source_window_sha=raw_hash(SOURCE),
                writing_task=task(2))
        self.assertEqual(len(w.calls),0)
    def test_invalid_slot_never_sees_secrets(self):
        for slot in (-1,3,None,"0"):
            with self.subTest(slot=slot):
                with self.assertRaisesRegex(DiscoveryError,"INVALID_FRESH_HOLDOUT_SLOT"):
                    run(slot=slot)
if __name__=="__main__":
    unittest.main()
