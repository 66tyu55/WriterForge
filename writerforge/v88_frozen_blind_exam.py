"""V88: exact-source, no-future, abstention-aware WF heldout answer contract.

The model emits hypotheses only. Mechanical source matching is not literary
semantic truth; both A and B must be blindly reviewed by an independent
authority to decide whether experience improved reasoning.
"""
from __future__ import annotations
from hashlib import sha256
import json
import re

FORMAT="wf.exam.frozen-two-work-answer.v88"
STATUS=frozenset(("HYPOTHESIS","ABSTAIN"))
ANSWER_KEYS=frozenset((
    "status","claim_id","question","observation","consequence","character_knowledge",
    "hypothesis","alternative","falsifier","uncertainty"))
ANCHOR_KEYS=frozenset(("unit","start","end","quote"))
KNOWLEDGE_KEYS=frozenset(("actor","known","unknown"))
MIN_TEXT=8
MAX_TEXT=180
MAX_QUOTE=72
MAX_RESPONSE_BYTES=10000
MAX_PAID_REQUESTS=4
MAX_OUTPUT_TOKENS_PER_REQUEST=1250
MAX_CONSERVATIVE_INPUT_OUTPUT_TOKENS=40000
SOURCE_UNITS=2
ARM_ORDER={"历史":("baseline","experience"),
           "科幻":("experience","baseline")}
V82_BATCH_SHA="d46ffec05927dfba3f2819089e76e79f720db2a2f3f6793b56965ac6413c177f"
V82_EXPERIENCE_SHA="ddbf86e87e3bf44900b4e5e4d8ffc2de99c9ed5d3c5aec98a69bfd8eb7cf2fe7"
V82_TRAINED_SOURCE_SHA="0f00a16f6a0c121404a28257f3aa728468c9dae78d464ff1341746a45c41ddbd"
V87_DRAW_SHA="ddb50ed6b88681c23d214073d45ba4edba151bf0de1e0bfed5153efeeb3e1f6c"
V87_COLD_SOURCE_RECEIPT_SHA="6565040f03811c51df6aa211b5f79305bb1a65fc8ebdfda5acc209259e515b9a"
SYSTEM_PROMPT=(
 "你是WriterForge的私有文学盲考学生，只能依据提供的两个连续已读原文单位提出"
 "因果或人物信息推断，不得声称了解前后章节、作者意图或未来结局。"
 "本次是不同作品局部片段，并非完整章节。允许且鼓励证据不足时弃权。"
 "若有可证伪的局部推断，status=HYPOTHESIS；否则status=ABSTAIN。"
 "只输出严格JSON对象，且恰好包含status,claim_id,question,observation,"
 "consequence,character_knowledge,hypothesis,alternative,falsifier,uncertainty。"
 "HYPOTHESIS时claim_id给出只含英数的2-40字符标识，observation和consequence各为精确锚点对象"
 '{"unit":1,"start":0,"end":10,"quote":"原文中精确对应的短语"}，'
 "unit只能是1或2；start/end为Python字符串0起点字符偏移，"
 "quote为字节一致的原文连续子串，8-72字符，禁止捏造证据。"
 "character_knowledge恰含actor/known/unknown三个字段，分别写"
 "人物标识、人物当时可能知道什么、不知道什么；只是假说不能当作真值。"
 "question/hypothesis/alternative/falsifier/uncertainty各8-180字符。"
 "ABSTAIN时claim_id设null，两个锚点设null，character_knowledge设null，"
 "question/hypothesis/alternative/falsifier都设为空字符串，uncertainty写8-180字符弃权理由。"
 "禁止泄漏未见单位，禁止抄写长原著。禁止自评分、作弊、文学晋级或代替考官。"
 "JSON"
)

class WF88BlindError(ValueError):
    pass

def require(ok,code):
    if not ok: raise WF88BlindError(code)

def canonical(doc):
    return json.dumps(doc,ensure_ascii=False,sort_keys=True,
                      separators=(",",":"),allow_nan=False).encode("utf8")

def hexdigest(data):
    return sha256(data).hexdigest()

def sha_text(value):
    return hexdigest(value.encode("utf8"))

def _text(s,*,lo=MIN_TEXT,hi=MAX_TEXT):
    return isinstance(s,str) and lo<=len(s.strip())<=hi and \
           "\x00" not in s and \
           not any(ord(ch)<32 for ch in s)

def _anchor(answer,units):
    require(isinstance(answer,dict) and set(answer)==ANCHOR_KEYS,
            "WF88_ANCHOR_FIELDS_INVALID")
    unit,start,end,quote=[answer[key] for key in (
        "unit","start","end","quote")]
    require(type(unit) is int and 1<=unit<=SOURCE_UNITS and
            type(start) is int and type(end) is int and
            isinstance(quote,str) and MIN_TEXT<=len(quote)<=MAX_QUOTE,
            "WF88_ANCHOR_NOT_VISIBLE_OR_INVALID")
    source=units[unit-1]
    require(0<=start<end<=len(source) and
            source[start:end]==quote and end-start==len(quote),
            "WF88_ANCHOR_NOT_EXACT_VISIBLE_SOURCE")
    return {
        "unit":unit,"start":start,"end":end,
        "source_unit_sha256":sha_text(source),
        "short_quote_sha256":sha_text(quote),
        "long_source_quote_not_exported":True,
    }

