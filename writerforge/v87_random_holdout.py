"""V87: reproducible, anonymous random holdout draw from user's private R2.

The assistant freezes this rule in GitHub BEFORE reading the private catalog.
Only private R2/WF Railway readers see object keys and novel content. Public
receipts contain only genre-folder hints, SHA256 digests and unit counts.
No model calls, no R2 writes and no alternative source handpicking.

Seed = SHA256(user instruction UTC timestamp + preceding frozen V86 HEAD).
This is reproducible pseudorandom selection, NOT an external randomness beacon.
"""
from __future__ import annotations

from hashlib import sha256
import json

from .private_r2_sql_smoke import candidate_sources

FORMAT="wf.v87.random-heldout-plan.v1"
SOURCE_GENRES=("仙侠","历史","科幻")
TARGET_BOOKS=2
MAX_TRIES_PER_GENRE=4
MAX_SOURCE_BYTES=8*1024*1024
MIN_SOURCE_BYTES=10*1024
ANCHOR="writerforge-v87-random-unseen-corpus-v1|2026-10-20T05:18:01Z|afb366a09ada126040e6696488fabfc685a79c66"
KNOWN_TRAINING_KEY_SHA256="370400053cded15ca89e3232e7be84b28aa20ca70542150138bef6201dc7cb22"
EXCLUDED_SOURCE_SHA256=frozenset((
    "0f00a16f6a0c121404a28257f3aa728468c9dae78d464ff1341746a45c41ddbd",
    "e3fb51aa6d9ed50f79c7c9d60361a366c4a168b8593d1cdaaec65784e46f8cd8",
))

class WF87HoldoutError(ValueError):
    pass

def need(ok,code):
    if not ok:
        raise WF87HoldoutError(code)

def sha(raw):
    return sha256(raw).hexdigest()

def canonical(doc):
    return json.dumps(doc,sort_keys=True,ensure_ascii=False,
                      separators=(",",":"),allow_nan=False).encode("utf8")

def seed_sha():
    return sha(ANCHOR.encode("ascii"))

def stable_rank(*parts):
    return sha(("v87-seeded-rank|"+seed_sha()+"|"+
                "|".join(str(p) for p in parts)).encode("utf8"))

def key_hash(key):
    need(isinstance(key,str) and 1<=len(key)<1600,
         "WF87_OBJECT_KEY_INVALID")
    return sha(key.encode("utf8"))

def metadata_only_plan(catalog):
    rows=candidate_sources(catalog)
    candidates=[]
    for row in rows:
        if (row["category"] not in SOURCE_GENRES or
            not MIN_SOURCE_BYTES<=row["size_bytes"]<=MAX_SOURCE_BYTES):
            continue
        hashed=key_hash(row["object_key"])
        if hashed==KNOWN_TRAINING_KEY_SHA256:
            continue
        candidates.append({
            "genre_hint":row["category"],
            "key_sha256":hashed,"size_bytes":row["size_bytes"],
            "etag_sha256":sha(str(row.get("etag")).encode("utf8")),
        })
    need(len({x["key_sha256"] for x in candidates})==len(candidates),
         "WF87_DUPLICATE_ELIGIBLE_SOURCE")
    candidates.sort(key=lambda x:(x["genre_hint"],x["key_sha256"]))
    catalog_sha=sha(canonical(candidates))
    genres=sorted(SOURCE_GENRES,key=lambda g:(stable_rank("genre",g),g))
    selected=[g for g in genres if any(
        c["genre_hint"]==g for c in candidates)][:TARGET_BOOKS]
    need(len(selected)==TARGET_BOOKS,"WF87_NOT_ENOUGH_DISTINCT_SOURCE_GENRES")
    draws=[]
    for g in selected:
        rows_g=[x for x in candidates if x["genre_hint"]==g]
        rows_g.sort(key=lambda x:(stable_rank("object",g,x["key_sha256"]),
                                   x["key_sha256"]))
        draws.append({
            "genre_hint":g,
            "eligible_count_in_genre":len(rows_g),
            "predeclared_fallback_key_sha256":[
                x["key_sha256"] for x in rows_g[:MAX_TRIES_PER_GENRE]],
            "predeclared_fallback_sizes_bytes":[
                x["size_bytes"] for x in rows_g[:MAX_TRIES_PER_GENRE]],
        })
    receipt={
        "format":FORMAT,
        "seed_derivation":"SHA256(user_message_utc_time | pinned_prior_V86_HEAD)",
        "randomness_method":"deterministic_seeded_sha256_rank",
        "draw_seed_sha256":seed_sha(),
        "frozen_catalog_sha256":catalog_sha,
        "eligible_source_count":len(candidates),
        "eligible_counts_by_genre":{
            g:sum(x["genre_hint"]==g for x in candidates)
            for g in SOURCE_GENRES},
        "genres_seeded_order":genres,
        "sample_size":TARGET_BOOKS,
        "draws":draws,
        "max_download_attempts_per_selected_genre":MAX_TRIES_PER_GENRE,
        "max_candidate_bytes":MAX_SOURCE_BYTES,
        "previously_trained_and_old_holdout_source_shas_excluded_after_read":True,
        "source_text_or_keys_in_output":False,
        "prose_ever_read_during_metadata_plan":False,
        "new_paid_model_calls":0,
        "r2_writes":0,
    }
    receipt["plan_sha256"]=sha(canonical(receipt))
    return receipt

def recover_key_by_sha(catalog, key_sha):
    need(isinstance(key_sha,str) and len(key_sha)==64,
         "WF87_PINNED_OBJECT_HASH_INVALID")
    rows=candidate_sources(catalog)
    found=[r for r in rows if key_hash(r["object_key"])==key_sha]
    need(len(found)==1,"WF87_PINNED_SOURCE_MISSING_OR_AMBIGUOUS")
    return found[0]

def chapter_order(key_sha, chapters):
    # All chapter positions are determined before reading the chosen
    # chapter's content. No searching for a high-scoring/easy excerpt.
    positions=range(2,min(len(chapters),20)+1)
    return sorted(positions,key=lambda n:(
        stable_rank("chapter",key_sha,n),n))
