"""V105: bounded *forward* causal preflight + append-only candidate debt chain.

Use existing V96/V98/V102 episode and R2/StoryCommit infrastructure. Do not
create a second long-term database. A forward plan is NOT narrative truth.
An authentic short quote is NOT proof of cost/motivation/causality.
Borrow concepts, not code, from AIMA partial-order causal links/open
preconditions and Event Sourcing/Saga compensation vs irreversible events.

Critical invariant: an unreviewed model cannot mark its own debt paid;
a forecast cannot silently become a historical FACT or FactJournal KNOWN.
"""
from __future__ import annotations

from hashlib import sha256
import json
import re

from .v96_causal_turns import canonical as canon
from .v102_emotional_causality import verified_receipt as v102_receipt

MAX_CHOICES=3
MAX_STEPS=4
MAX_CHECKS=6
MAX_EFFECTS=6
MAX_DEBTS_PER_STEP=3
MAX_DEBTS=48
MAX_STORED_FACTS=48
MAX_HORIZON_BYTES=14500
MAX_CHECKPOINT_BYTES=48000
MAX_PRESSURE_CONTEXT_CHARS=1900
MAX_DESCRIPTION=190
MAX_LABEL=88

KEY=re.compile(r"[a-z][a-z0-9_]*(?::[a-z][a-z0-9_]*){0,2}\Z")
ID=re.compile(r"[a-z][a-z0-9_]{1,70}\Z")
SHA=re.compile(r"[0-9a-f]{64}\Z")
KINDS=frozenset(("RESOURCE","PROMISE","RELATIONSHIP","TIME","KNOWLEDGE",
                 "SAFETY","MONEY","LEGAL","OTHER"))
SEVERITY=frozenset(("POSSIBLE","COSTLY","IRREVERSIBLE"))
REQUIRED_STEP=frozenset(("id","actor","action","requires","sets","future_debts",
                         "claims_resolved"))
SCENE_SCHEMA=frozenset(("choices",))
CHOICE_SCHEMA=frozenset(("id","steps"))
CHECK_SCHEMA=frozenset(("key","is"))
EFFECT_SCHEMA=frozenset(("key","becomes"))
DEBT_SCHEMA=frozenset(("id","kind","owner","pressure","due_after",
                       "if_ignored","severity"))

class V105FutureCausalityError(ValueError):
    pass

def require(condition,reason):
    if not condition:
        raise V105FutureCausalityError(reason)

def packed(value):
    return canon(value)

def digest(value):
    return sha256(value).hexdigest()

def fields(value,names,code):
    require(type(value) is dict and set(value)==set(names),code)

def token(value,maxlen=MAX_LABEL):
    return (type(value) is str and 1<=len(value.strip())<=maxlen and
            value.strip()==value and
            "\ufffd" not in value and "\x00" not in value and
            not any(ord(c)<32 for c in value))

def phrase(value,minimum=6,maximum=MAX_DESCRIPTION):
    return token(value,maximum) and len(value)>=minimum

def key(value):
    return type(value) is str and KEY.fullmatch(value) is not None

def ident(value):
    return type(value) is str and ID.fullmatch(value) is not None

def _frozen_author_world(pinned):
    """Only the EXPLICIT CALLER can pin facts; model proposals cannot."""
    require(type(pinned) is dict and len(pinned)<=MAX_STORED_FACTS,
            "WF105_PINNED_AUTHOR_WORLD_BOUNDS")
    for name,value in pinned.items():
        require(key(name) and token(value,64),
                "WF105_PINNED_AUTHOR_FACT_INVALID")
    return dict(pinned)

def _condition(value):
    fields(value,CHECK_SCHEMA,"WF105_PRECONDITION_SCHEMA")
    require(key(value["key"]) and token(value["is"],64),
            "WF105_PRECONDITION_VALUE")
    return (value["key"],value["is"])

def _effect(value):
    fields(value,EFFECT_SCHEMA,"WF105_EFFECT_SCHEMA")
    require(key(value["key"]) and token(value["becomes"],64),
            "WF105_EFFECT_VALUE")
    return (value["key"],value["becomes"])

def _debt(value):
    fields(value,DEBT_SCHEMA,"WF105_FUTURE_DEBT_SCHEMA")
    require(ident(value["id"]) and value["kind"] in KINDS and
            phrase(value["owner"],1,64) and
            phrase(value["pressure"]) and
            phrase(value["if_ignored"]) and
            type(value["due_after"]) is int and
            1<=value["due_after"]<=12 and
            value["severity"] in SEVERITY,
            "WF105_FUTURE_DEBT_VALUE_INVALID")
    return value

