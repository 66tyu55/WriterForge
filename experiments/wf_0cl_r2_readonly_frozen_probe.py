"""0.CL frozen-before-first-run real-source read-only analysis, no model/Canon/R2 writes.

A lexical candidate is a source-grounded *possibility*, not a literary verdict.
Report candidate coverage and why 0.CK misses/misroutes; never disclose private R2
content, change the 0.CK record or rewrite the pinned R2 originals.
"""
from __future__ import annotations

from collections import Counter
from pathlib import Path
from tempfile import TemporaryDirectory
from shutil import copyfile
import json
import re

from writerforge import WriterForgeDB, RuntimeEngine, XuehaiStore
from writerforge.xuehai import Query, _author_craft_scope, _literary_craft_grams
from experiments.wf_0cf_r2_durable_literary_snapshot import (
    LIBRARY, _vault, inspect_literary_db,
)
from experiments.wf_0cg_existing_r2_to_real_writer_offline import (
    PINNED_SNAPSHOT, PINNED_CONTENT,
)
from experiments.wf_0ck_real_classics_unseen_probe import UNSEEN

ROOT=Path(__file__).resolve().parents[1]
FROZEN=ROOT/"experiments/wf_0cl_frozen_unseen_transfer_cases_20261029.json"
ROLES=("classical_original_annotation_reflection","original_annotation_reflection")
INSPECT_CLUSTERS=(
    "classic-fantasy-jh-3","original-read-bq-03",
    "original-read-bq-04","original-read-bq-13",
)

def _cluster(db, entry_id):
    row=db.conn.execute("SELECT method_cluster FROM xuehai_entries WHERE id=?",
                        (entry_id,)).fetchone()
    return row["method_cluster"] if row else None

def _inspect_candidates(store, db, writing_problem):
    scope=_author_craft_scope(writing_problem)
    candidates={}
    for role in ROLES:
        for item in store.query(Query(
                source_role=role,limit=32,max_per_work=8,max_per_cluster=1)):
            candidates[_cluster(db,int(item["entry_id"]))]=item
    target=_literary_craft_grams(scope)
    clauses=[_literary_craft_grams(s) for s in re.split(r"[，,；;]",scope)
             if len(s.strip())>=5]
    out=[]
    for name in INSPECT_CLUSTERS:
        item=candidates.get(name)
        if not item:
            out.append({"source":name,"in_retrieval_shortlist":False})
            continue
        reading=store.read_literary_reading(int(item["entry_id"]))
        notes="\n".join(reading["annotations"])+"\n"+reading["reflection"]
        grams=_literary_craft_grams(notes)
        hits=target&grams
        independent=[]
        for word in sorted(hits,key=lambda t:(-len(t),t)):
            if not any(word in old for old in independent):
                independent.append(word)
        out.append({
            "source":name,"in_retrieval_shortlist":True,
            "note_overlap_fragments":len(independent),
            "matched_note_phrases":independent[:12],
            "matching_craft_clauses":sum(bool(part&grams) for part in clauses),
            "original_anchor_count":sum(
                1 for t in target if len(t)==4 and t in _literary_craft_grams(reading["original"])),
            "complete_reading_chars":len(
                "【出处】"+reading["source"]+"\n【原文】\n"+reading["original"]
                +"\n【批注】\n"+"\n".join(reading["annotations"])
                +"\n【心得】\n"+reading["reflection"]),
        })
    return {"explicit_craft_scope":scope[:250],
            "scope_length":len(scope),"scope_fragments":len(target),
            "candidate_diagnostics":out}

def run():
    frozen=json.loads(FROZEN.read_text("utf8"))
    assert frozen["format"]=="wf.0cl.pre-registered.genuine-readings.v1"
    assert len(frozen["cases"])==14
    with TemporaryDirectory(prefix="wf0cl-real-r2-readonly-") as tmp:
        root=Path(tmp)
        restored=_vault(cold_only=True).restore(
            library=LIBRARY,snapshot=PINNED_SNAPSHOT,destination=root/"r2")
        proof=inspect_literary_db(Path(restored["db"]))
        assert proof["content_sha256"]==PINNED_CONTENT
        assert proof["contents"]==126 and proof["complete_three_part_readings"]==78
        dbfile=root/"scratch.sqlite3"
        copyfile(restored["db"],dbfile)
        db=WriterForgeDB(dbfile)
        rt=RuntimeEngine()
        rt.enter_write(XuehaiStore(db,rt).latest_published())
        try:
            store=XuehaiStore(db,rt)
            records=[]
            for c in frozen["cases"]:
                selected=store.select_literary_reading_for_author(
                    goal=c["goal"],writing_problem=c["writing_problem"],max_chars=4900)
                cluster=_cluster(db,selected["entry_id"]) if selected else None
                records.append({
                    "case":c["id"],"hypothesis_class":c["class"],
                    "plausible_nonexclusive_sources":c["possible_sources"],
                    "selected":cluster or None,
                    "candidate_kind":"ABSTAIN" if selected is None else
                        "POSSIBLE_SOURCE_UNVERIFIED",
                    "complete_unmodified_reading":not selected or
                        all(x in selected["complete_reading"]
                            for x in ("【原文】","【批注】","【心得】")),
                    "match_basis":selected.get("matching_basis") if selected else None,
                    "literary_truth_unverified":True,
                })
            original={}
            for case in UNSEEN:
                if case["id"] not in ("coat-swap-reveals-social-mask",
                                       "quiet-everyday-fragment"):
                    continue
                selected=store.select_literary_reading_for_author(
                    goal=case["goal"],writing_problem=case["problem"],max_chars=4900)
                original[case["id"]]={
                    "selected":_cluster(db,selected["entry_id"]) if selected else None,
                    **_inspect_candidates(store,db,case["problem"]),
                }
            assert inspect_literary_db(Path(restored["db"]))==proof
            return {
                "status":"WF0CL_FROZEN_REAL_READONLY_BASELINE",
                "r2_snapshot":PINNED_SNAPSHOT,
                "source_contents":proof["contents"],
                "source_complete_readings":proof["complete_three_part_readings"],
                "cases_frozen_before_first_run":len(records),
                "new_cases":records,"old_0ck_root_diagnostics":original,
                "literary_gain_proven":False,
                "model_calls":0,"paid_api_calls":0,"r2_writes":0,"canon_writes":0,
            }
        finally:
            rt.exit()
            db.close()

if __name__=="__main__":
    print(json.dumps(run(),ensure_ascii=False,sort_keys=True))
