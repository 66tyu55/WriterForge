"""Real published-source readiness audit for the gradual literary ladder.

It does NOT call an LLM, pretend to review literary style, or auto-certify
any classification. It may be used in CI on actual 100-/120-/70-chapter books
to expose the exact missing prerequisite before composition is allowed.
"""
from __future__ import annotations

from pathlib import Path
import json
import sys

from writerforge import WriterForgeDB,RuntimeEngine
from writerforge.literary_ladder import LiteraryLadder


def main():
    if len(sys.argv)!=5:
        raise SystemExit(
            "usage: python scripts/literary_ladder_readiness.py DB WORK_ID GOAL OUTPUT_JSON"
        )
    path,work_id,goal,output=sys.argv[1:]
    db=WriterForgeDB(Path(path))
    try:
        snap=db.conn.execute(
            "SELECT id FROM snapshots WHERE status='published' ORDER BY id DESC LIMIT 1"
        ).fetchone()
        if not snap:
            raise SystemExit("FAIL: no published original source")
        rt=RuntimeEngine()
        rt.enter_write(int(snap["id"]))
        exercises=LiteraryLadder(db,rt,"readiness-audit-only").tasks(
            work_id=work_id,goal=goal,
        )
        status={
            "work_id":work_id,
            "source_snapshot_id":snap["id"],
            "source_exists":True,
            "stage_readiness":[x.trace() for x in exercises],
            "ready_stages":sum(x.readiness=="ready" for x in exercises),
            "blocked_stages":sum(x.readiness!="ready" for x in exercises),
            "human_verified_category_gate_in_effect":True,
            "model_called":False,
            "external_critic_called":False,
            "model_parameters_trained":False,
            "cross_work_literary_evaluation_performed":False,
            "literary_quality_certified":False,
            "50_work_review_threshold_unchanged":50,
        }
        dest=Path(output)
        dest.parent.mkdir(parents=True,exist_ok=True)
        dest.write_text(json.dumps(status,ensure_ascii=False,indent=2),
                        encoding="utf-8")
        print(json.dumps({
            "work_id":work_id,
            "ready_stages":status["ready_stages"],
            "blocked_stages":status["blocked_stages"],
            "missing_semantic_prerequisites":[x["reason"] for x in status["stage_readiness"]
                                               if x["readiness"]!="ready"],
            "literary_quality_certified":False,
        },ensure_ascii=False))
    finally:
        db.close()


if __name__=="__main__":
    main()