def validate_horizon(plan,*,author_pinned=None):
    """Two+ alternate futures, each 1-4 steps, from the SAME pinned state.

    Does NOT choose a 'best' branch. Missing facts remain UNKNOWN.
    Planned changes can support later steps CONDITIONALLY, not as canon.
    False hard preconditions and self-defeating proposed dependencies are
    surfaced before new prose is written. Quiet futures are permitted.
    """
    if type(plan) is str:
        require(2<=len(plan.encode("utf8"))<=MAX_HORIZON_BYTES,
                "WF105_FORECAST_JSON_SIZE")
        try:
            def no_duplicates(items):
                out={}
                for name,value in items:
                    if name in out:raise ValueError("duplicate key")
                    out[name]=value
                return out
            plan=json.loads(plan,object_pairs_hook=no_duplicates,
                            parse_constant=lambda _:
                                (_ for _ in ()).throw(ValueError("invalid")))
        except (ValueError,UnicodeError,TypeError):
            raise V105FutureCausalityError(
                "WF105_FORECAST_JSON_DUPLICATE_OR_INVALID") from None
    require(type(plan) is dict,"WF105_FORECAST_NOT_OBJECT")
    require(len(packed(plan))<=MAX_HORIZON_BYTES,
            "WF105_FORECAST_TOO_MANY_BYTES")
    fields(plan,SCENE_SCHEMA,"WF105_FORECAST_TOP_SCHEMA")
    opts=plan["choices"]
    require(type(opts) is list and 2<=len(opts)<=MAX_CHOICES,
            "WF105_ALTERNATIVE_BRANCH_COUNT")
    pinned=_frozen_author_world(author_pinned or {})
    option_ids=set()
    result=[]
    for option in opts:
        fields(option,CHOICE_SCHEMA,"WF105_BRANCH_SCHEMA")
        name=option["id"]
        require(ident(name) and name not in option_ids,
                "WF105_BRANCH_ID_NOT_UNIQUE")
        option_ids.add(name)
        steps=option["steps"]
        require(type(steps) is list and 1<=len(steps)<=MAX_STEPS,
                "WF105_FUTURE_STEPS_BOUNDS")
        projected=dict(pinned)
        origins={k:"AUTHOR_PINNED" for k in pinned}
        concerns=[]
        debt_ids=set()
        promised=[]
        ids=set()
        traces=[]
        debt_born_at={}
        claimed_resolutions=set()
        for i,s in enumerate(steps,1):
            fields(s,REQUIRED_STEP,"WF105_FUTURE_STEP_SCHEMA")
            require(ident(s["id"]) and s["id"] not in ids and
                    phrase(s["actor"],1,64) and
                    phrase(s["action"]) and
                    type(s["requires"]) is list and
                    len(s["requires"])<=MAX_CHECKS and
                    type(s["sets"]) is list and
                    len(s["sets"])<=MAX_EFFECTS and
                    type(s["future_debts"]) is list and
                    len(s["future_debts"])<=MAX_DEBTS_PER_STEP and
                    type(s["claims_resolved"]) is list and
                    len(s["claims_resolved"])<=MAX_DEBTS_PER_STEP,
                    "WF105_FUTURE_STEP_VALUE_INVALID")
            ids.add(s["id"])
            this_issues=[]
            required=set()
            for req in s["requires"]:
                fact,expected=_condition(req)
                require(fact not in required,
                        "WF105_DUPLICATE_PRECONDITION_IN_STEP")
                required.add(fact)
                current=projected.get(fact)
                if current is None:
                    status="UNPROVEN_PRECONDITION"
                elif current!=expected:
                    status=("CONTRADICTS_PINNED_FACT"
                            if origins[fact]=="AUTHOR_PINNED"
                            else "THREATENS_PREVIOUS_PLANNED_EFFECT")
                else:
                    status=("SUPPORTED_BY_AUTHOR_PIN"
                            if origins[fact]=="AUTHOR_PINNED"
                            else "DEPENDS_ON_UNVERIFIED_PLANNED_EFFECT")
                if status not in ("SUPPORTED_BY_AUTHOR_PIN",):
                    this_issues.append({
                        "kind":status,"step_id":s["id"],"fact_key":fact,
                        "expected":expected,"known_or_projected":current,
                        "source":origins.get(fact,"UNKNOWN")})
            for effect in s["sets"]:
                fact,new=_effect(effect)
                require(fact not in [x["key"] for x in s["sets"]
                    if x is not effect],
                    "WF105_TWO_EFFECTS_SAME_FACT_IN_STEP")
                projected[fact]=new
                origins[fact]="PLANNED_UNVERIFIED"
            for debt in s["future_debts"]:
                _debt(debt)
                require(debt["id"] not in debt_ids,
                        "WF105_PROPOSED_DEBT_REPEATED")
                debt_ids.add(debt["id"])
                debt_born_at[debt["id"]]=i
                promised.append({
                    "id":debt["id"],"kind":debt["kind"],
                    "owner":debt["owner"],
                    "pressure":debt["pressure"],
                    "if_ignored":debt["if_ignored"],
                    "severity":debt["severity"],
                    "due_after":debt["due_after"],
                    "future_event_id":s["id"],
                    "forecast_only":True})
            for claim in s["claims_resolved"]:
                require(ident(claim) and claim in debt_ids,
                        "WF105_CANNOT_RESOLVE_AN_UNCREATED_DEBT")
                # A plan cannot settle itself: proposed compensation is
                # not a real payment, even in a speculative future.
                claimed_resolutions.add(claim)
                this_issues.append({
                    "kind":"FUTURE_SETTLEMENT_ONLY_NOT_YET_PAID",
                    "step_id":s["id"],"debt_id":claim})
                if any(d["id"]==claim and d["severity"]=="IRREVERSIBLE"
                       for d in promised):
                    this_issues.append({
                        "kind":"IRREVERSIBLE_LOSS_NOT_ERASED_BY_COMPENSATION",
                        "step_id":s["id"],"debt_id":claim})
            concerns.extend(this_issues)
            traces.append({"step_id":s["id"],"preflight_findings":this_issues,
                           "future_debts_born":len(s["future_debts"])})
        for d in promised:
            due=debt_born_at[d["id"]]+d["due_after"]
            if due<=len(steps) and d["id"] not in claimed_resolutions:
                concerns.append({
                    "kind":"FUTURE_DUE_PRESSURE_UNADDRESSED",
                    "debt_id":d["id"],
                    "step_id":d["future_event_id"],"due_step":due})
        fatal=any(z["kind"] in
                  ("CONTRADICTS_PINNED_FACT",
                   "THREATENS_PREVIOUS_PLANNED_EFFECT")
                  for z in concerns)
        unknown=any(z["kind"] in
                    ("UNPROVEN_PRECONDITION",
                     "DEPENDS_ON_UNVERIFIED_PLANNED_EFFECT")
                    for z in concerns)
        result.append({
            "branch_id":name,
            "proposed_future_actions":[{
                "step_id":s["id"],"actor":s["actor"],"action":s["action"]}
                for s in steps],
            "status":("SYMBOLICALLY_BLOCKED" if fatal else
                      "CONDITIONAL_OR_UNKNOWN" if unknown else
                      "NOT_CONTRADICTED_BY_KNOWN_SYMBOLS"),
            "step_findings":traces,
            "all_findings":concerns,
            "forecast_debts":promised,
            "semantic_writing_feasibility_verified":False,
            "branch_winner":False,
        })
    report={
        "format":"wf.writing.future-causal-branches.v105",
        "proposed_futures_sha256":digest(packed(plan)),
        "pinned_author_facts_sha256":digest(packed(pinned)),
        "author_pinned_keys":sorted(pinned),
        "branches":result,"choice_selected_by_software":None,
        "all_proposed_future_effects_unverified":True,
        "future_debts_not_yet_paid_or_incurred":True,
        "model_calls_for_validation":0,
        "canonical_or_factjournal_writes":0,
        "literary_causality_proven":False,
    }
    report["receipt_sha256"]=digest(packed(report))
    return report

