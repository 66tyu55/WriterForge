"""0.CO source-grounded regression: older actual literary reading must be eligible.

Uses unchanged real 《红楼梦》 third-chapter 原文＋批注＋心得 from
0.BR. Later unrelated published readings are only a test fixture to expose
the previous 32-candidate recency truncation. No model/R2, no new schema.
"""
from __future__ import annotations
from pathlib import Path
from tempfile import TemporaryDirectory
import json
import unittest

from writerforge import WriterForgeDB,RuntimeEngine,XuehaiStore
from writerforge.xuehai import Query,_author_craft_scope,_literary_craft_grams

ROOT=Path(__file__).resolve().parents[1]
PACK=ROOT/"experiments/wf_0br_classical_original_annotation_reflection_20261028.json"
ROLE="classical_original_annotation_reflection"
GOAL="刚被仙门接纳的少女第一次参加长老家宴，面对仆人端上的茶水，猜不透自己应坐哪里。"
PROBLEM=("想写出初到仙门的少女如何在饭桌上被安排客位、反复推让，"
         "观察丫鬟侍立、茶具和礼节差异；她虽受周全照料，"
         "却还得小心判断，不能让旁白直接宣布她心里只有怨怼。")


def original_entry():
    pack=json.loads(PACK.read_text("utf8"))
    row=next(x for x in pack["items"] if x["id"]=="classic-hl-meal")
    source=pack["sources"][row["source_key"]]
    text=(f"【出处】{row['work']}·{row['chapter']}｜{source['url']}\n"
          "【原文】\n"+row["original"]+"\n【批注】\n"+
          "\n".join(f"{n}. {note}" for n,note in enumerate(row["annotation"],1))+
          "\n【心得】\n"+row["reflection"])
    return row,text


class OldRealReadingCoverage(unittest.TestCase):
    def test_old_published_classic_not_hidden_by_newer_irrelevant_text(self):
        row,full=original_entry()
        self.assertIn("賈母",row["original"])
        self.assertEqual(len(row["annotation"]),3)
        target=_literary_craft_grams(_author_craft_scope(PROBLEM))
        notes=_literary_craft_grams("\n".join(row["annotation"])+"\n"+row["reflection"])
        hits=sorted(target & notes,key=lambda t:(-len(t),t))
        nonoverlap=[]
        for token in hits:
            if not any(token in old for old in nonoverlap):
                nonoverlap.append(token)
        self.assertGreaterEqual(len(nonoverlap),3)
        with TemporaryDirectory() as tmp:
            db=WriterForgeDB(Path(tmp)/"real-source-fixture.sqlite3")
            rt=RuntimeEngine()
            try:
                rt.enter_learn()
                store=XuehaiStore(db,rt)
                sid=store.create_staging_snapshot()
                old_id=store.add_entry(
                    sid,work_id="gitenberg-pinned-hl",text=full,source_role=ROLE,
                    method_cluster="classic-hl-meal",
                    function=row["topic"],effect=row["title"])
                # This is a deterministic scheduling counterexample, not
                # additional literary or model "training" material.
                unrelated=("【出处】检索覆盖测试夹具\n【原文】\n"
                           +("工匠按次序查看铁炉温度和木箱编号。"*12)
                           +"\n【批注】\n1. 这段测试记录的机械步骤没有涉及饭桌座次。\n"
                           "2. 所有温度数据仅用于验证古籍调度的候选覆盖。\n"
                           "3. 夹具不是新的原始文学来源或文学价值判断。\n"
                           "【心得】\n本条只模拟后来插入的无关条目，不可推荐给小说作者。")
                for n in range(40):
                    store.add_entry(
                        sid,work_id=f"synthetic-unrelated-{n}",
                        text=unrelated,source_role=ROLE,
                        method_cluster=f"unrelated-{n}")
                store.publish(sid)
                rt.exit()
                rt.enter_write(sid)
                old_shortlist=store.query(Query(
                    source_role=ROLE,limit=32,max_per_work=8,max_per_cluster=1))
                self.assertNotIn(old_id,{v["entry_id"] for v in old_shortlist})
                selected=store.select_literary_reading_for_author(
                    goal=GOAL,writing_problem=PROBLEM,max_chars=4900)
                self.assertIsNotNone(selected)
                self.assertEqual(selected["entry_id"],old_id)
                self.assertIn(row["original"],selected["complete_reading"])
                self.assertIn("【心得】",selected["complete_reading"])
                self.assertTrue(selected["author_use_must_be_decided_by_model"])
            finally:
                rt.exit()
                db.close()


if __name__=="__main__":
    unittest.main()