def validate_wf_answer(answer,*,visible_units):
    require(isinstance(visible_units,tuple) and
            len(visible_units)==SOURCE_UNITS and
            all(isinstance(u,str) and 50<=len(u)<=900 for u in visible_units),
            "WF88_TWO_VISIBLE_UNITS_REQUIRED")
    require(isinstance(answer,dict) and set(answer)==ANSWER_KEYS,
            "WF88_RESPONSE_SCHEMA_INVALID")
    require(len(canonical(answer))<=MAX_RESPONSE_BYTES,
            "WF88_RESPONSE_TOO_LARGE")
    status=answer["status"]
    require(status in STATUS,"WF88_RESPONSE_STATUS_INVALID")
    require(_text(answer["uncertainty"]),
            "WF88_UNCERTAINTY_MISSING_OR_UNBOUNDED")
    if status=="ABSTAIN":
        require(answer["claim_id"] is None and
                answer["observation"] is None and
                answer["consequence"] is None and
                answer["character_knowledge"] is None and
                all(answer[f]=="" for f in (
                    "question","hypothesis","alternative","falsifier")),
                "WF88_ABSTENTION_MUST_NOT_ASSERT_SOURCE_FACTS")
        return {"status":"ABSTAIN","schema_valid":True,
                "exact_source_anchor_checked":False,
                "uncertainty_supplied":True,
                "literary_semantics_independently_verified":False,
                "model_fabrication_not_independently_ruled_out":True}
    require(isinstance(answer["claim_id"],str) and
            re.fullmatch(r"[a-zA-Z0-9_-]{2,40}",answer["claim_id"]),
            "WF88_CLAIM_ID_INVALID")
    require(all(_text(answer[f]) for f in (
        "question","hypothesis","alternative","falsifier")),
        "WF88_HYPOTHESIS_EXPLANATIONS_INVALID")
    evidence=[_anchor(answer[f],visible_units)
              for f in ("observation","consequence")]
    require((evidence[0]["unit"],evidence[0]["start"],evidence[0]["end"])!=
            (evidence[1]["unit"],evidence[1]["start"],evidence[1]["end"]),
            "WF88_SAME_ANCHOR_TWICE")
    knowledge=answer["character_knowledge"]
    require(isinstance(knowledge,dict) and set(knowledge)==KNOWLEDGE_KEYS
            and _text(knowledge["actor"],lo=1,hi=80)
            and all(_text(knowledge[f]) for f in ("known","unknown")),
            "WF88_CHARACTER_KNOWLEDGE_UNVERIFIED")
    # Long copy blocks in analysis are not necessary for this comparison.
    prose="\n".join(str(answer[x]) for x in (
        "question","hypothesis","alternative","falsifier","uncertainty"))
    require(not any(u[i:i+55] in prose for u in visible_units
                    for i in range(0,max(0,len(u)-54),12)),
            "WF88_UNAUTHORIZED_LONG_VERBATIM_SOURCE_COPY")
    return {
        "status":"HYPOTHESIS","schema_valid":True,
        "source_anchors":evidence,
        "character_claims_are_only_hypotheses":True,
        "historical_chapter_context_unavailable":True,
        "causality_independently_verified":False,
        "falsifier_proposed_not_tried":True,
        "literary_semantics_independently_verified":False,
        "future_content_not_provided_by_exam":True,
    }

def shared_prompt(units):
    require(len(units)==2,"WF88_SHARED_PROMPT_TWO_UNITS_REQUIRED")
    return ("以下是同一陌生来源的两个连续原文片段。"
            "题型是局部阅读，不能假装读完整章。"
            "你只能依据当前可见片段作答。\n"
            "[已读单位1]\n"+units[0]+"\n"
            "[已读单位2]\n"+units[1]+"\n"
            "不能查看后面的任何原文单元。")

def arm_prompt(shared,*,arm,strategy):
    require(arm in ("baseline","experience") and isinstance(shared,str),
            "WF88_ARM_INVALID")
    require(isinstance(strategy,str) and 8<=len(strategy)<=200,
            "WF88_SAVED_STRATEGY_INVALID")
    # Fixed prefix and shared source payload; only experimental strategy
    # condition differs. The other arm's answer is not in the prompt.
    condition=("没有历史经验。请按你当下的原文观察和不确定性判断。"
               if arm=="baseline" else
               "这是此前WF第15章在R2签收的检查策略（未经文学质量证明）："+
               strategy)
    return condition+"\n"+shared

def mechanical_pair(baseline,experience,baseline_schema,experience_schema):
    return {
       "answers_are_byte_identical":canonical(baseline)==canonical(experience),
       "baseline_answer_status":baseline.get("status"),
       "experience_answer_status":experience.get("status"),
       "baseline_schema_passed":baseline_schema.get("schema_valid",False),
       "experience_schema_passed":experience_schema.get("schema_valid",False),
       "baseline_anchor_count":len(baseline_schema.get("source_anchors",[])),
       "experience_anchor_count":len(experience_schema.get("source_anchors",[])),
       "independent_literary_quality_winner":"UNDETERMINED",
       "significant_positive_learning_transfer_proven":False,
       "model_prompt_conditioning_could_explain_differences":True,
    }
