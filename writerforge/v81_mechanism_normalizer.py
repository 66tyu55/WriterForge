"""V81 source-provenance-safe normalization of model mechanism JSON.

DeepSeek JSON mode requires one JSON object, not an application schema.
Accept only model-provided unit numbers and real textual claims. Never
invent interpretations or original positions. Attach independently
verified source SHA; reject mismatched model-supplied SHA. Free prose and
missing fields remain failures, not fabricated successes.
"""
from __future__ import annotations
import json
from .r2_learn_journal import mechanism_schema

class WFMechanismFormatError(ValueError):
    pass

WRAPPER_KEYS=("mechanisms","techniques","observations","analysis",
              "results","literary_analysis","devices","items")
UNIT_KEYS=("unit","unit_no","unit_number","source_unit",
           "paragraph","paragraph_number","单位","段落编号","段落")
MECHANISM_KEYS=("mechanism","technique","literary_device",
                "narrative_mechanism","technique_name",
                "叙事手法","文学手法","手法","叙事机制")
EFFECT_KEYS=("reader_effect","effect","narrative_effect",
             "impact_on_reader","读者效果","阅读效果","效果")
UNCERTAINTY_KEYS=("uncertainty","limitations","evidence_limit",
                  "confidence_limit","不确定性","局限","局限性")
HASH_KEYS=("evidence_unit_sha256","source_unit_sha256")


def _first(obj,names):
    return next((obj[k] for k in names if k in obj),None)


def _extract(value,depth=0):
    if depth>5:
        raise WFMechanismFormatError("WF_V81_ANALYSIS_TOO_DEEPLY_NESTED")
    if isinstance(value,str):
        stripped=value.strip()
        if stripped.startswith(("[","{")):
            try:parsed=json.loads(stripped)
            except (ValueError,UnicodeError):
                raise WFMechanismFormatError(
                    "WF_V81_ANALYSIS_STRING_NOT_JSON") from None
            return _extract(parsed,depth+1)
        raise WFMechanismFormatError(
            "WF_V81_ANALYSIS_FREE_TEXT_NOT_EVIDENCE")
    if isinstance(value,list):
        if not value:
            raise WFMechanismFormatError("WF_V81_ANALYSIS_EMPTY_MECHANISMS")
        if not all(isinstance(x,dict) for x in value[:6]):
            raise WFMechanismFormatError("WF_V81_ANALYSIS_UNSTRUCTURED_LIST")
        return value,max(0,len(value)-6)
    if isinstance(value,dict):
        for k in WRAPPER_KEYS:
            if k in value:
                try:return _extract(value[k],depth+1)
                except WFMechanismFormatError:
                    pass
        if _first(value,UNIT_KEYS) is not None:
            return [value],0
        if value and all(str(k).isdecimal() for k in value):
            out=[]
            for key,row in sorted(value.items(),key=lambda kv:int(kv[0])):
                if not isinstance(row,dict):
                    raise WFMechanismFormatError(
                        "WF_V81_ANALYSIS_NUMBERED_ENTRY_NOT_OBJECT")
                original_unit=_first(row,UNIT_KEYS)
                if original_unit is not None and str(original_unit)!=str(int(key)):
                    raise WFMechanismFormatError(
                        "WF_V81_ANALYSIS_MAP_UNIT_CONTRADICTS_FIELD")
                out.append({**row,"unit":int(key)})
            return out,max(0,len(out)-6)
        if len(value)==1:
            return _extract(next(iter(value.values())),depth+1)
    raise WFMechanismFormatError("WF_V81_ANALYSIS_SHAPE_UNSUPPORTED")


def normalize_mechanisms(raw,verified_unit_hashes):
    if not isinstance(verified_unit_hashes,(tuple,list)) or not (
        1<=len(verified_unit_hashes)<=80
    ):
        raise WFMechanismFormatError("WF_V81_SOURCE_UNIT_HASH_LIST_UNAVAILABLE")
    found,extra=_extract(raw)
    normalized=[]
    for row in found[:6]:
        pos=_first(row,UNIT_KEYS)
        if isinstance(pos,str) and pos.isdecimal():pos=int(pos)
        if type(pos) is not int or not 1<=pos<=len(verified_unit_hashes):
            raise WFMechanismFormatError("WF_V81_MODEL_SOURCE_POSITION_INVALID")
        expected=verified_unit_hashes[pos-1]
        given=_first(row,HASH_KEYS)
        if given is not None and given!=expected:
            raise WFMechanismFormatError("WF_V81_MODEL_FABRICATED_EVIDENCE_SHA")
        mech=_first(row,MECHANISM_KEYS)
        effect=_first(row,EFFECT_KEYS)
        doubt=_first(row,UNCERTAINTY_KEYS)
        if not all(isinstance(x,str) and 1<=len(x)<=160
                   for x in (mech,effect,doubt)):
            raise WFMechanismFormatError(
                "WF_V81_MODEL_EVIDENCE_FIELDS_MISSING_OR_OVERSIZED")
        complete={
           "unit":pos,"evidence_unit_sha256":expected,
           "mechanism":mech,"reader_effect":effect,
           "uncertainty":doubt,
        }
        if not mechanism_schema(complete):
            raise WFMechanismFormatError(
                "WF_V81_NORMALIZED_EVIDENCE_SCHEMA_INVALID")
        normalized.append(complete)
    return normalized,{
        "source_unit_count":len(verified_unit_hashes),
        "supported_rows_accepted":len(normalized),
        "additional_model_mechanisms_not_persisted":extra,
        "model_source_hash_never_trusted":True,
        "missing_literary_analysis_never_fabricated":True,
    }
