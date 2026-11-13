"""Source-grounded xianxia time-parameter coverage, independent of story writer.

This extractor reads complete original files locally. It produces *candidate*
observations with exact source spans and conservatively typed numeric units.
It MUST NOT claim that source occurrence, training labels or file hashes prove
narrative time, true causal direction or a complete world representation.

No model calls, network requests, Xuehai mutation, R2 writes or original text
published by default. Private detailed receipts must stay outside Git.
"""
from __future__ import annotations

from bisect import bisect_right
from collections import Counter
from fractions import Fraction
from hashlib import sha256
import argparse
import json
from pathlib import Path
import re

FORMAT="wf.xianxia-time-parameter-candidates.v3"
NUMS="一二三四五六七八九十百千万亿兩两零〇○廿卅"
QUANTITY=rf"(?:半|(?:约|大约|近|将近|足足|至少|超过|不到|数|几)?[0-9{NUMS}]{{1,8}}(?:余|多|来|几)?)"
AMOUNT=re.compile(rf"({QUANTITY})\s*(个)?\s*(年|载|月|天|日|时辰|小时|时|刻|岁|甲子)")
CHAPTER=re.compile(r"^第[零〇○一二三四五六七八九十百千万兩两0-9]{1,12}章(?:[\s:：、.．-]+.*)?$")
VOLUME=re.compile(r"^第[零〇○一二三四五六七八九十百千万兩两0-9]{1,12}[卷集].{0,45}(?:第[零〇○一二三四五六七八九十百千万兩两0-9]{1,12}章|魔序).{0,32}$")
DOMAINS={
 "narrative_revelation":("char_offset","reader","source character order; NOT event time"),
 "world_elapsed":("world_time_unit","world","duration if its referent is known"),
 "story_relative_order":("relative_relation","event","earlier/later/simultaneous, reference may be unknown"),
 "actor_subjective_elapsed":("subjective_time_unit","actor","only if explicit character experienced time"),
 "actor_biological_age":("age_time_unit","actor","reported age distinct from lifespan"),
 "lifespan_ceiling":("lifespan_unit","actor","claim of possible lifespan, not a death date"),
 "cultivation_exposure":("training_time_unit","actor","actual training time, not training effect"),
 "cultivation_efficiency":("effect_per_training_time","actor","learning/progress equivalence, NOT physical time dilation"),
 "local_time_rate":("subjective/world_duration_ratio","frame","must have evidence for different elapsed clocks"),
 "frame_access_schedule":("visits_per_world_day and visit_duration","frame","capacity/entry limit distinct from physical rate"),
 "actor_biological_aging_rate":("biological_age_increment/subjective_elapsed","actor","cannot derive bodily aging from dream experience"),
 "advancement_condition":("temporal_precondition","actor","candidate threshold, never auto success"),
 "travel_elapsed":("world_time_unit","journey","time spent traveling, actor/speed usually unknown"),
 "waiting_deadline":("world_time_unit","event","reported waiting or constraint, may be forecast"),
 "recurrence_period":("period_time_unit","event","period, not guarantee of next occurrence"),
 "historical_era":("era_id_or_offset","history","cannot assume universal alignment between eras"),
 "parallel_offscreen_time":("world_time_unit","actors","events outside POV continue if text attests"),
 "uncertainty":("qualification","evidence","approximate/range/rumour/unknown not exact"),
}
CONTEXT_PATTERNS={
 "cultivation_exposure":r"闭关|修炼|苦修|静修|修行|打坐|吐纳|悟道|养气|炼气",
 "cultivation_efficiency":r"修炼速度|修炼效率|抵得上|相当于|媲美|堪比|修炼效果|效率|事半功倍",
 "actor_biological_age":r"年龄|年纪|年岁|今年|岁数|几岁|十几岁|二十多岁",
 "lifespan_ceiling":r"寿元|寿数|寿命|寿终|大限|活到|享年",
 "story_relative_order":r"当年|此前|之后|之前|后来|此前|前日|多年前|数年后|过去",
 "travel_elapsed":r"赶路|路程|一路飞行|飞行了|抵达|出发|跋涉|路途|沿路",
 "waiting_deadline":r"等待|等候|约定|截止|期限|还剩|剩下|之内|时限",
 "recurrence_period":r"每隔|每年|每月|十年一届|每.{0,5}一次|周而复始|周期",
 "historical_era":r"纪元|上古|远古|太古|古代|古时|前朝|历史|世代",
 "parallel_offscreen_time":r"与此同时|另一边|同一时间|另一处|那一边",
 "advancement_condition":r"突破|破境|进阶|瓶颈|冲关|筑基|结丹|元婴",
}
RX={k:re.compile(p) for k,p in CONTEXT_PATTERNS.items()}
NEGATIVE_RATE=re.compile(r"并无.{0,8}时间流速|并没有.{0,8}时间流速|没有.{0,8}时间加速")
# Some of the most important clock relationships contain NO number at all.
NON_NUMERIC_SIGNALS={
 "local_time_rate":re.compile(r"时间流速|时间加速|时光加速|时光流速"),
 "historical_era":re.compile(r"[一-鿿]{1,6}元年|第[零一二三四五六七八九十0-9]{1,6}纪(?:元)?|[上太远]古"),
 "story_relative_order":re.compile(r"与此同时|此前|此后|当年|很久以前|多年以后"),
 "parallel_offscreen_time":re.compile(r"与此同时|同一时间|另一边|另一处"),
}
EVIDENT_RATE=re.compile(r"时间流速.{0,12}(?:快|慢|不同|倍)|(?:外界|洞中).{0,15}(?:一年|一日).{0,15}(?:里面|外面|洞中|外界)")
EFFICIENCY=re.compile(CONTEXT_PATTERNS["cultivation_efficiency"])
AFTER=re.compile(r"之后|以后|以后|后面|后$|前$|以前|之前")
UNIT={"年":"calendar_year","载":"calendar_year","月":"calendar_month",
      "天":"day","日":"day","时辰":"shichen","小时":"hour",
      "时":"ambiguous_shi","刻":"ke","岁":"age_year","甲子":"jiazi"}

