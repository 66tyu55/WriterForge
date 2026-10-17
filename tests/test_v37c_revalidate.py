"""V37c genuine format-boundary review tests, synthetic only."""
import unittest
from scripts.revalidate_v37c_l2_historical_reviews import (
    validate_source,validate_draft,L2SplitReviewError,
)
from test_v37b_l2_two_stage import Critic
from test_v37_L2_forensic import evidence
from scripts.forensic_v37_xiyouji_L2 import sentence_menu
from scripts.forensic_v37b_xiyouji_two_stage import _source_input,_draft_input

class V37CLosslessTests(unittest.TestCase):
    def test_short_but_real_uncertainty_is_preserved_verbatim(self):
        x=Critic("deepseek-v4-pro-0813").ask(
            "examiner",_source_input(evidence()),num_predict=5100)["result"]
        x["uncertainty"]="此结果有不确定性"
        self.assertLess(len(x["uncertainty"]),15)
        y=validate_source({"result":x})
        self.assertEqual(y["uncertainty"],x["uncertainty"])
        self.assertEqual(y["source_reason"],x["source_reason"])
        self.assertEqual(y["source_support"],x["source_support"])

    def test_eight_exact_indices_and_long_reason_accepted_without_crop(self):
        e=evidence()
        menus={"first":sentence_menu(e["original_draft"],"I"),
               "revised":sentence_menu(e["revised_draft"],"R")}
        x=Critic("deepseek-v4-pro-0813").ask(
            "examiner",_draft_input(e,menus),num_predict=6700)["review"]
        x["revised_payoff_numbers"]=[3,4,5,6,7,8,9]
        x["execution_reason"]="因此出现的具体因果联系还需进一步独立核查。"*19
        x["uncertainty"]="此结果有不确定性"
        y=validate_draft({"review":x},menus)
        self.assertEqual(y["revised_payoff_numbers"],[3,4,5,6,7,8,9])
        self.assertEqual(y["execution_reason"],x["execution_reason"])

    def test_missing_uncertainty_still_invalid_even_with_many_valid_quotes(self):
        e=evidence()
        menus={"first":sentence_menu(e["original_draft"],"I"),
               "revised":sentence_menu(e["revised_draft"],"R")}
        x=Critic("minimax-m3").ask(
            "examiner",_draft_input(e,menus),num_predict=6700)["review"]
        x["uncertainty"]=None
        with self.assertRaisesRegex(L2SplitReviewError,"UNCERTAINTY_MISSING"):
            validate_draft(x,menus)
        x["uncertainty"]="真实的风险不能靠补造文字解决。"
        x["revised_setup_numbers"]=[len(menus["revised"])+1]
        with self.assertRaisesRegex(L2SplitReviewError,"CITATIONS_NOT_GENUINE"):
            validate_draft(x,menus)

if __name__=="__main__":
    unittest.main()
