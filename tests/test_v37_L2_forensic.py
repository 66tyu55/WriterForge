"""V37 exact sentence-clue/payoff evidence, independent graders, immutable R2.

All materials in these tests are completely synthetic. These are format and
provenance regressions, NEVER genuine Xi You Ji literary judgments.
"""
from __future__ import annotations
import json,unittest
from types import SimpleNamespace
from unittest.mock import patch
from writerforge.v35_observable_trace import sha,canonical
import scripts.forensic_v37_xiyouji_L2 as run
from test_v35_xiyouji_observable import FakeVault

TEXT=("少年在木桥上看见用红线缠过的一枚旧铜扣。"
      "他却急忙赶回村口寻找师傅，并没有核对铜扣是谁遗失的。"
      "最后打开漆盒时，盒里的红线与桥上铜扣的红线一样。")*9

class Vault(FakeVault):
    def __init__(self):
        super().__init__()
        self.client=SimpleNamespace(put_object=self.put_object)
    def put_object(self,*,Bucket,Key,Body,ContentType):
        assert Bucket=="writerforge-private-library"
        if Key in self.data:raise ValueError("OVERWRITE")
        self.data[Key]=Body

class Critic:
    def __init__(self,model,broken=False):
        self.model=model;self.broken=broken;self.calls=0
    def ask(self,system,user,*,num_predict):
        self.calls+=1
        data=json.loads(user.split("\n【仅修复格式】")[0])
        first=data["first_unmodified_essay_sentences"]
        revised=data["later_revision_essay_sentences"]
        obj={
            "source_support":"PARTIAL",
            "abstraction_fidelity":"PARTIAL",
            "task_fit":"RISKY",
            "first_execution":"PARTIAL",
            "revised_execution":"PARTIAL",
            "foreshadow_payoff":"WEAK",
            "first_setup_ids":[first[0]["id"]],
            "first_payoff_ids":[first[2]["id"]],
            "revised_setup_ids":[revised[0]["id"]],
            "revised_payoff_ids":[revised[2]["id"]],
            "source_reason":"模型无法完全证明节选内容在原著上下文中具有规划者所断言的全部伏笔作用。",
            "abstraction_reason":"这类读书感受可能成立，但是需要判断从局部示例推导出的规则是否脱离语境。",
            "task_reason":"新题目的人物目标和有限知识构成了必要前提，但未能证明所有细节都适配。",
            "execution_reason":"首稿有可回查的物品线索，但从铺垫到结尾的联系仍可能没有足够因果支撑。",
            "uncertainty":"文学判断存在模型个人偏好，这不是经过真人独立审阅后的文学能力证明。",
        }
        return {"result":obj} if not self.broken else {"B":obj}

def evidence():
    return {
        "source_chapter":1,
        "source_window":"石猴望着远处落下的水帘，众人议论是否有人敢于上前观察。"*36,
        "original_observation":{
            "chapter":1,"source_quote":"石猴望着远处落下的水帘",
            "narrative_function":"眼前景物与后来行动之间存在逐渐加深的叙事联系。",
            "character_knowledge":"角色知道自己能看见水帘，但还不知道内部究竟有什么。",
            "possible_alternative_reading":"也许当下只是人物表现勇气，不能直接当成最终伏笔。",
        },
        "original_lesson":{
            "id":"L2","source_observation_index":0,
            "technique":"让读者先看到细节再让角色后续行动回收该信息。",
            "why":"先前景物与角色行动互相呼应，使读者能追溯新结果。",
            "use_when":"当事件结果能由之前人物亲眼见过的细节触发。",
            "avoid_when":"当角色缺乏必要信息时不能让他突然掌握最终真相。",
            "verification_question":"结尾是否有可明确回查的开头线索，并且角色知情范围一致。",
        },
        "frozen_foreshadowing_decision":{
            "angle":"foreshadowing",
            "learned_lesson_id":"L2",
            "chosen_approach":"在首段安排可观察的细节，使结尾转折的证据能够被查回。",
            "reason":"人物必须从亲眼观察逐步形成自己的误判，不能凭空补结尾秘密。",
            "rejected_alternative":"拒绝在结尾直接引入没有任何早期铺垫的新证据。",
            "expected_story_effect":"读者能够根据最初的观察，重新理解后来出现在另一地点的物件。",
        },
        "original_draft":TEXT,
        "revised_draft":TEXT.replace("却急忙赶回","先后赶回"),
        "parent_v36_trace_sha256":"a"*64,
        "stage_sha256s":["a"*64]*6,
    }

