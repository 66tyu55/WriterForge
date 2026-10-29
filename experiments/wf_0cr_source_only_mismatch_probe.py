"""0.CR: true frozen R2 145/97 evidence for overbroad reading selection.

No author model/paid calls, no new rules or memory, no DB/R2/Canon writes.
Only public source ids and small match fragments appear in the CI output.
"""
from __future__ import annotations
from collections import Counter
from pathlib import Path
from tempfile import TemporaryDirectory
from shutil import copyfile
import json,math,re

from writerforge import WriterForgeDB,RuntimeEngine,XuehaiStore
from writerforge.xuehai import (
    Query,_author_craft_scope,_literary_craft_grams,_independent_literary_hits,
)
from experiments.wf_0cf_r2_durable_literary_snapshot import _vault
from experiments.wf_source_pinned_literary_incremental import inspect,pack_from

ROOT=Path(__file__).resolve().parents[1]
CASES=ROOT/"experiments/wf_0cr_frozen_author_reading_cases_20261029.json"
LIBRARY="wf-0cq-xuehai-literary-145-20261029-v1"
PACK=ROOT/"experiments/wf_0cq_five_fusheng_shishuo_close_readings_20261029.json"

def run():
    frozen=json.loads(CASES.read_text("utf8"))
    if (frozen.get("format")!="wf.0cr.preserved-source-first-author-task-freeze.v1"
        or len(frozen["cases"])!=9
        or frozen["model_calls"]!=0):
        raise ValueError("WF0CR_FROZEN_CASES_CHANGED")
    previous=pack_from(PACK)
    with TemporaryDirectory(prefix="wf0cr-public-r2-only-") as tmp:
        path=Path(tmp)
        restored=_vault(cold_only=True).restore(
            library=LIBRARY,snapshot=frozen["old_literary_snapshot"],
            destination=path/"remote")
        original=inspect(Path(restored["db"]),previous)
        if (original["entries"]!=145 or original["full_readings"]!=97
            or original["all_content_sha256"]!=frozen["old_content_sha256"]):
            raise ValueError("WF0CR_SOURCE_R2_SNAPSHOT_CHANGED")
        copyfile(restored["db"],path/"query.sqlite3")
        db=WriterForgeDB(path/"query.sqlite3")
        runtime=RuntimeEngine()
        store=XuehaiStore(db,runtime)
        runtime.enter_write(store.latest_published())
        report=[]
        try:
            for case in frozen["cases"]:
                scope=_author_craft_scope(case["problem"])
                target=_literary_craft_grams(scope)
                selected=store.select_literary_reading_for_author(
                    goal=case["goal"],writing_problem=case["problem"],max_chars=4900)
                if selected:
                    row=db.conn.execute(
                        "SELECT method_cluster FROM xuehai_entries WHERE id=?",
                        (selected["entry_id"],)).fetchone()
                    selected_id=row["method_cluster"]
                else:
                    selected_id=None
                rows=[]
                # No retriever modifications: independently inspect all 97
                # published three-part sources that can be referenced.
                for role in ("classical_original_annotation_reflection",
                             "original_annotation_reflection"):
                    for raw in store._candidate_rows(Query(
                        source_role=role,limit=32,max_per_work=8,max_per_cluster=1)):
                        if not raw["text"] or len(raw["text"])>4900+40:
                            continue
                        try:
                            reading=store.read_literary_reading(int(raw["id"]))
                        except ValueError:
                            continue
                        notes=_literary_craft_grams(
                            "\n".join(reading["annotations"])+"\n"+reading["reflection"])
                        independent=_independent_literary_hits(target,notes)
                        annotation_hits=_independent_literary_hits(
                            target,_literary_craft_grams("\n".join(reading["annotations"])))
                        reflection_hits=_independent_literary_hits(
                            target,_literary_craft_grams(reading["reflection"]))
                        if len(independent)<2:
                            continue
                        clauses=[_literary_craft_grams(c)
                                 for c in re.split(r"[，,；;]",scope)
                                 if len(c.strip())>=5]
                        supported=sum(bool(c & notes) for c in clauses)
                        source=_literary_craft_grams(reading["original"])
                        anchors={x for x in target if len(x)==4 and x in source}
                        rows.append({
                            "cluster":raw["method_cluster"],
                            "note_fragments":len(independent),
                            "supported_clauses":supported,
                            "source_anchors":len(anchors),
                            "first_fragments":independent[:12],
                            "annotation_hits":annotation_hits[:12],
                            "reflection_hits":reflection_hits[:12],
                            "role":role
                        })
                rows.sort(key=lambda v:(-v["source_anchors"],-v["note_fragments"],-v["supported_clauses"],v["cluster"]))
                expected={k for k in case.get("reference_candidates",[])}
                expected_diag=[v for v in rows if v["cluster"] in expected]
                chosen_diag=next((v for v in rows if v["cluster"]==selected_id),None)
                report.append({
                    "case":case["id"],"kind":case["kind"],
                    "choice":selected_id,
                    "scope_chars":len(scope),
                    "source_candidates":case.get("reference_candidates",[]),
                    "chosen_detail":chosen_diag,
                    "expected_source_details":expected_diag,
                    "top_note_or_source_matches":rows[:6],
                    "candidate_evidence_is_lexical_not_literary_truth":True,
                })
        finally:
            runtime.exit()
            db.close()
    return {"status":"WF0CR_PRECHANGE_FROZEN_REAL_145_SOURCE_READONLY",
            "entries":original["entries"],"readings":original["full_readings"],
            "cases":report,"model_calls":0,"r2_writes":0,"canon_writes":0}

if __name__=="__main__":
    print(json.dumps(run(),ensure_ascii=False,sort_keys=True))
