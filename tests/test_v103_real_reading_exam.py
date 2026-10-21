"""V103 real-exam contract fixtures, OFFLINE and no secrets / DeepSeek / R2."""
from __future__ import annotations
from copy import deepcopy
import unittest

from writerforge.v103_frozen_original_exam import (
    CHAPTERS,TRANSFER_STORY,RUN_NAME,MAX_CALLS,
    READ_MAX_OUTPUT,WRITE_MAX_OUTPUT,MAX_RESERVED_OUTPUT,
    MAX_CONSERVATIVE_REQUEST_BUDGET,TARGET_CHARS,precommit,h,encode,
)
from wf_railway_v103_real_three_reveal_exam import (
    read_prompt,prompt_to_write,validate_read,
    clean_prior,public_read_observation,
)
from writerforge.v99_longform_quality_evidence import (
    freeze_manuscript,compare_equal_length,
)

class V103RealExamContract(unittest.TestCase):
    def test_three_chapters_individually_hidden_and_sha_frozen(self):
        self.assertEqual(len(CHAPTERS),3)
        record=precommit()
        self.assertEqual(record["source_sha256"],h(encode(CHAPTERS)))
        self.assertEqual(record["max_paid_requests"],5)
        self.assertEqual(record["no_auto_retry_on_network_failure"],True)
        self.assertEqual(MAX_RESERVED_OUTPUT,
                         3*READ_MAX_OUTPUT+2*WRITE_MAX_OUTPUT)
        self.assertLess(MAX_RESERVED_OUTPUT,17000)
        self.assertLessEqual(MAX_CONSERVATIVE_REQUEST_BUDGET,70000)
        self.assertEqual(record["promotion_gate"],"LOCKED")
        self.assertEqual(record["independent_human_literary_review"],
                         "NOT_PERFORMED")
        first=read_prompt(1,[])
        self.assertIn("霜天还没亮",first)
        self.assertNotIn("铁栓，",first)
        self.assertNotIn("画着海面的布景倾斜",first)
        history=[{"chapter":1,"answer":{
            "forecast":{"most_likely":"周迦偷偷收走票款",
                        "alternative":"她不愿承担演出风险"}}}]
        second=read_prompt(2,history)
        self.assertIn("黄昏尚未点灯",second)
        self.assertNotIn("半月记号",second)
        third=read_prompt(3,history)
        self.assertIn("半月记号",third)

    def sample_answer(self):
        return {
          "plot":"葛梨听见梁内异响，却想今晚继续演出，以支付戏班的债",
          "motives":{
            "葛梨":"葛梨怕欠粮钱，隐瞒自己已经知道梁快裂了",
            "周迦":"周迦既想保住戏班，又担忧屋梁危险"},
          "knowledge_boundary":"周迦未必知道短栓情况，葛梨知道裂纹已持续两日",
          "relationship":{
            "before":"两人旧日一起收绳，彼此尚能合作",
            "after":"周迦开始疑虑却没有公开对峙",
            "why":"递灯相助但也怀疑梁的安全",
            "evidence_quote":"总是她们两个留下来收绳"},
          "emotion":{
            "person":"葛梨",
            "trigger_quote":"周迦问：『换根木楔，能撑过今夜吗？』",
            "reaction_quote":"她没说这根梁从前日就开始裂",
            "reading":"葛梨被追问时更怕债务暴露，选择掩盖险情",
            "alternative":"她也许真相信只撑一场不会出事"},
          "causality":{
            "action_quote":None,"effect_quote":None,
            "actual_cost":"没有实际失去订银，债务风险仍在",
            "future_constraint":"当晚如果停演就须退双倍订银"},
          "literary_sentence":{
            "quote":"纸被夜里的潮气浸得发软",
            "why_effective_or_weak":"物理触感让戏班的窘迫具象而不是空泛说明",
            "flat_rewrite":"潮气很重，戏班很穷，周迦很焦急。",
            "change_in_reader_effect":"会失去靠小物件传达艰难的含蓄"},
          "forecast":{
            "most_likely":"横梁危机会造成停演，人际互信将承受压力",
            "alternative":"也可能及时修梁，危机只作为伏笔",
            "uncertainty":"目前没有证据证明横梁为何损坏"},
          "correction":{
            "prior_guess":"当前是第一段，还没有历史预测",
            "current_correction":"目前只根据首段作谨慎猜测",
            "still_unknown":"不知道周迦是否真正知道危险根源"},
          "transfer_lesson":"小物件可以体现窘境，人物的隐瞒应由具体压力造成",
        }

    def test_actual_source_anchors_validate_but_not_semantics(self):
        rec=validate_read(self.sample_answer(),CHAPTERS[0])
        self.assertEqual(rec["source_sha256"],h(CHAPTERS[0].encode("utf8")))
        self.assertIsNone(rec["quote_witnesses"]["action"])
        self.assertIsNone(rec["quote_witnesses"]["effect"])
        self.assertFalse(rec["literary_semantics_independently_verified"])
        self.assertFalse(rec["predictive_accuracy_verified"])
        obs=public_read_observation(1,self.sample_answer(),True,None)
        self.assertEqual(obs["semantic_grade"],"UNDETERMINED")
        self.assertIn("不",obs["student_plot"])

    def test_unwritten_evidence_and_future_leak_are_not_accepted(self):
        fake=self.sample_answer()
        fake["relationship"]["evidence_quote"]="第二章才会揭露的重要真相"
        with self.assertRaisesRegex(ValueError,"NOT_IN_ALREADY_READ_SOURCE"):
            validate_read(fake,CHAPTERS[0])
        fake=self.sample_answer()
        fake["emotion"]["reaction_quote"]="周迦问：『换根木楔，能撑过今夜吗？』"
        fake["emotion"]["trigger_quote"]="她没说这根梁从前日就开始裂"
        with self.assertRaisesRegex(ValueError,"AFTER_REACTION"):
            validate_read(fake,CHAPTERS[0])

    def test_cannot_treat_earlier_prediction_as_authoritative_truth(self):
        ctx=clean_prior([{"chapter":1,"answer":{
            "forecast":{"most_likely":"周迦一定背叛葛梨",
                        "alternative":"也可能保护众人"},
            "relationship":{"after":"信任尚未结束"}
        }}])
        self.assertIn("尚未证明正确",ctx)
        self.assertIn("也可能保护众人",ctx)

    def test_fair_transfer_only_gets_wf_abstract_lessons(self):
        stages=[{"chapter":i,"answer":{"transfer_lesson":
            f"第{i}阶段谨慎处理未证实人物心理，真实代价必须延续后文选择"},
            "verified_witness":True} for i in (1,2,3)]
        a=prompt_to_write(stages,informed=False)
        b=prompt_to_write(stages,informed=True)
        self.assertEqual(a.count(TRANSFER_STORY),1)
        self.assertEqual(b.count(TRANSFER_STORY),1)
        self.assertNotIn("第1阶段谨慎",a)
        self.assertIn("第1阶段谨慎",b)
        self.assertNotIn("周迦",b)
        with self.assertRaisesRegex(ValueError,"REQUIRES_THREE"):
            prompt_to_write(stages[:2],informed=True)
        changed=deepcopy(stages)
        changed[1]["answer"]["transfer_lesson"]="葛梨其实从早晨看见了梁的裂缝"
        with self.assertRaisesRegex(ValueError,"LEAKED_OLD_STORY"):
            prompt_to_write(changed,informed=True)

    def test_equal_length_rule_must_not_give_auto_literary_winner(self):
        a=freeze_manuscript(prose="有人在夜里放下旧钥匙。"*68,arm="single",
                            case_id="v103_experiment_new_world_transfer",
                            requested_chars=TARGET_CHARS)
        b=freeze_manuscript(prose="另一位旅人决定在大雪前回去。"*60,
                            arm="rolling_causal",
                            case_id="v103_experiment_new_world_transfer",
                            requested_chars=TARGET_CHARS)
        result=compare_equal_length(samples=[a,b])
        self.assertIsInstance(result["lengths_comparable"],bool)
        self.assertEqual(result["literary_winner"],"UNDETERMINED")
        self.assertFalse(result["independent_semantic_review_completed"])

if __name__=="__main__":
    unittest.main()
