"""0.CJ independent source-first literary holdout; diagnostic, NOT tune-to-green.

Read-only existing pinned R2 literary library (126 pieces / 78 deep readings),
using the REAL existing Xuehai selector. Pre-registered test cases were
committed before this code. No paid or local LLM, no separate databases,
no R2/Canon write. Report partial and abstention distinctly from exact hits.
"""
from __future__ import annotations
from pathlib import Path
from tempfile import TemporaryDirectory
from shutil import copyfile
import json

from experiments.wf_0cf_r2_durable_literary_snapshot import (
    LIBRARY, _vault, inspect_literary_db,
)
from experiments.wf_0cg_existing_r2_to_real_writer_offline import (
    PINNED_SNAPSHOT, PINNED_CONTENT,
)
from writerforge import WriterForgeDB, RuntimeEngine, XuehaiStore
from writerforge.xuehai import Query, _author_craft_scope, _literary_craft_grams

ROOT=Path(__file__).resolve().parents[1]
FROZEN=ROOT/"experiments/wf_0cj_independent_real_classic_holdouts_20261029.json"
ROLES=("classical_original_annotation_reflection","original_annotation_reflection")


def source_cluster(db,chosen):
    if chosen is None:
        return None
    row=db.conn.execute(
        "SELECT method_cluster FROM xuehai_entries WHERE id=?",
        (chosen["entry_id"],)).fetchone()
    return row["method_cluster"] if row else None


def inspect_holdouts():
    frozen=json.loads(FROZEN.read_text("utf8"))
    assert frozen["format"]=="wf.0cj.pre-registered.classic-holdouts.v1"
    assert len(frozen["cases"])==9
    with TemporaryDirectory(prefix="wf0cj-r2-real-literary-") as scratch:
        base=Path(scratch)
        restored=_vault(cold_only=True).restore(
            library=LIBRARY,snapshot=PINNED_SNAPSHOT,destination=base/"source")
        proof=inspect_literary_db(Path(restored["db"]))
        assert proof["content_sha256"]==PINNED_CONTENT
        work=base/"no-canon.sqlite3"
        copyfile(restored["db"],work)
        db=WriterForgeDB(work)
        rt=RuntimeEngine()
        sid=XuehaiStore(db,rt).latest_published()
        rt.enter_write(sid)
        try:
            store=XuehaiStore(db,rt)
            available={}
            for role in ROLES:
                found=store.query(Query(
                    source_role=role,limit=32,
                    max_per_work=8,max_per_cluster=1))
                available[role]={source_cluster(db,item) for item in found}
            report=[]
            for task in frozen["cases"]:
                picked=store.select_literary_reading_for_author(
                    goal=task["goal"],max_chars=4900,
                    writing_problem=task["writing_problem"])
                selected=source_cluster(db,picked)
                expected=task["possible_sources"]
                if task["class"]=="should_abstain":
                    disposition=("ABSTAIN" if picked is None
                                 else "UNSUPPORTED_OFFER")
                else:
                    disposition=("SUGGESTED_SOURCE" if selected in expected
                                 else "ABSTAIN" if selected is None
                                 else "OTHER_POSSIBLY_RELATED")
                # Audit just the broad bounded SQL shortlist, not source
                # quotes or passwords. Missing candidates cannot be chosen.
                source_locations=[
                    {"candidate":name,
                     "available_in_bounded_shortlist":any(
                         name in available[role] for role in ROLES)}
                    for name in expected
                ]
                report.append({
                    "case":task["id"],
                    "pre_registered_class":task["class"],
                    "pre_registered_possible_sources":expected,
                    "wf_selected_source":selected,
                    "observed_disposition":disposition,
                    "candidate_shortlist":source_locations,
                    "received_complete_three_part_source":(
                        picked is not None and picked["annotation_count"]==3
                        and all(mark in picked["complete_reading"] for mark in
                                ("【原文】","【批注】","【心得】"))),
                    "reported_evidence_basis":(
                        picked.get("matching_basis") if picked else None),
                    "lexical_grams_matched":(
                        picked.get("matched_craft_fragments",0) if picked else 0),
                    "one_best_not_a_literary_truth":True,
                })
            # Re-read the untouched ORIGINAL restore, not the local mutable
            # copy. No new method/value evaluation is ever written.
            unchanged=inspect_literary_db(Path(restored["db"]))
            assert unchanged==proof
            return {
                "status":"WF0CJ_NEW_HOLDOUT_REAL_R2_LITERATURE_DIAGNOSTIC",
                "snapshot_sha256":PINNED_SNAPSHOT,
                "source_integrity_verified":True,
                "total_literature_entries":proof["contents"],
                "three_part_readings":proof["complete_three_part_readings"],
                "pre_registered_cases":len(report),
                "source_cases":report,
                "r2_writes":0,"canon_writes":0,
                "model_requests":0,"literary_gain_proven":False,
                "criteria_not_tuned_in_this_run":True,
            }
        finally:
            rt.exit()
            db.close()


if __name__=="__main__":
    print(json.dumps(inspect_holdouts(),ensure_ascii=False,sort_keys=True))
