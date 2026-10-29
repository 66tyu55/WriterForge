"""0.CL R2-grounded negative regressions expressed with repo's genuine classics.

Neither these source-only tests nor the older 0.CK cases are new blind holdouts:
all came from already observed real source failures. No new library or model.
"""
from __future__ import annotations

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from writerforge import WriterForgeDB, RuntimeEngine, XuehaiStore
from writerforge.xuehai import _author_craft_scope

ROOT=Path(__file__).resolve().parents[1]
BW=ROOT/"experiments/wf_0bw_three_fantasy_classics_six_long_readings_20261029.json"
BU=ROOT/"experiments/wf_0bu_remaining_sixteen_original_close_readings_20261028.json"

def _real_reading(row, role):
    if role=="classical_original_annotation_reflection":
        orig=row["original"]
        source=f'{row["work"]}·{row["chapter"]}'
    else:
        bqid=row["source_id"] if "source_id" in row else row["id"]
        # Published 0.BU includes the actual original prose in each row or
        # references the 0.BQ source; fetch it from the pinned 0.BQ corpus.
        original=row.get("original")
        if not original:
            corpus=json.loads((ROOT/"experiments/wf_0bq_full_literary_detail_corpus_A_20261028.json").read_text("utf8"))
            corpus["items"]+=json.loads((ROOT/"experiments/wf_0bq_full_literary_detail_corpus_B_20261028.json").read_text("utf8"))["items"]
            match=next(o for o in corpus["items"] if o["id"].startswith(bqid.split("-")[-1]+"-"))
            original=match["prose"]
        orig=original
        source=f'WF original unaccepted scene {row["id"]}'
    return "【出处】"+source+"\n【原文】\n"+orig+"\n【批注】\n"+\
        "\n".join(row["annotation"])+"\n【心得】\n"+row["reflection"]

class SourceBasedTransferRegressions(unittest.TestCase):
    def setUp(self):
        self.temp=TemporaryDirectory()
        self.db=WriterForgeDB(Path(self.temp.name)/"only-published-real-literature.sqlite3")
        self.rt=RuntimeEngine()
        self.rt.enter_learn()
        self.store=XuehaiStore(self.db,self.rt)
        sid=self.store.create_staging_snapshot()
        bw={x["id"]:x for x in json.loads(BW.read_text("utf8"))["items"]}
        bu={x["id"]:x for x in json.loads(BU.read_text("utf8"))["items"]}
        for id,role,row in [
            ("classic-fantasy-jh-3","classical_original_annotation_reflection",bw["classic-fantasy-jh-3"]),
            ("original-read-bq-03","original_annotation_reflection",bu["original-read-bq-03"]),
            ("original-read-bq-04","original_annotation_reflection",bu["original-read-bq-04"]),
            ("original-read-bq-13","original_annotation_reflection",bu["original-read-bq-13"]),
        ]:
            self.store.add_entry(sid,work_id=id,text=_real_reading(row,role),
                                 source_role=role,method_cluster=id,genre="广义叙事")
        self.store.publish(sid)
        self.rt.exit()
        self.rt.enter_write(sid)

    def tearDown(self):
        self.rt.exit()
        self.db.close()
        self.temp.cleanup()

    def _selected(self,goal,problem):
        v=self.store.select_literary_reading_for_author(
            goal=goal,writing_problem=problem,max_chars=4900)
        if v is None:
            return None
        r=self.db.conn.execute(
            "SELECT method_cluster FROM xuehai_entries WHERE id=?",
            (v["entry_id"],)).fetchone()
        self.assertTrue(all(s in v["complete_reading"]
                            for s in ("【原文】","【批注】","【心得】")))
        return r["method_cluster"]

    def test_real_jinghuayuan_social_treatment_is_not_discarded_before_ranking(self):
        from experiments.wf_0ck_real_classics_unseen_probe import UNSEEN
        case=next(c for c in UNSEEN if c["id"]=="coat-swap-reveals-social-mask")
        self.assertNotEqual(_author_craft_scope(case["problem"]),"")
        self.assertEqual(self._selected(case["goal"],case["problem"]),
                         "classic-fantasy-jh-3")

    def test_quiet_care_not_replaced_by_technique_about_faulty_array(self):
        from experiments.wf_0ck_real_classics_unseen_probe import UNSEEN
        case=next(c for c in UNSEEN if c["id"]=="quiet-everyday-fragment")
        selected=self._selected(case["goal"],case["problem"])
        self.assertNotEqual(selected,"original-read-bq-03")
        # No consensus that other sources are fully applicable. Abstention is
        # permissible and should not be counted as missed literary truth.

    def test_unseen_real_classical_tasks_with_explicit_prose_intent_reach_craft_scope(self):
        # This set was frozen and RUN before the 0.CL diagnosis; see
        # the immutable first 14-case R2 GitHub Actions result.
        frozen=json.loads((ROOT/"experiments/wf_0cl_frozen_unseen_transfer_cases_20261029.json").read_text("utf8"))
        by_id={x["id"]:x for x in frozen["cases"]}
        for case_id in (
            "new-dd1-giving-up-catch-hunger",
            "new-zb1-servant-sacrifice-doubt",
            "new-dd2-false-river-spirit-tolls",
            "new-partial-social-speaking-vs-power",
        ):
            with self.subTest(case_id=case_id):
                self.assertNotEqual(
                    _author_craft_scope(by_id[case_id]["writing_problem"]),"")
        # Calling a mere wish for better text a source-grounded transfer
        # would not be justified; abstention must remain possible.
        self.assertEqual(_author_craft_scope("希望这一章写得更好"),"")

    def test_existing_genuine_classic_full_text_remains_untouched(self):
        data=json.loads(BW.read_text("utf8"))
        jing=next(x for x in data["items"] if x["id"]=="classic-fantasy-jh-3")
        original=jing["original"]
        row=self.db.conn.execute(
            "SELECT text FROM xuehai_entries WHERE method_cluster=?",
            ("classic-fantasy-jh-3",)).fetchone()
        self.assertIn(original,row["text"])
        self.assertIn("下半回",row["text"])
        self.assertIn("【心得】",row["text"])

if __name__=="__main__":
    unittest.main()
