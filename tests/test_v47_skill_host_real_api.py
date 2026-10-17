"""V47 source-grounded REAL WF host protocol; synthetic replies are NEVER
credited as literary model generations or improvement.
"""
from __future__ import annotations

from hashlib import sha256
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from contextlib import redirect_stdout
import json
import unittest

from writerforge import WriterForgeDB
from writerforge.skill_host_session import start,pending,submit,summary,HostSkillError
from writerforge.cli import main

REAL=Path(__file__).resolve().parent/"fixtures"/"xiyouji_chapter_001_original_zh.txt"
GOAL="江湖旧友因一份无人签名的账簿被迫在彼此信任和眼前利益之间做出选择，要让人物行动因果自洽。"
MODEL="SYNTHETIC_CONTRACT_TEST_NOT_AN_ACTUAL_MODEL"
FIRST=json.dumps({
 "expectations":["有人可能会决定用行动改变此前的困局"],
 "questions":["目前还不清楚人物下一步具体怎样选择"],
 "character_inferences":["人物此刻只掌握公开场景信息还不知道后续事件"],
},ensure_ascii=False)
DRAFT1=("暮色落到驿道上，卖炭人把账册放到桌边。"
        "他听见门外有人争吵，却没有立即开门。"
        "旧友从檐下走来，举起湿漉漉的包袱。"
        "他想起昨天听来的半句话，于是先问清楚事情经过。"
        "两人争执到夜里，才看见掌柜留下的纸条。")*5
DRAFT2=("夜色正浓，药铺门外传来敲门声。"
        "药童看见门缝里的信笺，却无法确定送信的人是谁。"
        "他根据已经知道的消息推测来者可能是旧友。"
        "他先向看门人问了两个问题，随后才决定开门。"
        "结果误了送药时刻，才发现旧印来自另一个人。")*5


