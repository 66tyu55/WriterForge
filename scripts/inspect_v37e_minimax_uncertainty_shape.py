"""Zero-model metadata only: MiniMax uncertainty array shape, never text."""
from __future__ import annotations
import json
from writerforge.r2_storage import R2StudyVault,R2Config
from scripts.revalidate_v37c_l2_historical_reviews import _get_raw
from scripts.forensic_v37b_xiyouji_two_stage import _unwrap,DRAFT_FIELDS

def run(vault):
    if vault.config.bucket!="writerforge-private-library":
        raise ValueError("PRIVATE_R2_REQUIRED")
    raw,h=_get_raw(vault,"minimax-m3","draft")
    record=_unwrap(raw,DRAFT_FIELDS)
    value=record["uncertainty"]
    summary={
        "stage":"V37E_MINIMAX_EXISTING_UNCERTAINTY_LIST_SHAPE",
        "source_raw_sha256":h,
        "type":type(value).__name__,
        "items_count":len(value) if isinstance(value,list) else None,
        "element_types":[type(x).__name__ for x in value] if isinstance(value,list) else None,
        "individual_char_lengths":[len(x) if isinstance(x,str) else None
                                   for x in value] if isinstance(value,list) else None,
        "sum_actual_characters":sum(len(x) for x in value if isinstance(x,str))
            if isinstance(value,list) else None,
        "publicly_disclosed_reviewer_language":False,
        "model_calls":0,
    }
    print(json.dumps(summary,ensure_ascii=False,sort_keys=True))
    return summary
if __name__=="__main__":
    run(R2StudyVault(R2Config.from_environment()))