def source_read(path):
    raw=Path(path).read_bytes()
    codec="utf-8" if raw.startswith(b"\xef\xbb\xbf") else "utf-8"
    try: text=raw.decode(codec,"strict")
    except UnicodeDecodeError:
        codec="gb18030";text=raw.decode(codec,"strict")
    assert text.encode(codec)==raw,"SOURCE_NOT_BYTE_ROUNDTRIPPED"
    return raw,text,codec

def first_story(text):
    pos=0
    for line in text.splitlines(keepends=True):
        if CHAPTER.fullmatch(line.strip()) or VOLUME.fullmatch(line.strip()):
            return pos
        pos+=len(line)
    raise ValueError("FIRST_STORY_HEADING_NOT_FOUND")

def chinese_exact(s):
    """Return exact numeric count only for unambiguous single Chinese numerals."""
    if s=="半":return Fraction(1,2)
    if s.isdecimal():return Fraction(int(s),1)
    numerals={"零":0,"〇":0,"○":0,"一":1,"二":2,"两":2,"兩":2,
              "三":3,"四":4,"五":5,"六":6,"七":7,"八":8,"九":9}
    units={"十":10,"百":100,"千":1000,"万":10000,"亿":100000000}
    if not s or any(ch not in numerals and ch not in units for ch in s):
        return None
    # Colloquial merged counts "三五年", "十七八岁" are ranges, NOT exact 5/18.
    if any(a in numerals and b in numerals and a not in "零〇○" and b not in "零〇○"
           for a,b in zip(s,s[1:])):
        return None
    total,group,current=0,0,0
    try:
        for ch in s:
            if ch in numerals: current=numerals[ch]
            elif ch=="万" or ch=="亿":
                group=(group+current)*units[ch];total+=group;group=current=0
            else:
                mult=units[ch]
                group+=(current if current else 1)*mult
                current=0
        return Fraction(total+group+current,1)
    except (OverflowError,ValueError):return None

