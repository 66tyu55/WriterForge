"""V27 tests: ordered source comprehension -> ONE -> TWO -> MANY categories.

Model return values are fixtures. No synthetic review is ever represented as
real external criticism, and no machine observation is auto-verified.
"""
from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import json
import sqlite3
import unittest

from writerforge import WriterForgeDB,RuntimeEngine
from writerforge.encyclopedia import FictionEncyclopedia,FacetQuery
from writerforge.literary_ladder import LiteraryLadder,LadderError,STAGES

SOURCE = "山门前的女弟子停住脚步，望见老人来时把剑柄藏到袖中，过了许久才问了一句。"
SHORT = "她将袖口往下压了压，听见石阶上的脚步声，才不紧不慢地转身迎上前去。"
SINGLE = ("少女将杯子轻轻放在桌边，眼睛望着院内的雨帘。她本可以立刻离开，却一直等到对方把"
          "最后一句话说完，才轻轻地拉开木门。")
PAIR = SINGLE+"屋外的风卷起一片潮湿的落叶，落叶被她踩住的时候，她忽然做了一个决定。"
MANY = PAIR+"远处古钟响了三声，岩壁后有水声流过，她握紧衣袖，却没有回头向那位老人求助。"
PARA = MANY+SINGLE+PAIR
SCENE = (MANY+PAIR+SINGLE)*3

ANALYSIS=json.dumps({
    "category":"行为",
    "evidence":"停住脚步",
    "certainty":"explicit",
    "reason":"原文明确描述人物暂时停止行动，但无法确定其全部心理动机。",
    "text":SHORT,
},ensure_ascii=False)


def make_source(db):
    con=db.conn
    sid=con.execute(
        "INSERT INTO snapshots(parent_id,status,layout,note) VALUES(NULL,'published','full','real source demo')"
    ).lastrowid
    con.execute(
        """INSERT INTO studied_works(work_id,title,source_uri,source_sha256,chapter_count)
           VALUES('original-book','古代白话原著','test://public-domain-original','studyhash',1)"""
    )
    for p,text in enumerate((SOURCE, "岩洞中落下水滴，门外的老者拿着一枚青铜铃。"
                              "那铃声传过石壁，赶路的人便停下了脚步。",
                              "有一种猛兽栖息在山谷深处，背覆鳞甲，"
                              "寒夜时伏在巨石上，听见脚步便跃起。" ),1):
        con.execute(
            """INSERT INTO source_spans(work_id,chapter,paragraph,sentence,excerpt,
                        source_sha256,tracks_json,craft_json)
                VALUES('original-book',1,?,1,?,?,'{}','{}')""",
            (p,text,"hash-"+str(p)),
        )
        con.execute(
            """INSERT INTO xuehai_entries(snapshot_id,work_id,chapter,paragraph,sentence,text,
                 library_class,culture,genre,source_role,function,effect,method_cluster,source_hash)
                VALUES(?,'original-book',1,?,1,?,'中国古典原著','中国','古代白话',
                       'core','action_sequence','unverified','classical_action','ref')""",
            (sid,p,text),
        )
    con.execute(
        """INSERT INTO studied_chapters(work_id,chapter,chapter_sha256,heading,
                       source_spans,retrieval_entries,snapshot_id)
           VALUES('original-book',1,'chapterhash','第一回',3,3,?)""",(sid,)
    )
    con.commit()
    return sid


