"""V45 independent red-team tests; genuine WF SQLite and production writer flow.

Fixture story-state is authored by the TEST, not learned by WF. No model,
fiction-quality score or external reviewer is claimed.
"""
import json, hmac, unittest
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
from writerforge import WriterForgeDB,RuntimeEngine,OriginalStudy,VerifiedWritingFlow,WritingExecutionError,save_candidate
from writerforge.v45_state_experience import StateDerivedExperience,V45ExperienceError,_canon

SOURCE=Path(__file__).parent/"fixtures"/"xiyouji_chapter_001_original_zh.txt"
CASES=(
 ("storm-coast","海岸邮差发现渡船航次被改动"),
 ("snow-inn","雪镇旅店发现失踪客人的留言"),
 ("orchard","果园合伙人发现账目交接异常"),
 ("desert-watch","沙漠巡护员发现水箱封签破损"),
 ("canal","运河船工发现旧航标偏离河道"),
 ("theater","剧团服装师发现演出衣箱被调换"),
)
PROSE=("青禾在渡口看见那枚铜铃挂在门边。她尚未确定是谁重新挂起。"
       "青禾因此决定暂缓放行，把船票放回匣子。"
       "这一停顿使守船的年轻人错过了当天的末班渡轮。"
       "天明时青禾知道了铜铃是旧渡船留下的信号。")
QUOTES={
"observation":"青禾在渡口看见那枚铜铃挂在门边",
"actor_decision":"青禾因此决定暂缓放行，把船票放回匣子",
"causal_consequence":"这一停顿使守船的年轻人错过了当天的末班渡轮",
"later_reveal":"天明时青禾知道了铜铃是旧渡船留下的信号",
}

