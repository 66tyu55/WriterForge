"""V50 engineering-only regression for V49 third-strike failure.

No real model calls, reader ratings, prose training, or literary promotion.
Evidence is seeded strictly as test fixture; cannot be called WF self-study.
"""
import json
import sqlite3
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from writerforge import WriterForgeDB,RuntimeEngine,OriginalStudy
from writerforge.skill_host_session import start,pending,submit,summary,_trial,_packet
from writerforge.experience_applicability import choose_experience
from writerforge.scene_learning import SceneLiteraryStudy, VerifiedScene

ORIGINAL=Path(__file__).parent/"fixtures"/"xiyouji_chapter_001_original_zh.txt"
GOALS=(
    "请写一段秋日庭院的静态景物描写，全文不要出现人物或道德选择，仅描写光影与叶片的颜色。",
    "写初冬河冰如何自然形成的观察记录，不出现人物抉择，也不要使用牺牲和回收悬念技巧。",
    "写一段描述木匣、纸张和墨水纹理的工坊物件素描，不发生人物行动或道德冲突。",
)
FIRST=json.dumps({
  "expectations":["读者尚不知道此后人物行动会产生什么后果"],
  "questions":["接下来人物会怎样改变已有的选择仍然未知"],
  "character_inferences":["目前角色只拥有自己亲眼看过的情况尚不知道结果"],
},ensure_ascii=False)
DRAFT=("晚风拂过楼檐，少女停在石桥尽头。她注意到桥边有一枚旧木牌，"
       "却并不清楚它由谁留下。她仔细辨认后，决定暂时不走旧路。"
       "这一停顿让船队失去最后一次过河的机会。")*5