class LadderStageTests(unittest.TestCase):
    def setUp(self):
        self.tmp=TemporaryDirectory()
        self.root=Path(self.tmp.name)
        self.dbfile=self.root/"learning.sqlite3"
        self.db=WriterForgeDB(self.dbfile)
        sid=make_source(self.db)
        self.rt=RuntimeEngine()
        self.rt.enter_write(sid)
        self.engine=LiteraryLadder(self.db,self.rt,"novel-a")

    def tearDown(self):
        self.db.close()
        self.tmp.cleanup()

    def approved_categories(self):
        enc=FictionEncyclopedia(self.db)
        ch=enc.entity(work_id="original-book",kind="character",name="山门少女",
                      genre="古代白话",gender="female")
        place=enc.entity(work_id="original-book",kind="place",name="山门",
                         genre="古代白话")
        beast=enc.entity(work_id="original-book",kind="creature",name="谷底猛兽",
                         genre="古代白话",subtype="野兽")
        rows=(
            (ch,1,"性格/女性/谨慎","举动","停住脚步"),
            (place,2,"地点/山门/声响","环境声音","那铃声传过石壁"),
            (beast,3,"外貌/野兽/鳞甲","体表","背覆鳞甲"),
        )
        for entity,p,cat,attr,quote in rows:
            proof=enc.observe(
                entity_id=entity,chapter=1,paragraph=p,sentence=1,
                category_path=cat,attribute=attr,quotation=quote,
                explanation="人工核对源句位置，关联实体和当前属性。",
                origin="manual",
            )
            enc.review(proof,approved=True,reason="测试扮演人工核验，对应实际来源",
                       reviewer_confirmed=True)

    def test_tiers_progress_without_smuggling_unreviewed_facets(self):
        steps=self.engine.tasks(work_id="original-book",
                                goal="设计一次忠诚与恐惧冲突中的人物选择")
        self.assertEqual([x.readiness for x in steps],
                         ["ready"]+["blocked_unverified_facets"]*5)
        self.assertEqual(steps[0].source_excerpt,SOURCE)
        with patch("writerforge.literary_ladder.local_chat_completion",return_value=ANALYSIS) as model:
            result=self.engine.run(
                work_id="original-book",
                goal="设计一次忠诚与恐惧冲突中的人物选择",
                model="local-model-test",through_stage=6,
                output_dir=self.root/"stage-drafts",
            )
        self.assertEqual(model.call_count,1)
        self.assertEqual([x["status"] for x in result["attempts"]],
                         ["practiced_not_mastered","blocked_unverified_facets"])
        self.assertFalse(result["literary_skill_promoted"])
        self.assertFalse(result["model_finetuned"])
        self.assertEqual(self.db.conn.execute(
            "SELECT COUNT(*) FROM literary_training_attempts"
        ).fetchone()[0],1)
        self.assertEqual(self.db.conn.execute(
            "SELECT COUNT(*) FROM encyclopedia_evidence WHERE status='verified'"
        ).fetchone()[0],0)

    def test_true_reviewed_category_sources_make_two_and_three_class_tasks_ready(self):
        self.approved_categories()
        stages=self.engine.tasks(work_id="original-book",
                                 goal="先写动作，再由环境影响角色作出选择")
        self.assertTrue(all(item.readiness=="ready" for item in stages))
        self.assertEqual([len(x.facet_cards) for x in stages],[0,1,2,3,3,3])
        combined={x["category_path"].split("/")[0] for x in stages[3].facet_cards}
        self.assertEqual(combined,{"性格","地点","外貌"})
        with patch("writerforge.literary_ladder.local_chat_completion",
                   side_effect=(ANALYSIS,SINGLE,PAIR,MANY)) as model:
            result=self.engine.run(
                work_id="original-book",goal="先写动作，再由环境影响角色作出选择",
                model="local-model-test",through_stage=4,output_dir=self.root/"run",
            )
        self.assertEqual(model.call_count,4)
        self.assertEqual([x["status"] for x in result["attempts"]],
                         ["practiced_not_mastered"]*4)
        self.assertTrue(all(x["source_facets"]>=0 for x in result["attempts"]))
        with sqlite3.connect(self.dbfile) as con:
            self.assertEqual(con.execute(
                "SELECT COUNT(*) FROM literary_training_attempts WHERE project_id='novel-a'"
            ).fetchone()[0],4)
        last=Path(result["attempts"][-1]["receipt"])
        meta=json.loads(last.read_text(encoding="utf-8"))
        self.assertEqual(meta["task"]["stage"],4)
        self.assertEqual(len(meta["task"]["selected_facets"]),3)
        self.assertEqual(meta["status"],"not_run_short_stage")
        self.assertFalse(meta["skill_promoted"])

    def test_wrong_model_evidence_cannot_pass_first_classification(self):
        invalid=json.dumps({
            "category":"性格","evidence":"这里没有这个词语",
            "certainty":"explicit","reason":"看到了原文",
            "text":SHORT,
        },ensure_ascii=False)
        with patch("writerforge.literary_ladder.local_chat_completion",return_value=invalid):
            with self.assertRaisesRegex(LadderError,"unproven category"):
                self.engine.run(work_id="original-book",
                                goal="塑造一个善于隐藏忧虑的女子",
                                model="dummy",output_dir=self.root/"invalid")
        self.assertEqual(self.db.conn.execute(
            "SELECT COUNT(*) FROM literary_training_attempts"
        ).fetchone()[0],0)

    def test_stale_source_proof_cannot_be_used_for_composition(self):
        self.approved_categories()
        self.db.conn.execute(
            "UPDATE source_spans SET source_sha256='changed' WHERE paragraph=3"
        )
        self.db.conn.commit()
        stages=self.engine.tasks(work_id="original-book",
                                 goal="让一名少女在危机中改变对人的看法")
        self.assertEqual(stages[2].readiness,"ready")
        self.assertEqual(stages[3].readiness,"blocked_unverified_facets")
        self.assertEqual(len(stages[2].facet_cards),2)

    def test_no_global_50_work_judgement_or_skill_promotion(self):
        self.approved_categories()
        with patch("writerforge.literary_ladder.local_chat_completion",
                   side_effect=(ANALYSIS,SINGLE,PAIR,MANY,PARA,SCENE)):
            result=self.engine.run(
                work_id="original-book",goal="少女必须守住诺言但又不能让同伴受伤",
                model="dummy",through_stage=6,output_dir=self.root/"all")
        self.assertEqual(len(result["attempts"]),6)
        self.assertTrue(result["global_50_book_review_performed"] is False)
        self.assertFalse(result["literary_skill_promoted"])
        receipt=json.loads(Path(result["attempts"][4]["receipt"]).read_text())
        self.assertEqual(receipt["status"],"independent_critic_not_configured")
        self.assertNotIn("critique_report_path",receipt)

    def test_independent_litcritic_review_causes_bounded_revision_without_fake_promotion(self):
        self.approved_categories()
        project=self.root/"real-critic-project"
        project.mkdir()
        (project/"CANON.md").write_text("# 人物与世界事实\n",encoding="utf-8")
        (project/"STYLE.md").write_text("# 克制，不照抄原文\n",encoding="utf-8")
        def actual_report(**kwargs):
            path=self.root/"critic-output.json"
            path.write_text(json.dumps({
                "provider":"lit-critic","verified_with_live_provider":True,
                "findings":[{"impact":"这里人物选择的后果过于轻描淡写，风险没有兑现。"}],
                "scene_sha256":"external-report-fixture",
            },ensure_ascii=False),encoding="utf-8")
            return {"json":str(path),"markdown":str(path.with_suffix(".md")),"count":1}

        with patch("writerforge.literary_ladder.local_chat_completion",
                   side_effect=(ANALYSIS,SINGLE,PAIR,MANY,PARA,PARA)) as model, \
             patch("writerforge.literary_ladder.LitCriticAdapter.review",
                   side_effect=actual_report) as reviewer:
            result=self.engine.run(
                work_id="original-book",
                goal="少女在守约与照顾同伴之间作出选择并承担责任",
                model="local-fixture",
                through_stage=5,critic_project=project,
                output_dir=self.root/"independent",
            )
        self.assertEqual(reviewer.call_count,1)
        self.assertEqual(model.call_count,6)
        last=result["attempts"][-1]
        self.assertEqual(last["critic_status"],"independent_review_then_revision_unverified")
        receipt=json.loads(Path(last["receipt"]).read_text(encoding="utf-8"))
        self.assertIn("critique_report_path",receipt)
        self.assertIn("revision_candidate_sha256",receipt)
        self.assertFalse(receipt["skill_promoted"])
        self.assertEqual(self.db.conn.execute(
            "SELECT COUNT(*) FROM literary_training_attempts WHERE status='independent_review_then_revision_unverified'"
        ).fetchone()[0],1)

    def test_litcritic_failure_still_persists_the_unevaluated_original(self):
        self.approved_categories()
        project=self.root/"unavailable-critic"
        project.mkdir()
        (project/"CANON.md").write_text("# 人物事实\n",encoding="utf-8")
        (project/"STYLE.md").write_text("# 文体\n",encoding="utf-8")
        with patch("writerforge.literary_ladder.local_chat_completion",
                   side_effect=(ANALYSIS,SINGLE,PAIR,MANY,PARA)), \
             patch("writerforge.literary_ladder.LitCriticAdapter.review",
                   side_effect=ConnectionError("private critic endpoint unavailable")):
            with self.assertRaises(ConnectionError):
                self.engine.run(
                    work_id="original-book",goal="主人公为了不失信必须承担救人的后果",
                    model="local-fixture",through_stage=5,
                    critic_project=project,output_dir=self.root/"unavailable",
                )
        failed=self.db.conn.execute(
            "SELECT status,receipt_json FROM literary_training_attempts WHERE stage=5"
        ).fetchone()
        self.assertEqual(failed["status"],"critic_failed")
        self.assertEqual(json.loads(failed["receipt_json"])["failure_type"],"ConnectionError")
        self.assertEqual(self.db.conn.execute(
            "SELECT COUNT(*) FROM literary_training_attempts"
        ).fetchone()[0],5)

    def test_restart_can_query_durable_trial_and_strict_quota(self):
        with patch("writerforge.literary_ladder.local_chat_completion",return_value=ANALYSIS):
            result=self.engine.run(
                work_id="original-book",goal="写出一个克制人物面对误会时的举动",
                model="dummy",output_dir=self.root/"bounded")
        self.db.close()
        reopened=WriterForgeDB(self.dbfile)
        row=reopened.conn.execute(
            "SELECT model,body,status,receipt_json FROM literary_training_attempts"
        ).fetchone()
        self.assertEqual(row["body"],SHORT)
        self.assertEqual(row["model"],"dummy")
        self.assertFalse(json.loads(row["receipt_json"])["skill_promoted"])
        self.db=reopened
        self.engine=LiteraryLadder(reopened,self.rt,"novel-a")


if __name__=="__main__":
    unittest.main()
