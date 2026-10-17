"""V37b synthetic only: strict two-critic, two-phase, numbered quotations."""
import json,unittest
from unittest.mock import patch
from test_v37_L2_forensic import Vault,evidence
import scripts.forensic_v37b_xiyouji_two_stage as v37b
from scripts.forensic_v37_xiyouji_L2 import sentence_menu

class Critic:
    def __init__(self,name,bad=False):
        self.name=name;self.bad=bad;self.calls=0
    def ask(self,system,user,*,num_predict):
        self.calls+=1
        doc=json.loads(user)
        if "genuine_chapter_window" in doc:
            return {"result":{
                "source_support":("SUPPORTED" if self.name.startswith("deepseek") else "PARTIAL"),
                "abstraction_fidelity":"PARTIAL","task_fit":"RISKY",
                "source_reason":"原著细节确实存在，不过其在全篇的伏笔功能仍需要更多上下文证据。",
                "abstraction_reason":"文学规律的抽象从局部观察出发，但不能直接等同全部场景都适用。",
                "fit_reason":"原创人物的有限知识会影响信息释放，若刻意套用将破坏选择动机。",
                "uncertainty":"这个判断只是模型阅读意见，不能冒充真人专家对文学质量的认证。",
            }}
        first=doc["first_draft_indexed_exact_sentences"]
        revised=doc["revised_draft_indexed_exact_sentences"]
        if self.bad:
            return {"result":{
                "first_execution":"OBSERVED","revised_execution":"OBSERVED",
                "revised_payoff":"GROUNDED",
                "first_setup_numbers":[999],"first_payoff_numbers":[3],
                "revised_setup_numbers":[1],"revised_payoff_numbers":[3],
                "execution_reason":"从最早的事物线索到结尾产生行动因果，仍需要严格核对。",
                "uncertainty":"有些表面相同的词未必是伏笔，还需要人为判断语义作用。",
            }}
        return {"review":{
            "first_execution":"PARTIAL","revised_execution":"PARTIAL",
            "revised_payoff":("GROUNDED" if self.name.startswith("deepseek") else "WEAK"),
            "first_setup_numbers":[1],"first_payoff_numbers":[3],
            "revised_setup_numbers":[1],"revised_payoff_numbers":[3],
            "execution_reason":"最早的线索与后文的回扣保持时间次序，但叙事意义未必完全建立。",
            "uncertainty":"即使存在两句可查文字，也不能仅凭数字位置证明读者理解了伏笔。",
        }}

class V37BSplitTests(unittest.TestCase):
    def test_two_independent_critics_do_not_average_disagreements(self):
        vault=Vault();agents={}
        def factory(name):
            a=Critic(name);agents[name]=a;return a
        with patch.object(v37b,"frozen_evidence",return_value=evidence()):
            got=v37b.run(vault=vault,models_factory=factory)
            cached=v37b.run(vault=vault,models_factory=factory)
        self.assertEqual(got["status"],"FOUR_VALID_INDEPENDENT_MODEL_PHASES")
        self.assertEqual(len(got["opinions"]),4)
        self.assertTrue(got["literary_progress_proven"] is False)
        self.assertEqual(cached["model_calls_now"],0)
        self.assertEqual(sum(x.calls for x in agents.values()),4)
        self.assertFalse(got["agreement"]["source_support"])
        self.assertFalse(got["agreement"]["revised_payoff"])
        self.assertEqual(got["opinions"][1]["exact_host_sentence_numbers"]["first_setup_numbers"],[1])
        self.assertNotIn(evidence()["original_draft"][:30],
                         json.dumps(got,ensure_ascii=False))
        self.assertFalse(any(x.get("literary_skill_promoted",False) for x in got["opinions"]))
    def test_out_of_range_citation_fails_without_guessing(self):
        vault=Vault()
        def factory(name):return Critic(name,bad=True)
        with patch.object(v37b,"frozen_evidence",return_value=evidence()):
            result=v37b.run(vault=vault,models_factory=factory)
        self.assertEqual(result["status"],"INCOMPLETE_MODEL_EVIDENCE_NO_CONCLUSION")
        self.assertEqual(len(result["failures"]),2)
        self.assertTrue(all(x["failure_code"].startswith(
            "V37B_INVALID_NUMBERED_FIRST_SETUP_NUMBERS") for x in result["failures"]))
        self.assertFalse(result["literary_progress_proven"])
    def test_missing_quote_cannot_count_as_grounded_payoff(self):
        e=evidence()
        menus={"first":sentence_menu(e["original_draft"],"I"),
               "revised":sentence_menu(e["revised_draft"],"R")}
        raw=Critic("deepseek-v4-pro-0813").ask("ignored",v37b._draft_input(e,menus),
                                              num_predict=6700)
        raw["review"]["revised_setup_numbers"]=[]
        with self.assertRaisesRegex(v37b.L2SplitReviewError,"WITHOUT_EARLY"):
            v37b.validate_draft_phase(raw,menus)
        raw["review"]["revised_setup_numbers"]=[1]
        raw["review"]["revised_payoff_numbers"]=[1]
        with self.assertRaisesRegex(v37b.L2SplitReviewError,"BEFORE_SETUP"):
            v37b.validate_draft_phase(raw,menus)

if __name__=="__main__":
    unittest.main()