class V37ForensicTests(unittest.TestCase):
    def test_citation_menu_offsets_and_temporal_order(self):
        excerpt=evidence()
        rows=run.sentence_menu(excerpt["original_draft"],"I")
        self.assertGreaterEqual(len(rows),10)
        self.assertEqual(rows[0]["id"],"I01")
        for row in rows:
            self.assertEqual(excerpt["original_draft"][row["start"]:row["end"]],
                             row["text"])
            self.assertEqual(row["text_sha256"],sha(row["text"]))
        valid=Critic("critic").ask("ignored",run.prompt(excerpt,rows,
                                run.sentence_menu(excerpt["revised_draft"],"R")),
                                num_predict=5400)
        grade=run.validate_review(valid,{
            "first":rows,
            "revised":run.sentence_menu(excerpt["revised_draft"],"R")})
        self.assertEqual(grade["foreshadow_payoff"],"WEAK")
    def test_fake_excerpt_or_missing_clue_never_counts_as_grounded_payoff(self):
        exp=evidence()
        menus={"first":run.sentence_menu(exp["original_draft"],"I"),
               "revised":run.sentence_menu(exp["revised_draft"],"R")}
        record=run._unwrap(Critic("a").ask("test",run.prompt(
            exp,menus["first"],menus["revised"]),num_predict=5400))
        record["revised_setup_ids"]=[]
        record["foreshadow_payoff"]="GROUNDED"
        with self.assertRaisesRegex(run.L2ForensicError,"WITHOUT_EARLY"):
            run.validate_review(record,menus)
        record["revised_setup_ids"]=["R99"]
        with self.assertRaisesRegex(run.L2ForensicError,"UNKNOWN_OR_DUPLICATED"):
            run.validate_review(record,menus)
        record["revised_setup_ids"]=[menus["revised"][5]["id"]]
        record["revised_payoff_ids"]=[menus["revised"][1]["id"]]
        with self.assertRaisesRegex(run.L2ForensicError,"TEMPORAL_ORDER"):
            run.validate_review(record,menus)
    def test_two_models_save_only_private_raw_and_no_public_prose(self):
        vault=Vault();exp=evidence()
        models=[]
        def factory(name):
            x=Critic(name);models.append(x);return x
        with patch.object(run,"frozen_evidence",return_value=exp):
            result=run.run(vault,models_factory=factory)
            cached=run.run(vault,models_factory=factory)
        self.assertEqual(result["status"],"TWO_INDEPENDENT_CRITICS_VALID_NOT_HUMAN")
        self.assertEqual(result["model_calls"],0) # synthetic factory bypasses charging
        self.assertEqual(sum(x.calls for x in models),2)
        self.assertEqual(cached["model_calls"],0)
        self.assertEqual(len(models),2)
        self.assertEqual(len(result["models"]),2)
        self.assertFalse(result["literary_skill_promoted"])
        self.assertNotIn("少年在木桥",str(result))
        self.assertTrue(any("unvalidated-" in x for x in vault.data))
        self.assertTrue(any("result-" in x for x in vault.data))
        self.assertNotIn(TEXT[:35],json.dumps(result,ensure_ascii=False))
    def test_no_model_output_contract_does_not_autofill(self):
        vault=Vault();exp=evidence()
        with patch.object(run,"frozen_evidence",return_value=exp):
            models=[]
            result=run.run(vault,models_factory=lambda name:(
                models.append(Critic(name,broken=True)) or models[-1]))
        self.assertEqual(result["status"],"INCOMPLETE_CRITIC_REVIEW_UNSCORED")
        self.assertEqual(len(result["models"]),0)
        self.assertTrue(result["errors"])
        self.assertEqual(sum(x.calls for x in models),2)
        self.assertFalse(result["literary_skill_promoted"])

if __name__=="__main__":
    unittest.main()
