"""Offline V33 hard length and JSON reviewer contracts, no model calls."""
import json,unittest
from writerforge.v33_exam_contracts import (
    length_state,fair_pair,strict_grade,grade_with_one_repair,
    grade_prompt,ExamContractError,DIMENSIONS,
)
from writerforge.v33_balanced_writing import controlled_pair

TASK=("雨后的桥边，一位年轻药师要在责任与友谊之间作决定。"
      "他对事情的真实原因所知有限，意外选择造成了可见代价。"
      "请写原创首章，通过前面的实物线索产生悬念，保持人物自然。")
UNIT="少年沿着河岸走过破损的石桥，发现袖口被冷雨浸湿，想起母亲交给他的信。"
def body(n):return (UNIT*((n+len(UNIT)-1)//len(UNIT)))[:n]
def grade(n=84):
    return {"A":{d:{"score":n,"reason":"叙事因果线索存在，但人物行动仍需更具体地交代。"} for d in DIMENSIONS},
            "B":{d:{"score":n-3,"reason":"关键伏笔在结尾才出现，仍需要检查前文是否建立。"} for d in DIMENSIONS},
            "uncertainty":"模型不能代表真实读者，评分仍有不确定性。"}

class StubWriter:
    def __init__(self,lengths):
        self.lengths=lengths;self.calls=[]
    def ask(self,system,user,*,num_predict):
        self.calls.append((system,json.loads(user),num_predict))
        return {"scene":body(self.lengths[len(self.calls)-1])}
class StubGrader:
    def __init__(self,replies):self.replies=replies;self.calls=[]
    def ask(self,system,user,*,num_predict):
        self.calls.append((system,json.loads(user),num_predict))
        return self.replies[len(self.calls)-1]

class V33Contracts(unittest.TestCase):
    def test_absolute_and_relative_both_required(self):
        self.assertFalse(fair_pair({"control":body(897),"wf_memory":body(1172)})["pass"])
        self.assertFalse(fair_pair({"control":body(1410),"wf_memory":body(1420)})["pass"])
        ok=fair_pair({"control":body(1040),"wf_memory":body(1180)})
        self.assertTrue(ok["pass"])
        self.assertEqual(length_state(body(1040))["missing_or_excess"],80)
    def test_symmetric_length_repairs_same_target_not_opponent(self):
        writer=StubWriter([897,1172,1090,1150])
        answers,report=controlled_pair(writer,TASK,())
        self.assertTrue(report["overall_eligible_for_blind_grading"])
        self.assertEqual(report["symmetric_revision_calls"],2)
        self.assertEqual([call[2] for call in writer.calls],[7500,7500,6000,6000])
        self.assertEqual(writer.calls[2][1]["own_exact_characters_including_punctuation"],897)
        self.assertEqual(writer.calls[3][1]["own_exact_characters_including_punctuation"],1172)
        self.assertEqual(writer.calls[2][1]["required_self_change"],223)
        self.assertEqual(writer.calls[3][1]["required_self_change"],-52)
        self.assertNotIn("other_draft",str(writer.calls[2][1]))
        self.assertNotIn(body(1172),str(writer.calls[2][1]))
        self.assertFalse(report["manuscripts_cropped_or_padded"])
        self.assertEqual(len(answers["control"]),1090)
    def test_repair_failure_unscored_and_no_cropping(self):
        w=StubWriter([900,1280,900,1280])
        answers,r=controlled_pair(w,TASK,())
        self.assertFalse(r["overall_eligible_for_blind_grading"])
        self.assertEqual(r["symmetric_revision_calls"],2)
        self.assertEqual(len(answers["control"]),900)
        self.assertEqual(len(answers["wf_memory"]),1280)
    def test_enveloped_grades_unwrapped_only_unambiguous(self):
        actual=grade()
        normalized,path=strict_grade({"result":{"review":actual}})
        self.assertEqual(normalized,actual)
        self.assertEqual(path,"UNAMBIGUOUS_ENVELOPE_result/review")
        direct,path=strict_grade(actual)
        self.assertEqual(path,"DIRECT_EXACT")
    def test_missing_scores_or_bad_reason_never_invented(self):
        x=grade()
        x["A"]["language"].pop("score")
        with self.assertRaisesRegex(ExamContractError,"GRADER_JSON_DIMENSION_OBJECT"):
            strict_grade(x)
        x=grade();x["B"]["language"]["score"]=True
        with self.assertRaisesRegex(ExamContractError,"GRADER_JSON_SCORE"):
            strict_grade(x)
        x=grade();x.pop("uncertainty")
        with self.assertRaisesRegex(ExamContractError,"GRADER_JSON_TOP_LEVEL"):
            strict_grade(x)
        x=grade();x["metadata"]="unrelated"
        with self.assertRaisesRegex(ExamContractError,"GRADER_JSON_TOP_LEVEL"):
            strict_grade(x)
    def test_retry_only_for_invalid_json_and_not_for_bad_score(self):
        bad={"ratings":grade()}
        grader=StubGrader([{"review":{"wrong":"missing"}},bad])
        result,detail=grade_with_one_repair(grader,TASK,{"A":body(1100),"B":body(1120)})
        self.assertEqual(result,grade())
        self.assertEqual(detail["attempted_calls"],2)
        self.assertEqual(detail["parsing_path"],"UNAMBIGUOUS_ENVELOPE_ratings")
        self.assertIsNotNone(detail["format_error_first_attempt"])
        self.assertFalse("old_writer_version" in str(grader.calls))
        second=StubGrader([grade(),grade()])
        _,record=grade_with_one_repair(second,TASK,{"A":body(1100),"B":body(1120)})
        self.assertEqual(record["attempted_calls"],1)
        self.assertEqual(len(second.calls),1)
        failed=StubGrader([{"unexpected":{}},{"A":{},"B":{},"uncertainty":"unclear"}])
        with self.assertRaisesRegex(ExamContractError,"FAILED_AFTER_ONE_CORRECTION"):
            grade_with_one_repair(failed,TASK,{"A":body(1100),"B":body(1120)})
        self.assertEqual(len(failed.calls),2)
    def test_grader_prompt_has_no_numeric_score_anchor(self):
        prompt=grade_prompt(TASK,{"A":body(1100),"B":body(1120)})
        self.assertNotIn('"score":75',prompt)
        self.assertEqual(json.loads(prompt)["required_top_level_keys"],["A","B","uncertainty"])

if __name__=="__main__":
    unittest.main()
