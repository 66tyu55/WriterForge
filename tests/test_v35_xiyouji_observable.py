"""V35 no-model tests for actual source anchors, locked prewrite, separate full drafts."""
import unittest
from hashlib import sha256
from types import SimpleNamespace
from writerforge.v35_observable_trace import (
    validate_read,validate_lessons,validate_plan,validate_draft,
    validate_after,TraceContractError,sha,canonical)
from scripts.run_v35_xiyouji_decision_trace import (
    save_stage,restore_stage,stage_key,audit,STAGES)

WINDOWS={
 1:"石猴在高山之间观察瀑布，听见同伴议论险处，才决定在众人注视下向水帘奔去。"*30,
 2:"一名求学之人来到山脚，起初没有听懂对方话语，后来从亲眼所见的行动修正判断。"*30,
}
DRAFT=("小镇青年看到江水上涨，察觉桥梁有异，"
       "决定在夜间寻找村老商议，结果错过渡船。")*21
READ={"observations":[
 {"chapter":1,"source_quote":"石猴在高山之间观察瀑布",
  "narrative_function":"先展示险境和集体目光，随后才由具体行动体现角色性格。",
  "character_knowledge":"角色看到瀑布和同伴反应，但不知道水帘里面究竟存在什么。",
  "possible_alternative_reading":"也可能只是人物临时逞强，尚不能确定行为的长期动机。"},
 {"chapter":2,"source_quote":"一名求学之人来到山脚",
  "narrative_function":"求学者的动机先出现，对话再逐步改变他对环境的理解。",
  "character_knowledge":"角色知道自己前来求学，却不掌握接下来是否有人愿意教导。",
  "possible_alternative_reading":"人物的迟疑也可能只是环境陌生，而非刻意的悬念结构。"},
]}
LESSONS={"lessons":[{
 "source_observation_index":0,
 "technique":"让人物的具体冒险动作承接此前的感知和他人压力。",
 "why":"读者先看到人物所感知的危险，才能理解他之后的冒险选择。",
 "use_when":"当人物需要以行动证明决心，而场景中存在真实风险时。",
 "avoid_when":"若角色已经处于安全场合，则不该强行安排危险来彰显性格。",
 "verification_question":"是否能从行动前已出现的线索推导出人物冒险的具体目标。",
}]}
PLAN={"decisions":[
 {"angle":angle,
  "chosen_approach":"准备让人物从具体场面看见危险，逐渐作出实际有代价的选择。",
  "reason":"考虑到有限人物知识与情境压力，避免角色突然获得幕后答案。",
  "rejected_alternative":"不采用由旁白直接解释隐藏真相和全部角色心理的简便写法。",
  "expected_story_effect":"希望读者能够从先前细节理解选择的代价和末尾悬念。",
  "learned_lesson_id":"L1"} for angle in
 ("goal","knowledge","causality","sensory")
]}
AFTER={"checks":[
 {"angle":"goal","actual_draft_quote":"小镇青年看到江水上涨",
  "followed_prewrite_plan":True,
  "observed_gap":"人物确实关注了眼前水势，但尚未交代选择的全部代价。",
  "possible_next_revision":"补足一次明确的关系冲突，让人物的决策更加令人信服。"},
 {"angle":"causality","actual_draft_quote":"决定在夜间寻找村老商议",
  "followed_prewrite_plan":False,
  "observed_gap":"寻找村老的理由仍显笼统，缺少不能另行求助的具体阻碍。",
  "possible_next_revision":"加入时间与路况的变化，使选择建立在人物所知的事实上。"},
], "biggest_mistake":"第一稿的行动因果转接不够明确，转折过度依赖事件自然发生。"}

class FakeVault:
    config=SimpleNamespace(bucket="writerforge-private-library")
    def __init__(self):self.data={}
    def _head(self,key):
        return {"ContentLength":len(self.data[key])} if key in self.data else None
    def _get_small(self,key,cap):
        data=self.data[key]
        if len(data)>cap:raise ValueError("over")
        return data
    def _put_small_immutable(self,key,value,digest):
        if sha(value)!=digest:raise ValueError("bad SHA")
        if key in self.data and self.data[key]!=value:raise ValueError("overwrite")
        self.data[key]=value

class TraceTests(unittest.TestCase):
    def test_exact_source_reading_and_no_false_quote(self):
        result=validate_read(READ,WINDOWS)
        self.assertEqual(len(result["observations"]),2)
        self.assertFalse(result["independent_semantic_correctness_verified"])
        forged={"observations":[dict(item) for item in READ["observations"]]}
        forged["observations"][0]["source_quote"]="这句话是凭空发明的原著文本，不存在"
        with self.assertRaisesRegex(TraceContractError,"QUOTED_TEXT_NOT_FOUND"):
            validate_read(forged,WINDOWS)
    def test_extracted_lessons_prewrite_plan_and_draft_quotes(self):
        read=validate_read(READ,WINDOWS)
        lessons=validate_lessons(LESSONS,len(read["observations"]))
        plan=validate_plan(PLAN,{"L1"})
        self.assertTrue(plan["decisions_written_before_first_draft"])
        self.assertEqual(lessons["lessons"][0]["id"],"L1")
        first=validate_draft(DRAFT,WINDOWS)
        self.assertEqual(first["body"],DRAFT)
        after=validate_after(AFTER,DRAFT,plan)
        self.assertEqual(len(after["checks"]),2)
        invalid={"checks":[dict(item) for item in AFTER["checks"]],
                 "biggest_mistake":AFTER["biggest_mistake"]}
        invalid["checks"][0]["actual_draft_quote"]="这一句从未出现在真实写作正文之中"
        with self.assertRaisesRegex(TraceContractError,"QUOTE_NOT_IN_DRAFT"):
            validate_after(invalid,DRAFT,plan)
    def test_no_draft_can_copy_long_original_quote(self):
        copied=WINDOWS[1][:40]+DRAFT
        with self.assertRaisesRegex(TraceContractError,"ORIGINAL_TEXT_COPIED"):
            validate_draft(copied,WINDOWS)
    def test_separate_sha_linked_r2_records_cannot_modify_prewrite(self):
        vault=FakeVault();parent=None
        for i in range(5):
            body={"index":i,"content":("original-story" if i==4 else "explicit-choices")}
            item,parent=save_stage(vault,i,body,parent)
        self.assertEqual(len(vault.data),5)
        self.assertEqual(restore_stage(vault,3,
            restore_stage(vault,2,
                restore_stage(vault,1,
                    restore_stage(vault,0,None)[1])[1])[1])[0]["index"],3)
        with self.assertRaisesRegex(ValueError,"OVERWRITE|already|overwrite"):
            vault._put_small_immutable(stage_key(3),b"tampered",sha(b"tampered"))
        report=audit(vault)
        self.assertEqual(report["stages_completed"],5)
        self.assertTrue(report["prewriting_record_immutable_before_draft"])
        self.assertFalse(report["official_skill_core_promoted"])
        self.assertFalse(report["hidden_model_chain_of_thought_not_claimed"] is False)

if __name__=="__main__":
    unittest.main()
