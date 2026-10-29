"""0.CO single read-only check of true 136/88 Xuehai before any repair.

Diagnoses whether a source-backed writing issue is screened out by
the first 32 *untargeted* candidates, rather than by its own evidence.
No score or quality grade, no model calls, no R2/Canon mutations.
"""
from __future__ import annotations
from collections import Counter
from pathlib import Path
from tempfile import TemporaryDirectory
from writerforge import WriterForgeDB,RuntimeEngine,XuehaiStore
from writerforge.xuehai import Query,_author_craft_scope,_literary_craft_grams
from experiments.wf_0cf_r2_durable_literary_snapshot import _vault
from experiments.wf_0cn_append_daily_classics import load,inspect,NEW_LIBRARY
from shutil import copyfile
import json

CASES=(
    {
      "id":"source-backed-door-to-door-horror",
      "expected_one_possible_reference":"classic-fantasy-lz-1",
      "goal":"一位筑基修士借住已经荒废的山塔，夜里听见由外向内的异声。",
      "problem":"想让原本安静的房间一点点变得不安全，每跨过一道门声响就逼近一层；结尾可以留下实物痕迹，但不能把怪事真相全部解释明白。",
    },
    {
      "id":"quiet-care-with-real-life-source",
      "expected_one_possible_reference":"classic-0cn-rl-01",
      "goal":"宗门灶边一位学徒给师兄留下一口热饭，又替他把衣襟掖好。",
      "problem":"怎样写不多言的照顾？用饭菜、衣着、劳作和省下的零碎钱带出人物之间的感情。",
    },
    {
      "id":"mother-daughter-care-paraphrase",
      "expected_one_possible_reference":"classic-0cn-rl-01",
      "goal":"冬夜一位女子照看做工归来的母亲，把仅有的好饭菜包好留给她。",
      "problem":"希望写出少言的家庭照料，借衣服、食物和手头不多的钱展示相互惦念，但不要赞美贫困。",
    },
)

def _independent(a,b):
    hits=a & b
    chosen=[]
    for token in sorted(hits,key=lambda v:(-len(v),v)):
        if not any(token in old for old in chosen):
            chosen.append(token)
    return chosen

def run():
    p=load()
    with TemporaryDirectory(prefix="wf0co-readonly-pinned-") as tmp:
        parent=Path(tmp)
        remote=_vault(cold_only=True).restore(
            library=NEW_LIBRARY,snapshot=p["base_r2_snapshot"]
            if p["base_r2_library"]==NEW_LIBRARY else
                "ae522ac98ae083a7c59f1bf0823f712c5d757a9bec144bd91defd235938a2e2a",
            destination=parent/"remote",
        )
        original_proof=inspect(Path(remote["db"]))
        if (original_proof["entries"]!=136
            or original_proof["full_readings"]!=88):
            raise ValueError("WF0CO_R2_136_SOURCE_CHANGED")
        copyfile(remote["db"],parent/"scratch.sqlite3")
        db=WriterForgeDB(parent/"scratch.sqlite3")
        runtime=RuntimeEngine()
        runtime.enter_write(XuehaiStore(db,runtime).latest_published())
        try:
            store=XuehaiStore(db,runtime)
            role_counts=dict(db.conn.execute(
                "SELECT source_role,COUNT(*) FROM xuehai_entries "
                "WHERE source_role IN ('classical_original_annotation_reflection','original_annotation_reflection') "
                "GROUP BY source_role").fetchall())
            shortlist={}
            for role in ("classical_original_annotation_reflection","original_annotation_reflection"):
                matches=store.query(Query(source_role=role,limit=32,
                                    max_per_work=8,max_per_cluster=1))
                shortlist[role]={x["entry_id"] for x in matches}
            cases=[]
            for case in CASES:
                scope=_author_craft_scope(case["problem"])
                target=_literary_craft_grams(scope)
                actual=store.select_literary_reading_for_author(
                    goal=case["goal"],writing_problem=case["problem"],max_chars=4900)
                candidate_rows=db.conn.execute(
                    "SELECT id,source_role,method_cluster FROM xuehai_entries "
                    "WHERE source_role IN ('classical_original_annotation_reflection','original_annotation_reflection')"
                ).fetchall()
                evidence=[]
                for row in candidate_rows:
                    reading=store.read_literary_reading(row["id"])
                    notes=_literary_craft_grams("\n".join(reading["annotations"])+"\n"+reading["reflection"])
                    independent=_independent(target,notes)
                    if len(independent)<2:
                        continue
                    evidence.append({
                       "cluster":row["method_cluster"],
                       "independent_note_overlap":len(independent),
                       "shortlisted":row["id"] in shortlist[row["source_role"]],
                       "original_anchors":len({
                           t for t in target if len(t)==4
                           and t in _literary_craft_grams(reading["original"])
                       }),
                    })
                evidence.sort(key=lambda x:(-x["independent_note_overlap"],-x["original_anchors"],x["cluster"]))
                chosen=db.conn.execute(
                    "SELECT method_cluster FROM xuehai_entries WHERE id=?",
                    (actual["entry_id"],)).fetchone()["method_cluster"] if actual else None
                reference=next((e for e in evidence if e["cluster"]==case["expected_one_possible_reference"]),None)
                cases.append({
                    "case":case["id"],
                    "scope_len":len(scope),
                    "selected":chosen,
                    "source_reference":case["expected_one_possible_reference"],
                    "source_evidence":reference,
                    "best_source_candidate_details":evidence[:6],
                    "lexical_evidence_not_literary_truth":True
                })
            return {
                "status":"WF0CO_READONLY_REAL_R2_CANDIDATE_COVERAGE",
                "entries":original_proof["entries"],"readings":original_proof["full_readings"],
                "reading_source_counts":role_counts,
                "candidate_shortlist_counts":{k:len(v) for k,v in shortlist.items()},
                "cases":cases,"model_calls":0,"r2_writes":0,"canon_writes":0
            }
        finally:
            runtime.exit()
            db.close()

if __name__=="__main__":
    print(json.dumps(run(),ensure_ascii=False,sort_keys=True))