class ActualWFV45(unittest.TestCase):
 def setUp(self):
  self.tmp=TemporaryDirectory()
  self.db=WriterForgeDB(Path(self.tmp.name)/"original.sqlite")
  rt=RuntimeEngine();rt.enter_learn()
  OriginalStudy(self.db,rt).ingest(SOURCE.read_text(encoding="utf-8"),work_id="v45-real-fixture",require_hundred=False)
  sid=self.db.conn.execute("SELECT MAX(id) id FROM snapshots WHERE status='published'").fetchone()["id"]
  rt.exit();rt.enter_write(int(sid))
  self.flow=VerifiedWritingFlow(self.db,rt,"v45-audit")
  self.p=StateDerivedExperience(self.db.conn,"v45-audit")
  self.key=self.p.install(opt_in=True)
 def tearDown(self):
  self.db.close();self.tmp.cleanup()
 def seed(self,scene,known=None,unknown=None,role="setup",review="candidate",token="铜铃"):
  known=["old_route"] if known is None else known
  unknown=["seal_origin"] if unknown is None else unknown
  with self.db.conn:
   self.db.conn.execute("INSERT OR REPLACE INTO character_state(project_id,character_id,state_json) VALUES(?,?,?)",
    ("v45-audit","青禾",json.dumps({"knowledge":{"known":known,"unknown":unknown}},ensure_ascii=False)))
   self.db.conn.execute("INSERT INTO causal_events(project_id,event_id,payload_json) VALUES(?,?,?)",
    ("v45-audit",scene,json.dumps({"scene_id":scene,"actor_id":"青禾","clue_id":"id-"+scene,
     "clue_token":token,"fact_id":"seal_origin",
     "observation":"渡口旧船门边的铜铃重新被挂在门前",
     "choice":"暂缓放行并核对旧铜铃与船期记录",
     "expected_consequence":"年轻船员因此错过了末班渡轮",
     "reveal_target":"铜铃确是旧船留下，但并不代表有人破坏",
     "alternative":"也可能是搬运者把旧铜铃放回原位",
     "narrative_role":role,"review_status":review},ensure_ascii=False)))
 def prep(self,scene,goal="一个原创人物因果场景",enabled=True,concerns=("setup_payoff",)):
  return self.flow.prepare(scene,goal,concerns=concerns,v45_experience=enabled)
 def test_six_new_scenes_real_generation_prompt_changes(self):
  for scene,goal in CASES:
   self.seed(scene)
   base=self.prep(scene,goal,False)
   learned=self.prep(scene,goal,True)
   self.assertNotEqual(base.prompt,learned.prompt)
   self.assertNotIn("铜铃",base.prompt)
   self.assertIn("铜铃",learned.prompt)
   self.assertEqual(learned.strategy_receipt["state"],"APPLIED")
   self.assertFalse(learned.strategy_receipt["literary_semantics_verified"])
   self.assertEqual(self.db.conn.execute("SELECT COUNT(*) FROM wf_v45_prewrite WHERE project=? AND scene=?",
                     ("v45-audit",scene)).fetchone()[0],1)
 def test_no_examiner_plan_accepted(self):
  self.seed("manual")
  with self.assertRaisesRegex(WritingExecutionError,"V45_REJECTS_EXAMINER"):
   self.flow.prepare("manual","故事",concerns=("setup_payoff",),v45_experience=True,
                     causal_plan={"examiner":"filled story"})
 def test_contradictory_and_disputed_states_are_withheld(self):
  self.seed("contradict",known=["seal_origin"],unknown=["seal_origin"])
  self.assertEqual(self.prep("contradict").strategy_receipt["state"],"WITHHELD_CONTRADICTORY_FACT_IDS")
  self.seed("known",known=["seal_origin"],unknown=["other_fact"])
  self.assertEqual(self.prep("known").strategy_receipt["state"],"WITHHELD_KNOWN_REVEAL_NOT_SETUP")
  self.seed("disputed",review="disputed")
  self.assertEqual(self.prep("disputed").strategy_receipt["state"],"WITHHELD_DISPUTED")
  self.seed("paid",role="payoff")
  self.assertEqual(self.prep("paid").strategy_receipt["state"],"WITHHELD_ALREADY_PAYOFF")
 def test_irrelevant_event_abstains(self):
  self.assertEqual(self.prep("no-event").strategy_receipt["state"],"WITHHELD_NO_STORY_STATE")
  self.assertEqual(self.prep("dialogue",concerns=("dialogue",)).strategy_receipt["state"],"NOT_APPLICABLE")
 def test_frozen_prewrite_cannot_change_after_input_mutation(self):
  self.seed("frozen");self.prep("frozen")
  with self.db.conn:
   self.db.conn.execute("UPDATE character_state SET state_json=? WHERE project_id=? AND character_id=?",
        (json.dumps({"knowledge":{"known":["old_route","later_info"],"unknown":["seal_origin"]}}),
         "v45-audit","青禾"))
  with self.assertRaisesRegex(WritingExecutionError,"V45_PREWRITE_IMMUTABLE"):
   self.prep("frozen")
 def test_true_anchors_only_structurally_pass_and_missing_fails(self):
  self.seed("draft");p=self.prep("draft")
  with self.assertRaisesRegex(WritingExecutionError,"V45_POSTWRITE_FOUR_ANCHORS"):
   save_candidate(p,PROSE,"synthetic-fixture",Path(self.tmp.name)/"out")
  saved=save_candidate(p,PROSE,"synthetic-fixture",Path(self.tmp.name)/"out",postwrite_evidence=QUOTES)
  metadata=json.loads(Path(saved["manifest"]).read_text(encoding="utf-8"))
  self.assertEqual(metadata["v45_experience_postwrite_receipt"]["format"],"WF.v45.afterdraft.v1")
  self.assertFalse(metadata["experience_semantic_correctness_verified"])
 def test_old_disconnected_four_sentences_no_longer_pass(self):
  self.seed("attack");p=self.prep("attack")
  story=("村口晒着四个未收走的空竹篮。少女走到城中买了两斤盐和一尺麻绳。"
         "昨夜的雨冲掉了山坡上的几片旧瓦。第二天有人发现书架上的画册早已虫蛀。")
  proof=dict(zip(("observation","actor_decision","causal_consequence","later_reveal"),
   ("村口晒着四个未收走的空竹篮","少女走到城中买了两斤盐和一尺麻绳",
    "昨夜的雨冲掉了山坡上的几片旧瓦","第二天有人发现书架上的画册早已虫蛀")))
  with self.assertRaisesRegex(WritingExecutionError,"V45_CLUE_IDENTITY"):
   save_candidate(p,story,"not-WF-prose",Path(self.tmp.name)/"out",postwrite_evidence=proof)
 def test_unverified_feedback_is_rejected_and_cannot_pause(self):
  self.seed("fake");self.prep("fake")
  receipt={"scene_id":"fake","policy_sha256":self.key,"reviewer_id":"forged-reviewer",
           "review_report_sha256":"a"*64,"outcome":"HARMED"}
  with self.assertRaisesRegex(V45ExperienceError,"V45_FEEDBACK_SIGNATURE_REJECTED"):
   self.p.accept_attested_feedback(receipt=receipt,mac_hex="0"*64,verifier_shared_key=b"x"*32)
  self.assertEqual(self.db.conn.execute("SELECT mode FROM wf_v45_strategy WHERE project='v45-audit'").fetchone()[0],
                   "ACTIVE_EXPERIMENT")
 def test_two_synthetic_authenticated_negative_receipts_pause_without_literary_truth(self):
  key=b"p"*32
  for n in range(2):
   scene=f"negative-{n}";self.seed(scene);self.prep(scene)
   receipt={"scene_id":scene,"policy_sha256":self.key,"reviewer_id":"synthetic-not-human",
            "review_report_sha256":sha256(scene.encode()).hexdigest(),"outcome":"HARMED"}
   result=self.p.accept_attested_feedback(
    receipt=receipt,mac_hex=hmac.new(key,_canon(receipt),"sha256").hexdigest(),verifier_shared_key=key)
  self.assertEqual(result["strategy_mode"],"PAUSED")
  self.assertFalse(result["human_or_literary_accuracy_proven"])
  self.assertEqual(self.prep("after-pause").strategy_receipt["state"],"ROLLED_BACK")

if __name__=="__main__":
 unittest.main()