def qualified_quantity(word,unit):
    # "一时" often a discourse adverb, "万天明" is a person's name; neither
    # may silently become a measured duration.
    if word in {"多","一时"} or (word=="万" and unit=="天"):
        return None,"AMBIGUOUS_LEXEME"
    marker=word
    exact=chinese_exact(word)
    if exact is not None:return str(exact),"EXACT"
    if word.startswith(("约","大约","近","将近","足足","数","几","至少","超过","不到")) or word.endswith(("余","多","来","几")):
        return None,"BOUNDED_OR_APPROX_UNRESOLVED"
    return None,"UNRESOLVED_QUANTITY"

def independently_coded(context,literal):
    found=[k for k,rx in RX.items() if rx.search(context)]
    if NEGATIVE_RATE.search(context):
        found.append("local_time_rate")
        status="NEGATED_UNUSUAL_RATE"
    elif EVIDENT_RATE.search(context):
        found.append("local_time_rate")
        status="POTENTIAL_EXPLICIT_RATE"
    else:
        status="NO_FRAME_RATE_EVIDENCE"
    # Training *efficiency* does not license physical rate != 1.
    if EFFICIENCY.search(context):
        if "cultivation_efficiency" not in found:found.append("cultivation_efficiency")
    if "lifespan_ceiling" in found and "actor_biological_age" in found:
        # Both are candidate dimensions, never collapse into death time.
        pass
    if "cultivation_efficiency" in found and "local_time_rate" not in found:
        status="EFFICIENCY_IS_NOT_TIME_DILATION"
    return sorted(set(found)),status

