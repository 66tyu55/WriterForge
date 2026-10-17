"""Zero-model PRIVATE R2 diagnostics of V37b raw reviewer structure.

Print only field types, lengths and whether actual numbered citations exist.
Never show any source passage, story, reviewer prose or secret in GitHub logs.
"""
from __future__ import annotations
import json
from writerforge.r2_storage import R2Config,R2StudyVault
from writerforge.v35_observable_trace import sha
from scripts.forensic_v37b_xiyouji_two_stage import (
    _root, SOURCE_FIELDS,DRAFT_FIELDS,SOURCE_ENUM,DRAFT_ENUM,
    _unwrap,L2SplitReviewError,
)
RAW={
    ("deepseek-v4-pro-0813","source"):
      "549299d153941b743251b5f6a2b1938d962e0797f94205356e691073d5cd4480",
    ("deepseek-v4-pro-0813","draft"):
      "62e23f86da3356ed23826e712132b8ff086479612b5828d04690d83a2e4e3414",
    ("minimax-m3","source"):
      "66c1ea24aea5eeb07ca9dbd4236c43e7d633d40daede862bd2f13f7245abeb96",
    ("minimax-m3","draft"):
      "6ffade7d090f9703fff197d32e66413d501a48445c66e2c18c8839bab83658cc",
}
def run(vault):
    if vault.config.bucket!="writerforge-private-library":
        raise ValueError("PRIVATE_R2_ONLY")
    report=[]
    for (model,phase),h in RAW.items():
        key=f"{_root()}/unfiltered-{model}-{phase}-{h}.json"
        blob=vault._get_small(key,35000)
        if sha(blob)!=h:raise ValueError("R2_RAW_REVIEW_SHA_MISMATCH")
        record=json.loads(blob)
        data=record.get("unmodified_model_response")
        fields=SOURCE_FIELDS if phase=="source" else DRAFT_FIELDS
        try:
            row=_unwrap(data,fields)
            reason_fields=(("source_reason","abstraction_reason","fit_reason","uncertainty")
                           if phase=="source" else ("execution_reason","uncertainty"))
            lengths={k:len(row[k]) if isinstance(row[k],str) else -1
                     for k in reason_fields}
            too_short=[k for k in lengths if lengths[k]<15]
            too_long=[k for k in lengths if lengths[k]>275]
            enums=SOURCE_ENUM if phase=="source" else DRAFT_ENUM
            valid_enums={k:row[k] in allowed if isinstance(row[k],str) else False
                         for k,allowed in enums.items()}
            evidence_arrays=({k:{"count":len(row[k]) if isinstance(row[k],list) else -1,
                                  "types":sorted({type(i).__name__ for i in row[k]})
                                  if isinstance(row[k],list) else []}
                              for k in ("first_setup_numbers","first_payoff_numbers",
                                        "revised_setup_numbers","revised_payoff_numbers")}
                             if phase=="draft" else None)
            report.append({"model":model,"phase":phase,"schema_exact":True,
                           "reason_lengths":lengths,"short_reason_fields":too_short,
                           "overlong_reason_fields":too_long,
                           "enum_types_valid":valid_enums,
                           "cited_number_arrays":evidence_arrays,
                           "raw_response_sha256":h})
        except L2SplitReviewError as exc:
            report.append({"model":model,"phase":phase,
                           "schema_exact":False,
                           "reason_code":str(exc),
                           "raw_response_sha256":h})
    result={"stage":"V37B_REAL_RAW_REVIEW_SHAPE_ONLY_ZERO_MODEL",
            "records":report,"model_calls":0,
            "raw_reviewer_prose_logged":False,
            "source_and_draft_text_logged":False}
    print(json.dumps(result,ensure_ascii=False,sort_keys=True))
    return result
if __name__=="__main__":
    run(R2StudyVault(R2Config.from_environment()))
