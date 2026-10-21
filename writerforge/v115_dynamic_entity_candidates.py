"""V115 conservative zero-LLM discovery of novel-specific entities.

Independent of pre-listed swords, pills and props. A suffix+context filter
discovers candidate literary resources and injuries with ORIGINAL quote offsets.
A *mention* does not imply holder, power, ownership or condition; no such
state may be committed without a separately anchored event.

This is a bounded coverage aid to the original MIT Novel Studio temporal
reducer, not a second entity/knowledge database.
"""
from __future__ import annotations
from hashlib import sha256
import re

MAX_TEXT=20000
MAX_ENTITIES=36
MAX_MENTIONS=100
PAT=re.compile(r"(?<![\u4e00-\u9fff])([\u4e00-\u9fff]{1,5}(?:髓果|灵果|仙果|灵丹|宝丹|丹药|剑穗|佩剑|飞剑|法剑|符箓|宝符|阵旗|法器|法宝))")
EXACT_SUFFIX=("髓果","灵果","仙果","灵丹","宝丹","丹药","剑穗",
              "佩剑","飞剑","法剑","符箓","宝符","阵旗","法器","法宝")
COMMON=("右臂","左臂","右手","左手","右腿","左腿","胸口","肩头","丹田")
HURT=("断","伤","裂","折","流血","骨折","无力","发麻","灼","疼","痛")
MENTION_KINDS={"resource","injury"}
class EntityDiscoveryError(ValueError):
    pass

def discover_candidates(prose):
    if type(prose) is not str or not 0<len(prose)<=MAX_TEXT:
        raise EntityDiscoveryError("WF115_TEXT_INVALID_OR_TOO_BIG")
    candidate={}
    for m in PAT.finditer(prose):
        term=m.group(1)
        start=m.start(1)
        # A Chinese classifier ('一枚火髓果') must not be mistaken for
        # the object's actual name. Keep exact span of 火髓果 instead.
        if term.endswith("髓果") and len(term)>3:
            term=term[-3:]
            start=m.end(1)-3
        # The native prompt cannot assume a captured prose word is a fact.
        # Only source-anchored entity mention; decide holder separately.
        candidate.setdefault((term,"resource"),[]).append((start,m.end(1)))
    for part in COMMON:
        for match in re.finditer(re.escape(part),prose):
            nearby=prose[max(0,match.start()-12):min(len(prose),match.end()+20)]
            if any(w in nearby for w in HURT):
                candidate.setdefault((part,"injury"),[]).append(
                    (match.start(),match.end()))
    # In fluent CJK the first regex can miss a specific proper compound
    # embedded after preceding hanzi. Match suffix terms bounded by source
    # punctuation/adjacent textual phrase, never assign holder.
    for suffix in ("髓果","灵果","仙果","灵丹","宝丹","法器","飞剑","剑穗"):
        for m in re.finditer(r"[\u4e00-\u9fff]{0,3}"+re.escape(suffix),prose):
            fragment=m.group()
            if len(fragment)>7:continue
            # Precise artifact name appears in the prose (e.g. 火髓果):
            # only preserve last 1-2 prefix chars as a candidate alias,
            # don't select arbitrary long noun phrases as truth.
            start=max(m.start(),m.end()-len(suffix)-(1 if suffix=="髓果" else 2))
            candidate.setdefault((prose[start:m.end()],"resource"),[]).append(
                (start,m.end()))
    rows=[]
    for (name,kind),ranges in sorted(candidate.items()):
        if len(rows)>=MAX_ENTITIES:break
        if kind not in MENTION_KINDS:continue
        unique=sorted(set(ranges))[:8]
        for start,end in unique:
            if len(rows)>=MAX_MENTIONS:break
            token=prose[start:end]
            rows.append({
                "term":token,"kind":kind,"start":start,"end":end,
                "literal_span_sha256":sha256(token.encode("utf8")).hexdigest(),
                "source_sha256":sha256(prose.encode("utf8")).hexdigest(),
                "candidate_not_confirmed_as_world_fact":True,
                "holder":"UNKNOWN",
                "change_of_ownership_not_inferred":True,
            })
    return {
       "format":"wf.writing.dynamic-entity-candidates.v115",
       "source_sha256":sha256(prose.encode("utf8")).hexdigest(),
       "mentions":rows,"candidate_count":len(rows),
       "authoritative_entity_states_created":0,
       "literary_semantics_verified":False,
       "model_calls":0,"canon_writes":0,
    }

def compact_entity_context(report):
    if report.get("format")!="wf.writing.dynamic-entity-candidates.v115":
        raise EntityDiscoveryError("WF115_BAD_ENTITY_REPORT")
    seen={}
    for row in report["mentions"]:
        seen.setdefault(row["term"],row["kind"])
    lines=["【原文实际出现但尚未确认位置/持有人的实体、伤势】"]
    for name,kind in list(seen.items())[:18]:
        lines.append(name+("（身体伤势线索）" if kind=="injury"
                           else "（物件/力量来源线索）")+
                     "：只有名字出现，不能自称已知道谁拥有、能否使用或是否痊愈。")
    lines.append("下一段继续观察这些对象，真正发生交接、伤害或恢复时再提出证据事件。")
    return "\n".join(lines)[:950]