def scan(path,max_matches=50000,include_private_context=False):
    raw,text,encoding=source_read(path)
    cut=first_story(text)
    lines=text.splitlines(keepends=True)
    char_off=[0];byte_off=[0]
    for line in lines:
        char_off.append(char_off[-1]+len(line))
        byte_off.append(byte_off[-1]+len(line.encode(encoding)))
    assert char_off[-1]==len(text) and byte_off[-1]==len(raw)
    rows=[]
    for m in AMOUNT.finditer(text,cut):
        val,magnitude,unit=m.group(1),m.group(2),m.group(3)
        if unit=="时" and (m.end()<len(text) and text[m.end()] in "间代候分机光期节") :
            continue
        # Prevent source names like '万天明', '二天一流' from becoming duration.
        if unit in ("天","日","时") and m.end()<len(text):
            next_char=text[m.end()]
            if (next_char not in "了来后前内中间左右以而为至即这那与，。！？,.、：:；;）)]〉\n\r \t"
                    and m.group(0) in {"万天","一日","一时"}):
                continue
        ln=bisect_right(char_off,m.start())-1
        byte_start=byte_off[ln]+len(lines[ln][:m.start()-char_off[ln]].encode(encoding))
        surface=m.group(0)
        bs=surface.encode(encoding)
        assert raw[byte_start:byte_start+len(bs)]==bs
        context=text[max(cut,m.start()-38):min(len(text),m.end()+38)]
        labels,rate_status=independently_coded(context,surface)
        # A nearby negated/affirmed frame-rate statement is NOT evidence
        # that this particular numeric duration describes frame dilation.
        # Keep the rate claim as its own independently anchored signal.
        labels=[x for x in labels if x!="local_time_rate"]
        if rate_status in ("NEGATED_UNUSUAL_RATE","POTENTIAL_EXPLICIT_RATE"):
            rate_status="NEARBY_TIME_RATE_CLAIM_NOT_THIS_DURATION"
        quantity,qual=qualified_quantity(val,unit)
        if "cultivation_efficiency" in labels and "local_time_rate" not in labels:
            rate_status="EFFICIENCY_IS_NOT_TIME_DILATION"
        row={
          "source_byte_start":byte_start,"source_byte_end":byte_start+len(bs),
          "source_char_start":m.start(),"source_char_end":m.end(),
          "surface_sha256":sha256(bs).hexdigest(),
          "unit":UNIT[unit],"explicit_quantity":quantity,
          "quantity_status":qual,"candidate_parameter_ids":labels,
          "time_rate_inference_status":rate_status,
          "semantic_review_status":"NOT_REVIEWED",
          "actor_identity_verified":False,
          "story_event_time_verified":False
        }
        if include_private_context:
            row["source_surface_PRIVATE"]=surface
            row["context_PRIVATE"]=context
        rows.append(row)
        if len(rows)>max_matches:raise ValueError("TIME_MATCH_CAP_EXCEEDED")
    # Non-numeric expressions are source evidence too: "元年",
    # "与此同时", "时间流速并无变化" MUST not vanish from training.
    for parameter,signal in NON_NUMERIC_SIGNALS.items():
        for match in signal.finditer(text,cut):
            ln=bisect_right(char_off,match.start())-1
            byte_start=byte_off[ln]+len(lines[ln][:match.start()-char_off[ln]].encode(encoding))
            surface=match.group(0)
            bs=surface.encode(encoding)
            assert raw[byte_start:byte_start+len(bs)]==bs
            ctx=text[max(cut,match.start()-38):min(len(text),match.end()+38)]
            _,status=independently_coded(ctx,surface)
            row={
              "source_byte_start":byte_start,"source_byte_end":byte_start+len(bs),
              "source_char_start":match.start(),"source_char_end":match.end(),
              "surface_sha256":sha256(bs).hexdigest(),"unit":"NO_QUANTIFIED_UNIT",
              "explicit_quantity":None,"quantity_status":"NO_NUMERIC_QUANTITY",
              "candidate_parameter_ids":[parameter],
              "time_rate_inference_status":status if parameter=="local_time_rate" else "NOT_APPLICABLE",
              "semantic_review_status":"NOT_REVIEWED",
              "actor_identity_verified":False,"story_event_time_verified":False
            }
            if include_private_context:
                row["source_surface_PRIVATE"]=surface
                row["context_PRIVATE"]=ctx
            rows.append(row)
            if len(rows)>max_matches:raise ValueError("TIME_MATCH_CAP_EXCEEDED")
    rows.sort(key=lambda row:(row["source_char_start"],row["source_char_end"]))
    counts=Counter();units=Counter();quals=Counter()
    for row in rows:
        counts.update(row["candidate_parameter_ids"])
        units[row["unit"]]+=1;quals[row["quantity_status"]]+=1
    return {"format":FORMAT,"source_sha256":sha256(raw).hexdigest(),
       "source_bytes":len(raw),"source_encoding":encoding,
       "story_start_char_offset":cut,"source_spans_byte_verified":True,
       "candidates":rows,
       "summary":{"candidate_mentions":len(rows),"candidate_parameters":dict(counts),
                  "units":dict(units),"quantity_status":dict(quals),
                  "unreviewed_semantic_candidates":len(rows),
                  "model_weight_training_performed":False,
                  "full_story_semantic_time_coverage_proven":False}}


