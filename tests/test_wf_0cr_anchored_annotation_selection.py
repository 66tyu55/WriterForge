"""0.CR real original tests: reflection speculation is not source-grounded proof.

All materials come verbatim from existing pinned classical 原文＋批注＋心得.
These are literary dispatch tests, not a model evaluation or literary truth.
"""
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from writerforge import WriterForgeDB,RuntimeEngine,XuehaiStore

ROOT=Path(__file__).resolve().parents[1]
FILES={
  "classic-xy-play":"experiments/wf_0br_classical_original_annotation_reflection_20261028.json",
  "classic-0cq-ss-01":"experiments/wf_0cq_five_fusheng_shishuo_close_readings_20261029.json",
  "classic-0cp-lc-04":"experiments/wf_0cp_four_lao_can_sequel_social_close_readings_20261029.json",
}

def load_source(identifier):
    data=json.loads((ROOT/FILES[identifier]).read_text("utf8"))
    r=next(row for row in data["items"] if row["id"]==identifier)
    src=data["sources"][r["source_key"]]
    full=(f"【出处】{r['work']}·{r['chapter']}｜{src['url']}\n"
          "【原文】\n"+r["original"]+"\n【批注】\n"+
          "\n".join(f"{n}. {text}" for n,text in enumerate(r["annotation"],1))+
          "\n【心得】\n"+r["reflection"])
    return r,full

class SourceGroundedDispatch(unittest.TestCase):
    def execute(self,include,goal,problem):
        with TemporaryDirectory() as tmp:
            db=WriterForgeDB(Path(tmp)/"source-only.sqlite3")
            rt=RuntimeEngine()
            try:
                rt.enter_learn()
                store=XuehaiStore(db,rt)
                snap=store.create_staging_snapshot()
                ids={}
                for name in include:
                    row,text=load_source(name)
                    entry=store.add_entry(
                        snap,work_id="gitenberg-existing-"+row["source_key"],
                        text=text,source_role="classical_original_annotation_reflection",
                        method_cluster=row["id"],function=row["topic"],
                        effect=row["title"],reuse_policy="read_reflect_not_copy")
                    ids[entry]=name
                store.publish(snap)
                rt.exit();rt.enter_write(snap)
                out=store.select_literary_reading_for_author(
                    goal=goal,writing_problem=problem,max_chars=4900)
                if out is None:
                    return None
                self.assertTrue(out["author_use_must_be_decided_by_model"])
                self.assertTrue(all(tag in out["complete_reading"]
                                    for tag in ("【原文】","【批注】","【心得】")))
                return ids[out["entry_id"]]
            finally:
                rt.exit();db.close()

    def test_only_monkey_reflection_question_cannot_answer_dangerous_promise(self):
        got=self.execute(
            ("classic-xy-play",),
            "两位修士渡河逃命，曾答应让一个陌生人上船，后遇追兵。",
            "如何写人物承诺的代价，在真正危险到来以后才显出谁愿意遵守先前选择？")
        self.assertIsNone(got)

    def test_original_boat_debate_outweighs_monkey_reflective_supposition(self):
        got=self.execute(
            ("classic-xy-play","classic-0cq-ss-01"),
            "两位修士渡河逃命，曾答应让一个陌生人上船，后遇追兵。",
            "如何写人物承诺的代价，在真正危险到来以后才显出谁愿意遵守先前选择？")
        self.assertEqual(got,"classic-0cq-ss-01")

    def test_source_boat_oath_outranks_unrelated_friendly_garden_scene(self):
        got=self.execute(
            ("classic-0cp-lc-04","classic-0cq-ss-01"),
            "战乱山路，船家已让落难旅客上船，后方追兵逼近，同行者有人提出把旅客推回岸上。",
            "怎样表现救人时口头答应得轻松，真有追兵来时却有人要反悔；既已允许他依托，面对危急还能不能丢下？")
        self.assertEqual(got,"classic-0cq-ss-01")

    def test_actual_collective_adventure_still_selects_monkeys(self):
        got=self.execute(
            ("classic-xy-play","classic-0cq-ss-01"),
            "一群猴子避暑嬉戏，在山涧洗澡后起意寻找水源，说好能进瀑布而不伤的，就推他当王。",
            "如何写玩耍、集体起哄、临时约定与冒险的自然衔接，不用一开始就搞得像严肃的宗门会议？")
        self.assertEqual(got,"classic-xy-play")

    def test_technical_code_still_no_literary_reading(self):
        got=self.execute(
            ("classic-xy-play","classic-0cq-ss-01"),
            "渡船票价、山寨物品库存及旅客记录系统",
            "请输出 Python 价格汇总公式、SQL 字段定义和 JSON 返回数据，不要创作小说。")
        self.assertIsNone(got)

if __name__=="__main__":
    unittest.main()
