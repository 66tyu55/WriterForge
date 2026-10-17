"""V33 no-network realistic full-chain exam: true frozen memory, length and JSON repair."""
from __future__ import annotations
import json,unittest
from unittest.mock import patch

from test_v32_examiner_blind import FakeStore
import scripts.run_v32_examiner_blind as v32
import scripts.run_v33_repair_e2e as runner
import scripts.audit_v33_repair_e2e as auditor
from writerforge.v33_repair_topics import ids,manifest_sha,question
from writerforge.v33_exam_contracts import DIMENSIONS

UNIT="少年在清晨的山路尽头看见新近修好的石桥，想起自己答应同伴的事情。"

def text_at(n):
    return (UNIT*((n+len(UNIT)-1)//len(UNIT)))[:n]

class Writer:
    def __init__(self,log,lengths):
        self.log=log;self.lengths=lengths;self.index=0
    def ask(self,system,user,*,num_predict):
        self.log.append(("writer",system,user,num_predict))
        n=self.lengths[self.index]
        self.index+=1
        return {"scene":text_at(n)}

class Grader:
    def __init__(self,model,log,invalid_once=False):
        self.model=model;self.log=log;self.n=0;self.invalid_once=invalid_once
    def ask(self,system,user,*,num_predict):
        self.log.append((self.model,system,user,num_predict));self.n+=1
        if self.invalid_once and self.n==1:
            return {"incomplete":"schema"}
        A={d:{"score":79,"reason":"人物行动有因果关联，但缺少若干重要的铺垫细节。"} for d in DIMENSIONS}
        B={d:{"score":81,"reason":"描写结构相对连续，结尾还需要独立的真实读者验证。"} for d in DIMENSIONS}
        return {"result":{"A":A,"B":B,"uncertainty":"两个模型评分仍不足以构成人类文学质量的证明。"}}

class V33RealisticTests(unittest.TestCase):
    def setUp(self):
        self.store=FakeStore()
        self.patches=[
            patch.object(v32,"STAGE1_SHA",self.store.sha1),
            patch.object(v32,"STAGE2_SHA",self.store.sha2),
            patch.object(runner,"STAGE2_SHA",self.store.sha2),
            patch.object(auditor,"STAGE2_SHA",self.store.sha2),
        ]
        for p in self.patches:
            p.start();self.addCleanup(p.stop)
    def test_preregistered_new_exam_and_fresh_length_repair(self):
        self.assertEqual(len(ids()),2)
        self.assertEqual(len(manifest_sha()),64)
        self.assertTrue(all(95<=len(question(i))<=490 for i in range(2)))
        log=[]
        writer=Writer(log,[897,1172,1090,1130])
        critics={}
        def create(role,name):
            if role=="writer":return writer
            obj=Grader(name,log,invalid_once=name=="minimax-m3")
            critics[name]=obj
            return obj
        result=runner.run(0,store=self.store,model_factory=create)
        self.assertEqual(result["stage"],"V33_REAL_LENGTH_AND_JSON_E2E_VERIFIED")
        self.assertTrue(result["final_length_compliant"])
        self.assertFalse(result["initial_length_compliant"])
        self.assertEqual(result["symmetric_revisions"],2)
        self.assertEqual(result["grader_models_with_full_json"],2)
        self.assertEqual([x[0] for x in log],
            ["writer","writer","writer","writer",
             "deepseek-v4-pro-0813","minimax-m3","minimax-m3"])
        self.assertNotIn("internal_experimental_rules",log[-1][2])
        cache=runner.run(0,store=self.store,model_factory=create)
        self.assertEqual(cache["calls_now"],0)
        self.assertEqual(len(log),7)
        root=runner.root_for_slot(0)
        ptr=json.loads(self.store.objects[root+"/complete.json"])
        receipt=json.loads(self.store.objects[root+"/snapshot-"+ptr["sha256"]+".json"])
        self.assertEqual(len(receipt["two_critic_individual_results"]),2)
        self.assertEqual(receipt["length_evidence"]["final"]["arms"]["control"]["chars"],1090)
        self.assertEqual(receipt["two_critic_individual_results"][1]["format_validation"]["attempted_calls"],2)
        self.assertFalse(receipt["formal_skill_core_promoted"])
        self.assertNotIn("少年在清晨",str(receipt))
        audited=auditor.audit(self.store)
        self.assertEqual(audited["two_valid_grader_trials"],1)
        self.assertEqual(audited["results"][0]["status"],
                         "TWO_INDEPENDENT_MODELS_JSON_SCORED")
        self.assertFalse(audited["official_skill_promoted"])
    def test_unrepairable_pair_never_invokes_critic(self):
        log=[]
        writer=Writer(log,[800,1400,800,1400])
        def factory(role,name):
            if role=="writer":return writer
            self.fail("critic must not run when length invalid")
        result=runner.run(1,store=self.store,model_factory=factory)
        self.assertEqual(result["grade_status"],"UNSCORABLE_ABSOLUTE_OR_RELATIVE_LENGTH")
        self.assertEqual(len(log),4)
        root=runner.root_for_slot(1)
        ptr=json.loads(self.store.objects[root+"/complete.json"])
        doc=json.loads(self.store.objects[root+"/snapshot-"+ptr["sha256"]+".json"])
        self.assertEqual(doc["two_critic_individual_results"],[])
        self.assertFalse(doc["literary_improvement_proven"])

if __name__=="__main__":
    unittest.main()
