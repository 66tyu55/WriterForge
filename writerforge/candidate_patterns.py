"""V53 mechanism candidate ledger: model-free verification and comparison.

Candidates are derived ONLY from corpus index locations and recurrence counts;
they never contain original sentences or writer instructions. This ledger
records uncertainty and negative comparisons but cannot promote a skill.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path


class PatternLedgerError(ValueError):
    pass


def _json(doc):
    return json.dumps(doc,ensure_ascii=False,sort_keys=True,
                      separators=(",",":"),allow_nan=False)


class PatternLedger:
    def __init__(self, path):
        # This is a derived metadata ledger, not the R2 source database.
        self.db=sqlite3.connect(str(Path(path)))
        self.db.execute("PRAGMA cache_size=-1024")
        self.db.execute("""CREATE TABLE IF NOT EXISTS comparison_candidates(
            id TEXT PRIMARY KEY,
            snapshot_sha256 TEXT NOT NULL,
            pattern_sha256 TEXT NOT NULL,
            evidence_json TEXT NOT NULL,
            status TEXT NOT NULL,
            contrast_json TEXT NOT NULL)""")
        self.db.commit()

    def close(self):
        self.db.close()

    def observe(self, comparison):
        if not isinstance(comparison,dict) or comparison.get("format")!="WF.corpus-verify-comparison.v1":
            raise PatternLedgerError("CANDIDATE_ONLY_CORPUS_COMPARISON")
        matches=comparison["matches"]
        if not isinstance(matches,list) or len(matches)>8:
            raise PatternLedgerError("CANDIDATE_MATCHES_UNBOUNDED")
        seen={(x["work_id"],*x["location"]) for x in matches}
        if len(seen)!=len(matches):
            raise PatternLedgerError("CANDIDATE_REPEATED_LOCATION")
        refs=[{"work_id":x["work_id"],"location":x["location"],
               "source_unit_sha256":x["source_unit_sha256"]}
              for x in matches]
        refs.sort(key=lambda x:(x["work_id"],x["location"]))
        work_chapters={(x["work_id"],x["location"][0]) for x in refs}
        has_contrast=len(work_chapters)>=2
        term_bytes=_json(comparison["query_terms"]).encode()
        pattern_sha=hashlib.sha256(term_bytes).hexdigest()
        evidence_sha=hashlib.sha256(_json(refs).encode()).hexdigest()
        record_sha=hashlib.sha256(
            (comparison["snapshot_sha256"]+pattern_sha+evidence_sha).encode()
        ).hexdigest()
        verdict="MULTI_CHAPTER_LEXICAL_RECURRENCE" if has_contrast else (
            "SAME_CHAPTER_REPETITION_ONLY" if len(refs)>=2
            else "INSUFFICIENT_COMPARISON")
        uncertainty={
            "comparison_kind":verdict,
            "evidence_count":len(refs),
            "distinct_work_chapters":len(work_chapters),
            "semantic_causality_verified":False,
            "technique_effectiveness_verified":False,
            "eligible_to_guide_writing":False,
        }
        prior=self.db.execute(
            "SELECT pattern_sha256,evidence_json FROM comparison_candidates WHERE id=?",
            (record_sha,)).fetchone()
        if prior:
            if prior!=(pattern_sha,_json(refs)):
                raise PatternLedgerError("CANDIDATE_IMMUTABILITY_CONFLICT")
        else:
            with self.db:
                self.db.execute(
                    "INSERT INTO comparison_candidates VALUES(?,?,?,?,?,?)",
                    (record_sha,comparison["snapshot_sha256"],pattern_sha,
                     _json(refs),"STRUCTURAL_OBSERVATION_ONLY",_json(uncertainty)))
        return {"candidate_sha256":record_sha,"status":"STRUCTURAL_OBSERVATION_ONLY",
                **uncertainty,"source_evidence_location_hash":evidence_sha,
                "no_original_prose_stored":True,"no_model_calls":True}