def horizon_prompt(*,pinned_world=None):
    """One small extra field in WF's EXISTING chapter planning model call."""
    pinned=_frozen_author_world(pinned_world or {})
    return (
        "\n【V105前瞻而非事后擦屁股：未来有条件的剧情选择】"
        "\n在一次现有章计划JSON里同时附加一个horizon字段；"
        "它必须是{choices:[{id,steps:[{id,actor,action,"
        "requires:[{key,is}],sets:[{key,becomes}],"
        "future_debts:[{id,kind,owner,pressure,due_after,if_ignored,severity}],"
        "claims_resolved:[debt_id]}]}]}。"
        "choices为2条不同可能未来，steps各1到4步。"
        "未来前提和变化要有可复核的资源/位置/时间/知识条件；"
        "key为英文小写和下划线，可用冒号如power:station。"
        "debt.kind仅RESOURCE/PROMISE/RELATIONSHIP/TIME/KNOWLEDGE/"
        "SAFETY/MONEY/LEGAL/OTHER；severity仅POSSIBLE/COSTLY/"
        "IRREVERSIBLE。due_after为1到12之间的后续场景跨度。"
        "必须思考行动使得以后的哪些选择做不到、谁承担什么压力。"
        "允许安静生活场景没有债务，不要强迫每幕牺牲/反转。"
        "只能把确证事实当规则：所有未核实值应在后续写作中"
        "标为假说或未知。提出A/B路径，不要替作者选定胜者。"
        "\n【仅作者授权的已知初始事实，模型不得偷偷扩充为已证事实】"
        +json.dumps(pinned,ensure_ascii=False,separators=(",",":"))
    )

