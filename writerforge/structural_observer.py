"""V54 observe verified local index hits into the deterministic fact ledger.

No host interpretation, R2 networking, original prose, autonomous literary
causal claim, or copy/paste route to WRITE. Observations only say a normalized
token occurred in a SHA-pinned indexed source unit. Compare across times,
chapters and counterexamples elsewhere.
"""
from __future__ import annotations
from hashlib import sha256
from pathlib import Path
import json

from .corpus_foundation import search_disk
from .fact_journal import FactJournal


def _hex(value):
    return sha256(value.encode("utf-8")).hexdigest()


def observe_corpus(*, cache: str | Path, library: str, snapshot: str,
                   terms: tuple[str, ...], journal_path: str | Path,
                   limit: int = 6):
    comparison = search_disk(cache, library=library,snapshot=snapshot,
                             terms=terms,limit=limit)
    journal = FactJournal(journal_path)
    created = []
    try:
        normalized_terms = tuple(comparison["query_terms"])
        term_set_id = _hex(json.dumps(normalized_terms,ensure_ascii=False))[:20]
        source_group = "index_" + term_set_id
        # Keep separate namespace from fictional character knowledge state.
        # One bounded source occurrence == one observed structural fact.
        for word in normalized_terms:
            matches = [
                r for r in comparison["matches"]
                if word in r["terms_matched"]
            ]
            matches.sort(key=lambda r:(r["work_id"],*r["location"]))
            for tick, item in enumerate(matches,1):
                detail = json.dumps(
                    [comparison["snapshot_sha256"],word,item["work_id"],
                     item["location"],item["source_unit_sha256"]],
                    ensure_ascii=False,separators=(",",":"))
                event_id = "src_" + _hex(detail)[:28]
                scene = source_group
                fact = "lex_" + _hex(word)[:20]
                doc = {
                    "event_id":event_id,"scene_id":scene,
                    "actor_id":"index_witness","fact_id":fact,
                    "tick":tick,"state":"KNOWN",
                    "role":"OBSERVE",
                    "evidence_sha256":item["source_unit_sha256"],
                }
                out = journal.append(doc)
                created.append(out["event_id"])
                # Corpus index order is NOT story-time chronology.
                # Do not fabricate BEFORE/causal links from lexical order.
        return {
            "format":"WF.corpus-structural-observation.v1",
            "source_snapshot_sha256":snapshot,
            "source_library":library,
            "observed_events":len(created),
            "temporal_order_relations":0,
            "index_order_is_not_story_time":True,
            "journal_event_ids":created,
            "journal_source_event_sha256":_hex("".join(sorted(created))),
            "network_calls":0,"model_calls":0,
            "actual_original_sentences_exposed":False,
            "literal_occurrence_only":True,
            "literary_causality_verified":False,
            "candidate_eligible_for_creative_execution":False,
        }
    finally:
        journal.close()
