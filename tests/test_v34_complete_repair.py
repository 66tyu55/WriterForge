"""V34 synthetic chain regression: two self-length repairs + real MiniMax nesting shape."""
from __future__ import annotations
import json,unittest
from unittest.mock import patch
from test_v32_examiner_blind import FakeStore
from writerforge.v33_exam_contracts import DIMENSIONS
import scripts.run_v32_examiner_blind as v32
import scripts.run_v34_repair_e2e as runner
import scripts.audit_v34_repair_e2e as auditor
from writerforge.v34_repair_topics import question,manifest_sha

UNIT="风暴之后，少年在石桥边找到一枚铜扣，他疑惑它为什么会被人丢在这里。"
def body(n):return (UNIT*((n+len(UNIT)-1)//len(UNIT)))[:n]

class Writer:
    def __init__(self,log):
        self.log=log;self.n=0
    def ask(self,system,user,*,num_predict):
        self.log.append(("writer",system,user,num_predict));self.n+=1
        return {"scene":body([850,1400,1062,945,1090,1132][self.n-1])}
class Grader:
    def __init__(self,model,log):self.name=model;self.log=log
    def ask(self,system,user,*,num_predict):
        self.log.append((self.name,system,user,num_predict))
        A={d:{"score":82,"reason":"场景逻辑连贯但需要更明确说明人物行为的代价。"} for d in DIMENSIONS}
        B={d:{"score":77,"reason":"结尾所需的具体伏笔出现偏晚，需要读者回查。"} for d in DIMENSIONS}
        extra="两个模型评价仍然存在偏见风险，不能构成人类文学验证。"
        if self.name=="minimax-m3":
            # Reproduce ACTUAL long-form MiniMax structure seen on gateway.
            return {"A":{**A,"B":{**B,"uncertainty":extra}}}
        return {"A":A,"B":B,"uncertainty":extra}

class V34Tests(unittest.TestCase):
    def setUp(self):
        self.store=FakeStore()
        self.patches=[
            patch.object(v32,"STAGE1_SHA",self.store.sha1),
            patch.object(v32,"STAGE2_SHA",self.store.sha2),
            patch.object(runner,"STAGE2_SHA",self.store.sha2),
            patch.object(auditor,"STAGE2_SHA",self.store.sha2),
        ]
        for p in self.patches:p.start();self.addCleanup(p.stop)
    def test_exam_is_new_precommitted_story(self):
        self.assertEqual(len(manifest_sha()),64)
        self.assertTrue(95<=len(question(0))<=490)
        with self.assertRaises(Exception):runner.root_for_slot(1)
    def test_both_writer_repairs_and_both_grader_json_structures_succeed(self):
        log=[];w=Writer(log)
        def factory(role,name):
            return w if role=="writer" else Grader(name,log)
        outcome=runner.run(0,store=self.store,model_factory=factory)
        self.assertEqual(outcome["stage"],"V34_REAL_LENGTH_AND_JSON_E2E_VERIFIED")
        self.assertEqual(outcome["grade_status"],"TWO_INDEPENDENT_MODELS_JSON_SCORED")
        self.assertTrue(outcome["final_length_compliant"])
        self.assertEqual(outcome["symmetric_revisions"],4)
        self.assertEqual([x[0] for x in log[:6]],["writer"]*6)
        self.assertEqual(len(log),8)
        root=runner.root_for_slot(0)
        pointer=json.loads(self.store.objects[root+"/complete.json"])
        report=json.loads(self.store.objects[root+"/snapshot-"+pointer["sha256"]+".json"])
        self.assertTrue(report["length_evidence"]["overall_eligible_for_blind_grading"])
        self.assertEqual(report["length_evidence"]["symmetric_revision_cycles"],2)
        details=report["two_critic_individual_results"]
        self.assertEqual(details[1]["format_validation"]["parsing_path"],
                         "EXACT_NESTED_A_B_UNCERTAINTY_RELOCATION")
        self.assertFalse(report["literary_improvement_proven"])
        verify=auditor.audit(self.store)
        self.assertEqual(verify["two_valid_grader_trials"],1)
        self.assertTrue(verify["user_goal_length_json_chain_fixed_in_real_runs"])
        self.assertFalse(verify["official_skill_promoted"])
        again=runner.run(0,store=self.store,model_factory=factory)
        self.assertEqual(again["calls_now"],0)
        self.assertEqual(len(log),8)

if __name__=="__main__":
    unittest.main()