def admit_frame_visit(schedule, state, *, world_day_id):
    """Source-specific access quota. Never turn quota into elapsed/training time.

    Example provenance: a private original may report three entries per day
    and 'more than twenty shichen per entry'. The latter is an approximate
    claim, NOT an exact numeric maximum duration or 10x effective learning.
    No story clock or biological aging is inferred here.
    """
    needed={"frame_id","max_visits_per_world_day","reported_entry_duration",
            "source_claim_status","universal_rule"}
    if type(schedule) is not dict or set(schedule)!=needed:
        raise ValueError("FRAME_QUOTA_SCHEMA")
    if (type(schedule["frame_id"]) is not str or
        type(schedule["max_visits_per_world_day"]) is not int or
        not 1<=schedule["max_visits_per_world_day"]<=100 or
        schedule["source_claim_status"] not in ("reported","narrated") or
        schedule["universal_rule"] is not False):
        raise ValueError("FRAME_QUOTA_NOT_SOURCE_BOUNDED")
    info=schedule["reported_entry_duration"]
    if type(info) is not dict or set(info)!={"quantity","unit","qualifier"}:
        raise ValueError("ENTRY_DURATION_SCHEMA")
    if (type(info["quantity"]) is not str or
        info["unit"] not in ("shichen","hour","day") or
        info["qualifier"] not in ("EXACT","MORE_THAN","APPROX","UNKNOWN")):
        raise ValueError("ENTRY_DURATION_NOT_CALIBRATED")
    if (type(state) is not dict or set(state)!={"day_id","visits_used"} or
        type(world_day_id) is not int or world_day_id<0 or
        type(state["visits_used"]) is not int or
        state["visits_used"]<0 or
        (state["day_id"] is not None and
         (type(state["day_id"]) is not int or world_day_id<state["day_id"]))):
        raise ValueError("FRAME_QUOTA_STATE_INVALID")
    consumed=(state["visits_used"] if state["day_id"]==world_day_id else 0)
    if consumed >= schedule["max_visits_per_world_day"]:
        raise ValueError("FRAME_DAILY_ENTRY_QUOTA_EXHAUSTED")
    return {
        "next_state":{"day_id":world_day_id,"visits_used":consumed+1},
        "visit_count_recorded":True,
        "subjective_elapsed_from_visit":None,
        "cultivation_credit_from_visit":None,
        "biological_aging_from_visit":None,
        "source_reported_duration_exact":info["qualifier"]=="EXACT",
        "rate_and_quota_separately_required":True,
    }


def do_not_infer_aging_from_cultivation(cultivation_credit, *, direct_age_evidence=None):
    """Dream-practice duration is not evidence of bodily aging."""
    if cultivation_credit is None:
        raise ValueError("CULTIVATION_DURATION_MISSING")
    if direct_age_evidence is None:
        return {"biological_age_increment":None,
                "knowledge_state":"UNKNOWN_NO_DIRECT_AGING_EVIDENCE",
                "may_not_set_to_cultivation_credit":True}
    if type(direct_age_evidence) is not dict or set(direct_age_evidence)!={"duration","unit","epistemic"}:
        raise ValueError("AGING_EVIDENCE_SCHEMA")
    if direct_age_evidence["epistemic"] not in ("narrated","reported"):
        raise ValueError("AGING_EVIDENCE_NOT_ESTABLISHED")
    return {"biological_age_increment":direct_age_evidence["duration"],
            "unit":direct_age_evidence["unit"],
            "knowledge_state":"SOURCE_REPORTED_NOT_UNIVERSAL"}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--source",action="append",required=True)
    ap.add_argument("--private-output",required=True)
    a=ap.parse_args();out=Path(a.private_output)
    if out.exists():raise FileExistsError("PRIVATE_OUTPUT_EXISTS")
    out.mkdir(parents=True)
    summary=[]
    for index,path in enumerate(a.source,1):
        result=scan(path,include_private_context=True)
        (out/f"private_original_{index:02}.json").write_text(json.dumps(
            result,ensure_ascii=False,indent=2),"utf-8")
        summary.append({"source_sha256":result["source_sha256"],
                        "source_bytes":result["source_bytes"],
                        **result["summary"]})
    allsum={"format":FORMAT+".aggregate", "works":len(summary),
      "raw_original_bytes":sum(s["source_bytes"] for s in summary),
      "candidate_mentions":sum(s["candidate_mentions"] for s in summary),
      "parameter_slots":list(DOMAINS),
      "source_summaries":summary,
      "all_claims_remain_unreviewed":True,
      "complete_original_novel_time_training":False}
    (out/"aggregate_no_original_text.json").write_text(json.dumps(
       allsum,ensure_ascii=False,indent=2),"utf-8")
    print(json.dumps({"works":allsum["works"],
                      "raw_original_bytes":allsum["raw_original_bytes"],
                      "candidate_mentions":allsum["candidate_mentions"],
                      "parameters_defined":len(DOMAINS)},ensure_ascii=False))
if __name__=="__main__":
    main()
