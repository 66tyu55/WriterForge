"""V87.1: seeded raw contiguous passage fallback after chapter-parser red run.

This is NOT a whole chapter or a proof of authorial provenance. Source work,
codec, SHA and candidate order must already have passed the frozen V87 gate.
The offset uses only seeded SHA and file length, not the plot or readability.
No model, no R2 mutation, no source text in receipts.
"""
from __future__ import annotations

from hashlib import sha256
from .v87_random_holdout import stable_rank,sha
from .wf_b01_prefix_prepare import _split_into_ordered_units

WINDOW=2300
BREAKS=frozenset("。！？；\n")
MIN_SOURCE_CHARACTERS=6000

class WF87PassageError(ValueError):
    pass

def need(ok,reason):
    if not ok:
        raise WF87PassageError(reason)

def choose_passage(decoded,*,key_sha256,source_sha256):
    need(isinstance(decoded,str) and
         len(decoded)>=MIN_SOURCE_CHARACTERS and
         isinstance(key_sha256,str) and len(key_sha256)==64 and
         isinstance(source_sha256,str) and len(source_sha256)==64,
         "WF87_PASSAGE_SOURCE_NOT_VERIFIED")
    length=len(decoded)
    begin=max(1,length//10)
    end=min(length-WINDOW-350,(length*8)//10)
    need(end>begin,"WF87_PASSAGE_OFFSET_RANGE_EMPTY")
    seed_rank=stable_rank("raw-passage",key_sha256,source_sha256)
    nominal=begin+int(seed_rank[:16],16)%(end-begin)
    # Apply only one deterministic local punctuation alignment, not a
    # search for the best literary tension/plot resolution.
    options=[i+1 for i in range(nominal,min(nominal+220,end))
             if decoded[i] in BREAKS]
    start=options[0] if options else nominal
    fragment=decoded[start:start+WINDOW]
    need(len(fragment)==WINDOW,
         "WF87_PASSAGE_PRIVATE_SOURCE_TRUNCATED")
    try:
        windows=_split_into_ordered_units(fragment)
    except ValueError as exc:
        raise WF87PassageError(
            "WF87_PASSAGE_UNSAFE_DETERMINISTIC_SPLIT") from None
    need(len(windows)>=4 and "".join(windows)==fragment,
         "WF87_PASSAGE_NOT_FOUR_CONTIGUOUS_UNITS")
    return {
        "format":"wf.v87.raw-contiguous-literary-holdout.v1",
        "source_original_sha256":source_sha256,
        "source_key_sha256":key_sha256,
        "source_total_characters":length,
        "fragment_start_char":start,
        "fragment_end_char":start+WINDOW,
        "fragment_sha256":sha(fragment.encode("utf8")),
        "fragment_unit_count":len(windows),
        "first_read_visible_unit_indices":[1,2],
        "first_read_visible_unit_sha256":[
            sha(x.encode("utf8")) for x in windows[:2]],
        "first_read_visible_unit_characters":[len(x) for x in windows[:2]],
        "sealed_unread_unit_index":3,
        "sealed_unread_unit_sha256":sha(windows[2].encode("utf8")),
        "sealed_unread_unit_characters":len(windows[2]),
        "precise_chapter_identity_verified":False,
        "full_chapter_read_claim":False,
        "selection_independent_of_model_answers":True,
        "passage_contents_in_public_receipt":False,
        "future_unit_text_in_wf_prompt":False,
        "judge_has_not_evaluated_narrative_semantics":True,
    }
