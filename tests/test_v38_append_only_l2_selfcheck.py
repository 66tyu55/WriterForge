"""V38 synthetic one-shot frozen self-reflection; all content fictional."""
import json,unittest
from unittest.mock import patch
from copy import deepcopy
from test_v37_L2_forensic import Vault
from test_v38_lesson_transfer_bridge import (
    STORY,START,FINISH,PLANS,LESSONS,RATIONALES,CHECK,
)
import scripts.append_v38_frozen_l2_selfcheck as runner
from writerforge.v35_observable_trace import sha

def fake_evidence():
    learned=deepcopy(LESSONS)
    learned["lessons"][0].update({
        "why":"为了让读者在后续事件重新理解已经出现的真实物品和信息。",
        "use_when":"人物先接触到某种细节但不清楚其作用，后续事件自然回收。",
        "avoid_when":"人物没有足够观察机会或后续事件无法与该细节建立关联。",
        "verification_question":"是否能在角色认知范围内查到前置线索与其后果。",
    })
    prior={
        "checks":[deepcopy(CHECK["checks"][0]),{
            "angle":"knowledge","actual_draft_quote":START[:25],
            "followed_prewrite_plan":False,
            "observed_gap":"人物局限有所体现，但尚未正确解释相关证据的意义。",
            "possible_next_revision":"下次可以核对人物的知识边界与实际行为是否一致。",
        }],
        "biggest_mistake":CHECK["biggest_mistake"],
    }
    return {
        "story":STORY,"plan":deepcopy(PLANS),"learned":learned,
        "lesson":learned["lessons"][0],
        "prior":prior,"stage5_sha256":"a"*64,
    }

def valid_response(status="CLAIMED_APPLIED"):
    return {
        "foreshadowing_check":{
            "angle":"foreshadowing",
            "actual_draft_quote":FINISH,
            "followed_prewrite_plan":status=="CLAIMED_APPLIED",
            "observed_gap":"前后确实提及了同一条细绳，但只凭这点不能证明叙事伏笔具有文学效果。",
            "possible_next_revision":"未来应观察线索是否改变人物决定，而不仅是同一个物件再出现。",
        },
        "transfer_claim":{
            "lesson_id":"L2","angle":"foreshadowing",
            "application_status":status,
            "setup_quote":START if status=="CLAIMED_APPLIED" else None,
            "payoff_quote":FINISH if status=="CLAIMED_APPLIED" else None,
            **RATIONALES,
        },
    }

class FakeModel:
    def __init__(self,outputs):self.outputs=list(outputs);self.calls=[]
    def ask(self,system,user,*,num_predict):
        self.calls.append((system,user,num_predict))
        return self.outputs[len(self.calls)-1]

class V38AppendOnlyIntegrationTests(unittest.TestCase):
    def test_true_integrated_validator_accepts_source_grounded_append_only_review(self):
        store=Vault();d=fake_evidence();model=FakeModel([valid_response()])
        with patch.object(runner,"_load",return_value=d):
            out=runner.run(vault=store,model_factory=lambda budget:model)
            cached=runner.run(vault=store,model_factory=lambda budget:model)
        self.assertEqual(out["status"],"APPENDED_STRICT_TEXTUAL_EVIDENCE_ONLY")
        self.assertEqual(out["application_claim"],"CLAIMED_APPLIED")
        self.assertTrue(out["host_verified_quoted_setup_and_payoff"])
        self.assertFalse(out["semantics_proven"])
        self.assertEqual(len(model.calls),1)
        self.assertEqual(cached["calls_now"],0)
        location=f"{runner.ROOT}/{runner.SESSION}/result-{out['sha256']}.json"
        report=json.loads(store.data[location])
        bridge=report["strict_validated_aftercheck"]["full_validated_aftercheck"]
        self.assertEqual(len(bridge["checks"]),3)
        self.assertEqual(bridge["checks"][:2],d["prior"]["checks"])
        self.assertEqual(bridge["biggest_mistake"],d["prior"]["biggest_mistake"])
        self.assertFalse(report["formal_skill_core_promoted"])
        self.assertNotIn(STORY,str(out))

    def test_no_false_success_when_student_admits_not_applied(self):
        store=Vault();d=fake_evidence()
        model=FakeModel([valid_response("NOT_APPLIED")])
        with patch.object(runner,"_load",return_value=d):
            outcome=runner.run(vault=store,model_factory=lambda budget:model)
        self.assertEqual(outcome["application_claim"],"NOT_APPLIED")
        self.assertFalse(outcome["host_verified_quoted_setup_and_payoff"])
        self.assertFalse(outcome["official_promotion"])
        self.assertEqual(len(model.calls),1)

    def test_raw_failed_first_reply_is_saved_and_not_silent(self):
        store=Vault();d=fake_evidence()
        bad=valid_response()
        bad["transfer_claim"]["setup_quote"]="完全不在作文中出现的无效模型臆测"
        model=FakeModel([bad,valid_response()])
        with patch.object(runner,"_load",return_value=d):
            out=runner.run(vault=store,model_factory=lambda budget:model)
        self.assertEqual(out["raw_attempts"],2)
        report=json.loads(store.data[
            f"{runner.ROOT}/{runner.SESSION}/result-{out['sha256']}.json"])
        self.assertEqual(len(report["attempts"]),2)
        self.assertIsNotNone(report["attempts"][0]["validation_error_code"])
        self.assertTrue(report["attempts"][1]["schema_and_quote_valid"])
        self.assertEqual(len(model.calls),2)
        self.assertEqual(sum("raw-before-validate-" in k for k in store.data),2)

    def test_two_invalid_attempts_stop_no_literary_promotion(self):
        store=Vault();d=fake_evidence()
        bad=valid_response()
        bad["foreshadowing_check"]["actual_draft_quote"]="虚构的不会存在的正文句子"
        model=FakeModel([bad,bad])
        with patch.object(runner,"_load",return_value=d):
            out=runner.run(vault=store,model_factory=lambda budget:model)
        self.assertEqual(out["status"],"LEARNER_COULD_NOT_PROVIDE_GROUNDED_L2_APPLICATION")
        self.assertIsNone(out["application_claim"])
        self.assertEqual(len(model.calls),2)
        self.assertFalse(out["official_promotion"])

if __name__=="__main__":
    unittest.main()
