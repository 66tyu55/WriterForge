"""Deterministic pseudo-random chapter sample for one pre-registered V28 test.

Sample is chosen from chapter numbers BEFORE reading literary scores. We pin
the entire source SHA and seed and do not replace an inconvenient chapter
after seeing results. No raw copyrighted source or model API is used here.
"""
from __future__ import annotations
from hashlib import sha256

SOURCE_SHA="86a2fd859b424efe0500b4b36713ea8b05d551140650904ffc2ae02eb244ed28"
SEED="writerforge-v28-20261017-three-random-chapters:"+SOURCE_SHA
RANGE=range(3,25)
SAMPLE_SIZE=3

def chosen_chapters()->tuple[int,...]:
    ranked=sorted(RANGE,key=lambda n:sha256(f"{SEED}:{n}".encode()).digest())
    sample=tuple(sorted(ranked[:SAMPLE_SIZE]))
    if sample!=(3,15,17):
        raise ValueError("pinned deterministic selection changed")
    return sample

def selection_hash()->str:
    from json import dumps
    doc={"source_sha256":SOURCE_SHA,"seed":SEED,"chapters":chosen_chapters(),
         "selection":"three lowest SHA256(seed:chapter) from 3..24"}
    return sha256(dumps(doc,sort_keys=True,separators=(",",":")).encode()).hexdigest()