def horizon_context(report,*,max_chars=1450):
    """No winners, no pseudo-truth. Keeps risky causal preconditions visible."""
    require(type(report) is dict and
            report.get("format")=="wf.writing.future-causal-branches.v105"
            and len(report.get("branches",[])) in (2,3) and
            report.get("receipt_sha256")==digest(packed({
                k:v for k,v in report.items() if k!="receipt_sha256"})),
            "WF105_CONTEXT_REQUIRES_VALIDATED_FORECAST")
    lines=["【未来是分支候选，不是已发生事实。请选择可执行的路径而不是硬拼结果】"]
    for opt in report["branches"]:
        lines.append(opt["branch_id"]+": "+opt["status"])
        for step in opt["proposed_future_actions"][:MAX_STEPS]:
            lines.append("未来只是假设："+step["actor"]+"可能"+
                         step["action"])
        for issue in opt["all_findings"][:5]:
            if issue["kind"]=="FUTURE_SETTLEMENT_ONLY_NOT_YET_PAID":
                lines.append("拟偿债务"+issue["debt_id"]+
                             "只是假设，不能宣称已兑现。")
            elif issue["kind"]=="IRREVERSIBLE_LOSS_NOT_ERASED_BY_COMPENSATION":
                lines.append("不可因补偿或道歉就抹去已发生的不可逆损失："+
                    issue["debt_id"]+"；后续必须承担真实余波。")
            elif issue["kind"]=="FUTURE_DUE_PRESSURE_UNADDRESSED":
                lines.append("预想期限已临近但尚无后续处理的候选债务"+
                    issue["debt_id"]+"；不能被安静遗忘。")
            else:
                lines.append(issue["kind"]+" "+issue["fact_key"]+
                    "要求"+issue["expected"]+"；当前"+
                    str(issue["known_or_projected"] or "未知"))
        for debt in opt["forecast_debts"][:4]:
            lines.append("未来风险（还未发生）"+debt["owner"]+"："+
                         debt["pressure"]+"；若不处理"+debt["if_ignored"])
    notice=("以上检查是符号条件与提示，不是人物的真实心理或"
            "情节文学评价；不得把预测当已证，允许写沉默、未决及意外。")
    raw="\n".join(lines)
    return raw[:max_chars-len(notice)-1]+"\n"+notice

def _validate_prior_checkpoint(old,story_sha):
    if old is None:return [],None
    require(type(old) is dict and
            old.get("format")=="wf.writing.candidate-debt-checkpoint.v105" and
            old.get("story_sha256")==story_sha and
            old.get("literary_semantics_verified") is False and
            old.get("auto_debt_settlements")==0 and
            old.get("canon_writes")==0,
            "WF105_PRIOR_CHECKPOINT_WRONG_STORY_OR_TRUTH")
    h=old.get("receipt_sha256")
    require(type(h) is str and SHA.fullmatch(h) is not None and
            h==digest(packed({k:v for k,v in old.items()
                             if k!="receipt_sha256"})) and
            type(old.get("open_debts")) is list and
            len(old["open_debts"])<=MAX_DEBTS and
            len(packed(old))<=MAX_CHECKPOINT_BYTES,
            "WF105_PRIOR_CHECKPOINT_HASH_OR_LIMIT")
    return list(old["open_debts"]),h