class SkillV50CoreRepair(unittest.TestCase):
 def setUp(self):
  self.tmp=TemporaryDirectory()
  self.db=WriterForgeDB(Path(self.tmp.name)/"real.sqlite")
  self.src=Path(self.tmp.name)/"original.txt"
  self.src.write_bytes(ORIGINAL.read_bytes())
 def tearDown(self):
  self.db.close();self.tmp.cleanup()
 def new(self,n,goal):
  name=f"v50-check-{n}"
  if len(goal)<35:
   goal=goal+"。请保持题目原有的叙事限制，不要复制过去作品中的人物和句子。"
  start(self.db,run_id=name,source=str(self.src),goal=goal,model_id="TEST_HOST_NOT_REAL")
  return name
 def finish_learning(self,name):
  p=pending(self.db,name)
  submit(self.db,run_id=name,model_id="TEST_HOST_NOT_REAL",
         reply=FIRST,prompt_sha256=p["prompt_sha256"],output_dir=self.tmp.name)
  p=pending(self.db,name)
  row=_trial(self.db,name)
  from writerforge.skill_host_session import _load
  _,scene=_load(row)
  quote=scene.text[400:438].strip()
  reply=json.dumps({"mechanisms":[{
   "source_quote":quote,
   "hypothesis":"作者让人物先在有限信息中作出选择，并展示选择的情境代价",
   "counterfactual":"如果先说明最终结果，就会改变前段读者形成的理解和期待",
   "transfer_question":"新场景有没有真实人物知道与不知道的边界及对应的行动代价",
  }]},ensure_ascii=False)
  submit(self.db,run_id=name,model_id="TEST_HOST_NOT_REAL",
         reply=reply,prompt_sha256=p["prompt_sha256"],output_dir=self.tmp.name)
  return row
 def typed_scene(self,row,*,reviewed=True,known=False,role="setup"):
  scene=row["scene_id"];project=row["project_id"]
  with self.db.conn:
   self.db.conn.execute(
    "INSERT INTO character_state(project_id,character_id,state_json) VALUES(?,?,?)",
    (project,"测试角色",json.dumps({"knowledge":{
     "known":["clue-fact"] if known else ["previous-fact"],
     "unknown":["clue-fact"]}},ensure_ascii=False)))
   self.db.conn.execute(
    "INSERT INTO causal_events(project_id,event_id,payload_json) VALUES(?,?,?)",
    (project,"event-01",json.dumps({
     "scene_id":scene,"scene_type":"character_choice",
     "actor_id":"测试角色","fact_id":"clue-fact",
     "clue_id":"clue-01","narrative_role":role,
     "review_status":"confirmed"},ensure_ascii=False)))
   if reviewed:
    self.db.conn.execute(
      "UPDATE literary_scene_trials SET review_status='approved',"
      "reviewer_reason=? WHERE project_id=? AND scene_id=?",
      ("仅合成的已确认签收声明，不代表真实独立文学评论",project,scene))
 def test_three_scenery_tasks_abstain_and_never_start_experience_prose(self):
  for i,goal in enumerate(GOALS):
   n=self.new(i,goal)
   self.finish_learning(n)
   row=_trial(self.db,n)
   eligibility=choose_experience(self.db,row)
   self.assertEqual(eligibility.state,"ABSTAIN")
   self.assertEqual(eligibility.cause,"NO_SCENE_FACTS")
   baseline=_packet(self.db,row,False)
   self.assertNotIn("让人物根据已知信息、欲望和风险作出有后果的选择",baseline.prompt)
   p=pending(self.db,n)
   self.assertEqual(p["stage"],"baseline")
   submit(self.db,run_id=n,model_id="TEST_HOST_NOT_REAL",
          reply=DRAFT,prompt_sha256=p["prompt_sha256"],
          output_dir=self.tmp.name)
   outcome=summary(self.db,n)
   self.assertEqual(outcome["stage"],"abstained")
   self.assertIsNone(outcome["learned_draft_sha256"])
   self.assertEqual(outcome["experience_admission"]["cause"],"NO_SCENE_FACTS")
   self.assertIsNone(pending(self.db,n)["host_prompt"])
   self.assertEqual(len(outcome["events"]),3)
 def test_unreviewed_source_cannot_turn_typed_story_into_training(self):
  name=self.new(9,"记录一个人物对尚未核实的旧物线索做出具有现实后果的选择的完整原创短篇场景")
  self.finish_learning(name);row=_trial(self.db,name)
  self.typed_scene(row,reviewed=False)
  decision=choose_experience(self.db,row)
  self.assertEqual(decision.cause,"SOURCE_REVIEW_NOT_APPROVED")
 def test_typed_and_attested_source_can_enter_sandbox_only(self):
  name=self.new(10,"描写一名角色发现密封物件异常，最终根据有限事实做出有代价的原创决定")
  self.finish_learning(name);row=_trial(self.db,name)
  self.typed_scene(row)
  decision=choose_experience(self.db,row)
  self.assertEqual(decision.state,"ELIGIBLE_EXPERIMENT_ONLY")
  plain=_packet(self.db,row,False)
  active=_packet(self.db,row,True)
  self.assertTrue(active.prompt.startswith(plain.prompt))
  self.assertNotEqual(active.prompt_sha256,plain.prompt_sha256)
  self.assertIn("测试角色",active.prompt)
  self.assertIn("clue-fact",active.prompt)
  self.assertFalse(active.strategy_receipt["literary_improvement_verified"])
  self.assertFalse(active.strategy_receipt["semantic_correctness_verified"])
 def test_resolved_or_contradictory_fact_abstains(self):
  for i,flaw in enumerate(("known","payoff")):
   name=self.new(20+i,"写人物面对未知线索、责任与风险作出一个后果明确的场景选择")
   self.finish_learning(name);row=_trial(self.db,name)
   self.typed_scene(row,known=flaw=="known",role="payoff" if flaw=="payoff" else "setup")
   decision=choose_experience(self.db,row)
   self.assertEqual(decision.state,"ABSTAIN")
   self.assertIn(decision.cause,("FACT_KNOWN_OR_CONTRADICTED","UNCONFIRMED_NARRATIVE_ROLE"))
 def test_result_does_not_promote_old_failed_evidence(self):
  name=self.new(30,"写一段具有清晰场景与人物关系、没有既定文学经验指导的原创人物行为片段")
  self.finish_learning(name)
  r=summary(self.db,name)
  self.assertFalse(r["skill_autonomous_literary_gain_proven"])
  self.assertEqual(r["stage"],"baseline")

if __name__=="__main__":
 unittest.main()