class HostSkillLiveAPITests(unittest.TestCase):
 def setUp(self):
  self.tmp=TemporaryDirectory()
  self.db=WriterForgeDB(Path(self.tmp.name)/"trial.sqlite")
  self.source=Path(self.tmp.name)/"chapter-original.txt"
  self.source.write_bytes(REAL.read_bytes())
  self.run="actual-skill-contract-01"
  self.init=start(self.db,run_id=self.run,source=str(self.source),
                  goal=GOAL,model_id=MODEL)
 def tearDown(self):
  self.db.close();self.tmp.cleanup()
 def send(self,payload,*,model=MODEL,hash=None):
  p=pending(self.db,self.run)
  return submit(self.db,run_id=self.run,model_id=model,
                reply=payload,prompt_sha256=hash or p["prompt_sha256"],
                output_dir=str(Path(self.tmp.name)/"runs"))
 def test_original_learner_gate_to_same_host_writing_and_readback(self):
  p1=pending(self.db,self.run)
  self.assertEqual(p1["stage"],"first")
  self.assertNotIn("不许事后改写这些推测",p1["host_prompt"])
  self.assertTrue(self.init["source_ingested_into_existing_WF_Xuehai"])
  with self.assertRaisesRegex(HostSkillError,"HOST_MODEL_CHANGED"):
   self.send(FIRST,model="ANOTHER_MODEL")
  with self.assertRaisesRegex(HostSkillError,"HOST_REPLY_FOR_DIFFERENT_PROMPT"):
   self.send(FIRST,hash="0"*64)
  first=self.send(FIRST)
  self.assertEqual(first["next_stage"],"close")
  p2=pending(self.db,self.run)
  self.assertEqual(p2["stage"],"close")
  self.assertIn("不许事后改写这些推测",p2["host_prompt"])
  # Pick a real verbatim quote programmatically; no examiner-supplied lesson.
  from writerforge.skill_host_session import _trial,_load
  row=_trial(self.db,self.run)
  _,scene=_load(row)
  quote=scene.text[310:360].strip()
  reading=json.dumps({"mechanisms":[{
   "source_quote":quote,
   "hypothesis":"前文先限定了人物见闻，后续行动能改变读者已经建立的预期",
   "counterfactual":"若先交代所有后续真相，前面建立的疑问就难以推动读者继续",
   "transfer_question":"新作的读者是否先获得足够线索再理解人物付出的具体代价",
  }]},ensure_ascii=False)
  deep=self.send(reading)
  self.assertEqual(deep["next_stage"],"baseline")
  b=pending(self.db,self.run)
  self.assertNotIn("从已锁定原文分析自动选取",b["host_prompt"])
  self.send(DRAFT1)
  learned=pending(self.db,self.run)
  self.assertEqual(learned["stage"],"learned")
  self.assertIn("从已锁定原文分析自动选取",learned["host_prompt"])
  self.assertNotEqual(learned["prompt_sha256"],b["prompt_sha256"])
  self.assertNotIn(quote,learned["host_prompt"])
  self.send(DRAFT2)
  review=pending(self.db,self.run)
  self.assertEqual(review["stage"],"self_review")
  self.assertIn("只是同一宿主自评",review["host_prompt"])
  self.send(json.dumps({
   "baseline_problem":"前段故事没有清楚写出关键的已知和未知信息",
   "learned_problem":"后段的因果链仍有突兀的推进与真实动机不足",
   "evidence_baseline":DRAFT1[:22],
   "evidence_learned":DRAFT2[:22],
  },ensure_ascii=False))
  s=summary(self.db,self.run)
  self.assertEqual(s["stage"],"complete")
  self.assertEqual(len(s["events"]),5)
  self.assertEqual(s["baseline_draft_sha256"],sha256(DRAFT1.encode()).hexdigest())
  self.assertEqual(s["learned_draft_sha256"],sha256(DRAFT2.encode()).hexdigest())
  self.assertTrue(s["learned_experience_recorded"])
  self.assertFalse(s["skill_autonomous_literary_gain_proven"])
  self.assertFalse(s["host_installation_proven"])
  self.db.close()
  self.db=WriterForgeDB(Path(self.tmp.name)/"trial.sqlite")
  self.assertEqual(summary(self.db,self.run)["stage"],"complete")
  with self.assertRaisesRegex(HostSkillError,"HOST_TRIAL_ALREADY_COMPLETE"):
   self.send(DRAFT1)
 def test_frozen_source_refuses_edition_change(self):
  with self.assertRaisesRegex(HostSkillError,"HOST_RUN_ALREADY_EXISTS"):
   start(self.db,run_id=self.run,source=str(self.source),
         goal=GOAL,model_id=MODEL)
  text=self.source.read_text(encoding="utf-8")
  self.source.write_text(text+"有人私自修改了书尾。",encoding="utf-8")
  with self.assertRaisesRegex(HostSkillError,"HOST_SOURCE_EDITION_CHANGED"):
   pending(self.db,self.run)
 def test_bad_stage_payload_must_not_be_filled_in_by_skill(self):
  with self.assertRaisesRegex(HostSkillError,"HOST_STAGE_REJECTED"):
   self.send('{"not_a_reader":"pre-filled sample"}')
  s=summary(self.db,self.run)
  self.assertEqual(s["stage"],"first")
  self.assertEqual(s["failed_submissions"],1)
  self.assertEqual(len(s["events"]),0)
 def test_cli_exposes_actual_skill_subcommands(self):
  cli_db=Path(self.tmp.name)/"cli.sqlite"
  with redirect_stdout(StringIO()) as out:
   main(["--db",str(cli_db),"skill-host-start","--run-id","real-CLI-01",
         "--source",str(REAL),"--chapter","1",
         "--model-id",MODEL,"--goal",GOAL])
  data=json.loads(out.getvalue())
  self.assertEqual(data["stage"],"first")
  with redirect_stdout(StringIO()) as out:
   main(["--db",str(cli_db),"skill-host-next","--run-id","real-CLI-01"])
  p=json.loads(out.getvalue())
  self.assertIn("截至此刻可见原文",p["host_prompt"])
  self.assertTrue(p["prompt_sha256"])
  with redirect_stdout(StringIO()) as out:
   main(["--db",str(cli_db),"skill-host-status","--run-id","real-CLI-01"])
  s=json.loads(out.getvalue())
  self.assertEqual(s["stage"],"first")
  self.assertFalse(s["skill_autonomous_literary_gain_proven"])

if __name__=="__main__":
 unittest.main()