def derive_open_checkpoint(*,story_sha,chapter,accepted,previous=None):
    """Immutable candidate record from ACTUAL V102 prose receipts.

    Every previous debt remains OPEN. Even a next chapter saying 'I paid'
    cannot delete the loss; only an independently authorized review could
    create a later compensating event in the existing canonical system.
    """
    require(type(story_sha) is str and SHA.fullmatch(story_sha) is not None
            and type(chapter) is int and 1<=chapter<=10000000 and
            type(accepted) in (tuple,list) and 1<=len(accepted)<=16,
            "WF105_CHECKPOINT_SOURCE_OR_CHAPTER_INVALID")
    old,parent=_validate_prior_checkpoint(previous,story_sha)
    if previous is not None:
        require(chapter==previous["chapter"]+1,
                "WF105_CANDIDATE_CHAPTER_GAP_OR_REPLAY")
    known={item["debt_id"] for item in old}
    added=[]
    for turn in accepted:
        rec=v102_receipt(turn)
        if rec["affect_state"]!="QUOTED_EMOTIONAL_HYPOTHESIS":
            continue
        if rec["cost_anchor"] is None and rec["open_pressure"] is None:
            continue
        debt_id=f"d{chapter:06d}_{rec['turn_id']}"
        require(debt_id not in known and ident(debt_id),
                "WF105_REUSED_OR_DUPLICATE_DEBT_IN_HISTORY")
        known.add(debt_id)
        entry={
            "debt_id":debt_id,"source_chapter":chapter,
            "source_turn_id":rec["turn_id"],
            "actor":rec["actor"],
            "cost_anchor":rec["cost_anchor"],
            "source_prose_sha256":rec["prose_sha256"],
            "open_pressure":rec["open_pressure"],
            "state":"OPEN_UNVERIFIED_CANDIDATE",
            "claim_of_settlement_is_not_proof":True,
            "actual_cost_semantics_proven":False,
            "chronology_and_effect_requires_review":True,
        }
        added.append(entry)
    debts=old+added
    require(len(debts)<=MAX_DEBTS,
            "WF105_OPEN_DEBT_CAPACITY_REFUSE_SILENT_FORGET")
    result={
        "format":"wf.writing.candidate-debt-checkpoint.v105",
        "story_sha256":story_sha,"chapter":chapter,
        "previous_checkpoint_sha256":parent,
        "open_debts":debts,
        "new_debts":len(added),
        "open_debts_count":len(debts),
        "auto_debt_settlements":0,
        "no_silent_elision_or_undo":True,
        "irrevocable_events_not_reversed_by_prose":True,
        "literary_semantics_verified":False,
        "canon_writes":0,
        "model_calls":0,
    }
    require(len(packed(result))<=MAX_CHECKPOINT_BYTES,
            "WF105_CHECKPOINT_TOO_LARGE_REFUSE_SILENT_TRUNCATION")
    result["receipt_sha256"]=digest(packed(result))
    return result

def open_debt_context(checkpoint,*,max_chars=MAX_PRESSURE_CONTEXT_CHARS):
    require(type(checkpoint) is dict and
            type(checkpoint.get("story_sha256")) is str,
            "WF105_CONTEXT_CHECKPOINT_MISSING")
    _validate_prior_checkpoint(checkpoint,checkpoint["story_sha256"])
    need=checkpoint["open_debts"]
    buf=["【历史正文留下的候选债务（都未核实；不能因一句承诺自动清零）】"]
    limit=max(250,min(max_chars,MAX_PRESSURE_CONTEXT_CHARS))
    remaining=limit-160
    shown=0
    for debt in need[-14:]:
        s=f"{debt['debt_id']} {debt['actor']}：{debt['open_pressure'] or '代价尚未在正文中证实'}。"
        if len(s)>remaining:continue
        remaining-=len(s);shown+=1
        buf.append(s)
    if len(need)>shown:
        buf.append(f"还有{len(need)-shown}条未展示债务仍在完整不可变账本中，不可视为解决。")
    buf.append("如果未来承诺补偿，记作新行动的候选证据，而不是擦除历史损失。")
    return "\n".join(buf)[:limit]
