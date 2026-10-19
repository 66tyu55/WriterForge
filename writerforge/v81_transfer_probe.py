"""V81 held-out cross-work transfer probe, precommitted and non-grading.

A fair comparison uses the SAME exact unopened passage from a deterministic,
frozen B00 historical TXT source, presented under two conditions to the
same stateless DeepSeek Flash model:
  A: no prior WF literary learning strategy (baseline)
  B: chapter10's actual immutable learned next_strategy from private R2

Arm order comes from a SHA256 precommit, not from response quality. Questions
and hypotheses are produced by the model without a ChatGPT/examiner-provided
answer or keyword list. Audit only schema/source-unit grounding and the
difference, not literary quality. A response difference cannot prove
transfer or learning: it may be mere prompt conditioning.

All original text is private to Railway/DeepSeek. Only hashes, counts and
bounded model-generated study questions may be stored in private R2 CAS.
"""
from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import json
import re

from .wf_self_learning_admission import _scan_document
from .wf_b01_prefix_prepare import _split_into_ordered_units

FORMAT="wf.exam.cross-work-strategy.v81"
SHA=re.compile(r"^[a-f0-9]{64}$")
FIELDS=frozenset(("question","hypothesis","uncertainty","evidence_units","focus"))
MAX_RESPONSE_CHARS=240


class WFTransferExamError(ValueError):
    pass


def require(ok,code):
    if not ok:
        raise WFTransferExamError(code)


def digest_bytes(raw:bytes):
    return sha256(raw).hexdigest()


def canonical(doc):
    return json.dumps(doc,ensure_ascii=False,sort_keys=True,
                      separators=(",",":"),allow_nan=False).encode("utf-8")


def prepare_heldout(path,*,original_sha,source_key_sha,
                    encoding,trained_experience_sha):
    """Choose first 2 contiguous source units, never a cherry-picked quote."""
    require(all(isinstance(h,str) and SHA.fullmatch(h) for h in
                (original_sha,source_key_sha,trained_experience_sha)),
            "WF_V81_TRANSFER_BAD_SOURCE_HASH")
    source=Path(path)
    require(source.is_file() and
            digest_bytes(source.read_bytes())==original_sha,
            "WF_V81_TRANSFER_SOURCE_CONTENT_CHANGED")
    require(encoding in ("gb18030","utf-8","utf-8-sig"),
            "WF_V81_TRANSFER_ENCODING_NOT_ATTESTED")
    chapters,scan=_scan_document(source,encoding)
    first=chapters[0]
    with source.open("r",encoding=encoding,errors="strict",
                     newline=None) as fp:
        fp.seek(first.start_cookie)
        body=[]
        while fp.tell()<first.end_cookie:
            before=fp.tell()
            line=fp.readline()
            require(line and fp.tell()>before,
                    "WF_V81_TRANSFER_CHAPTER_EOF")
            body.append(line)
        require(fp.tell()==first.end_cookie,
                "WF_V81_TRANSFER_FIRST_CHAPTER_RANGE_WRONG")
    body="".join(body)
    require(len(body)==first.body_characters and
            digest_bytes(body.encode("utf8"))==first.body_sha256,
            "WF_V81_TRANSFER_ORIGINAL_CHAPTER_HASH_MISMATCH")
    units=_split_into_ordered_units(body)
    require(len(units)>=3,
            "WF_V81_TRANSFER_HELDOUT_SOURCE_TOO_SHORT")
    trial=units[:2]
    prompt_order_seed=digest_bytes((
        source_key_sha+trained_experience_sha+first.body_sha256
    ).encode("ascii"))
    order=("experience","baseline") if int(
        prompt_order_seed[:2],16)%2==1 else ("baseline","experience")
    proof={
        "format":FORMAT,
        "source_key_sha256":source_key_sha,
        "original_sha256":original_sha,
        "first_source_chapter_sha256":first.body_sha256,
        "first_chapter_source_line":first.source_line,
        "source_first_two_unit_sha256":[digest_bytes(x.encode("utf8"))
                                        for x in trial],
        "first_two_unit_characters":[len(x) for x in trial],
        "source_full_first_chapter_unit_count":len(units),
        "trained_experience_sha256":trained_experience_sha,
        "arm_order":list(order),
        "arm_order_seed_sha256":prompt_order_seed,
        "source_folder_genre_is_not_literary_truth":True,
        "original_edition_verified":False,
        "unseen_other_work":True,
        "model_calls_before_precommit":0,
        "source_text_logged":False,
        "independent_literary_quality_verified":False,
    }
    return tuple(trial),proof


def validate_model_proposal(obj,*,source_units):
    """Mechanical validity only; rejects source copies and ungrounded IDs."""
    require(isinstance(obj,dict) and set(obj)==FIELDS,
            "WF_V81_TRANSFER_JSON_SCHEMA_INVALID")
    for field in ("question","hypothesis","uncertainty","focus"):
        value=obj[field]
        require(isinstance(value,str) and
                8<=len(value)<=MAX_RESPONSE_CHARS and
                "\x00" not in value,
                "WF_V81_TRANSFER_FIELD_BOUNDS_OR_EMPTY")
    ids=obj["evidence_units"]
    require(isinstance(ids,list) and 1<=len(ids)<=2 and
            all(type(v) is int and v in (1,2) for v in ids) and
            len(set(ids))==len(ids),
            "WF_V81_TRANSFER_EVIDENCE_UNIT_NOT_GROUNDED")
    # This is an exam record, not a way to copy complete private paragraphs
    # into prompts/logs; long verbatim excerpts fail in either arm.
    for field in ("question","hypothesis","uncertainty","focus"):
        txt=obj[field]
        require(all(span not in txt for unit in source_units
                    for span in (unit[i:i+28] for i in
                                 range(0,max(0,len(unit)-27),14))),
                "WF_V81_TRANSFER_UNAUTHORIZED_LONG_SOURCE_COPY")
    return {
        "source_units_referenced":list(ids),
        "nonempty_uncertainty_recorded":True,
        "model_proposal_hash_sha256":digest_bytes(canonical(obj)),
        "mechanical_evidence_indices_valid":True,
        "interpretation_truth_not_established":True,
        "difference_does_not_prove_transfer":True,
    }


def compare_arms(baseline,experience):
    require(all(isinstance(x,dict) for x in (baseline,experience)),
            "WF_V81_TRANSFER_ARM_RECORD_INVALID")
    return {
        "answer_sha_differs":digest_bytes(canonical(baseline))!=
                             digest_bytes(canonical(experience)),
        "baseline_evidence_unit_count":len(baseline["evidence_units"]),
        "experience_evidence_unit_count":len(experience["evidence_units"]),
        "source_unit_references_changed":
            baseline["evidence_units"]!=experience["evidence_units"],
        "literary_quality_delta_grading_unavailable":True,
        "prompt_conditioning_alone_can_explain_difference":True,
        "learned_skill_improvement_unproven":True,
        "no_examiner_preselected_literary_answer":True,
    }
