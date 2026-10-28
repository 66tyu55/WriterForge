"""Invisible, event-driven writing assistance over existing V25 verified source evidence.

Live author typing yields two OPTIONAL prose continuations, never an implicit
manuscript rewrite. Autonomous mode uses the outline and chapter goals to plan
and save generated chapters; acceptance remains the author's explicit choice.

Lexical intent is only an INTERNAL routing hint, never a verified literary
interpretation or an automatic upgrade of unreviewed encyclopedia entries.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from difflib import SequenceMatcher
from hashlib import sha256
from pathlib import Path
from datetime import datetime, timezone
import json
import re
import os

from .db import WriterForgeDB
from .r2_storage import (
    R2NarrativeMemoryStore,R2Config,R2StorageError,
)
from .encyclopedia import FictionEncyclopedia, FacetQuery
from .runtime import RuntimeEngine
from .prose_style import format_prose_reference
from .verified_flow import (
    VerifiedWritingFlow, GroundedDraftPacket, WritingExecutionError,
    local_chat_completion, save_candidate, MAX_PROMPT_CHARS,
)
from .v96_causal_turns import (
    V96CausalDraftError,parse_turn_outline,make_turn_instructions,
    check_turn,assemble_prose,receipts_only,canonical as causal_canonical,
    normalize_model_source_citations,review_only_model_turn,
    trace_failure_reviewable,
    MAX_PROSE_CHARS as _WF96_LEGACY_TURN_CHARS,
    CONTINUITY_MAX_PROSE_CHARS as _WF96_GUARDED_TURN_CHARS,
    CRAFT as _WF96_OPTIONAL_CRAFT,BEAT_FIELDS as _WF96_BEAT_FIELDS,
    MAX_PLAN_JSON_BYTES as _WF96_PLAN_BUDGET,
)
from .v98_rolling_causal_planner import (
    V98RollingPlanError,MAX_ROLLING_REPLANS_PER_JOB,
    prepare_replan_instructions,validate_replan,
    latest_source_basis_for_replan,author_signed_prior_prose_for_writer,
)
from .v102_emotional_causality import (
    V102EmotionalCausalityError,check_emotional_turn,
    pressure_context,emotion_turn_instructions,export_candidate_emotions,
)
from .v105_forward_horizon import (
    V105FutureCausalityError,validate_horizon,horizon_prompt,
    horizon_context,derive_open_checkpoint,open_debt_context,
    _frozen_author_world,_validate_prior_checkpoint,
)
from .v110_host_branch_identity import (
    V110IdentityError,recover_host_branch_identity,
)
from .v114_continuity_memory import (
    V114ContinuityError,validated_checkpoint,compact_status,
)
from .v114_external_story_state import (
    V114ExternalMemoryError,require_external_runtime,
    external_temporal_step,temporal_prompt,
)
from .v116_state_delta import preflight_next_prose
from .v117_continuity_trace import (
    audit_continuity,compact_context,preflight_continuation,
    make_resume,read_resume,ContinuityTraceError,
)
from .v118_lamp_scheduler import (
    plan_scene_lamps,LampDecisionError,MAX_CHARS as MAX_LAMP_CHARS,
)
from .v119_revision_transaction import (
    preview_revision as preview_surgical_revision,
    prepare_source_repair_contract,compare_source_repair_impact,
    RevisionTransactionError,
)
from .v120_plan_prose_gate import (
    compare_plan_to_prose, pending_dependency_hint, PlanExecutionError,
)
from .v123_long_arc import (
    verify_long_arc,read_long_arc_from_resume,relevant_revenge_hint,
    audit_revenge_prose,advance_open_revenge,LongArcError,
)
from .narrative_core import (
    new_graph as new_unified_narrative_graph,
    validate as verify_narrative_core,
    read_core_from_resume,
    schedule as schedule_narrative,
    audit_candidate as audit_narrative_candidate,
    advance_graph as advance_narrative_graph,
    NarrativeCoreError,
    record_chapter_memory,
    buffered_memory_context,
    character_collision_context,
    relevant_history_context,recall_original,
    detect_long_prose_replay,
    audit_scene_delivery,validate_scene_delivery_contract,
    propose_scene_delivery_debt,
)

MAX_LIVE_CONTEXT = 1400
MAX_OUTLINE_CHARS = 6000
MAX_CHAPTERS = 6
MAX_CHAPTER_GOAL = 450
MAX_PROSE_CHARS = 16000
FACET_COUNT = 4
MAX_STORED_AUTONOMOUS_RUNS = 32  # Do not silently grow candidate history forever.
MAX_SEGMENTED_CHAPTERS_PER_JOB = 2
MAX_SEGMENTED_TOTAL_TURNS = 16  # Provider calls bounded before first prose segment.


@dataclass(frozen=True)
class WritingIntent:
    category: str | None
    kind: str | None
    need: str
    rationale: str
    cue: str


def infer_intent(text: str) -> WritingIntent | None:
    """Conservative route. A single '山', '龙' or '雷' is NOT a full category."""
    if not isinstance(text,str) or not text.strip():
        return None
    tail=text[-270:]
    patterns=(
        (r"(?:性格|脾气|生性|性情).{0,20}(?:温柔|倔强|刚烈|冷清|清冷|暴躁|阴鸷|狠辣|傲慢|沉稳|谨慎|胆小|豪爽|孤僻|精明|坚韧|多疑|冷漠|柔弱)", "性格","character","character","通过选择和行动呈现人物性格"),
        (r"(?:温柔|倔强|刚烈|冷清|清冷|暴躁|阴鸷|狠辣|傲慢|沉稳|谨慎|胆小|豪爽|孤僻|精明|坚韧|多疑|冷漠|柔弱).{0,10}(?:女人|女子|姑娘|少年|男子|之人|性格|的她|的他)", "性格","character","character","不要直接给人物贴性格标签"),
        (r"(?:妖兽|凶兽|魔兽|灵兽|异兽).{0,32}(?:外貌|獠牙|鳞片|爪|尾|嘶吼|咆哮|出现|扑来|盯着|袭来|身形|体型|浑身|毛发|眼睛)", "外貌","creature","description","从实体动作及外貌产生威胁"),
        (r"(?:描写|形容|遇到|出现|走出|面前|眼前).{0,24}(?:妖兽|凶兽|魔兽|灵兽|异兽)", "生物","creature","description","只有核实过的妖兽属性可被当作来源"),
        (r"(?:天劫|雷劫|渡劫|劫雷)", "设定","event","description","天劫是事件规则，不是雷字就算"),
        (r"(?:榜单|天骄榜|风云榜|百强榜|排行榜|排名榜)", "设定","system","world","榜单需要排序规则与冲突用途"),
        (r"(?:秘境|洞府|遗迹|地宫|禁地).{0,32}(?:入口|走进|面前|里面|深处|出现|探查|开启|来到|抵达|通往)", "地点","place","description","环境必须影响角色的行动"),
    )
    matches=[]
    for pattern,category,kind,need,rationale in patterns:
        for match in re.finditer(pattern,tail):
            matches.append((match.end(),WritingIntent(category,kind,need,rationale,match.group(0)[-48:])))
    if matches:
        return max(matches,key=lambda item:item[0])[1]
    if len(tail.strip())>=110 and tail.rstrip().endswith(("。","！","？","\n")):
        return WritingIntent(None,None,"scene","完整段落已有叙事线索","段落结束")
    return None


def _verified_facets(db: WriterForgeDB, intent: WritingIntent | None) -> tuple[dict,...]:
    if intent is None or intent.category is None:
        return ()
    # V25 SQL enforces e.status=verified, original span location and source SHA.
    cards=FictionEncyclopedia(db).query(FacetQuery(
        category_path=intent.category,kind=intent.kind,
        status="verified",limit=16,
    ))["items"]
    if intent.kind=="creature":
        cards=[c for c in cards if c["subtype"] in ("妖兽","凶兽","灵兽","异兽","魔兽")]
    seen=set()
    result=[]
    for card in cards:
        identity=(card["entity_id"],card["category_path"],card["attribute"])
        if identity not in seen:
            seen.add(identity)
            result.append(card)
        if len(result)>=FACET_COUNT:
            break
    return tuple(result)


def _craft_needs(needs: tuple[str, ...]) -> tuple[str, ...]:
    """Map writing intentions into the ALREADY EXISTING CraftEngine triggers."""
    meanings = {
        "character": ("character_entrance", "relationship_pressure"),
        "world": ("scene", "setup_payoff"),
        "decision": ("interiority", "decision"),
        "action": ("scene", "detail_utility"),
        "scene": ("scene",),
    }
    values=[]
    for key in needs:
        for name in meanings.get(key,(key,)):
            if name not in values:
                values.append(name)
    return tuple(values[:4])


def _enrich(packet: GroundedDraftPacket, addition: str,
            facets: tuple[dict,...] = (), *,
            prose_task: bool = True) -> GroundedDraftPacket:
    context=packet.prompt
    # Move the human-approved prose reference AFTER facts, live manuscript
    # and chapter instructions; never feed style samples to JSON-only planning.
    tail=(format_prose_reference(packet.prose_reference_text)
          if packet.prose_reference_text else "")
    if tail and context.endswith(tail):
        context=context[:-len(tail)]
    if facets:
        context+="\n已由真实来源和审核状态确认的实体属性（只借鉴机制，不能复制原句）：\n"
        context+="\n".join(
            f"- {c['category_path']} / {c['attribute']}；"
            f"说明：{c['explanation'][:100] or '来源已复核但未给出机制解释'}；"
            f"出处：{c['work_id']} 第{c['chapter']}回；审核：verified"
            for c in facets
        )
    context+="\n"+addition
    if prose_task and tail:
        context+=tail
    if len(context)>MAX_PROMPT_CHARS:
        raise WritingExecutionError("assembled writing context exceeds size limit")
    return replace(
        packet,prompt=context,encyclopedia_refs=facets,
        prompt_sha256=sha256(context.encode("utf-8")).hexdigest(),
    )


def _decode_json(raw: str) -> dict:
    if not isinstance(raw,str) or len(raw)>32000:
        raise WritingExecutionError("missing or excessive model JSON")
    candidate=raw.strip()
    if candidate.startswith(chr(96)*3):
        candidate=re.sub("^"+chr(96)*3+r"(?:json)?\s*","",candidate,flags=re.I)
        candidate=re.sub(r"\s*"+chr(96)*3+"$","",candidate)
    try:
        value=json.loads(candidate)
    except ValueError:
        pos=candidate.find("{")
        if pos<0:
            raise WritingExecutionError("model returned no JSON object")
        try:
            value,_=json.JSONDecoder().raw_decode(candidate[pos:])
        except ValueError as exc:
            raise WritingExecutionError("model returned invalid JSON") from exc
    if not isinstance(value,dict):
        raise WritingExecutionError("model JSON must be an object")
    return value


def _two_options(raw: str, source_excerpts: tuple[str,...]) -> tuple[dict,dict]:
    values=_decode_json(raw).get("choices")
    if not isinstance(values,list) or len(values)!=2:
        raise WritingExecutionError("model must return exactly two choices")
    result=[]
    for candidate in values:
        if not isinstance(candidate,dict):
            raise WritingExecutionError("choice must be a JSON object")
        prose=candidate.get("text")
        title=candidate.get("title")
        if (not isinstance(prose,str) or not 25<=len(prose.strip())<=300
            or not isinstance(title,str) or not 1<=len(title.strip())<=22):
            raise WritingExecutionError("invalid prose length or title")
        prose=prose.strip()
        if any(
            fragment and len(fragment)>=25 and any(
                fragment[i:i+25] in prose for i in range(0,len(fragment)-24,5)
            ) for fragment in source_excerpts
        ):
            raise WritingExecutionError("model copied an original literary excerpt")
        result.append({"title":title.strip(),"text":prose})
    if (result[0]["text"]==result[1]["text"]
        or SequenceMatcher(None,result[0]["text"],result[1]["text"]).ratio()>.78):
        raise WritingExecutionError("model suggestions are too similar")
    return tuple(result)


class InvisibleWritingAssist:
    """No category selection, search form or manual Skill invocation."""

    def __init__(self,db:WriterForgeDB,rt:RuntimeEngine,project_id:str,
                 scene_id:str,goal:str,*,model:str,api_base:str,
                 source_genre:str="古代白话"):
        self.db,self.rt=db,rt
        self.project_id,self.scene_id,self.goal=project_id,scene_id,goal
        self.model,self.api_base=model,api_base
        self.source_genre=source_genre
        self.flow=VerifiedWritingFlow(db,rt,project_id)

    def suggest(self,manuscript:str) -> dict:
        if not isinstance(manuscript,str) or len(manuscript)>12000:
            raise WritingExecutionError("invalid or excessive manuscript input")
        intent=infer_intent(manuscript)
        if intent is None:
            return {"triggered":False,"choices":[],"reason":"没有需要中断写作的明确时机"}
        packet=self.flow.prepare(
            self.scene_id,self.goal,concerns=_craft_needs((intent.need,)),
            genre=self.source_genre,
        )
        facets=_verified_facets(self.db,intent)
        addition=(
            "\n【作者正在写的未接受稿，仅用于辅助】\n"
            +manuscript[-MAX_LIVE_CONTEXT:]
            +"\n【自动检测的内部写作方向】"+intent.need+"；"+intent.rationale+"。"
            "方向只是候选，不能凭关键词捏造原著设定。"
            "\n给出两种不同的、逻辑连续的原创后续文字，各55到140字："
            "第一种由细小动作呈现人物，第二种由人物选择产生新的关系或风险。"
            "不许照抄原著，不能改写作者已经写下的内容，"
            "不要出现套路化排比或解释文学技法。只返回JSON："
            '{"choices":[{"title":"细微动作","text":"..."},'
            '{"title":"人物选择","text":"..."}]}'
        )
        packet=_enrich(packet,addition,facets)
        raw=local_chat_completion(
            packet,model=self.model,api_base=self.api_base,max_tokens=700,
        )
        options=_two_options(raw,tuple(x["evidence_excerpt"] for x in packet.evidence))
        return {
            "triggered":True,"choices":list(options),
            "intent_hint":intent.category or "场景推进",
            "manual_search_required":False,"original_manuscript_unchanged":True,
            "snapshot_id":packet.snapshot_id,
            "source_references":len(packet.evidence),
            "verified_category_references":len(facets),
            "prompt_sha256":packet.prompt_sha256,
            "study_level":"verified_facets_only + unverified_structural_cues",
            "model_used":self.model,
        }


VALID_NEEDS=frozenset({
    "dialogue","description","character","action","decision","scene",
    "world","pacing","relationship_pressure","reversal","interiority",
})


def _normalize_optional_model_craft_labels(raw:str):
    """Remove ONLY unrecognized *optional* model craft tags, not story plan.

    A live model may put chapter 'needs' such as 'decision' in a beat's
    optional craft_focus. The original raw answer is retained separately.
    Dropping an unsupported optional tag must not discard valid plot,
    character, event order or causality; all other invalid schemas stay red.
    Frozen/author-supplied turn outlines are never normalized.
    """
    if type(raw) is not str or len(raw.encode("utf8"))>_WF96_PLAN_BUDGET:
        return raw,None
    def no_duplicate(items):
        out={}
        for key,value in items:
            if key in out:
                raise ValueError("duplicate JSON field")
            out[key]=value
        return out
    try:
        doc=json.loads(raw,object_pairs_hook=no_duplicate,
                       parse_constant=lambda _: (_ for _ in ()).throw(
                           ValueError("nonfinite JSON")))
    except (ValueError,TypeError,UnicodeError):
        return raw,None
    if (type(doc) is not dict or set(doc)!={"turns"} or
        type(doc["turns"]) is not list or
        not 2<=len(doc["turns"])<=12 or
        any(type(row) is not dict or set(row)!=_WF96_BEAT_FIELDS or
            type(row["craft_focus"]) is not list or
            len(row["craft_focus"])>2 or
            any(type(tag) is not str for tag in row["craft_focus"])
            for row in doc["turns"])):
        return raw,None
    removed=[]
    for row in doc["turns"]:
        tags=row["craft_focus"]
        cleaned=list(dict.fromkeys(
            tag for tag in tags if tag in _WF96_OPTIONAL_CRAFT))
        if cleaned!=tags:
            removed.append({"turn_id":row["id"],
                            "removed_optional_tags":[
                                tag for tag in tags
                                if tag not in _WF96_OPTIONAL_CRAFT]})
            row["craft_focus"]=cleaned
    if not removed:
        return raw,None
    normalized=json.dumps(doc,ensure_ascii=False,separators=(",",":"))
    if len(normalized.encode("utf8"))>_WF96_PLAN_BUDGET:
        return raw,None
    receipt={
        "format":"wf.writing.optional-model-craft-compatibility.v1",
        "original_model_plan_sha256":sha256(raw.encode("utf8")).hexdigest(),
        "normalized_plan_sha256":sha256(
            normalized.encode("utf8")).hexdigest(),
        "only_model_optional_craft_fields_adjusted":True,
        "events_or_goals_unchanged":True,
        "original_model_answer_must_be_preserved":True,
        "removed":removed,"prose_not_rewritten":True,
        "canon_writes":0,"model_calls":0,
    }
    return normalized,receipt


def _chapter_plan(raw:str,chapter_goal:str) -> dict:
    result=_decode_json(raw)
    fields=("objective","conflict","decision","outcome","pov")
    if any(not isinstance(result.get(k),str) or not 2<=len(result[k].strip())<=400
           for k in fields):
        raise WritingExecutionError("model did not generate a full chapter plan")
    needs=result.get("needs",[])
    if not isinstance(needs,list):
        raise WritingExecutionError("model plan needs must be an array")
    needs=tuple(dict.fromkeys(x for x in needs if isinstance(x,str) and x in VALID_NEEDS))[:3]
    if not needs:
        needs=("scene","description")
    return {**{k:result[k].strip() for k in fields},
            "needs":needs,"chapter_goal":chapter_goal,
            "literary_quality_verified":False}


def _save_unified_cold_capsule(root:Path,packet:dict) -> dict:
    """Private append-only local cold manifest; a future R2 adapter may
    provide the same path/hash proof without changing the narrative core.

    This does not overwrite the original candidate.md or erase earlier
    archive pages. Fail closed if any persisted bytes do not match.
    """
    from .narrative_core import _bytes
    raw=_bytes(packet)
    digest=sha256(raw).hexdigest()
    page_dir=Path(root)/".wf-unified-cold"
    page_dir.mkdir(parents=True,exist_ok=True)
    path=page_dir/(f"chapter-{packet['chapter_index']:06d}-"+
                   digest[:20]+".json")
    if path.exists():
        if path.read_bytes()!=raw:
            raise WritingExecutionError(
                "WFCORE_COLD_ARCHIVE_IMMUTABLE_FILE_CONFLICT")
    else:
        try:
            with path.open("xb") as output:
                output.write(raw)
                output.flush()
                os.fsync(output.fileno())
        except FileExistsError:
            if path.read_bytes()!=raw:
                raise WritingExecutionError(
                    "WFCORE_COLD_ARCHIVE_RACE_CONFLICT") from None
    return {"path":str(path),"sha256":digest}


def g_writer_active_plan_view(plan):
    """Copy old chapter intent without replaying its stale action/outcome.

    G+V98 already lets the actual writer choose a next turn from observed
    prose. Keep the original file and the writer's objective, conflict, POV,
    craft needs and chapter goal unchanged; only stop presenting the OLD
    chapter decision and presumed outcome as instructions for every later
    segment. No host supplies a replacement decision or literary summary.
    """
    if type(plan) is not dict or any(
            key not in plan for key in
            ("objective","conflict","decision","outcome","pov","needs",
             "chapter_goal","literary_quality_verified")):
        raise WritingExecutionError("WF_G_AUTHOR_PLAN_VIEW_CONTRACT_INVALID")
    return {key:value for key,value in plan.items()
            if key not in ("decision","outcome")}


def _source_progression_literary_cue(accepted_turns):
    """Optional writer *craft* cue, not a source-state or canon instruction.

    Triggered after real preceding prose exists. Avoid replaying the same
    preparation beats; keep the character's right to stall, err or refuse.
    Neither a genre-specific punchline template nor a compulsory twist.
    """
    if not accepted_turns:
        return ""
    return (
        "\n【后续正文的创作推进（可选择，不是剧情硬命令）】"
        "前一段已经发生的动作、误会和应对不需要原样重演。"
        "站在此刻人物真实所知、所欲与必须付出的代价上，"
        "让本段给上一段带来新的反馈：行动后果、对方的新反应、"
        "关系变化，或一个有实际代价的克制与延迟。"
        "同一计谋／道具若再次出现，须产生新的意义，不只重复解释用法。"
        "人物对他人用意的推断只能是其判断，未见证的结果不要当旁白事实。"
        "仍可安静、失败、改变原计划；不能为了制造反转而强行结案。"
    )


def _prepare_guarded_turn_packet(
        body_base:GroundedDraftPacket,*,plan:dict,
        hard_turn_addition:str,facets:tuple[dict,...],
        dependency_hint:str,project_id:str,chapter_index:int,
        turn_index:int,beat:dict,frame:dict|None,
        previous_lamp_receipt:dict|None,
        narrative_graph:dict|None=None,
        narrative_scene_id:str|None=None,
        working_memory_context:str="",
        creative_progression_cue:str=""):
    """V121: source/causal constraints have priority over optional cues.

    A speculative chapter plan may be dropped if it crowds out actual prior
    state. The V120 direct dependency hint and V118 lamps are optional.
    Never trim source constraints, silently claim a cue was sent, or move a
    dropped craft cue into the next turn's cooldown history.
    """
    lane=None
    if narrative_graph is not None:
        lane=schedule_narrative(
            narrative_graph,project_id=project_id,
            scene_id=(narrative_scene_id or body_base.scene_id),
            beat=beat,chapter_index=chapter_index)
        if lane["required_context"]:
            hard_turn_addition+="\n"+lane["required_context"]
    hard="\n【本章当前事件】"+hard_turn_addition
    # If even the source/causal constraints cannot fit, fail BEFORE
    # any LLM call; never quietly shorten their contents.
    hard_packet=_enrich(body_base,hard,facets)
    if not isinstance(working_memory_context,str) or len(
            working_memory_context)>1800:
        raise WritingExecutionError("WFCORE_WORKING_MEMORY_CONTEXT_INVALID")
    if (type(creative_progression_cue) is not str or
            len(creative_progression_cue)>850):
        raise WritingExecutionError(
            "WF_LITERARY_OPTIONAL_PROGRESSION_CUE_INVALID")
    memory_suffix=("\n"+working_memory_context
                   if working_memory_context else "")
    memory_reserve=(len(memory_suffix)
                    if len(memory_suffix)<=MAX_PROMPT_CHARS-len(
                        hard_packet.prompt) else 0)
    plan_part="\n【原创章计划】"+json.dumps(plan,ensure_ascii=False)
    with_plan=plan_part+hard
    plan_delivered=False
    if len(plan_part)+memory_reserve<=MAX_PROMPT_CHARS-len(
            hard_packet.prompt):
        # Plan is only proposed intent. It is lower-priority than hard state.
        core_packet=_enrich(body_base,with_plan,facets)
        core_addition=with_plan
        plan_delivered=True
    else:
        core_packet=hard_packet
        core_addition=hard
    space=MAX_PROMPT_CHARS-len(core_packet.prompt)
    memory_delivered=False
    used_memory=""
    if memory_suffix and len(memory_suffix)<=space:
        used_memory=memory_suffix
        space-=len(used_memory)
        memory_delivered=True
    dep_delivered=False
    used_debt=""
    if dependency_hint and len(dependency_hint)<=space:
        used_debt=dependency_hint
        space-=len(used_debt)
        dep_delivered=True
    # A new literary prompt must NEVER enlarge the old dependency string:
    # otherwise its extra chars can evict the EXISTING causal hint.
    used_progression=""
    progression_delivered=False
    if (creative_progression_cue and
            len(creative_progression_cue)<=space):
        used_progression=creative_progression_cue
        space-=len(used_progression)
        progression_delivered=True
    # Lamp text carries an added newline when present. Leave one character
    # for that newline; zero available characters yields a zero-lamp receipt.
    lamp_budget=min(MAX_LAMP_CHARS,max(0,space-1))
    lamps=plan_scene_lamps(
        project_id=project_id,chapter_index=chapter_index,
        turn_index=turn_index,beat=beat,frame=frame,
        previous=previous_lamp_receipt,max_prompt_chars=lamp_budget)
    lamp_suffix=("\n"+lamps["prompt"]) if lamps["prompt"] else ""
    delivered_addition=(core_addition+used_memory+used_debt+
                        used_progression+lamp_suffix)
    final=_enrich(body_base,delivered_addition,facets)
    if not (len(final.prompt)<=MAX_PROMPT_CHARS and
            hard_turn_addition in final.prompt):
        raise WritingExecutionError(
            "WF121_REQUIRED_CONTINUITY_CONTEXT_WAS_DROPPED")
    receipt={
        "format":"wf.writing.v121.prompt-delivery",
        "project_id":project_id,
        "chapter_index":chapter_index,
        "turn_index":turn_index,
        "hard_context_sha256":sha256(
            hard_turn_addition.encode("utf8")).hexdigest(),
        "minimum_prompt_sha256":hard_packet.prompt_sha256,
        "delivered_prompt_sha256":final.prompt_sha256,
        "hard_context_preserved":True,
        "hard_characters":len(hard_packet.prompt),
        "delivered_characters":len(final.prompt),
        "prompt_cap":MAX_PROMPT_CHARS,
        "provisional_plan_included":plan_delivered,
        "provisional_plan_dropped_due_to_budget":not plan_delivered,
        "unproven_dependency_hint_eligible":bool(dependency_hint),
        "unproven_dependency_hint_delivered":dep_delivered,
        "creative_progression_cue_eligible":bool(creative_progression_cue),
        "creative_progression_cue_delivered":progression_delivered,
        "creative_progression_cue_characters":len(used_progression),
        "working_memory_context_delivered":memory_delivered,
        "working_memory_context_chars":len(used_memory),
        "working_memory_not_canon":True,
        "lamp_prompt_delivered":bool(lamps["prompt"]),
        "lamp_prompt_characters":lamps["prompt_chars"],
        "lamp_dropped_risks":lamps["budget_suppressed_risks"],
        "lamp_dropped_craft":lamps["budget_suppressed_craft"],
        "unified_narrative_priority_dispatch":lane,
        "priority_lanes_ordered":["HARD_STATE","NPC_KNOWLEDGE",
                                  "CHARACTER_INTENT","LONG_THREAD","CRAFT"],
        "no_model_call_for_prompt_scheduling":True,
        "no_canon_promotion":True,
    }
    receipt["receipt_sha256"]=sha256(
        causal_canonical(receipt)).hexdigest()
    return final,lamps,receipt



def _writing_scene_scope(base_scene,*,local_index,resume_source_chapter=None):
    """Use the *actual* story chapter when a one-chapter run resumes.

    Historical segmented runs labeled every resumed chapter as local 001
    even while V117/unified graph correctly advanced 002/003/004. The
    prompt's scene id thus repeated chapter-001 and could invite replay.
    Fix this label only; never infer narrative facts or update Canon.
    """
    if (type(base_scene) is not str or not base_scene or
        type(local_index) is not int or not 1<=local_index<=6 or
        (resume_source_chapter is not None and
         (type(resume_source_chapter) is not int or
          not 0<=resume_source_chapter<=1000000))):
        raise WritingExecutionError("WFCORE_SCENE_CHAPTER_SCOPE_INVALID")
    absolute=(local_index if resume_source_chapter is None
              else resume_source_chapter+local_index)
    if absolute>1000000:
        raise WritingExecutionError("WFCORE_SCENE_CHAPTER_OVERFLOW")
    return f"{base_scene}.chapter-{absolute:03d}"


SELF_EDIT_SCOPES={"sentence":180,"paragraph":650,"scene":1800}
SELF_EDIT_MAX_PER_TURN=2
SELF_EDIT_MAX_PROVIDER_CALLS_PER_RUN=8
SELF_EDIT_MODEL_MAX_TOKENS=1800



SELF_EDIT_MOMENT_TOKENS=600


def _rewind_unaccepted_turn_suffix(*,accepted,source_sha256,snapshots,tracked):
    """Restore a pre-turn snapshot, never a deleted draft's derived state.

    Only the immediately preceding UNACCEPTED event turn is eligible. All
    V96/V114/V117/unified provisional side-receipts after its boundary are
    truncated together. Caller must replay the AI-revised source through
    the ordinary validation/reducer path and write a NEW downstream turn.
    This does not touch signed earlier chapters, Canon or the story graph.
    """
    if (not accepted or type(source_sha256) is not str or
        len(snapshots)!=len(accepted)+1):
        raise WritingExecutionError("WF_WRITER_REWIND_INVALID_BOUNDARY")
    prose=accepted[-1].get("prose")
    if (type(prose) is not str or
        sha256(prose.strip().encode("utf8")).hexdigest()!=source_sha256):
        raise WritingExecutionError("WF_WRITER_REWIND_STALE_SOURCE")
    boundary=snapshots[-2]
    counts=boundary.get("counts")
    if (type(counts) is not tuple or len(counts)!=len(tracked) or
        any(type(n) is not int or n<0 or n>len(items)
            for items,n in zip(tracked,counts))):
        raise WritingExecutionError("WF_WRITER_REWIND_SNAPSHOT_INVALID")
    for items,n in zip(tracked,counts):
        del items[n:]
    del snapshots[-2:]
    return boundary


def _capture_unaccepted_turn_restore(*,tracked,snapshots):
    """Freeze the pre-CURRENT-turn candidate, not a second story memory.

    Snapshot existing G/V114/V117 provisional receipts so a failed edited
    previous-turn branch can restore the last *fully observed* source. The
    current original response is retained separately by its caller.
    """
    if not snapshots or type(snapshots) is not list:
        raise WritingExecutionError("WF_WRITER_ATOMIC_SNAPSHOT_MISSING")
    boundary=snapshots[-1]
    counts=boundary.get("counts")
    if (type(counts) is not tuple or len(counts)!=len(tracked) or
        any(type(n) is not int or n<0 or n>len(seq)
            for n,seq in zip(counts,tracked))):
        raise WritingExecutionError("WF_WRITER_ATOMIC_SNAPSHOT_INVALID")
    return {
        "boundary":boundary,
        "state_prefixes":tuple(tuple(seq[:n]) for seq,n in
                               zip(tracked,counts)),
        "prior_snapshots":tuple(snapshots[:-1]),
    }


def _restore_unaccepted_turn_capture(*,capture,tracked,snapshots):
    """Undo *all* transient descendants before retrying ORIGINAL bytes."""
    if (type(capture) is not dict or
        set(capture)!={"boundary","state_prefixes","prior_snapshots"} or
        type(capture["state_prefixes"]) is not tuple or
        len(capture["state_prefixes"])!=len(tracked) or
        type(capture["prior_snapshots"]) is not tuple or
        any(type(seq) is not list for seq in tracked) or
        type(snapshots) is not list):
        raise WritingExecutionError("WF_WRITER_ATOMIC_RESTORE_INVALID")
    for seq,old in zip(tracked,capture["state_prefixes"]):
        seq[:]=list(old)
    snapshots[:]=list(capture["prior_snapshots"])
    return capture["boundary"]



def _physical_relation_source_hold(*,prose,preflight):
    """Source-scoped candidate HOLD, not a host-written literary correction.

    A signed V114/V122 or a direct V116 candidate can expose two mutually
    unreconciled physical claims; their referents and literary intent remain
    uncertain. Only dependent continuation is held. The writer chooses
    whether to clarify, separate items/ends, delete, or preserve mystery.
    """
    if (type(prose) is not str or type(preflight) is not dict or
        preflight.get("next_prose_sha256")!=
            sha256(prose.encode("utf8")).hexdigest()):
        raise WritingExecutionError(
            "WF122_RELATION_HOLD_WRONG_SOURCE_SHA")
    pairs=preflight.get("physical_relation_review_pairs",[])
    descendants=preflight.get(
        "physical_relation_dependent_on_previous_source",[])
    if (type(pairs) is not list or len(pairs)>8 or
        type(descendants) is not list or len(descendants)>8):
        raise WritingExecutionError("WF122_RELATION_HOLD_EVIDENCE_BOUNDS")
    if not (pairs or descendants):
        return None
    for item in pairs:
        for prefix in ("first","second"):
            quote=item.get(prefix+"_source_quote")
            start=item.get(prefix+"_source_start")
            digest=item.get(prefix+"_source_quote_sha256")
            if (type(quote) is not str or type(start) is not int or
                not 6<=len(quote)<=160 or
                prose[start:start+len(quote)]!=quote or
                digest!=sha256(quote.encode("utf8")).hexdigest()):
                raise WritingExecutionError(
                    "WF122_RELATION_HOLD_UNVERIFIED_ORIGINAL_QUOTE")
    for item in descendants:
        quote=item.get("current_source_quote")
        start=item.get("current_source_start")
        if (type(quote) is not str or type(start) is not int or
            not 6<=len(quote)<=160 or
            prose[start:start+len(quote)]!=quote or
            item.get("current_source_quote_sha256")!=
                sha256(quote.encode("utf8")).hexdigest()):
            raise WritingExecutionError(
                "WF122_RELATION_HOLD_UNVERIFIED_DEPENDENT_QUOTE")
    info={
        "format":"wf.writer.source-relation-private-hold.v1",
        "prose_sha256":sha256(prose.encode("utf8")).hexdigest(),
        "v122_relation_receipt_sha256":preflight.get(
            "physical_relation_receipt_sha256"),
        "current_conflicting_source_quote_pairs":pairs,
        "downstream_claims_relying_on_unverified_prior_relation":descendants,
        "status":"HELD_NEEDS_SOURCE_RELATION_REVIEW",
        "literary_ellipsis_and_physical_state_are_separate":True,
        "actor_unknown_may_remain_literary_mystery":True,
        "item_identity_or_free_end_is_not_assumed":True,
        "source_sha_and_exact_quotes_required_before_downstream":True,
        "original_prose_kept_private_not_promoted":True,
        "writer_owns_edit_and_literary_choice":True,
        "safe_author_options":[
            "KEEP_MYSTERY_BUT_EXPLAIN_WHICH_RELATION_REMAINS",
            "LOCALLY_REVISE_AUTHOR_CHOSEN_EXACT_SPAN_USING_V119",
            "DISTINGUISH_DIFFERENT_OBJECT_OR_FREE_END_IF_TRUE_IN_STORY",
            "DELETE_UNSUPPORTED_RELATION_CLAIM_WITH_VALIDATED_DEPENDENCIES",
        ],
        "downstream_relation_dependent_scene_must_not_reuse_old_state":True,
        "new_model_calls":0,"R2_writes":0,"canon_writes":0,
        "automatic_author_decision_or_fiction_generation":False,
    }
    info["receipt_sha256"]=sha256(json.dumps(
        info,ensure_ascii=False,sort_keys=True,
        separators=(",",":")).encode("utf8")).hexdigest()
    return info


def _source_only_writer_replay_index(prose:str,*,cast:tuple[str,...]) -> dict:
    """Enumerate literal scene units, NEVER diagnose their literary meaning.

    Reuses the actual model-written prose as the only source of evidence.
    Offsets, quoted bytes and literal character mentions are mechanical.
    It intentionally does NOT infer locations, injuries, motivations, errors,
    scene outcomes or needed edits. One temporary read-only prompt aid;
    never a parallel story memory, Canon, or a grade/revision trigger.
    """
    if (type(prose) is not str or not 1<=len(prose)<=16000 or
        type(cast) is not tuple or not 1<=len(cast)<=10 or
        any(type(name) is not str or not 1<=len(name)<=70
            for name in cast) or len(set(cast))!=len(cast)):
        raise WritingExecutionError("WF_WRITER_SOURCE_INDEX_INPUT_INVALID")
    chunks=[]
    start=0
    for i,ch in enumerate(prose):
        if i<start or ch not in "。！？\n":
            continue
        end=i+1
        if ch!="\n" and end<len(prose) and prose[end] in "”’":
            end+=1
        chunk=prose[start:end]
        if chunk:
            chunks.append({
                "start":start,"end":end,"source_quote":chunk,
                "explicit_names":[name for name in cast if name in chunk],
            })
        start=end
    if start<len(prose):
        chunks.append({
            "start":start,"end":len(prose),"source_quote":prose[start:],
            "explicit_names":[name for name in cast if name in prose[start:]],
        })
    if "".join(row["source_quote"] for row in chunks)!=prose:
        raise WritingExecutionError("WF_WRITER_SOURCE_INDEX_NOT_LOSSLESS")
    raw=json.dumps(chunks,ensure_ascii=False,sort_keys=True,
                   separators=(",",":"))
    if len(chunks)>120 or len(raw)>21000:
        raise WritingExecutionError("WF_WRITER_SOURCE_INDEX_TOO_LARGE")
    # No semantic cells or auto-corrections: this aid is wholly derived
    # from the unchanged original source.
    index={
        "format":"wf.writer.literal-source-replay-index.v1",
        "source_sha256":sha256(prose.encode("utf8")).hexdigest(),
        "units":chunks,
        "any_source_beyond_original":False,
        "character_mentions_literal_only":True,
        "literary_error_found_by_host":False,
        "literary_quality_verified":False,
        "auto_revision_requested":False,
        "canon_writes":0,
    }
    index["receipt_sha256"]=sha256(json.dumps(
        index,ensure_ascii=False,sort_keys=True,
        separators=(",",":")).encode("utf8")).hexdigest()
    return index




SELF_EDIT_READER_MAX_TOKENS=1000
SELF_EDIT_READER_MAX_SOURCE_CHARS=5000


def _reader_separates_written_and_inferred(*,raw,turn_packet,ask_model,
                                           directory,cancel_check=None,
                                           earlier_source=None,
                                           earlier_source_sha256=None,
                                           compact_source_review=False):
    """Separate AI-as-unbiased-reader from AI-as-novelist on real prose.

    The SAME author model is asked once, in a NEW context with manuscript
    ONLY. No chapter outline, earlier model approval, previous editor's
    verdict, or automatic 'plot-hole' list appears in this request.

    The reader supplies source-anchored observations and hypotheses about
    UNWRITTEN transitions. Only literal quotes are verified by host code;
    the literary/semantic interpretation is always unproven. The original
    reply remains immutable in the private job before parsing.
    """
    if (type(raw) is not str or not callable(ask_model) or
        not isinstance(directory,Path) or
        type(compact_source_review) is not bool):
        raise WritingExecutionError("WF_READER_SOURCE_BOUNDARY_INVALID")
    try:
        doc=_decode_json(raw)
        if (set(doc)!={"prose","trace"} or
            type(doc["prose"]) is not str or
            not 80<=len(doc["prose"].strip())<=
                SELF_EDIT_READER_MAX_SOURCE_CHARS):
            raise ValueError("WF_READER_NOT_COMPLETE_PROSE")
        prose=doc["prose"].strip()
    except (WritingExecutionError,ValueError,KeyError,TypeError):
        return {"model_calls":0,"status":"NO_COMPLETE_SOURCE",
                "report":None,"receipt":{
                    "status":"NO_COMPLETE_SOURCE","model_calls":0,
                    "literary_quality_verified":False,
                    "canon_writes":0}}
    source_sha=sha256(prose.encode("utf8")).hexdigest()
    if (earlier_source is None)!=(earlier_source_sha256 is None):
        raise WritingExecutionError("WF_READER_EARLIER_SOURCE_INCOMPLETE")
    if earlier_source is not None:
        if (type(earlier_source) is not str or
            not 1<=len(earlier_source)<=5000 or
            type(earlier_source_sha256) is not str or
            sha256(earlier_source.encode("utf8")).hexdigest()!=
                earlier_source_sha256):
            raise WritingExecutionError(
                "WF_READER_EARLIER_SOURCE_HASH_OR_BOUNDS")
    max_observed,max_inferred,max_cross=(
        (3,1,1) if compact_source_review else (8,3,3))
    observed_cn=("三" if compact_source_review else "八")
    inferred_cn=("一" if compact_source_review else "三")
    # This request purposefully does NOT include turn_packet.prompt, plan,
    # system-made craft or last writer's justification. Source-only view.
    prompt=(
        "【独立读者视角·仅依据已经写出来的小说】"
        "你现在作为第一次读到这段小说的读者阅读。"
        "不要假装记得任何作者构思或过去自己对作品的肯定。"
        "不要润色、续写、下文学分数或替作者决定删稿。"
        f"先写出最多{observed_cn}处你确实从原文字面读到的动作，"
        "每一处附上唯一真实原文引句；"
        "如你为了理解人物行动或位置必须自行补充文字没有明写"
        f"的转换，请最多列出{inferred_cn}处可能的推测，并用前后两条"
        "真实原句解释依据。没有就返回空数组。"
        "省略动作可能是合理的小说技法，你不负责判断作品好坏。"
        "严格区分“原句确实写出来”与“我作为读者补出的推测”。"
        "只返回严格 JSON 对象，恰好三个键："
        "observed、inferred_links、reader_uncertainty。"
        f"observed 是列表（可空，最多{max_observed}个），每项恰好含"
        "quote、actor、visible_action 三项。"
        "quote 是字面唯一出现的6至160字原文连续子串，"
        "actor 是原文人物或叙述主体（1至40字），"
        "visible_action 是4至160字的读者描述，并不是证实事件。"
        f"inferred_links 是列表（可空，最多{max_inferred}个），每项恰好含"
        "before_quote、after_quote、reader_imagined_step 三项。"
        "before_quote 与 after_quote 必须分别来自前后不同位置，"
        "都是原文唯一出现的6至160字子串；"
        "reader_imagined_step 是6至180字的推测，不可冒充已写事实。"
        "reader_uncertainty 是一句不超过260字的未证读者感受"
        "（没有问题时也可填“没有明显未写连接”）。"
        "\n【当前唯一实际原文，无大纲也无作者自评】"+prose
    )
    if compact_source_review:
        prompt+=(
            "\n【紧凑读源，不是新审稿模型】"
            "只选最重要的原句、必要推测，不凑满数组。"
            "visible_action 与 reader_imagined_step 分别尽量不超过45字。"
            "一句话说明尚不确定处；不写正文，不强迫作者删改。")
    if earlier_source is not None:
        prompt+=(
            "\n【按真实创作顺序更早写出的紧邻前史原文】"
            +earlier_source+
            "\n请同时比较前史与当前正文。前史不是情节计划，"
            "里面未发生的角色行为也不许凭你想象当作已写事实。"
            "可以指出跨这两份文本需要读者自行补足的物件转移、"
            "人物认知、时间或动作等变化，但不要替作者决定是否有错。"
            f"此时 JSON 必须多一个 cross_source_links 键（可空，最多{max_cross}项），"
            "每一项恰好有 previous_quote、current_quote、"
            "reader_imagined_step，previous_quote 必须唯一存在于前史，"
            "current_quote 必须唯一存在于当前，均为6到160字连续原句，"
            "reader_imagined_step 是6到180字未证推测。"
            "原先 observed 与 inferred_links 仍只引用当前原文。")
    if len(prompt)>MAX_PROMPT_CHARS:
        return {"model_calls":0,"status":"SOURCE_EXCEEDS_READER_BUDGET",
                "report":None,"receipt":{
                    "status":"SOURCE_EXCEEDS_READER_BUDGET","model_calls":0,
                    "literary_quality_verified":False,"canon_writes":0}}
    packet=replace(turn_packet,prompt=prompt,
                   prompt_sha256=sha256(prompt.encode("utf8")).hexdigest())
    if cancel_check is not None:
        cancel_check()
    response=ask_model(packet,model=None,api_base=None,
                       max_tokens=SELF_EDIT_READER_MAX_TOKENS)
    directory.mkdir(parents=True,exist_ok=False)
    (directory/"original-reader-reply.json").write_text(
        response,encoding="utf8")
    if cancel_check is not None:
        cancel_check()
    status="INVALID_READER_SOURCE"
    report=None
    code=None
    try:
        reply=_fork_strict_json(response,max_bytes=19000)
        keys={"observed","inferred_links","reader_uncertainty"}
        if earlier_source is not None:
            keys=keys|{"cross_source_links"}
        if set(reply)==keys|{"type"} and reply["type"]=="json_object":
            reply={key:val for key,val in reply.items() if key!="type"}
        if (set(reply)!=keys or type(reply["observed"]) is not list or
            type(reply["inferred_links"]) is not list or
            len(reply["observed"])>max_observed or
            len(reply["inferred_links"])>max_inferred or
            (earlier_source is not None and (
                type(reply["cross_source_links"]) is not list or
                len(reply["cross_source_links"])>max_cross)) or
            type(reply["reader_uncertainty"]) is not str or
            len(reply["reader_uncertainty"])>260):
            raise WritingExecutionError("WF_READER_SCHEMA_INVALID")
        anchored=[]
        for item in reply["observed"]:
            if (type(item) is not dict or
                set(item)!={"quote","actor","visible_action"} or
                type(item["actor"]) is not str or
                not 1<=len(item["actor"])<=40 or
                type(item["visible_action"]) is not str or
                not 4<=len(item["visible_action"])<=160):
                raise WritingExecutionError("WF_READER_OBSERVATION_SCHEMA")
            quote=item["quote"]
            if type(quote) is not str or not 6<=len(quote)<=160 or (
                prose.count(quote)!=1):
                raise WritingExecutionError("WF_READER_OBSERVATION_QUOTE")
            anchored.append({
                **item,"literal_source_offset":prose.index(quote),
                "visible_action_is_model_interpretation":True})
        gaps=[]
        for item in reply["inferred_links"]:
            if (type(item) is not dict or
                set(item)!={"before_quote","after_quote",
                             "reader_imagined_step"} or
                type(item["reader_imagined_step"]) is not str or
                not 6<=len(item["reader_imagined_step"])<=180):
                raise WritingExecutionError("WF_READER_GAP_SCHEMA")
            before,after=item["before_quote"],item["after_quote"]
            if (any(type(q) is not str or not 6<=len(q)<=160
                    or prose.count(q)!=1 for q in (before,after)) or
                prose.index(before)+len(before)>prose.index(after)):
                raise WritingExecutionError("WF_READER_GAP_SOURCE_ORDER")
            gaps.append({
                **item,
                "first_source_offset":prose.index(before),
                "second_source_offset":prose.index(after),
                "imagined_step_is_not_story_fact":True})
        cross_links=[]
        if earlier_source is not None:
            for item in reply["cross_source_links"]:
                if (type(item) is not dict or
                    set(item)!={"previous_quote","current_quote",
                                 "reader_imagined_step"} or
                    type(item["reader_imagined_step"]) is not str or
                    not 6<=len(item["reader_imagined_step"])<=180):
                    raise WritingExecutionError(
                        "WF_READER_CROSS_SOURCE_SCHEMA")
                previous_quote=item["previous_quote"]
                current_quote=item["current_quote"]
                if (any(type(q) is not str or not 6<=len(q)<=160
                        for q in (previous_quote,current_quote)) or
                    earlier_source.count(previous_quote)!=1 or
                    prose.count(current_quote)!=1):
                    raise WritingExecutionError(
                        "WF_READER_CROSS_SOURCE_QUOTE_NOT_EXACT")
                cross_links.append({
                    **item,
                    "earlier_original_source_offset":
                        earlier_source.index(previous_quote),
                    "current_source_offset":prose.index(current_quote),
                    "inference_not_an_accepted_change":True})
        report={
            "source_sha256":source_sha,
            "earlier_source_sha256":earlier_source_sha256,
            "observed":anchored,"inferred_links":gaps,
            "cross_source_links":cross_links,
            "reader_uncertainty":reply["reader_uncertainty"],
            "all_semantics_are_model_generated_not_verified":True,
            "no_host_literary_error_decision":True,
        }
        status="SOURCE_ANCHORED_READER_HYPOTHESES"
    except (WritingExecutionError,ValueError,TypeError,KeyError) as error:
        code=str(error)[:160]
    receipt={
        "format":"wf.writer.reader-source-before-self-judgment.v1",
        "status":status,"source_sha256":source_sha,
        "raw_reader_reply_sha256":sha256(response.encode("utf8")).hexdigest(),
        "model_calls":1,"compact_source_review":compact_source_review,
        "max_observations":max_observed,
        "max_inferred_links":max_inferred,
        "max_cross_source_links":max_cross,
        "observed_count":(
            len(report["observed"]) if report is not None else 0),
        "hypothesized_gap_count":(
            len(report["inferred_links"]) if report is not None else 0),
        "cross_source_inference_count":(
            len(report["cross_source_links"]) if report is not None else 0),
        "earlier_original_sha256":earlier_source_sha256,
        "reason_code":code if code and code.startswith("WF_") else None,
        "source_verification_not_semantic_judgment":True,
        "no_auto_edit_if_reader_guesses_a_gap":True,
        "no_author_canon_writes":True,"literary_quality_verified":False,
        "canon_writes":0,
    }
    (directory/"reader-source-receipt.json").write_text(
        json.dumps(receipt,ensure_ascii=False,sort_keys=True,indent=2),
        encoding="utf8")
    return {"model_calls":1,"status":status,"report":report,
            "receipt":receipt}


def _reader_report_for_author(report,source_sha):
    """Read-only reader perspective, never a host direction to fix fiction."""
    if (report is None or type(report) is not dict or
        report.get("source_sha256")!=source_sha or
        report.get("all_semantics_are_model_generated_not_verified") is not True or
        report.get("no_host_literary_error_decision") is not True):
        return ""
    payload=json.dumps({
        "observed":report["observed"],
        "reader_inferred_links":report["inferred_links"],
        "reader_cross_source_links":report.get("cross_source_links",[]),
        "literal_earlier_source_sha256":report.get("earlier_source_sha256"),
        "reader_uncertainty":report["reader_uncertainty"],
        "all_reader_inferences_unverified":True,
        "author_can_choose_to_leave_story_as_is":True,
    },ensure_ascii=False,separators=(",",":"))
    if len(payload)>6200:
        return ""
    return (
        "\n【由同一写作模型在独立读者视角提出的未证实阅读意见】"
        "下列报告不是正文事实，不是 WF 找出的错误，更不是强制修改要求。"
        "逐字来源位置仅证明原句真实出现；对动作遗漏的推测仍待你取舍。"
        "请你作为原作者自行决定 MOVE_ON 或 LOOK_BACK_NOW，"
        "可以认为文学省略有意义而保留；"
        "但请分清哪些过渡已明写、哪些只是读者自己想象补足。"
        +payload)



SELF_EDIT_ATTRIBUTION_TOKENS=1150


def _validate_author_prior_source_claims(*,reader_report,earlier_source,
                                         current_source,claims):
    """A prose-source citation contract, NOT validation of what happened.

    The SAME writing AI reports its interpretation of each reader question.
    All the host can prove is that a cited quote occurs in the SHA-matched
    original chapter. A quote alone NEVER proves transfer, causality or
    literary quality. Missing/bad attributions do not rewrite the author's
    independently valid KEEP decision; they become reviewable source debt.
    """
    if (type(reader_report) is not dict or
        type(earlier_source) is not str or
        not 1<=len(earlier_source)<=5000 or
        type(current_source) is not str or
        reader_report.get("earlier_source_sha256")!=sha256(
            earlier_source.encode("utf8")).hexdigest() or
        reader_report.get("source_sha256")!=sha256(
            current_source.encode("utf8")).hexdigest() or
        reader_report.get("all_semantics_are_model_generated_not_verified")
            is not True or
        reader_report.get("no_host_literary_error_decision") is not True):
        raise WritingExecutionError(
            "WF_AUTHOR_PRIOR_SOURCE_ATTRIBUTION_MISMATCH")
    links=reader_report.get("cross_source_links")
    if (type(links) is not list or
        not 1<=len(links)<=3):
        raise WritingExecutionError(
            "WF_AUTHOR_PRIOR_SOURCE_LINKS_MISSING")
    for link in links:
        if (type(link) is not dict or
            type(link.get("previous_quote")) is not str or
            type(link.get("current_quote")) is not str or
            earlier_source.count(link["previous_quote"])!=1 or
            current_source.count(link["current_quote"])!=1):
            raise WritingExecutionError(
                "WF_AUTHOR_PRIOR_SOURCE_QUOTE_UNTRUSTED")
    receipt={
        "format":"wf.writer.prior-source-claim-attribution.v1",
        "status":"MISSING_SOURCE_ATTRIBUTIONS",
        "earlier_source_sha256":reader_report["earlier_source_sha256"],
        "current_source_sha256":reader_report["source_sha256"],
        "reader_link_count":len(links),
        "attributions":[],
        "claimed_written_links":0,
        "prior_state_only_citations_needing_review":0,
        "author_declared_unwritten_or_unknown_links":0,
        "author_declared_intentional_ellipsis_links":0,
        "author_prose_edit_forced":False,
        "quoted_text_identity_only_not_event_proof":True,
        "all_literary_meanings_still_unverified":True,
        "source_claims_not_promoted_to_canon":True,
        "model_calls_for_validation":0,
    }
    if claims is None:
        return receipt
    if type(claims) is not list or len(claims)!=len(links):
        receipt["status"]="MALFORMED_SOURCE_ATTRIBUTIONS"
        return receipt
    results=[]
    kinds={"WRITTEN_WITH_QUOTE","UNWRITTEN_OR_UNKNOWN",
           "INTENTIONAL_ELLIPSIS"}
    for position,(item,link) in enumerate(zip(claims,links)):
        if (type(item) is not dict or
            set(item)!={"link_index","basis","prior_transition_quote",
                       "literary_reason"} or
            type(item["link_index"]) is not int or
            item["link_index"]!=position or
            type(item["basis"]) is not str or
            item["basis"] not in kinds or
            type(item["literary_reason"]) is not str or
            not 8<=len(item["literary_reason"])<=220):
            receipt["status"]="MALFORMED_SOURCE_ATTRIBUTIONS"
            return receipt
        quote=item["prior_transition_quote"]
        record={
            "link_index":position,
            "model_selected_basis":item["basis"],
            "model_reason_sha256":sha256(
                item["literary_reason"].encode("utf8")).hexdigest(),
            "source_excerpt_mechanically_verified":False,
            "model_semantic_transition_never_automatically_verified":True,
            "fiction_event_state_changed":False,
            "canonical_fact_created":False,
        }
        if item["basis"]=="WRITTEN_WITH_QUOTE":
            if (type(quote) is not str or
                not 6<=len(quote)<=160 or
                earlier_source.count(quote)!=1):
                receipt["status"]="UNSUPPORTED_WRITTEN_SOURCE_QUOTE"
                receipt["attributions"]=results+[record]
                return receipt
            loc=earlier_source.index(quote)
            # Quoting the questioned state itself does not prove a MOVE
            # between two states. We can test this overlap mechanically,
            # but must NOT decide what the sentence means.
            state=link["previous_quote"]
            state_start=earlier_source.index(state)
            record.update({
                "source_excerpt_mechanically_verified":True,
                "prior_quote_sha256":sha256(
                    quote.encode("utf8")).hexdigest(),
                "prior_quote_offset":loc,
                "quote_overlaps_questioned_prior_state":not (
                    loc+len(quote)<=state_start or
                    loc>=state_start+len(state)),
                "literal_quote_is_not_proof_of_claimed_transition":True,
            })
            receipt["claimed_written_links"]+=1
            if record["quote_overlaps_questioned_prior_state"]:
                receipt["prior_state_only_citations_needing_review"]+=1
        else:
            if quote is not None:
                receipt["status"]="UNWRITTEN_BASIS_CANNOT_CITE_TRANSFER"
                receipt["attributions"]=results+[record]
                return receipt
            record["prior_transition_quote_is_null"]=True
            if item["basis"]=="UNWRITTEN_OR_UNKNOWN":
                receipt["author_declared_unwritten_or_unknown_links"]+=1
            else:
                receipt["author_declared_intentional_ellipsis_links"]+=1
        results.append(record)
    receipt["status"]=(
        "PRIOR_STATE_QUOTE_NOT_TRANSFER_PROOF"
        if receipt["prior_state_only_citations_needing_review"]
        else "SOURCE_ATTRIBUTIONS_RECORDED_LITERAL_ONLY")
    receipt["attributions"]=results
    receipt["original_manuscript_unchanged_by_source_audit"]=True
    return receipt



def _signed_previous_author_source_question(checkpoint,accepted):
    """One original-source unresolved question for the SAME author to assess.

    This is a projection of the EXISTING signed V114/V122 checkpoint, not
    a new memory, a host writing critic or a mandatory revision. Previous
    literal quotations and their source SHA remain evidence; their object
    identities and any unmentioned return remain UNPROVEN.
    """
    if checkpoint is None:
        return "",None
    from .v114_continuity_memory import packed,hashb
    from .v122_item_provenance import _digest as document_digest
    def valid(value,code):
        if not value:
            raise WritingExecutionError(code)
    valid(type(checkpoint) is dict and
          checkpoint.get("format")==
              "wf.writing.external-temporal-checkpoint.v114" and
          checkpoint.get("receipt_sha256")==hashb(packed({
              k:v for k,v in checkpoint.items() if k!="receipt_sha256"})) and
          checkpoint.get("semantic_truth_verified") is False and
          checkpoint.get("canon_writes")==0,
          "WF_WRITER_REVIEW_OLD_SOURCE_CHECKPOINT_NOT_SIGNED")
    if accepted:
        previous=accepted[-1]
        valid(type(previous) is dict and
              type(previous.get("prose")) is str and
              checkpoint.get("source_sha256")==sha256(
                  previous["prose"].encode("utf8")).hexdigest(),
              "WF_WRITER_REVIEW_OLD_SOURCE_NOT_PREVIOUS_TURN")
    source=checkpoint.get("v122_physical_relation_source_receipt")
    if source is None:
        return "",None
    valid(type(source) is dict and
          source.get("format")==
              "wf.v122.source-physical-relation-review.v1" and
          source.get("source_sha256")==checkpoint["source_sha256"] and
          source.get("receipt_sha256")==document_digest({
              k:v for k,v in source.items() if k!="receipt_sha256"}),
          "WF_WRITER_REVIEW_OLD_V122_SOURCE_NOT_SIGNED")
    rows=source.get("document_custody_open_source_reviews",[])
    valid(type(rows) is list and len(rows)<=8,
          "WF_WRITER_REVIEW_PRIOR_SOURCE_DEBT_NOT_BOUNDED")
    if not rows:
        return "",None
    pair=rows[-1]
    valid(type(pair) is dict and
          pair.get("literary_error_proven") is False and
          pair.get("omitted_return_or_distinct_copy_may_explain") is True and
          all(type(pair.get(k)) is str and pair[k] for k in (
              "earlier_source_quote","later_source_quote",
              "earlier_source_quote_sha256","later_source_quote_sha256",
              "earlier_source_sha256","later_source_sha256")) and
          len(pair["earlier_source_quote"])<=150 and
          len(pair["later_source_quote"])<=150 and
          all(pair[k+"_source_quote_sha256"]==sha256(
              pair[k+"_source_quote"].encode("utf8")).hexdigest()
              for k in ("earlier","later")),
          "WF_WRITER_REVIEW_PRIOR_SOURCE_DEBT_QUOTE_NOT_VERIFIED")
    # No host-authored transition, interpretation, literary score, or
    # automatic preference for revision. Only actual two original quotes.
    note=(
        "\n【已签名的前文来源疑问（不是小说错误结论）】"
        "在先前真实正文中曾出现「"+
        pair["earlier_source_quote"]+"」，另有一处正文写「"+
        pair["later_source_quote"]+"」。"
        "工作台只能证明两句存在，不能证明它们指同一个物件；"
        "可能是另一本、合理留白、尚未写出的归还，"
        "也可能需要作者自己改写。"
        "请由你作为原作者判断它是否影响当前或紧邻前一段的"
        "人物行为与阅读理解，也可以明确选择不改。"
        "切勿仅为通过审查强行补一段交接，更不能把推断冒充已写事实。"
    )
    return note,source["receipt_sha256"]


def _ai_decides_when_to_revisit(*,raw,beat,accepted,turn_packet,
                                ask_model,directory,cancel_check=None,
                                source_checkpoint=None,
                                reader_report=None,
                                source_identity_contract="model_sha",
                                earlier_source_for_attribution=None):
    """Ask the ACTUAL author model whether THIS visible draft needs revision.

    The code schedules a chance to reflect after an observable story turn.
    ONLY the model chooses MOVE_ON vs LOOK_BACK_NOW and WHY. No Python
    keyword/taste scoring or auto-delete decisions. A model assertion of
    dissatisfaction is a private, source-bounded hypothesis, never a
    literary PASS or permission to change Canon.
    """
    if (source_identity_contract not in ("model_sha","bind_null_current") or
        type(source_identity_contract) is not str):
        raise WritingExecutionError(
            "WF_AI_WRITER_SOURCE_IDENTITY_MODE_INVALID")
    if not callable(ask_model) or not isinstance(directory,Path):
        raise WritingExecutionError("WF_AI_WRITER_MOMENT_INPUT_INVALID")
    try:
        doc=_decode_json(raw)
        prose=doc["prose"].strip()
        if (set(doc)!={"prose","trace"} or type(doc["prose"]) is not str
            or not 80<=len(prose)<=_WF96_GUARDED_TURN_CHARS):
            raise ValueError("UNSAFE_INITIAL_DRAFT")
    except (WritingExecutionError,ValueError,KeyError,TypeError,
            AttributeError):
        return {"decision":"NO_SOURCE_FOR_REVIEW","model_calls":0,
                "reason":None,"risk":None,"desired_effect":None,
                "receipt":{"decision":"NO_SOURCE_FOR_REVIEW",
                           "literary_quality_verified":False,
                           "model_calls":0}}
    original_sha=sha256(prose.encode("utf8")).hexdigest()
    preceding=(accepted[-1] if accepted else None)
    preceding_prose=(preceding.get("prose","").strip()
                     if type(preceding) is dict else "")
    if not 80<=len(preceding_prose)<=_WF96_GUARDED_TURN_CHARS:
        preceding_prose=""
    preceding_sha=(sha256(preceding_prose.encode("utf8")).hexdigest()
                   if preceding_prose else None)
    seen_effects=[(x.get("effect_quote") or "")[:110]
                  for x in accepted[-2:]]
    reminder=(
        "\n【AI 作家自己决定此刻要不要回头写】"
        "下面是你刚刚真正写出来的文字，而不是小说大纲。"
        "你也可以检查紧邻上一段尚未被作者接受的真实原文。"
        "你是本篇小说的作者，不是替人类点按钮的程序评分器。"
        "只判断此刻应该继续创作，还是需要先回头修稿。"
        "可以为了节奏、人物性格或真实留白选择不改。"
        "若某个局部使后续人物动机、信息获取、时间、情绪、"
        "读者认知或者独特叙述感觉不成立，可以选择 LOOK_BACK_NOW。"
        "不能为了凑修改次数强迫反转或堆词。"
        "若最重要的问题是缺少必要的铺垫或结果，"
        "evidence_quote 可为 null，focus 必须为 scene；"
        "其它情况 evidence_quote 必须是目前原文中唯一出现的逐字原句。"
        "只用自己对本小说当前效果的简短文学判断，"
        "不输出隐藏推理过程或数字评分。"
        "这是【写后选择】，不是再写正文；不要返回 prose/trace 或重复小说。"
        "你可选择 target_turn=current（刚写的段）或 previous（紧邻上一段）；"
        "只有确实存在上一段原文时才可选择 previous。"
        "选择 previous 并修订成功时，后面尚未接受的草稿和其派生状态"
        "必须作废，由你依据新原文重新创作。"
        "\n返回严格 JSON 对象，字段必须且只能为："
        "decision(MOVE_ON 或 LOOK_BACK_NOW)、target_turn、"
        "source_sha256（所选目标原文的 SHA）、evidence_quote、focus、why_now、"
        "what_goes_wrong_if_unchanged、intended_reader_effect。"
        "MOVE_ON 时 evidence_quote/focus/what_goes_wrong_if_unchanged/"
        "intended_reader_effect 一律为 null，但 why_now 应说明为何此刻保留。"
        "LOOK_BACK_NOW 时 focus 只能是 sentence、paragraph 或 scene，"
        "其余三个理由字段必须是 8-260 字的中文自然语言，"
        "不允许给出编辑后的正文；真正改稿是随后独立一步。"
        "\n【过去已写出而非计划的后果】"
        +json.dumps(seen_effects,ensure_ascii=False)+
        "\n【当前人物与事件意图（可以质疑）】"
        +json.dumps(beat,ensure_ascii=False,separators=(",",":"))+
        "\n【上一段实际未接受的小说原文及 SHA；无则为 null】"+
        json.dumps({"prose":preceding_prose,"sha256":preceding_sha}
                   if preceding_sha else None,ensure_ascii=False)+
        "\n【当前实际未接受的小说原文】"+prose+
        "\n【当前原文字节身份】"+original_sha
    )
    # This is an INDEPENDENT model task, not another prose-generation
    # request. The previous G turn_packet contains an authoritative-looking
    # instruction to emit {"prose","trace"}. Concatenating it ahead of this
    # review request caused REAL DeepSeek replies to emit a second novel
    # paragraph instead of a MOVE_ON/LOOK_BACK_NOW decision (0.AQ: 4/6).
    # Reusing only actual immutable previous/current prose, their SHAs,
    # recorded source effects and frozen beat keeps review grounded while
    # preventing the two mutually exclusive JSON schemas competing.
    # The writer still chooses ALL literary reasons and whether to revise.
    # No host authoring, scoring, fact promotion or retry.
    review_stage_header=(
        "【WriterForge 独立写后审稿阶段 / ONLY_REVIEW_DECISION】"
        "上一条小说生成指令已经结束，绝不可继续输出小说正文、"
        "prose/trace 或新的章节计划。你是刚写完文字的同一位作者。"
        "当前任务只需根据下方逐字原稿自行选择 MOVE_ON 或 "
        "LOOK_BACK_NOW，后者只是提出回改意向，不在本条修改文字。"
        "没有外部文学分数或强制回改目标。"
        "\n【审稿来源安全边界】只有下方实际写出的当前段、"
        "紧邻上段、它们的 SHA 和已有引句可用作具体来源。"
        "未知人物心理、后果、物品归属仍是未知。"
        "曾经出现的创作任务大纲不是已发生事实，"
        "也不是本条要执行的 JSON 格式。"
    )
    content=review_stage_header+reminder
    source_note,source_note_sha=_signed_previous_author_source_question(
        source_checkpoint,accepted)
    if source_note and len(content)+len(source_note)<=MAX_PROMPT_CHARS:
        content+=source_note
        verified_source_note_delivered=True
    else:
        verified_source_note_delivered=False
    # An explicitly requested SAME-SOURCE literal reread must survive
    # task separation. Pass ONLY its existing, SHA-verified sentence index:
    # do not resurrect the prose-writing instructions that surrounded it.
    literal_source_index_passed=False
    index_marker="\n【同一稿件逐句原文来源目录】"
    if index_marker in turn_packet.prompt:
        raw_index=turn_packet.prompt.rsplit(index_marker,1)[1].strip()
        try:
            if len(raw_index)>22000:
                raise ValueError("index size")
            def no_dupe_index(items):
                result={}
                for k,v in items:
                    if k in result:
                        raise ValueError("duplicate source index field")
                    result[k]=v
                return result
            index=json.loads(raw_index,object_pairs_hook=no_dupe_index)
            keys={"format","source_sha256","units",
                  "any_source_beyond_original",
                  "character_mentions_literal_only",
                  "literary_error_found_by_host",
                  "literary_quality_verified","auto_revision_requested",
                  "canon_writes","receipt_sha256"}
            if (type(index) is not dict or set(index)!=keys or
                index["format"]!="wf.writer.literal-source-replay-index.v1" or
                index["source_sha256"]!=original_sha or
                index["any_source_beyond_original"] is not False or
                index["character_mentions_literal_only"] is not True or
                any(index[k] is not False for k in (
                    "literary_error_found_by_host",
                    "literary_quality_verified","auto_revision_requested")) or
                index["canon_writes"]!=0 or
                index["receipt_sha256"]!=sha256(json.dumps(
                    {k:v for k,v in index.items() if k!="receipt_sha256"},
                    ensure_ascii=False,sort_keys=True,
                    separators=(",",":")).encode("utf8")).hexdigest() or
                type(index["units"]) is not list or
                not 1<=len(index["units"])<=120):
                raise ValueError("index schema/source")
            cursor=0
            for unit in index["units"]:
                if (type(unit) is not dict or
                    set(unit)!={"start","end","source_quote","explicit_names"} or
                    type(unit["start"]) is not int or
                    type(unit["end"]) is not int or
                    unit["start"]!=cursor or
                    not cursor<unit["end"]<=len(prose) or
                    type(unit["source_quote"]) is not str or
                    prose[cursor:unit["end"]]!=unit["source_quote"] or
                    type(unit["explicit_names"]) is not list or
                    len(unit["explicit_names"])>10 or
                    any(type(n) is not str or not 1<=len(n)<=70 or
                        n not in unit["source_quote"]
                        for n in unit["explicit_names"])):
                    raise ValueError("source offsets altered")
                cursor=unit["end"]
            if cursor!=len(prose):
                raise ValueError("source not completely indexed")
        except (ValueError,TypeError,KeyError,UnicodeError):
            # The workbench must not pass guessed or forged provenance to
            # the novelist merely to get a green review response.
            raise WritingExecutionError(
                "WF_AI_WRITER_LITERAL_REVIEW_INDEX_SOURCE_INVALID") from None
        content+=index_marker+raw_index
        literal_source_index_passed=True
    if source_identity_contract=="bind_null_current":
        content+=(
            "\n【来源 SHA 为宿主机械字段，并非文学判断】"
            "如果本次只审阅 target_turn=current，"
            "source_sha256 可以返回 JSON null；"
            "工作台只会把 null 绑定到刚才实际提供的当前原文 SHA，"
            "绝不修正你主动提交的错误 SHA 或更改任何文学决定。"
            "若选择 previous，则必须提供前段真实来源 SHA。")
    reader_note=_reader_report_for_author(reader_report,original_sha)
    attribution_possible=(
        earlier_source_for_attribution is not None and
        type(reader_report) is dict and
        type(reader_report.get("cross_source_links")) is list and
        bool(reader_report["cross_source_links"]))
    if earlier_source_for_attribution is not None:
        if not attribution_possible:
            raise WritingExecutionError(
                "WF_AUTHOR_PRIOR_SOURCE_ATTRIBUTION_NOT_READY")
        # Fail BEFORE provider call if G did not supply the actual source
        # corresponding to the reader's SHA-verified citation report.
        _validate_author_prior_source_claims(
            reader_report=reader_report,
            earlier_source=earlier_source_for_attribution,
            current_source=prose,claims=None)
    reader_provided=False
    if reader_note and len(content)+len(reader_note)<=MAX_PROMPT_CHARS:
        # Hard story-state context ALWAYS outranks optional reader notes.
        content+=reader_note
        reader_provided=True
    cross_source_unproven_count=(
        len(reader_report.get("cross_source_links",[]))
        if reader_provided and type(reader_report) is dict and
        type(reader_report.get("cross_source_links",[])) is list else 0)
    attribution_requested=False
    if attribution_possible and reader_provided:
        instruction=(
            "\n【原作者对读者前后已写原文的来源归因，非自动文学裁决】"
            "以下是已核验字节身份的更早已写文本，"
            "它可能是紧邻上一段，也可能是 V117 签名的前章；"
            "它不是故事计划："+
            earlier_source_for_attribution+
            "\n请你对 reader_cross_source_links 中的每一项"
            "另填 source_attributions 数组（严格按0开始的 link_index 顺序）。"
            "每项必须恰好包含 link_index、basis、prior_transition_quote、"
            "literary_reason 四字段。"
            "basis 三选一："
            "WRITTEN_WITH_QUOTE（你认为更早原文确实写出了所说的转换）、"
            "UNWRITTEN_OR_UNKNOWN（原文没有明写或你无法确定）、"
            "INTENTIONAL_ELLIPSIS（你有意让读者自行补足的文学留白）。"
            "WRITTEN_WITH_QUOTE 时，prior_transition_quote 必须是"
            "更早原文中唯一出现、6至160字的确切过渡原句；"
            "不可仅复述它原先的持有状态来冒充实际转移。"
            "另外两类必须设 prior_transition_quote=null。"
            "literary_reason 必须是8至220字的你本人真实文学说明。"
            "你仍可 MOVE_ON；无证据就不能说前文已经明写转换。"
            "宿主只检查引句字面出现，不会替你判断它在语义上"
            "是否真的证明了那个动作，也不因此强迫改稿。"
        )
        if len(content)+len(instruction)<=MAX_PROMPT_CHARS:
            content+=instruction
            attribution_requested=True
    if len(content)>MAX_PROMPT_CHARS:
        return {"decision":"CONTEXT_TOO_FULL","model_calls":0,
                "reason":None,"risk":None,"desired_effect":None,
                "receipt":{"decision":"CONTEXT_TOO_FULL","model_calls":0,
                           "literary_quality_verified":False,
                           "writer_was_not_asked":True}}
    pkt=replace(turn_packet,prompt=content,
                prompt_sha256=sha256(content.encode("utf8")).hexdigest())
    if cancel_check is not None:
        cancel_check()
    response=ask_model(pkt,model=None,api_base=None,
                       max_tokens=(SELF_EDIT_ATTRIBUTION_TOKENS
                                   if attribution_requested
                                   else SELF_EDIT_MOMENT_TOKENS))
    directory.mkdir(parents=True,exist_ok=True)
    (directory/"ai-when-and-why-original.json").write_text(
        response,encoding="utf8")
    if cancel_check is not None:
        cancel_check()
    receipt={
        "format":"wf.writer.ai-owns-self-review-timing.v1",
        "model_calls":1,"original_prose_sha256":original_sha,
        "original_decision_sha256":sha256(
            response.encode("utf8")).hexdigest(),
        "only_ai_can_choose_revisit":True,
        "review_prompt_stage_isolated_from_prose_generation":True,
        "review_prompt_sha256":sha256(content.encode("utf8")).hexdigest(),
        "review_writer_source_prose_unchanged":True,
        "review_writer_not_forced_to_revise":True,
        "literal_source_reread_index_verified":literal_source_index_passed,
        "signed_prior_document_source_question_delivered":verified_source_note_delivered,
        "signed_prior_document_question_receipt_sha256":(
            source_note_sha if verified_source_note_delivered else None),
        "no_host_mandated_revision_from_source_question":True,
        "source_identity_contract":source_identity_contract,
        "earlier_author_source_attribution_requested":attribution_requested,
        "source_sha256_original_model_value_not_changed":True,
        "unverified_reader_input_delivered":reader_provided,
        "cross_source_reader_hypotheses_unverified_count":
            cross_source_unproven_count,
        "reader_hypotheses_not_source_facts":True,
        "reader_did_not_preselect_literary_decision":True,
        "code_has_not_scored_literary_quality":True,
        "no_canon_writes":True,
        "literary_quality_verified":False,
    }
    answer={"decision":"INVALID_SIGNAL","model_calls":1,
            "reason":None,"risk":None,"desired_effect":None,
            "receipt":receipt}
    try:
        if type(response) is not str or len(response.encode("utf8"))>14000:
            raise ValueError("WF_AI_WRITER_SIGNAL_TOO_BIG")
        def reject_duplicates(pairs):
            doc={}
            for k,v in pairs:
                if k in doc:
                    raise ValueError("WF_AI_WRITER_SIGNAL_DUPLICATE_FIELD")
                doc[k]=v
            return doc
        fields=json.loads(response,object_pairs_hook=reject_duplicates)
        keys={
            "decision","source_sha256","evidence_quote","focus",
            "why_now","what_goes_wrong_if_unchanged",
            "intended_reader_effect"}
        # Old real answers have no target_turn. Keep their exact schema
        # compatible; new author decisions can explicitly choose previous.
        target_keys=keys|{"target_turn"}
        claim_present=(
            type(fields) is dict and
            "source_attributions" in fields)
        if attribution_requested and claim_present:
            # Remove only the optional provenance array from the literary
            # decision envelope. It is judged independently below;
            # malformed SOURCE evidence cannot secretly change MOVE_ON.
            literal_claims=fields["source_attributions"]
            fields={k:v for k,v in fields.items()
                    if k!="source_attributions"}
        else:
            literal_claims=None
        # Observed REAL DeepSeek returned the correct author decision
        # with ONE harmless envelope marker: "type":"json_object".
        # Strip only that literal wrapper, not actual source/reason text;
        # malformed prose echoes must remain invalid model signals.
        wrapper_only_removed=False
        if (type(fields) is dict and
            set(fields) in (keys|{"type"},target_keys|{"type"}) and
            fields.get("type")=="json_object"):
            fields={k:v for k,v in fields.items() if k!="type"}
            wrapper_only_removed=True
        if type(fields) is not dict or set(fields) not in (keys,target_keys):
            raise ValueError("WF_AI_WRITER_SIGNAL_SCHEMA_OR_SOURCE")
        target_turn=fields.get("target_turn","current")
        if (target_turn not in ("current","previous") or
            (target_turn=="previous" and not preceding_sha) or
            (target_turn=="previous" and fields["decision"]=="MOVE_ON")):
            raise ValueError("WF_AI_WRITER_INVALID_LOOKBACK_TARGET")
        target_prose=(preceding_prose if target_turn=="previous" else prose)
        target_sha=(preceding_sha if target_turn=="previous" else original_sha)
        # The genuine new-scene DeepSeek reader-first answer chose MOVE_ON
        # but returned source_sha256:null. In explicitly opted-in mode only,
        # bind this ABSENT mechanical identity to the CURRENT source that
        # the host had already supplied with exact SHA. This never changes
        # a model's choice, source quote, reasoning, fiction or original wire.
        # Non-null mismatches and null PREVIOUS-turn targets fail closed.
        bound_null_current=(
            source_identity_contract=="bind_null_current" and
            target_turn=="current" and
            fields["source_sha256"] is None)
        source_claim=(target_sha if bound_null_current
                      else fields["source_sha256"])
        if (fields["decision"] not in ("MOVE_ON","LOOK_BACK_NOW") or
            source_claim!=target_sha or
            type(fields["why_now"]) is not str or
            not 8<=len(fields["why_now"])<=260):
            raise ValueError("WF_AI_WRITER_SIGNAL_SCHEMA_OR_SOURCE")
        if fields["decision"]=="MOVE_ON":
            if any(fields[x] is not None for x in (
                 "evidence_quote","focus",
                 "what_goes_wrong_if_unchanged",
                 "intended_reader_effect")):
                raise ValueError("WF_AI_WRITER_MOVE_ON_HAS_EDIT_FIELDS")
        else:
            if fields["focus"] not in ("sentence","paragraph","scene"):
                raise ValueError("WF_AI_WRITER_SIGNAL_FOCUS")
            quote=fields["evidence_quote"]
            if (quote is None and fields["focus"]!="scene"):
                raise ValueError("WF_AI_WRITER_UNGROUNDED_LOCAL_QUOTE")
            if quote is not None and (
                type(quote) is not str or not 6<=len(quote)<=160 or
                target_prose.count(quote)!=1):
                raise ValueError("WF_AI_WRITER_QUOTE_NOT_UNIQUE_IN_PROSE")
            for name in ("what_goes_wrong_if_unchanged",
                         "intended_reader_effect"):
                if (type(fields[name]) is not str or
                    not 8<=len(fields[name])<=260):
                    raise ValueError("WF_AI_WRITER_WHY_OR_EFFECT_MISSING")
        if attribution_requested:
            attribution_receipt=_validate_author_prior_source_claims(
                reader_report=reader_report,
                earlier_source=earlier_source_for_attribution,
                current_source=prose,claims=literal_claims)
            attribution_receipt["author_literary_decision_unchanged"]=True
            receipt["cross_source_author_attribution"]=attribution_receipt
            receipt["cross_source_author_attribution_status"]=(
                attribution_receipt["status"])
        receipt.update({
            "decision":fields["decision"],
            "author_kept_unresolved_cross_source_hypotheses":(
                fields["decision"]=="MOVE_ON" and
                cross_source_unproven_count>0),
            "cross_source_reader_review_did_not_confirm_fact":True,
            "format_wrapper_type_only_removed":wrapper_only_removed,
            "target_turn":target_turn,
            "target_prose_sha256":target_sha,
            "null_source_sha256_bound_from_current_source":bound_null_current,
            "model_original_source_sha256_was_null":(
                fields["source_sha256"] is None),
            "model_supplied_nonmatching_sha_never_repaired":True,
            "focus":fields["focus"],
            "has_exact_model_quote":fields["evidence_quote"] is not None,
            "quoted_prose_sha256":(
                sha256(fields["evidence_quote"].encode("utf8")).hexdigest()
                if fields["evidence_quote"] is not None else None),
            "why_now_sha256":sha256(
                fields["why_now"].encode("utf8")).hexdigest(),
        })
        answer.update({
            "decision":fields["decision"],
            "target_turn":target_turn,
            "target_prose_sha256":target_sha,
            "reason":fields["why_now"],
            "risk":fields["what_goes_wrong_if_unchanged"],
            "desired_effect":fields["intended_reader_effect"],
            "source_quote":fields["evidence_quote"],
            "focus":fields["focus"],
        })
    except (ValueError,TypeError,KeyError) as error:
        why=str(error)
        receipt.update({
            "decision":"INVALID_SIGNAL",
            "failure_code":(why if why.startswith("WF_AI_WRITER_")
                            else "WF_AI_WRITER_SIGNAL_PARSE_INVALID"),
        })
    return answer



def _ask_same_writer_for_source_trace_only(
        *,candidate_prose,invalid_trace,failure_code,beat,accepted,
        turn_packet,ask_model,directory,cancel_check=None):
    """One bounded SOURCE CITATION repair on already model-written fiction.

    DO NOT let metadata issues trigger another whole-prose generation loop.
    The same author may re-attribute its OWN unchanged candidate's action
    and consequence; the host never writes either prose or trace values.
    Caller must re-run V96/V114/V117 and decline the candidate if invalid.
    """
    if (type(candidate_prose) is not str or
        not 80<=len(candidate_prose)<=_WF96_GUARDED_TURN_CHARS or
        type(invalid_trace) is not dict or
        set(invalid_trace)!={"action_quote","effect_quote",
                             "parent_effect_quote"} or
        type(failure_code) is not str or not failure_code.startswith("WF96_") or
        type(beat) is not dict or
        not callable(ask_model) or not isinstance(directory,Path)):
        raise WritingExecutionError("WF_TRACE_ONLY_REPAIR_INPUT_INVALID")
    previous=None
    parent_pending=False
    if beat.get("causal_parent") is not None:
        parents=[a for a in accepted if a.get("beat_id")==beat["causal_parent"]]
        if len(parents)!=1:
            raise WritingExecutionError("WF_TRACE_ONLY_REPAIR_PARENT_INVALID")
        prior=parents[0]
        previous=prior.get("effect_quote")
        if type(previous) is not str:
            # V96 allows SOURCE-verified decisions with no observed effect.
            # The previous action can be used as a pending basis, but the
            # trace-only author must not invent a parent effect to pass.
            try:
                verified,basis,kind=latest_source_basis_for_replan((prior,))
            except V98RollingPlanError:
                raise WritingExecutionError(
                    "WF_TRACE_ONLY_REPAIR_PARENT_UNVERIFIED") from None
            if (kind!="DECISION_ACTION_ONLY_OUTCOME_PENDING" or
                verified.get("beat_id")!=beat["causal_parent"]):
                raise WritingExecutionError(
                    "WF_TRACE_ONLY_REPAIR_PARENT_UNVERIFIED")
            parent_pending=True
        elif (type(prior.get("receipt")) is dict and
              prior["receipt"].get("outcome_pending_source_only") is True):
            raise WritingExecutionError("WF_TRACE_ONLY_REPAIR_PARENT_UNVERIFIED")
    quote_rule=(
        "如果本段是 decision 且确实写出决定/尝试，却没有可见后果，"
        "action_quote 必须引用原句6至96字，effect_quote 可为 JSON null；"
        "如果已经有可见结果，两段实际引用均须在正文唯一出现且不重叠。"
        if beat.get("kind")=="decision" else
        "action_quote 与 effect_quote 引用必须是各6至96字的"
        "两个不同的、在下面小说中唯一出现且不重叠的实际子串；"
        "动作必须出现在后果之前。"
    )
    prompt=(
        "【WriterForge 源引句订正：保留你已经自己创作的全部新小说正文】"
        "你之前真正生成的这版小说正文现已冻结。"
        "WF 不会替你写句子、拆分引句或修改剧情。"
        "只有你本人可以重新为自己这一版既有正文给出"
        " trace.action_quote、trace.effect_quote 和"
        " trace.parent_effect_quote 三个字面引句。"
        "本次只允许更正引用元数据，不许返回 prose、replacement、"
        "reason、下一章或更多字段。"
        +quote_rule+
        "若这个版本没有可见后果，引用不能假装它存在，"
        "请输出真实能引用的文本，否则源校验仍会失败。"
        "如果段落没有前一个依赖事件，parent_effect_quote 为 JSON null；"
        +("如果父事件仅有来源锁定的决定而无实际后果，"
          "parent_effect_quote 必须为 JSON null，不可强行补一个结果。"
          if parent_pending else
          "如果有父事件，只能引用下面逐字来源的真正前一段结果。")+
        "只返回恰好一个 JSON 对象 {\"trace\":"
        "{\"action_quote\":... ,\"effect_quote\":... ,"
        "\"parent_effect_quote\":...}}，不得加文学评分。"
        "\n【旧引用失败码】"+failure_code+
        "\n【旧引用（模型原错答保留，尚未采用）】"+
        json.dumps(invalid_trace,ensure_ascii=False,separators=(",",":"))+
        "\n【本段既有事件类别】"+str(beat.get("kind"))+
        "\n【已存在的前段后果，未知则 null】"+
        json.dumps(previous,ensure_ascii=False)+
        "\n【原作者已经写出的冻结候选，必须逐字不变】"+
        candidate_prose
    )
    if len(prompt)>MAX_PROMPT_CHARS:
        raise WritingExecutionError("WF_TRACE_ONLY_REPAIR_CONTEXT_TOO_FULL")
    packet=replace(turn_packet,prompt=prompt,
                   prompt_sha256=sha256(prompt.encode("utf8")).hexdigest())
    if cancel_check is not None:
        cancel_check()
    response=ask_model(packet,model=None,api_base=None,
                       max_tokens=SELF_EDIT_MODEL_MAX_TOKENS)
    (directory/"same-writer-source-trace-only-original.json").write_text(
        response,encoding="utf8")
    if cancel_check is not None:
        cancel_check()
    def reject_duplicates(pairs):
        doc={}
        for k,v in pairs:
            if k in doc:
                raise ValueError("WF_TRACE_ONLY_DUPLICATE_KEY")
            doc[k]=v
        return doc
    if type(response) is not str or len(response.encode("utf8"))>12000:
        raise WritingExecutionError("WF_TRACE_ONLY_REPLY_TOO_LARGE")
    data=json.loads(response,object_pairs_hook=reject_duplicates)
    if (type(data) is dict and set(data)=={"type","trace"} and
        data["type"]=="json_object"):
        data={"trace":data["trace"]}
    if (type(data) is not dict or set(data)!={"trace"} or
        type(data["trace"]) is not dict or
        set(data["trace"])!={"action_quote","effect_quote",
                             "parent_effect_quote"}):
        raise WritingExecutionError("WF_TRACE_ONLY_REPLY_SCHEMA_INVALID")
    return data["trace"]



def _self_edit_one_turn(*,raw,beat,accepted,project_id,scene_id,
                        turn_packet,ask_model,round_limit,call_allowance,
                        directory,author_exclusions=(),
                        previous_candidate_state=None,cast=(),
                        current_external_story_checkpoint=None,
                        active_narrative_core=None,cancel_check=None,
                        story_chapter_index=0,writer_attention=None):
    """Writer self-reads and discards sentences/paragraphs/scenes BEFORE canon.

    The model can CHOOSE to keep, delete or rewrite. All text changes are
    applied ONLY by the existing V119 source-locked edit transaction, then
    rechecked by the old V96, V117 and unified narrative source gates.
    No model's subjective feeling or asserted quality is trusted as proof.
    The unmodified original and abandoned variants are private job drafts,
    capped and never used as authoritative cross-chapter story state.
    """
    if (type(round_limit) is not int or not
        0<=round_limit<=SELF_EDIT_MAX_PER_TURN or
        type(call_allowance) is not int or call_allowance<0 or
        not callable(ask_model)):
        raise WritingExecutionError("WF_SELF_EDIT_BOUNDARY_INVALID")
    if round_limit==0:
        return raw,{"format":"wf.writer.self-edit.v1",
                    "enabled":False,"model_calls":0,
                    "rounds":[],"author_accepted":False,
                    "canon_writes":0}
    try:
        doc=_decode_json(raw)
        if (set(doc)!={"prose","trace"} or
            type(doc["prose"]) is not str or
            type(doc["trace"]) is not dict or
            set(doc["trace"])!={"action_quote","effect_quote",
                               "parent_effect_quote"} or
            not 80<=len(doc["prose"].strip())<=
                   _WF96_GUARDED_TURN_CHARS):
            raise ValueError("UNSAFE_MODEL_TURN_ENVELOPE")
    except (WritingExecutionError,ValueError,TypeError) as e:
        return raw,{
            "format":"wf.writer.self-edit.v1",
            "enabled":True,"model_calls":0,
            "rounds":[{"status":"SKIPPED_UNSAFE_INITIAL_RESPONSE",
                       "original_sha256":sha256(raw.encode()).hexdigest()}],
            "author_accepted":False,"canon_writes":0,
            "literary_quality_verified":False,
        }
    if not isinstance(directory,Path):
        raise WritingExecutionError("WF_SELF_EDIT_PRIVATE_PATH_INVALID")
    directory.mkdir(parents=True,exist_ok=False)
    (directory/"first-original.md").write_text(doc["prose"],encoding="utf8")
    current_raw=raw
    original_sha=sha256(doc["prose"].strip().encode("utf8")).hexdigest()
    rounds=[]
    calls=0
    visited_source_hashes={original_sha}
    for i in range(min(round_limit,call_allowance)):
        if cancel_check is not None:
            cancel_check()
        previous=doc["prose"].strip()
        previous_sha=sha256(previous.encode("utf8")).hexdigest()
        guide=prepare_source_repair_contract(
            source=previous,source_sha256=previous_sha,
            beat=beat,accepted=accepted,original_trace=doc["trace"],
            writer_attention=writer_attention,
            previous_candidate_state=previous_candidate_state,
            cast=cast)
        # Durable non-literary repair contract, not a secondary memory.
        (directory/f"round-{i+1:02d}-source-repair-guide.json").write_text(
            json.dumps(guide,ensure_ascii=False,sort_keys=True,indent=2),
            encoding="utf8")
        # Use actual source evidence and the author's existing objective.
        # Model still chooses KEEP/DELETE/REVISE/REPLACE_SCENE and writes prose.
        details={
            "source_sha256":previous_sha,
            "prose":previous,
            "beat":beat,
            "wf_source_repair_contract":guide,
            "writer_previous_self_decided_focus":(
                writer_attention if type(writer_attention) is dict else None),
            "last_observed_effects":[
                (r.get("effect_quote") or "")[:120]
                for r in accepted[-2:]],
            "requirements":{
                "decision":["KEEP","DELETE","REVISE","REPLACE_SCENE"],
                "scope":["sentence","paragraph","scene"],
                "source_max_edit_codepoints":1800,
                "no_canon_or_prose_acceptance":True,
            },
        }
        parent=beat.get("causal_parent")
        parent_effect=next((
            x.get("effect_quote") for x in accepted
            if x.get("beat_id")==parent),None)
        parent_trace_instruction=(
            "\n【实际前因来源字段（技术格式，不是文学评价）】"
            "本段没有前一段来源依赖。"
            "trace.parent_effect_quote 必须是 JSON null，"
            "不得引用本段任何对话或同段动作冒充前段后果。"
            if parent is None else
            "\n【实际前因来源字段（技术格式，不是文学评价）】"
            "本段确有上一段来源依赖。"
            "trace.parent_effect_quote 必须逐字引用以下已经实际写出的"
            "上一段后果，不要从对话或计划猜测前因："+
            json.dumps(parent_effect,ensure_ascii=False))
        instruction=(
            "\n【WriterForge 写作过程中自主删改】"
            "你刚写完小说的一段，独自重新读自己的正文，像作家反复打磨草稿。"
            "先判断人物当时知道什么、为何选择、动作是否重复、"
            "时间地点和代价是否可信，语言是否自然。"
            "稿子已经合适就 KEEP，不允许为了凑修改次数强迫反转。"
            "不满意时自行选删除一句 DELETE、修改局部 REVISE"
            "（sentence 或 paragraph）或整场 REPLACE_SCENE。"
            "只能针对本轮 prose 源原句给出起止字符下标，"
            "不可重写选择范围以外的任何文字。"
            "删除/改写以后必须仍是一段完整小说，不准附带评语写进 prose。"
            "所有新文本必须延续上文真实已发生的结果，"
            "不得让人物突然获得未见过的秘密或改变他人物件持有者。"
            "只输出严格 JSON 对象，字段恰好为"
            "decision、scope、source_sha256、start、end、"
            "expected_original、replacement、trace、reason。"
            "KEEP 时 scope/start/end/expected_original/replacement/trace 均为 JSON null。"
            "改动时 trace 为 action_quote/effect_quote/parent_effect_quote"
            "三个键的对象：必须逐字引用修改后真正出现的原句，"
            "没有才填 null。"
            "若本段 beat.kind 是 action、decision 或 reversal"
            "（V96 要求实际动作与可观察结果），"
            "trace.action_quote 和 trace.effect_quote 各引用6到96字的"
            "两个【不同且互不重叠】的真实源连续子串，动作引句必须"
            "【先于】结果引句出现。"
            "同一句内可以分选两个不同子串，但严禁把整句、整个"
            "replacement 或同一段连续引句同时复制给这两个字段。"
            "如果实在没有可见结果，不能用相同引句假装后果存在；"
            "需要由你作为作家重新构思改稿内容，而非让软件补句。"
            "reason 用一句话指出真实缺陷，不能自评分。"
            "如果对 Unicode 字符坐标数不准，必须提供逐字准确且唯一的"
            "expected_original；工作台只能用原文唯一引句恢复坐标，"
            "不会猜测应该修改什么。"
            +parent_trace_instruction+
            "\n【本轮真实未完成草稿】"+
            json.dumps(details,ensure_ascii=False,separators=(",",":"))
        )
        prompt=turn_packet.prompt+instruction
        if len(prompt)>MAX_PROMPT_CHARS:
            rounds.append({"round":i+1,"status":"SKIPPED_CONTEXT_BUDGET",
                           "old_sha256":previous_sha})
            break
        own_packet=replace(
            turn_packet,prompt=prompt,
            prompt_sha256=sha256(prompt.encode("utf8")).hexdigest())
        # This is the SAME writing model, acting as its own provisional
        # editor. No external critic, no user resend and no hidden retrial.
        answer=ask_model(own_packet,model=None,api_base=None,
                         max_tokens=SELF_EDIT_MODEL_MAX_TOKENS)
        calls+=1
        (directory/f"round-{i+1:02d}-model-proposal.json").write_text(
            answer,encoding="utf8")
        wrapper_only_removed=False
        recovered_offset=False
        repair_impact=None
        source_trace_recovered_by_author=False
        original_trace_error=None
        try:
            if type(answer) is not str or len(answer.encode("utf8"))>18000:
                raise ValueError("WF_SELF_EDIT_REPLY_TOO_BIG")
            def no_duplicate(pairs):
                out={}
                for k,v in pairs:
                    if k in out:
                        raise ValueError("WF_SELF_EDIT_DUPLICATE_JSON_KEY")
                    out[k]=v
                return out
            choice=json.loads(answer,object_pairs_hook=no_duplicate)
            expected_keys={
                "decision","scope","source_sha256","start","end",
                "expected_original","replacement","trace","reason"}
            # Observed real DeepSeek V119 proposals may contain the literal
            # transport marker "type":"json_object". This ONE precise
            # wrapper is removable without changing model's prose, literary
            # decision, source quote, metadata, or raw provider answer.
            # Every other surplus field remains an error.
            if (type(choice) is dict and
                set(choice)==expected_keys|{"type"} and
                choice.get("type")=="json_object"):
                choice={k:v for k,v in choice.items() if k!="type"}
                wrapper_only_removed=True
            if type(choice) is not dict or set(choice)!=expected_keys:
                raise ValueError("WF_SELF_EDIT_SCHEMA_INVALID")
            decision=choice["decision"]
            if (decision not in ("KEEP","DELETE","REVISE","REPLACE_SCENE")
                or choice["source_sha256"]!=previous_sha or
                type(choice["reason"]) is not str or
                not 6<=len(choice["reason"])<=240):
                raise ValueError("WF_SELF_EDIT_UNTRUSTED_CHOICE")
            if decision=="KEEP":
                if any(choice[x] is not None for x in (
                        "scope","start","end","expected_original",
                        "replacement","trace")):
                    raise ValueError("WF_SELF_EDIT_KEEP_NOT_CLEAN")
                rounds.append({
                    "round":i+1,"status":"KEEP_BY_WRITER",
                    "source_sha256":previous_sha,
                    "source_repair_contract_sha256":guide["receipt_sha256"],
                    "no_edit_means_no_new_downstream_invalidation":True,
                    "model_self_assessment_not_literary_proof":True})
                break
            scope=choice["scope"]
            start,end=choice["start"],choice["end"]
            original=choice["expected_original"]
            replacement=choice["replacement"]
            if (scope not in SELF_EDIT_SCOPES or
                type(start) is not int or type(end) is not int or
                # Positions may be badly counted by the model. Recover
                # ONLY when the literal original text uniquely occurs in
                # this same SHA-locked source. Still cap integer bounds.
                not 0<=start<end<=20000 or
                type(original) is not str or not original or
                len(original)>SELF_EDIT_SCOPES[scope] or
                type(replacement) is not str or
                len(replacement)>SELF_EDIT_SCOPES[scope] or
                (decision=="DELETE" and replacement!="") or
                (decision!="DELETE" and not replacement) or
                (decision=="REPLACE_SCENE" and
                 (scope!="scene" or start!=0 or end!=len(previous))) or
                (decision!="REPLACE_SCENE" and
                 scope=="scene")):
                raise ValueError("WF_SELF_EDIT_INVALID_EDIT_REGION")
            # Real DeepSeek wrote correct exact original sentence/paragraph
            # but miscounted its Python Unicode offsets by 11 / 82 chars.
            # V119 must still receive an exact, UNIQUE source span.
            # Recover only from verbatim source evidence, never fuzzy
            # matching, guessed referents, or replacing another occurrence.
            model_start,model_end=start,end
            if previous[start:end]!=original:
                if previous.count(original)!=1:
                    raise ValueError(
                        "WF_SELF_EDIT_SOURCE_QUOTE_NOT_UNIQUE")
                start=previous.index(original)
                end=start+len(original)
                recovered_offset=True
                if (decision=="REPLACE_SCENE" and
                    (start!=0 or end!=len(previous))):
                    raise ValueError(
                        "WF_SELF_EDIT_REWRITE_SCOPE_NOT_ENTIRE_SCENE")
            trace=choice["trace"]
            if type(trace) is not dict or set(trace)!={
                    "action_quote","effect_quote","parent_effect_quote"}:
                raise ValueError("WF_SELF_EDIT_TRACE_SHAPE")
            preview=preview_surgical_revision(
                project_id=project_id,scene_id=scene_id,
                source=previous,source_sha256=previous_sha,
                start=start,end=end,expected_original=original,
                replacement=replacement,
                previous_candidate_state=previous_candidate_state,
                cast=cast)
            repair_impact=compare_source_repair_impact(
                preview_receipt=preview["receipt"])
            (directory/f"round-{i+1:02d}-before-after-impact.json"
             ).write_text(json.dumps(
                 repair_impact,ensure_ascii=False,sort_keys=True,indent=2),
                 encoding="utf8")
            if (preview["status"]!="PROVISIONAL_REVIEW" or
                type(preview["candidate_prose"]) is not str):
                rounds.append({
                    "round":i+1,"status":"REJECTED_NEW_SOURCE_WARNING",
                    "old_sha256":previous_sha,
                    "model_decision":decision,
                    "source_repair_contract_sha256":guide["receipt_sha256"],
                    "repair_impact_status":repair_impact["status"],
                    "new_hard_findings":repair_impact["new_hard_findings"],
                    "patch_receipt_sha256":preview["receipt"]["receipt_sha256"]})
                break
            changed=preview["candidate_prose"]
            if repair_impact["status"] in (
                    "HELD_NEW_UNVERIFIED_SOURCE_RISK",
                    "HELD_EXISTING_SOURCE_RELATION_RISK"):
                # A newly introduced OR previously unresolved physical
                # relation cannot be erased by editing unrelated prose.
                # This is source uncertainty, not a literary verdict.
                # Keep a private candidate for the original author to
                # resolve rather than promoting it into downstream state.
                (directory/f"round-{i+1:02d}-held-unverified-draft.md"
                 ).write_text(changed,encoding="utf8")
                rounds.append({
                    "round":i+1,
                    "status":repair_impact["status"],
                    "source_repair_contract_sha256":guide["receipt_sha256"],
                    "repair_impact_sha256":repair_impact["receipt_sha256"],
                    "new_review_findings":repair_impact[
                        "new_unverified_review_findings"],
                    "existing_physical_relation_review_remaining":(
                        repair_impact["existing_physical_relation_review_remaining"]),
                    "original_source_kept_for_continuation":True,
                    "author_objective_fulfillment_unverified":True})
                break
            changed_sha=sha256(changed.encode("utf8")).hexdigest()
            if changed_sha in visited_source_hashes:
                rounds.append({
                    "round":i+1,"status":"REJECTED_REVISION_OSCILLATION",
                    "previously_seen_source_sha256":changed_sha,
                    "source_repair_contract_sha256":guide["receipt_sha256"],
                    "repair_impact_sha256":repair_impact["receipt_sha256"],
                    "kept_last_valid_source_sha256":previous_sha,
                    "author_cannot_loop_back_to_same_draft_automatically":True})
                break
            # Do not accept a too-short deleted paragraph or forged
            # model-made trace; back out to the last valid draft.
            next_doc={"prose":changed,"trace":trace}
            next_raw=json.dumps(next_doc,ensure_ascii=False,
                                separators=(",",":"))
            try:
                check_turn(next_raw,beat,mode="causal_guard",
                           accepted=accepted,
                           author_confirmed_forbidden_phrases=author_exclusions,
                           max_prose_chars=_WF96_GUARDED_TURN_CHARS)
            except V96CausalDraftError as why:
                # This is not a prose rewrite retry. Offer a SINGLE
                # constrained citation-only response from the SAME AI
                # only if the user already opted for a second self-edit
                # round and the total source-authored call budget allows.
                allowed={
                    "WF96_ACTION_EFFECT_OVERLAP_OR_REVERSED",
                    "WF96_ACTION_NEEDS_ACTUAL_ACTION_AND_EFFECT",
                    "WF96_UNDECLARED_PREVIOUS_CAUSE",
                    "WF96_PARENT_CAUSE_NOT_ANCHORED_IN_PREVIOUS_PROSE",
                }
                if (str(why) not in allowed or
                    i+1>=min(round_limit,call_allowance) or
                    calls>=call_allowance):
                    raise
                original_trace_error=str(why)
                (directory/f"round-{i+1:02d}-invalid-model-trace.json"
                 ).write_text(json.dumps(trace,ensure_ascii=False,indent=2),
                              encoding="utf8")
                # If this extra same-model call still gets citation wrong,
                # V96 rejects, the source is rolled back, and no third
                # automatic request occurs.
                def counted_source_trace_model(packet,*,model,api_base,
                                               max_tokens):
                    nonlocal calls
                    # Count the call even if its reply is malformed:
                    # parsing failure must never silently refund tokens.
                    calls+=1
                    return ask_model(packet,model=model,
                                     api_base=api_base,max_tokens=max_tokens)
                updated_trace=_ask_same_writer_for_source_trace_only(
                    candidate_prose=changed,invalid_trace=trace,
                    failure_code=original_trace_error,
                    beat=beat,accepted=accepted,
                    turn_packet=turn_packet,ask_model=counted_source_trace_model,
                    directory=directory,cancel_check=cancel_check)
                next_doc={"prose":changed,"trace":updated_trace}
                next_raw=json.dumps(next_doc,ensure_ascii=False,
                                    separators=(",",":"))
                check_turn(next_raw,beat,mode="causal_guard",
                           accepted=accepted,
                           author_confirmed_forbidden_phrases=author_exclusions,
                           max_prose_chars=_WF96_GUARDED_TURN_CHARS)
                source_trace_recovered_by_author=True
            if active_narrative_core is not None:
                review=audit_narrative_candidate(
                    active_narrative_core,
                    project_id=project_id,scene_id=scene_id,
                    prose=changed,cast=cast)
                if review["blocked"]:
                    raise NarrativeCoreError(
                        "WF_SELF_EDIT_REVISED_POV_KNOWLEDGE_BLOCKED")
            if current_external_story_checkpoint is not None:
                review=preflight_continuation(
                    changed,current_external_story_checkpoint,
                    project_id=project_id,
                    chapter_index=story_chapter_index,
                    cast=cast)
                if review["blocked"]:
                    raise ContinuityTraceError(
                        "WF_SELF_EDIT_REVISED_SOURCE_STATE_BLOCKED")
            if cancel_check is not None:
                cancel_check()
            (directory/f"round-{i+1:02d}-discarded-draft.md").write_text(
                previous,encoding="utf8")
            (directory/f"round-{i+1:02d}-selected-draft.md").write_text(
                changed,encoding="utf8")
            current_raw=next_raw
            doc=next_doc
            visited_source_hashes.add(changed_sha)
            rounds.append({
                "round":i+1,"status":"PROVISIONALLY_REVISED",
                "decision":decision,"scope":scope,
                "revised_before_canon":True,
                "original_sha256":previous_sha,
                "candidate_sha256":sha256(changed.encode("utf8")).hexdigest(),
                "patch_receipt_sha256":preview["receipt"]["receipt_sha256"],
                "source_repair_contract_sha256":guide["receipt_sha256"],
                "repair_impact_status":repair_impact["status"],
                "repair_impact_sha256":repair_impact["receipt_sha256"],
                "source_trace_reattributed_by_same_author_model":
                    source_trace_recovered_by_author,
                "initial_model_V96_trace_failure":original_trace_error,
                "additional_trace_only_model_call":(
                    1 if source_trace_recovered_by_author else 0),
                "novelist_prose_never_changed_by_trace_repair":True,
                "baseline_findings_remaining":repair_impact[
                    "previously_existing_hard_findings_remain"],
                "literary_intent_satisfied_still_unverified":True,
                "subsequent_turns_require_regeneration":True,
                "source_offset_recovered_exactly":recovered_offset,
                "format_wrapper_only_removed":wrapper_only_removed,
                "original_model_coordinates":[model_start,model_end],
                "host_verified_coordinates":[start,end],
                "literary_quality_not_proven":True})
            if source_trace_recovered_by_author:
                # Both allowed requests have been spent, the same author's
                # source-quoted trace is verified; do NOT start another
                # unrelated full rewrite in this single bounded cycle.
                break
        except (ValueError,TypeError,KeyError,WritingExecutionError,
                RevisionTransactionError,V96CausalDraftError,
                NarrativeCoreError,ContinuityTraceError) as exc:
            if isinstance(exc,WriterDraftCancelled):
                raise  # User cancellation must never be converted to review.
            error=str(exc)
            if not error.startswith(("WF_", "WF96_", "WF119_", "WFCORE_")):
                error=type(exc).__name__+":SELF_EDIT_MODEL_OR_PATCH_INVALID"
            # Actionable exact failure feedback; never mutate failed
            # model prose/trace to fake an accepted literary revision.
            next_action=(
                "ORIGINAL_WRITER_MUST_QUOTE_TWO_DISTINCT_ORDERED_SOURCE_SPANS"
                if error=="WF96_ACTION_EFFECT_OVERLAP_OR_REVERSED" else
                "ORIGINAL_WRITER_MUST_PROVE_PRIOR_CAUSE_OR_USE_NULL"
                if error.startswith(("WF96_UNDECLARED_PREVIOUS_CAUSE",
                                     "WF96_PARENT_CAUSE_NOT_ANCHORED")) else
                "KEEP_LAST_VALID_SOURCE_AND_REEXAMINE_REPAIR_SCOPE")
            guidance={
                "source_sha256":previous_sha,
                "attempted_writer_focus_sha256":guide["receipt_sha256"],
                "exact_validation_failure":error[:150],
                "writer_next_safe_action":next_action,
                "new_source_risk_delta_receipt":(
                    repair_impact.get("receipt_sha256")
                    if repair_impact is not None else None),
                "cannot_claim_literary_problem_fixed":True,
                "no_unbounded_repair_retries":True,
                "no_host_authored_fiction_or_trace":True,
                "old_source_preserved":True,
            }
            (directory/f"round-{i+1:02d}-actionable-failure.json"
             ).write_text(json.dumps(guidance,ensure_ascii=False,
                                    sort_keys=True,indent=2),encoding="utf8")
            rounds.append({
                "round":i+1,"status":"REJECTED_AND_ROLLED_BACK",
                "reason_code":error[:150],
                "source_repair_contract_sha256":guide["receipt_sha256"],
                "repair_impact_sha256":(
                    repair_impact["receipt_sha256"]
                    if repair_impact is not None else None),
                "writer_next_safe_action":next_action,
                "metadata_only_trace_attempted":(
                    original_trace_error is not None),
                "model_written_prose_untouched_by_WF":True,
                "format_wrapper_only_removed":wrapper_only_removed,
                "source_offset_recovered_exactly":recovered_offset,
                "unmodified_candidate_sha256":previous_sha})
            break
    last=doc["prose"].strip()
    receipt={
        "format":"wf.writer.self-edit.v1",
        "enabled":True,
        "max_rounds":round_limit,
        "model_calls":calls,
        "original_sha256":original_sha,
        "final_candidate_sha256":sha256(last.encode("utf8")).hexdigest(),
        "discarded_drafts_preserved_locally_only":sum(
            r["status"]=="PROVISIONALLY_REVISED" for r in rounds),
        "rounds":rounds,
        "all_revisions_are_unaccepted_candidates":True,
        "model_critic_not_independent":True,
        "literary_quality_verified":False,
        "canon_writes":0,
        "no_external_review_model":True,
    }
    (directory/"self-edit-receipt.json").write_text(
        json.dumps(receipt,ensure_ascii=False,sort_keys=True,indent=2),
        encoding="utf8")
    return current_raw,receipt


class WriterDraftCancelled(WritingExecutionError):
    """A provisional draft was stopped by its author; never a Canon change."""


def _fork_private_local_file(job, value, *, max_bytes=3_000_000):
    """Read only a source-job artifact; reject escape paths and R2 URLs."""
    if (type(value) is not str or not value or
        value.startswith("r2://")):
        raise WritingExecutionError("WF_CHAPTER_FORK_SOURCE_PATH_INVALID")
    target=Path(value).resolve()
    if (not target.is_relative_to(job) or not target.is_file() or
        not 0<target.stat().st_size<=max_bytes):
        raise WritingExecutionError("WF_CHAPTER_FORK_SOURCE_PATH_INVALID")
    return target


def _fork_strict_json(value, *, max_bytes):
    if type(value) is not str or len(value.encode("utf8"))>max_bytes:
        raise WritingExecutionError("WF_CHAPTER_FORK_JSON_BOUNDS")
    def unique(pairs):
        result={}
        for k,v in pairs:
            if k in result:
                raise WritingExecutionError("WF_CHAPTER_FORK_DUPLICATE_KEY")
            result[k]=v
        return result
    try:
        parsed=json.loads(value,object_pairs_hook=unique)
    except (ValueError,TypeError):
        raise WritingExecutionError("WF_CHAPTER_FORK_BAD_JSON") from None
    if type(parsed) is not dict:
        raise WritingExecutionError("WF_CHAPTER_FORK_BAD_JSON")
    return parsed


def _prepare_unaccepted_chapter_fork(*,source_job_dir,writer_decision_reply,
                                     expected_old_head_sha256,
                                     retained_resume,project_id,scene_id,
                                     outline_sha256,source_snapshot_id,
                                     model_used,chapter_count):
    """Check a complete *local unaccepted* V117/NarrativeCore candidate chain.

    Writer supplied the literary decision; software never decides to rewrite
    a chapter or manufactures a replacement. The previous signed chapter
    (possibly containing earlier hot/warm/cold memory) is the only retained
    story owner. All later chapter candidates must be newly drafted in a
    DIFFERENT job, never copied as accepted events.
    """
    if (type(source_job_dir) not in (str,Path) or
        type(expected_old_head_sha256) is not str or
        len(expected_old_head_sha256)!=64 or
        type(retained_resume) is not dict):
        raise WritingExecutionError("WF_CHAPTER_FORK_INPUT_INVALID")
    job=Path(source_job_dir).resolve()
    if not job.is_dir() or not job.name.startswith("auto-"):
        raise WritingExecutionError("WF_CHAPTER_FORK_NOT_SOURCE_JOB")
    manifest_path=_fork_private_local_file(job,str(job/"job_manifest.json"))
    manifest=_fork_strict_json(manifest_path.read_text("utf8"),
                               max_bytes=3_000_000)
    if (manifest.get("status")!="candidates_saved" or
        manifest.get("draft_mode")!="continuity_guard" or
        manifest.get("project_id")!=project_id or
        manifest.get("outline_sha256")!=outline_sha256 or
        manifest.get("source_snapshot_id")!=source_snapshot_id or
        manifest.get("model_used")!=model_used or
        type(manifest.get("chapters")) is not list or
        not 2<=len(manifest["chapters"])<=2 or
        len(manifest["chapters"])!=chapter_count or
        manifest.get("chapter_count")!=chapter_count):
        raise WritingExecutionError("WF_CHAPTER_FORK_ORIGINAL_JOB_MISMATCH")
    try:
        read_resume(retained_resume,project_id=project_id,
                    scene_id=scene_id)
        earlier_core=read_core_from_resume(
            retained_resume,project_id=project_id,scene_id=scene_id)
    except (ContinuityTraceError,NarrativeCoreError):
        raise WritingExecutionError("WF_CHAPTER_FORK_PRIOR_RESUME_INVALID") from None
    if earlier_core is None or "v123_open_character_arc" in retained_resume:
        raise WritingExecutionError("WF_CHAPTER_FORK_REQUIRES_UNIFIED_GRAPH")
    # Never claim unrelated R2 memory was checked by local-only fork logic.
    old_memory=earlier_core["memory"]
    if (any(x.get("source_path","").startswith("r2://")
            for x in old_memory["hot"]+old_memory["warm"]) or
        any((ref.get("path","").startswith("r2://")
             if type(ref) is dict else False)
            for ref in [old_memory.get("cold_head")] +
                       list(old_memory.get("cold_node_heads",{}).values()))):
        raise WritingExecutionError("WF_CHAPTER_FORK_REMOTE_ARCHIVE_NOT_VERIFIED")
    decision=_fork_strict_json(writer_decision_reply,max_bytes=12000)
    required={"decision","target_chapter_index","source_sha256",
              "evidence_quote","why_now","what_goes_wrong_if_unchanged",
              "intended_reader_effect"}
    if (set(decision)!=required or
        decision["decision"]!="LOOK_BACK_NOW" or
        type(decision["target_chapter_index"]) is not int or
        type(decision["source_sha256"]) is not str or
        type(decision["why_now"]) is not str or
        type(decision["what_goes_wrong_if_unchanged"]) is not str or
        type(decision["intended_reader_effect"]) is not str or
        not all(8<=len(decision[k])<=260 for k in (
            "why_now","what_goes_wrong_if_unchanged",
            "intended_reader_effect"))):
        raise WritingExecutionError("WF_CHAPTER_FORK_WRITER_SIGNAL_INVALID")
    first=retained_resume["chapter_index"]+1
    if decision["target_chapter_index"]!=first:
        raise WritingExecutionError("WF_CHAPTER_FORK_NOT_ADJACENT_TO_PREFIX")
    upstream=earlier_core["receipt_sha256"]
    affected=[]
    for position,row in enumerate(manifest["chapters"]):
        if (type(row) is not dict or row.get("accepted") is not False or
            row.get("story_chapter_index")!=first+position or
            row.get("draft_mode")!="continuity_guard"):
            raise WritingExecutionError("WF_CHAPTER_FORK_ACCEPTED_OR_GAPPED")
        candidate_path=_fork_private_local_file(job,row.get("candidate"),
                                                 max_bytes=70_000)
        original_bytes=candidate_path.read_bytes()
        try:
            original=original_bytes.decode("utf8","strict")
        except UnicodeError:
            raise WritingExecutionError("WF_CHAPTER_FORK_SOURCE_NOT_UTF8") from None
        original_sha=sha256(original_bytes).hexdigest()
        resume_file=_fork_private_local_file(
            job,row.get("v117_unreviewed_text_trace_resume"))
        snapshot=_fork_strict_json(resume_file.read_text("utf8"),
                                   max_bytes=3_000_000)
        try:
            state=read_resume(snapshot,project_id=project_id,
                              scene_id=scene_id)
            graph=read_core_from_resume(
                snapshot,project_id=project_id,scene_id=scene_id)
        except (ContinuityTraceError,NarrativeCoreError):
            raise WritingExecutionError("WF_CHAPTER_FORK_OLD_RESUME_INVALID") from None
        if (graph is None or snapshot["chapter_index"]!=first+position or
            graph["parent_sha256"]!=upstream or
            graph["chapter_index"]!=first+position or
            state["receipt_sha256"]!=snapshot["source_checkpoint_sha256"] or
            state["source_sha256"]!=snapshot["source_prose_sha256"]):
            raise WritingExecutionError("WF_CHAPTER_FORK_GRAPH_PARENT_OR_SOURCE")
        hot=graph.get("memory",{}).get("hot",[])
        latest=(hot[-1] if hot else None)
        if (latest is None or latest["chapter"]!=first+position or
            latest["source_sha256"]!=original_sha or
            latest["source_path"].startswith("r2://") or
            Path(latest["source_path"]).resolve()!=candidate_path):
            raise WritingExecutionError("WF_CHAPTER_FORK_MANUSCRIPT_CHANGED")
        # Each individual signature can be authentic while the pair points
        # at DIFFERENT novel drafts. New cross-chapter forks require the
        # signed whole-chapter to ALL turn-level V114 source assembly proof.
        link=graph.get("source_temporal_link")
        if (type(link) is not dict or
            link.get("chapter_index")!=first+position or
            link.get("whole_chapter_sha256")!=original_sha or
            link.get("last_v114_checkpoint_sha256")!=
                state["receipt_sha256"] or
            link.get("source_assembly_verified") is not True):
            raise WritingExecutionError(
                "WF_CHAPTER_FORK_UNVERIFIED_SOURCE_ASSEMBLY")
        affected.append({
            "chapter_index":first+position,
            "source_sha256":original_sha,
            "old_v117_receipt_sha256":snapshot["receipt_sha256"],
            "old_graph_receipt_sha256":graph["receipt_sha256"],
        })
        upstream=graph["receipt_sha256"]
    if affected[-1]["old_v117_receipt_sha256"]!=expected_old_head_sha256:
        raise WritingExecutionError("WF_CHAPTER_FORK_STALE_HEAD")
    if affected[0]["source_sha256"]!=decision["source_sha256"]:
        raise WritingExecutionError("WF_CHAPTER_FORK_STALE_WRITER_SOURCE")
    quote=decision["evidence_quote"]
    first_source=_fork_private_local_file(
        job,manifest["chapters"][0]["candidate"],max_bytes=70_000
    ).read_text("utf8")
    if (quote is not None and
        (type(quote) is not str or not 6<=len(quote)<=160 or
         first_source.count(quote)!=1)):
        raise WritingExecutionError("WF_CHAPTER_FORK_WRITER_QUOTE_NOT_UNIQUE")
    return {
        "format":"wf.candidate.chapter-rewind-intent.v1",
        "project_id":project_id,"scene_id":scene_id,
        "original_job_manifest_sha256":sha256(
            manifest_path.read_bytes()).hexdigest(),
        "parent_resume_sha256":retained_resume["receipt_sha256"],
        "parent_graph_sha256":earlier_core["receipt_sha256"],
        "target_chapter_index":first,
        "old_head_resume_sha256":expected_old_head_sha256,
        "obsolete_only_in_this_fork":affected,
        "writer_reply_sha256":sha256(
            writer_decision_reply.encode("utf8")).hexdigest(),
        "model_choice_not_independently_proven":True,
        "author_accepted":False,"canon_writes":0,
        "old_artifacts_are_immutable":True,
        "no_literary_quality_decision_by_host":True,
    }


def _ai_decides_cross_chapter(*,assist,outline,chapter_goals,
                              original_result,parent_resume,directory,
                              cancel_check=None):
    """One genuine same-writer-model decision after two completed G chapters.

    The AI alone owns the literary reason and whether to revisit. WF keeps
    its original response exact; any bad signal is INVALID_SIGNAL, not an
    excuse to force a rewrite. One decision request maximum, no retry.
    """
    if (type(chapter_goals) is not list or len(chapter_goals)!=2 or
        type(outline) is not str or
        type(original_result) is not dict or
        type(parent_resume) is not dict or
        not isinstance(directory,Path) or
        not directory.is_dir()):
        raise WritingExecutionError("WF_AI_CHAPTER_MOMENT_CONTEXT_INVALID")
    try:
        read_resume(parent_resume,project_id=assist.project_id,
                    scene_id=assist.scene_id)
        parent_core=read_core_from_resume(
            parent_resume,project_id=assist.project_id,
            scene_id=assist.scene_id)
    except (ContinuityTraceError,NarrativeCoreError):
        raise WritingExecutionError("WF_AI_CHAPTER_MOMENT_PARENT_INVALID") from None
    if parent_core is None:
        raise WritingExecutionError("WF_AI_CHAPTER_MOMENT_UNIFIED_ONLY")
    chapters=original_result.get("chapters")
    job=Path(original_result.get("job_dir","")).resolve()
    if (not job.is_dir() or not job.name.startswith("auto-") or
        type(chapters) is not list or len(chapters)!=2 or
        not all(type(z) is dict and z.get("accepted") is False and
                z.get("story_chapter_index")==
                parent_resume["chapter_index"]+i+1
                for i,z in enumerate(chapters))):
        raise WritingExecutionError("WF_AI_CHAPTER_MOMENT_NOT_TWO_UNACCEPTED")
    sources=[]
    for row in chapters:
        source_file=_fork_private_local_file(
            job,row["candidate"],max_bytes=70_000)
        source=source_file.read_text("utf8")
        sources.append(source)
    start=parent_resume["chapter_index"]+1
    source_sha=sha256(sources[0].encode("utf8")).hexdigest()
    # Source must fit intact, else no false claim that the AI read the scene.
    base=assist.flow.prepare(
        _writing_scene_scope(assist.scene_id,local_index=1,
                             resume_source_chapter=parent_resume["chapter_index"]),
        chapter_goals[0],concerns=("scene","decision"),
        genre=assist.source_genre)
    addition=(
        "\n【小说作者自己的章节边界回看选择】"
        "你是正在写这本小说的原创作者。下列两章都是你刚写完且"
        "未被使用者正式采纳的实际小说，而不是大纲或别人写的示例。"
        "你自己决定现在应该 MOVE_ON 保留两个章节，还是"
        "LOOK_BACK_NOW 回头重新考虑前章以及从它衍生的后章。"
        "允许合理的留白、迟疑和错误；不要为了展示删改而刻意选择回头。"
        "叙事意义、角色想法和为什么不满意由你自己负责，"
        "工作台不会替你提出任何审美判断。"
        "若想回改，接下来会由你本人重新创作，绝不自动修改原稿。"
        "仅返回一个 JSON 对象，必须恰好包含字段："
        "decision、target_chapter_index、source_sha256、"
        "evidence_quote、why_now、what_goes_wrong_if_unchanged、"
        "intended_reader_effect。"
        "decision 仅 MOVE_ON 或 LOOK_BACK_NOW；target_chapter_index "
        "固定为本次显示的第一章编号（格式身份而非剧情命令），"
        "source_sha256 原样复制第一章 SHA。"
        "MOVE_ON 时后三个中的后两个理由字段为 null，"
        "evidence_quote 为 null；why_now 必须说明保留的文学理由。"
        "LOOK_BACK_NOW 时 evidence_quote 是第一章唯一出现的真实原句"
        "（6到160字）；若需要补一个完全缺失的场景效果则为 null；"
        "why_now、what_goes_wrong_if_unchanged、"
        "intended_reader_effect 各为 8到260字自然中文。"
        "不要返回 prose/trace，不要模仿写一段正文，不要评分或输出推理轨迹。"
        "\n【原作者大纲（仅作者意图而非已经发生的事实）】"+outline+
        "\n【章节原计划】"+json.dumps(chapter_goals,ensure_ascii=False)+
        "\n【第一章章号和 SHA】"+str(start)+" / "+source_sha+
        "\n【第一章全部未接受原文】"+sources[0]+
        "\n【第二章全部未接受原文】"+sources[1]
    )
    if len(base.prompt)+len(addition)+1>MAX_PROMPT_CHARS:
        return {
            "decision":"CONTEXT_TOO_FULL","model_calls":0,
            "raw_reply":None,
            "receipt":{"status":"CONTEXT_TOO_FULL","model_calls":0,
                       "writer_was_not_asked":True,
                       "literary_quality_verified":False,"canon_writes":0},
        }
    packet=_enrich(base,addition,prose_task=False)
    if cancel_check is not None:
        cancel_check()
    original_reply=local_chat_completion(
        packet,model=assist.model,api_base=assist.api_base,max_tokens=700)
    # Save the literal answer BEFORE parsing or any possible rewrite.
    (directory/"ai-chapter-review-original.json").write_text(
        original_reply,encoding="utf8")
    if cancel_check is not None:
        cancel_check()
    receipt={
        "format":"wf.writer.ai-owns-chapter-review.v1",
        "original_reply_sha256":sha256(
            original_reply.encode("utf8")).hexdigest(),
        "source_sha256":source_sha,
        "original_chapter_count":2,"target_chapter_index":start,
        "model_calls":1,"only_same_writer_model_asked":True,
        "one_choice_no_retry":True,
        "literary_quality_verified":False,"canon_writes":0,
    }
    action="INVALID_SIGNAL"
    try:
        data=_fork_strict_json(original_reply,max_bytes=12000)
        keys={"decision","target_chapter_index","source_sha256",
              "evidence_quote","why_now","what_goes_wrong_if_unchanged",
              "intended_reader_effect"}
        if set(data)==keys|{"type"} and data["type"]=="json_object":
            data.pop("type")
            receipt["format_wrapper_only_removed"]=True
        if (set(data)!=keys or data["decision"] not in (
                "MOVE_ON","LOOK_BACK_NOW") or
            type(data["target_chapter_index"]) is not int or
            data["target_chapter_index"]!=start or
            data["source_sha256"]!=source_sha or
            type(data["why_now"]) is not str or
            not 8<=len(data["why_now"])<=260):
            raise WritingExecutionError("WF_AI_CHAPTER_MOMENT_INVALID_SIGNAL")
        if data["decision"]=="MOVE_ON":
            if any(data[k] is not None for k in (
                "evidence_quote","what_goes_wrong_if_unchanged",
                "intended_reader_effect")):
                raise WritingExecutionError("WF_AI_CHAPTER_MOVE_ON_HAS_EDIT")
        else:
            quote=data["evidence_quote"]
            if quote is not None and (
                type(quote) is not str or not 6<=len(quote)<=160 or
                sources[0].count(quote)!=1):
                raise WritingExecutionError("WF_AI_CHAPTER_QUOTE_NOT_UNIQUE")
            if any(type(data[k]) is not str or
                   not 8<=len(data[k])<=260 for k in (
                       "what_goes_wrong_if_unchanged",
                       "intended_reader_effect")):
                raise WritingExecutionError("WF_AI_CHAPTER_WHY_INCOMPLETE")
        action=data["decision"]
    except (WritingExecutionError,ValueError,KeyError,TypeError) as error:
        receipt["failure_code"]=str(error)[:130]
    receipt["decision"]=action
    (directory/"ai-chapter-review-receipt.json").write_text(
        json.dumps(receipt,ensure_ascii=False,sort_keys=True,indent=2),
        encoding="utf8")
    return {"decision":action,"raw_reply":original_reply,
            "model_calls":1,"receipt":receipt}



def _validate_unaccepted_fork_resume(*,fork_receipt,candidate_resume,
                                     project_id,scene_id):
    """Reject a formerly valid OLD resume when caller selects a new fork."""
    if (type(fork_receipt) is not dict or
        fork_receipt.get("format")!="wf.candidate.chapter-fork-rebuilt.v1" or
        fork_receipt.get("project_id")!=project_id or
        fork_receipt.get("scene_id")!=scene_id or
        fork_receipt.get("author_accepted") is not False or
        fork_receipt.get("canon_writes")!=0 or
        fork_receipt.get("receipt_sha256")!=sha256(
            json.dumps({k:v for k,v in fork_receipt.items()
                        if k!="receipt_sha256"},sort_keys=True,
                       ensure_ascii=False,separators=(",",":")).encode(
                           "utf8")).hexdigest()):
        raise WritingExecutionError("WF_CHAPTER_FORK_RECEIPT_TAMPERED")
    try:
        read_resume(candidate_resume,project_id=project_id,
                    scene_id=scene_id)
    except (ContinuityTraceError,TypeError):
        raise WritingExecutionError("WF_CHAPTER_FORK_RESUME_INVALID") from None
    if (candidate_resume["receipt_sha256"]!=
        fork_receipt["new_branch_head_resume_sha256"] or
        candidate_resume["chapter_index"]!=
        fork_receipt["new_branch_final_chapter_index"]):
        raise WritingExecutionError("WF_CHAPTER_FORK_OLD_DESCENDANT_BLOCKED")
    return candidate_resume


class AutonomousWriting:
    """Bounded outline -> narrative decisions -> actual model chapters on disk."""

    def __init__(self,assist:InvisibleWritingAssist):
        self.assist=assist

    def preview_local_revision(self, *, source:str, source_sha256:str,
                               start:int, end:int, expected_original:str,
                               replacement:str, pinned_quotes:tuple[str,...]=(),
                               previous_candidate_state:dict|None=None,
                               previous_risks:tuple[dict,...]=(),
                               cast:tuple[str,...]=()) -> dict:
        """Opt-in host-bound text revision. No provider, disk, DB or canon writes.

        The model only proposes a replacement fragment. This returns a preview,
        never changes the original or marks a literary quality claim as true.
        """
        return preview_surgical_revision(
            project_id=self.assist.project_id, scene_id=self.assist.scene_id,
            source=source, source_sha256=source_sha256,
            start=start, end=end, expected_original=expected_original,
            replacement=replacement, pinned_quotes=pinned_quotes,
            previous_candidate_state=previous_candidate_state,
            previous_risks=previous_risks,cast=cast)

    def run(self,*,outline:str,chapter_goals:list[str],
            output_dir:str|Path,progress=None,
            draft_mode:str="single",
            author_confirmed_forbidden_phrases:tuple[str,...]=(),
            frozen_turn_outlines:tuple[str,...]|None=None,
            forward_author_pinned_facts:dict[str,str]|None=None,
            resume_candidate_checkpoint:dict|None=None,
            resume_story_checkpoint:dict|str|None=None,
            continuity_reference:dict|None=None,
            long_arc_checkpoint:dict|None=None,
            narrative_core_checkpoint:dict|None=None,
            narrative_memory_backend:str="local",
            scene_delivery_contracts:tuple[dict|None,...]|None=None,
            literary_progression_mode:str="baseline",
            cancel_requested=None,review_turn=None,
            bootstrap_unified_core:bool=False,
            self_edit_rounds:int=0,
            self_edit_timing:str="always_offer",
            reader_first_self_review:bool=False,
            cross_chapter_fork:dict|None=None,
            selected_fork_receipt:dict|None=None,
            g_rolling_author_planning:bool=False,
            host_nutrient_observer=None,
            xuehai_methods_enabled:bool=False) -> dict:
        if type(xuehai_methods_enabled) is not bool:
            raise WritingExecutionError("XUEHAI_METHOD_AUTHOR_CHOICE_INVALID")
        # First host completion SHA capture is opt-in and source-only.
        if (host_nutrient_observer is not None and
                not callable(host_nutrient_observer)):
            raise ValueError("WF0BC_HOST_NUTRIENT_OBSERVER_INVALID")
        host_nutrient_application_events=0
        host_nutrient_observer_failures=0
        if type(g_rolling_author_planning) is not bool or (
                g_rolling_author_planning and draft_mode!="continuity_guard"):
            raise WritingExecutionError("WF_G_ROLLING_REQUIRES_EXPLICIT_G_MODE")
        if (type(reader_first_self_review) is not bool or
            reader_first_self_review and (
                draft_mode!="continuity_guard" or self_edit_rounds==0 or
                self_edit_timing!="ai_decides")):
            raise WritingExecutionError(
                "WF_READER_FIRST_REQUIRES_AI_OWNED_G_SELF_EDIT")
        if (self_edit_timing not in ("always_offer","ai_decides") or
            self_edit_timing=="ai_decides" and (
                draft_mode!="continuity_guard" or self_edit_rounds==0)):
            raise WritingExecutionError(
                "WF_AI_WRITER_TIMING_REQUIRES_ACTIVE_G_SELF_EDIT")
        if (type(self_edit_rounds) is not int or not
            0<=self_edit_rounds<=SELF_EDIT_MAX_PER_TURN or
            self_edit_rounds and draft_mode!="continuity_guard"):
            raise WritingExecutionError(
                "WF_SELF_EDIT_REQUIRES_G_MODE_AND_BOUNDED_ROUNDS")
        if (type(bootstrap_unified_core) is not bool or
            bootstrap_unified_core and (
                draft_mode!="continuity_guard" or
                resume_story_checkpoint is not None or
                narrative_core_checkpoint is not None or
                long_arc_checkpoint is not None)):
            raise WritingExecutionError(
                "WFCORE_INITIAL_UNIFIED_BOOTSTRAP_SCOPE_INVALID")
        # Both optional callbacks are only used by the local staged Studio.
        # No waiting, cancellation or model call added to existing SDK runs.
        if (cancel_requested is not None and not callable(cancel_requested) or
            review_turn is not None and not callable(review_turn)):
            raise WritingExecutionError("WF_STUDIO_DRAFT_CONTROL_INVALID")
        def check_cancel():
            if cancel_requested is not None and cancel_requested():
                raise WriterDraftCancelled("WF_STUDIO_DRAFT_CANCELLED")

        def ask_model(packet,*,model,api_base,max_tokens):
            nonlocal host_nutrient_application_events
            nonlocal host_nutrient_observer_failures
            check_cancel()
            answer=local_chat_completion(
                packet,model=model,api_base=api_base,max_tokens=max_tokens)
            # Current synchronous request cannot be forcibly killed. Stop
            # immediately after it returns; do not start the next step.
            check_cancel()
            if host_nutrient_observer is not None:
                # APPLICATION model response, not verified provider wire.
                # Never reveal original prompt, model body or Canon to
                # an observer; authentic wire is checked elsewhere.
                event={
                    "format":"wf.first-host.application-payload-only.v1",
                    "model_id":model,
                    "application_request_sha256":sha256(
                        packet.prompt.encode("utf8")).hexdigest(),
                    "application_response_sha256":sha256(
                        answer.encode("utf8")).hexdigest(),
                    "max_completion_tokens_reserved_not_usage":max_tokens,
                    "source_is_untrusted_application_payload":True,
                    "provider_wire_verified":False,
                    "author_accepted_prose":False,
                    "new_host_requests_for_observation":0,
                    "literary_improvement_proven":False,
                }
                host_nutrient_application_events+=1
                try:
                    host_nutrient_observer(dict(event))
                except Exception:
                    # Failed observers cannot make the writer regenerate or
                    # discard real author candidates to satisfy a meta-Skill.
                    host_nutrient_observer_failures+=1
            return answer

        check_cancel()
        # Reverted trial-only promotion after source-locked first-turn A/B:
        # plot improved, but climax and horror did not (small editorial
        # sample, not a statistical or human-quality verdict).
        # New literary advice remains available by explicit opt-in only;
        # existing source/character/causal writing is the default.
        if literary_progression_mode not in (
                "baseline","source_progression"):
            raise WritingExecutionError(
                "WF_LITERARY_PROGRESSION_MODE_UNKNOWN")
        if (literary_progression_mode!="baseline" and
                draft_mode!="continuity_guard"):
            raise WritingExecutionError(
                "WF_LITERARY_PROGRESSION_REQUIRES_UNIFIED_SCENE")
        # R2 remains explicit opt-in, never inferred from unrelated secrets.
        # The same unified memory graph owns both local and R2 references.
        if narrative_memory_backend not in ("local","r2"):
            raise WritingExecutionError(
                "WFCORE_MEMORY_BACKEND_MUST_BE_LOCAL_OR_R2")
        if narrative_memory_backend=="r2" and draft_mode!="continuity_guard":
            raise WritingExecutionError(
                "WFCORE_R2_ONLY_ON_UNIFIED_CONTINUITY_GUARD")
        narrative_store=None
        if narrative_memory_backend=="r2":
            try:
                narrative_store=R2NarrativeMemoryStore(
                    R2Config.from_environment(),
                    project_id=self.assist.project_id,
                    scene_id=self.assist.scene_id)
            except R2StorageError:
                raise WritingExecutionError(
                    "WFCORE_R2_UNAVAILABLE_OR_INVALID_CREDENTIALS") from None
        if type(resume_story_checkpoint) is str:
            if narrative_store is None:
                raise WritingExecutionError(
                    "WFCORE_REMOTE_RESUME_NEEDS_R2_BACKEND")
            try:
                resume_story_checkpoint=narrative_store.read_resume(
                    resume_story_checkpoint)
            except (R2StorageError,ContinuityTraceError,ValueError):
                raise WritingExecutionError(
                    "WFCORE_R2_RESUME_READ_OR_HASH_FAILED") from None
        # 'single' remains byte-for-byte compatible with legacy output
        # behavior. split_only vs causal_guard share the SAME JSON turn
        # planning/response interface so B/C can be fairly compared.
        if draft_mode not in ("single","split_only","causal_guard","rolling_causal","emotion_rolling","foresight_rolling","continuity_guard"):
            raise WritingExecutionError("WF96_DRAFT_MODE_NOT_OPTED_IN")
        if draft_mode=="continuity_guard":
            try:
                require_external_runtime()
            except V114ExternalMemoryError as exc:
                raise WritingExecutionError(str(exc)) from None
        if draft_mode=="single" and (
           frozen_turn_outlines is not None or
           author_confirmed_forbidden_phrases):
            raise WritingExecutionError(
                "WF96_LEGACY_SINGLE_CANNOT_SILENTLY_IGNORE_NEW_GUARDS")
        if draft_mode!="foresight_rolling" and (
            forward_author_pinned_facts is not None or
            resume_candidate_checkpoint is not None):
            raise WritingExecutionError(
                "WF105_FORWARD_ONLY_GUARDS_CANNOT_BE_IGNORED_BY_OTHER_MODES")
        if draft_mode!="continuity_guard" and (
            resume_story_checkpoint is not None or
            continuity_reference is not None or
            long_arc_checkpoint is not None or
            narrative_core_checkpoint is not None or
            scene_delivery_contracts is not None):
            raise WritingExecutionError(
                "WF117_TEXT_CONTINUITY_ONLY_PARAMETERS_REFUSED")
        # A selected fork forbids continuing from an older, still-valid
        # historical descendant in THIS new branch. Other old branches remain
        # immutable archives; the selection must be supplied explicitly.
        if selected_fork_receipt is not None:
            if type(resume_story_checkpoint) is not dict:
                raise WritingExecutionError(
                    "WF_CHAPTER_FORK_SELECTED_RESUME_REQUIRED")
            _validate_unaccepted_fork_resume(
                fork_receipt=selected_fork_receipt,
                candidate_resume=resume_story_checkpoint,
                project_id=self.assist.project_id,
                scene_id=self.assist.scene_id)
        # Source-checkpoint resume is explicit, signed, project-scoped, and
        # NEVER silently imports a previous unaccepted draft as canon.
        earlier_external=None
        active_long_arc=None
        active_narrative_core=None
        first_story_chapter_index=0
        if bootstrap_unified_core:
            # An opt-in local Studio G task starts a genuine single unified
            # narrative graph at chapter zero; the first real source chapter
            # advances to 1. Do not initialize a competing memory owner.
            active_narrative_core=new_unified_narrative_graph(
                project_id=self.assist.project_id,
                scene_id=self.assist.scene_id)
            first_story_chapter_index=1
        if resume_story_checkpoint is not None:
            try:
                earlier_external=read_resume(
                    resume_story_checkpoint,
                    project_id=self.assist.project_id,
                    scene_id=self.assist.scene_id)
                first_story_chapter_index=(
                    resume_story_checkpoint["chapter_index"]+1)
                active_long_arc=read_long_arc_from_resume(
                    resume_story_checkpoint,
                    project_id=self.assist.project_id,
                    scene_id=self.assist.scene_id)
                active_narrative_core=read_core_from_resume(
                    resume_story_checkpoint,
                    project_id=self.assist.project_id,
                    scene_id=self.assist.scene_id)
                if active_narrative_core is not None:
                    from .v117_continuity_trace import (
                        _verify_unified_temporal_source_link)
                    # Old V117 files remain READABLE for forensic recovery,
                    # but an unbound old FULL chapter + unrelated LAST turn
                    # may NEVER become a trusted parent of NEW model prose.
                    _verify_unified_temporal_source_link(
                        active_narrative_core,earlier_external,
                        resume_story_checkpoint["chapter_index"],
                        require_strong_for_new=True,
                        require_verified_ancestry=True)
            except (ContinuityTraceError,LongArcError,NarrativeCoreError) as exc:
                raise WritingExecutionError(str(exc)) from None
        if long_arc_checkpoint is not None:
            try:
                verified=verify_long_arc(
                    long_arc_checkpoint,
                    project_id=self.assist.project_id,
                    scene_id=self.assist.scene_id)
                if resume_story_checkpoint is None:
                    raise LongArcError(
                        "WF123_LONG_ARC_REQUIRES_PRIOR_STORY_RESUME")
                if verified["last_chapter"]!=(
                        resume_story_checkpoint["chapter_index"]):
                    raise LongArcError("WF123_ARC_CHAPTER_NOT_CONTIGUOUS")
                if active_long_arc is not None and (
                        verified["receipt_sha256"]!=
                        active_long_arc["receipt_sha256"]):
                    raise LongArcError("WF123_ARC_CONFLICTS_WITH_RESUME")
                active_long_arc=verified
            except LongArcError as exc:
                raise WritingExecutionError(str(exc)) from None
        if narrative_core_checkpoint is not None:
            try:
                core=verify_narrative_core(
                    narrative_core_checkpoint,
                    project_id=self.assist.project_id,
                    scene_id=self.assist.scene_id)
                if resume_story_checkpoint is None or (
                        core["chapter_index"]!=
                        resume_story_checkpoint["chapter_index"]):
                    raise NarrativeCoreError(
                        "WFCORE_EXPLICIT_STATE_REQUIRES_MATCHED_STORY_RESUME")
                if active_narrative_core is not None and (
                        core["receipt_sha256"]!=
                        active_narrative_core["receipt_sha256"]):
                    raise NarrativeCoreError(
                        "WFCORE_EXPLICIT_STATE_CONFLICTS_WITH_RESUME")
                active_narrative_core=core
            except NarrativeCoreError as exc:
                raise WritingExecutionError(str(exc)) from None
        if active_narrative_core is not None and active_long_arc is not None:
            raise WritingExecutionError(
                "WFCORE_DUPLICATE_LONG_ARC_OWNERS_NOT_ALLOWED")
        if active_narrative_core is not None and narrative_store is None:
            mem=active_narrative_core.get("memory") or {}
            remote=(any(entry.get("source_path","").startswith("r2://")
                        for entry in mem.get("hot",[])+mem.get("warm",[]))
                    or type(mem.get("cold_head")) is dict and
                    mem["cold_head"].get("path","").startswith("r2://"))
            if remote:
                raise WritingExecutionError(
                    "WFCORE_REMOTE_STORY_REQUIRES_R2_BACKEND")
        if draft_mode!="single" and len(chapter_goals)>MAX_SEGMENTED_CHAPTERS_PER_JOB:
            raise WritingExecutionError(
                "WF96_SEGMENTED_CHAPTER_REQUEST_BUDGET_EXCEEDED")
        if frozen_turn_outlines is not None and (
             type(frozen_turn_outlines) is not tuple or
             len(frozen_turn_outlines)!=len(chapter_goals) or
             not all(type(s) is str for s in frozen_turn_outlines)):
            raise WritingExecutionError("WF96_FROZEN_OUTLINE_COUNT_MISMATCH")
        if not isinstance(outline,str) or not 15<=len(outline.strip())<=MAX_OUTLINE_CHARS:
            raise WritingExecutionError("outline requires 15..6000 characters")
        if (not isinstance(chapter_goals,list) or not 1<=len(chapter_goals)<=MAX_CHAPTERS
            or any(not isinstance(x,str) or not 8<=len(x.strip())<=450
                   for x in chapter_goals)):
            raise WritingExecutionError("provide 1..6 chapter goals of 8..450 characters each")
        if scene_delivery_contracts is not None:
            if (type(scene_delivery_contracts) is not tuple or
                len(scene_delivery_contracts)!=len(chapter_goals)):
                raise WritingExecutionError(
                    "WFCORE_SCENE_CONTRACT_COUNT_INVALID")
            try:
                for c in scene_delivery_contracts:
                    validate_scene_delivery_contract(c)
            except NarrativeCoreError as error:
                raise WritingExecutionError(str(error)) from None
        # Validate author-pinned world and optional immutable old candidate
        # checkpoint BEFORE creating a directory or reserving an LLM call.
        pinned_world={}
        checkpoint=None
        if draft_mode=="foresight_rolling":
            try:
                pinned_world=_frozen_author_world(
                    forward_author_pinned_facts or {})
                if resume_candidate_checkpoint is not None:
                    _validate_prior_checkpoint(
                        resume_candidate_checkpoint,
                        sha256(outline.encode("utf8")).hexdigest())
                    checkpoint=resume_candidate_checkpoint
            except V105FutureCausalityError as exc:
                raise WritingExecutionError(str(exc)) from None
        # A cross-chapter fork is only an explicit AI-proposed candidate
        # branch. Validate the old source and its complete signed graph chain
        # BEFORE creating the next job or making model calls.
        cross_chapter_plan=None
        if cross_chapter_fork is not None:
            if (draft_mode!="continuity_guard" or
                bootstrap_unified_core or
                narrative_memory_backend!="local" or
                type(resume_story_checkpoint) is not dict or
                type(cross_chapter_fork) is not dict or
                set(cross_chapter_fork)!={
                    "source_job_dir","writer_decision_reply",
                    "expected_old_head_sha256"}):
                raise WritingExecutionError(
                    "WF_CHAPTER_FORK_EXPLICIT_LOCAL_G_ONLY")
            cross_chapter_plan=_prepare_unaccepted_chapter_fork(
                source_job_dir=cross_chapter_fork["source_job_dir"],
                writer_decision_reply=cross_chapter_fork["writer_decision_reply"],
                expected_old_head_sha256=cross_chapter_fork[
                    "expected_old_head_sha256"],
                retained_resume=resume_story_checkpoint,
                project_id=self.assist.project_id,
                scene_id=self.assist.scene_id,
                outline_sha256=sha256(outline.encode("utf8")).hexdigest(),
                source_snapshot_id=self.assist.rt.pinned_snapshot_id,
                model_used=self.assist.model,
                chapter_count=len(chapter_goals))
        root=Path(output_dir)
        root.mkdir(parents=True,exist_ok=True)
        # Reject instead of silently deleting an author's older drafts. This
        # is a storage quota, not an unbounded new memory or project database.
        saved_runs=sum(1 for d in root.iterdir()
                       if d.is_dir() and d.name.startswith("auto-"))
        if saved_runs>=MAX_STORED_AUTONOMOUS_RUNS:
            raise WritingExecutionError("autonomous draft history is full (32 runs); archive prior runs before continuing")
        stamp=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        job=root/("auto-"+stamp)
        job.mkdir(exist_ok=False)
        if cross_chapter_plan is not None:
            (job/"cross-chapter-fork-intent.json").write_text(
                json.dumps(cross_chapter_plan,ensure_ascii=False,
                           indent=2),encoding="utf8")
        check_cancel()
        outline_hash=sha256(outline.encode("utf-8")).hexdigest()
        previous=""
        chapters=[]
        issued_turns=0
        self_edit_model_calls=0
        writer_rewind_count=0  # Bounded to one previous-turn branch per job.
        rolling_replan_calls=0
        g_rolling_source_skips=[]
        previous_emotional_turns=()
        previous_continuity_checkpoint=None
        previous_external_story_checkpoint=earlier_external
        for index,goal in enumerate(chapter_goals,1):
            chapter_contract=(
                scene_delivery_contracts[index-1]
                if scene_delivery_contracts is not None else None)
            last_chapter_pressure=(
                pressure_context(previous_emotional_turns)
                if draft_mode in ("emotion_rolling","foresight_rolling") and
                previous_emotional_turns else "")
            continuing_pressure=(
                open_debt_context(checkpoint)
                if draft_mode=="foresight_rolling" and checkpoint else "")
            prospective_report=None
            host_only_branch_receipt=None
            future_note=""
            earlier_item_state=(
                temporal_prompt(previous_external_story_checkpoint)
                if draft_mode=="continuity_guard" and
                   previous_external_story_checkpoint else "")
            current_continuity_checkpoint=previous_continuity_checkpoint
            current_external_story_checkpoint=previous_external_story_checkpoint
            if progress:
                progress(index,len(chapter_goals),"planning")
            arc_chapter_hint=(
                relevant_revenge_hint(
                    active_long_arc,project_id=self.assist.project_id,
                    scene_id=self.assist.scene_id,goal=goal)
                if active_long_arc is not None else "")
            scene=_writing_scene_scope(
                self.assist.scene_id,local_index=index,
                resume_source_chapter=(
                    resume_story_checkpoint["chapter_index"]
                    if draft_mode=="continuity_guard" and
                       resume_story_checkpoint is not None else None))
            base=self.assist.flow.prepare(
                scene,goal,concerns=("scene","decision"),
                genre=self.assist.source_genre,
            )
            plan_addition=(
                "\n原创新作的大纲：\n"+outline
                +"\n本章目标：\n"+goal
                +"\n上一章仅为候选、尚未作者接受的末尾：\n"+(previous[-260:] if active_narrative_core is not None
                    else previous[-700:])
                +("\n【上章尚未证实的情感后果和待处理代价】"+
                  last_chapter_pressure if last_chapter_pressure else "")
                +("\n【过去数章未偿压力的只读候选账本】"+
                  continuing_pressure if continuing_pressure else "")
                +("\n【前章已写正文的物件与角色状态（候选，并非正典）】"+
                  earlier_item_state if earlier_item_state else "")
                +("\n"+arc_chapter_hint if arc_chapter_hint else "")
                +"\n请先规划本章，不写正文。必须明确人物目的、冲突、选择、后果和视角；"
                "内部调用结构技法，不照搬原著。只返回 JSON："
                '{"objective":"...","conflict":"...","decision":"...",'
                '"outcome":"...","pov":"...","needs":["dialogue","decision"]}'
                +(horizon_prompt(pinned_world=pinned_world)
                  if draft_mode=="foresight_rolling" else "")
                +("\n【本章构思不是命运】不同人物可以因自身目标、"
                  "认知和眼前冲突改变初始选择，结局只作候选；"
                  "正文的真实决定和后果优先于预写大纲。"
                  if active_narrative_core is not None else "")
            )
            plan_prompt=_enrich(base,plan_addition,prose_task=False)
            if active_narrative_core is not None:
                # A writer considers independent character motives at
                # planning time, but the authored result is still provisional.
                # The warm buffer is for continuity of voice, mood, pacing;
                # protected hard knowledge and physical state remain separate.
                planning_notes=(
                    character_collision_context(
                        active_narrative_core,
                        project_id=self.assist.project_id,
                        scene_id=self.assist.scene_id,
                        scene_goal=goal,max_chars=800),
                    buffered_memory_context(
                        active_narrative_core,
                        project_id=self.assist.project_id,
                        scene_id=self.assist.scene_id,
                        max_chars=700),
                    relevant_history_context(
                        active_narrative_core,
                        project_id=self.assist.project_id,
                        scene_id=self.assist.scene_id,
                        scene_goal=goal,max_chars=650,
                        source_reader=(narrative_store.read_original
                                       if narrative_store else None),
                        archive_reader=(narrative_store.read_capsule
                                        if narrative_store else None)))
                plan_tail=""
                for note in planning_notes:
                    if note and len(plan_prompt.prompt)+len(plan_tail)+len(
                            note)+1<=MAX_PROMPT_CHARS:
                        plan_tail+="\n"+note
                if plan_tail:
                    plan_prompt=_enrich(
                        base,plan_addition+plan_tail,prose_task=False)
            plan_raw=ask_model(
                plan_prompt,model=self.assist.model,
                api_base=self.assist.api_base,
                max_tokens=(2400 if draft_mode=="foresight_rolling"
                            else 650),
            )
            if draft_mode=="foresight_rolling":
                # Preserve the ORIGINAL student plan before any shape check.
                # Never reveal it in public error receipts; job_dir is private.
                (job/f"chapter-{index:03d}-raw-plan.json").write_text(
                    plan_raw,encoding="utf8")
            try:
                plan=_chapter_plan(plan_raw,goal)
            except WritingExecutionError:
                if draft_mode=="foresight_rolling":
                    issue={
                        "format":"wf.writing.failed-foresight-preflight.v105",
                        "chapter":index,"draft_mode":draft_mode,
                        "code":"WF105_ORIGINAL_CHAPTER_PLAN_INVALID",
                        "original_plan_sha256":
                            sha256(plan_raw.encode("utf8")).hexdigest(),
                        "new_model_retries":0,"accepted_prose":False,
                        "canon_writes":0,
                    }
                    (job/f"chapter-{index:03d}-foresight-rejected.json").write_text(
                        json.dumps(issue,ensure_ascii=False,indent=2),
                        encoding="utf8")
                raise
            if draft_mode=="foresight_rolling":
                try:
                    plan_obj=_decode_json(plan_raw)
                    raw_horizon=plan_obj.get("horizon")
                    try:
                        prospective_report=validate_horizon(
                            raw_horizon,author_pinned=pinned_world)
                    except V105FutureCausalityError as primary:
                        if str(primary)!="WF105_BRANCH_ID_NOT_UNIQUE":
                            raise
                        # Original model choice/action/debt text is not
                        # edited; route labels are host-owned metadata.
                        # The byte-exact JSON remains the raw-plan file.
                        derived,host_only_branch_receipt=(
                            recover_host_branch_identity(raw_horizon))
                        prospective_report=validate_horizon(
                            derived,author_pinned=pinned_world)
                    future_note=horizon_context(prospective_report)
                    if all(b["status"]=="SYMBOLICALLY_BLOCKED"
                           for b in prospective_report["branches"]):
                        raise V105FutureCausalityError(
                            "WF105_ALL_FUTURE_PATHS_SYMBOLICALLY_BLOCKED")
                except (V105FutureCausalityError,V110IdentityError,ValueError) as exc:
                    # Preserve a red receipt: never recharge by retrying.
                    issue={"format":"wf.writing.failed-foresight-preflight.v105",
                           "chapter":index,"draft_mode":draft_mode,
                           "code":str(exc) if str(exc).startswith(
                               ("WF105_","WF110_"))
                                  else "WF105_FORECAST_INVALID",
                           "original_plan_sha256":
                               sha256(plan_raw.encode("utf8")).hexdigest(),
                           "new_model_retries":0,"accepted_prose":False,
                           "canon_writes":0}
                    (job/f"chapter-{index:03d}-foresight-rejected.json").write_text(
                        json.dumps(issue,ensure_ascii=False,indent=2),
                        encoding="utf8")
                    raise WritingExecutionError(issue["code"]) from None
            if progress:
                progress(index,len(chapter_goals),"drafting")
            body_base=self.assist.flow.prepare(
                scene,goal,concerns=_craft_needs(plan["needs"]),
                genre=self.assist.source_genre,
                # 0.BL: conditional reviewed Xuehai methods ONLY on the
                # real prose-writing seam, not on planning or self-edit.
                xuehai_methods_enabled=xuehai_methods_enabled,
            )
            inferred=infer_intent(goal+"\n"+plan["objective"]+"\n"+plan["conflict"])
            facets=_verified_facets(self.assist.db,inferred)
            packet=_enrich(
                body_base,
                "\n【完整原创大纲】\n"+outline[:2300]
                +"\n【本章内部规划】\n"+json.dumps(plan,ensure_ascii=False)
                +"\n【上一章尚未被作者接受的候选末尾】\n"+previous[-700:]
                +("\n【上章遗留人物变化和未解决后果】"+
                  last_chapter_pressure if last_chapter_pressure else "")
                +("\n【过去未偿债务不可凭空消失】"+
                  continuing_pressure if continuing_pressure else "")
                +("\n【未来多步备选路径与危险前提，均未发生】"+
                  future_note if future_note else "")
                +("\n【已经写过的连续性信息，不得凭空转移物品】"+
                  earlier_item_state if earlier_item_state else "")
                +"\n请按照因果、人物决定和冲突结果写完整原创正文，"
                "不要解释技巧，也不要复制原著人物、设定或句子。",
                facets,
            )
            turn_evidence=None
            turn_outline=None
            if draft_mode=="single":
                body=ask_model(
                    packet,model=self.assist.model,
                    api_base=self.assist.api_base,max_tokens=2600,
                )
            else:
                # The existing whole-chapter outline remains a provisional
                # scene purpose. The additional turn plan is shared by B/C.
                extra_outline=_enrich(
                    body_base,
                    "\n【本章目标（不是已成事实）】"+goal+
                    "\n【已有候选章节计划】"+json.dumps(
                        plan,ensure_ascii=False)+
                    "\n规划2到12个真正必要的叙事事件，允许安静过渡，"
                    "不强迫每段反转。只输出JSON对象turns数组，"
                    "每项字段：id(t01等顺序)、kind(action/decision/"
                    "reversal/setup/dialogue/quiet/aftermath/transition)、"
                    "actor、goal、causal_parent(之前已规划事件的id或null；"
                    "对话、安静观察可作顺序承接，但并不证明因果)、"
                    "craft_focus(0到2个："
                    "dialogue/detail/interiority/pacing/restraint/contrast/"
                    "action/none)。只做滚动短计划，不写正文；"
                    "不把模型猜测变成角色已经知道的事实。",
                    facets,prose_task=False,
                )
                turn_outline=(
                    frozen_turn_outlines[index-1]
                    if frozen_turn_outlines is not None else
                    ask_model(
                        extra_outline,model=self.assist.model,
                        api_base=self.assist.api_base,max_tokens=1450,
                    )
                )
                optional_craft_compatibility=None
                if (draft_mode=="continuity_guard" and
                    frozen_turn_outlines is None):
                    raw_turn_outline=turn_outline
                    turn_outline,optional_craft_compatibility=(
                        _normalize_optional_model_craft_labels(turn_outline))
                    if optional_craft_compatibility is not None:
                        (job/f"chapter-{index:03d}-raw-model-turn-outline.json").write_text(
                            raw_turn_outline,encoding="utf8")
                accepted_turns=[]
                accepted_beats=[]
                selected_turn_raws=[]  # The real source and ALL trace fields.
                # Snapshots of the ACTUAL V114 state after each authored
                # short turn. Rewind together with every other derived list.
                turn_external_checkpoints=[]
                trace_checks=[]
                last_lamp_receipt=None
                lamp_decisions=[]
                long_arc_checks=[]
                narrative_lane_decisions=[]
                narrative_source_reviews=[]
                unified_prose_replay_checks=[]
                unified_scene_delivery_turn_checks=[]
                source_citation_normalizations=[]
                model_trace_review_failures=[]
                self_edit_turn_receipts=[]
                self_edit_moment_receipts=[]
                self_edit_reader_receipts=[]
                self_edit_rewind_receipts=[]
                turn_snapshots=[]
                pending_revised_turn=None
                pending_original_turn=None
                rewind_pending=None
                redraw_turn_index=None
                source_length_reviews=[]
                prompt_delivery_receipts=[]
                plan_execution_checks=[]
                rolling_receipts=[]
                rolling_goals=[]
                rolling_prompt_shas=[]
                last_turn_response=""
                try:
                    beats=parse_turn_outline(turn_outline)
                    if issued_turns+len(beats)>MAX_SEGMENTED_TOTAL_TURNS:
                        raise V96CausalDraftError(
                            "WF96_TOTAL_SEGMENTED_MODEL_CALL_BUDGET_EXCEEDED")
                    issued_turns+=len(beats)
                    prompt_shas=[]
                    # Model-authored dialogue may name multiple people in
                    # ONE beat ("林槐/许照"). They are separate cast members,
                    # not a fictional third person or a shared-knowledge POV.
                    # Keep the original model beat untouched and source-signed.
                    cast=tuple(dict.fromkeys(
                        person for beat in beats
                        for person in (beat["actor"].split("/")
                            if "/" in beat["actor"] else (beat["actor"],))))
                    turn_index=0
                    while turn_index<len(beats):
                        try:
                            seed_beat=beats[turn_index]
                            if draft_mode=="continuity_guard":
                                # All of these are DERIVED from still-unaccepted
                                # prose. Restore their lengths and prior V114/V117
                                # state together when revising a previous turn.
                                tracked_rewind_lists=(
                                    accepted_turns,accepted_beats,
                                    selected_turn_raws,turn_external_checkpoints,
                                    trace_checks,
                                    lamp_decisions,long_arc_checks,
                                    narrative_lane_decisions,narrative_source_reviews,
                                    unified_prose_replay_checks,
                                    unified_scene_delivery_turn_checks,
                                    source_citation_normalizations,
                                    model_trace_review_failures,
                                    self_edit_turn_receipts,
                                    self_edit_moment_receipts,
                                    self_edit_reader_receipts,source_length_reviews,
                                    prompt_delivery_receipts,plan_execution_checks,
                                    prompt_shas,rolling_receipts,rolling_goals,
                                    rolling_prompt_shas,g_rolling_source_skips)
                                turn_snapshots.append({
                                    "counts":tuple(len(a) for a in
                                                   tracked_rewind_lists),
                                    "continuity":current_continuity_checkpoint,
                                    "external":current_external_story_checkpoint,
                                    "lamp":last_lamp_receipt})
                            beat=seed_beat
                            # 0.AV true original fiction A/B: t03 and t04
                            # remain readable signed prose even when their
                            # model trace is REVIEW-only. The old G stopped
                            # letting the author rethink the next character
                            # choice, fell back to frozen goals at t04/t05,
                            # and repeated the opening valve orders. In the
                            # existing G opt-in, offer the SAME model the
                            # current literal prose as unverified writer
                            # material; NEVER convert its story to a V96
                            # observed effect or narrative KNOWN fact.
                            g_replan=False
                            g_prose_only_author_replan=False
                            if g_rolling_author_planning and turn_index>0:
                                from .v98_rolling_causal_planner import (
                                    g_source_replan_eligibility)
                                eligibility=g_source_replan_eligibility(
                                    tuple(accepted_turns),
                                    allow_prose_only=True)
                                if eligibility["eligible"]:
                                    g_replan=True
                                    g_prose_only_author_replan=(
                                        eligibility["prose_only_unverified"])
                                else:
                                    g_rolling_source_skips.append({
                                        "turn_id":seed_beat["id"],
                                        "reason":eligibility["reason"],
                                        "source_sha256":eligibility["source_sha256"],
                                        "no_plan_model_call":True,
                                        "literary_truth_proven":False})
                            if (draft_mode in ("rolling_causal","emotion_rolling","foresight_rolling")
                                or g_replan) and turn_index>0:
                                if rolling_replan_calls>=MAX_ROLLING_REPLANS_PER_JOB:
                                    raise V98RollingPlanError(
                                        "WF98_REPLAN_MODEL_CALL_BUDGET_EXCEEDED")
                                instructions=prepare_replan_instructions(
                                    accepted=tuple(accepted_turns),
                                    seed_next_beat=seed_beat,
                                    allowed_actor_names=cast,
                                    allow_g_prose_only=(
                                        g_prose_only_author_replan))
                                if draft_mode in ("emotion_rolling","foresight_rolling"):
                                    instructions+=(
                                        "\n【人物变化/待解决代价】"+
                                        pressure_context(tuple(accepted_turns))+
                                        ("\n【多步前瞻及危险条件】"+future_note
                                          if draft_mode=="foresight_rolling" else "")+
                                        ("\n【跨章节仍欠的压力】"+continuing_pressure
                                          if draft_mode=="foresight_rolling" and
                                          continuing_pressure else ""))
                                rolling_packet=_enrich(
                                    body_base,
                                    "\n【本章总目标，未完成的规划不是故事事实】"+goal+
                                    instructions,
                                    facets,prose_task=False,
                                )
                                rolling_prompt_shas.append(
                                    rolling_packet.prompt_sha256)
                                rolling_replan_calls+=1
                                last_turn_response=ask_model(
                                    rolling_packet,model=self.assist.model,
                                    api_base=self.assist.api_base,max_tokens=650,
                                )
                                if draft_mode in ("foresight_rolling","continuity_guard"):
                                    (job/f"chapter-{index:03d}-replan-"
                                         f"{turn_index+1:02d}-raw.json").write_text(
                                        last_turn_response,encoding="utf8")
                                beat,rolling_receipt=validate_replan(
                                    last_turn_response,
                                    accepted=tuple(accepted_turns),
                                    accepted_beats=tuple(accepted_beats),
                                    seed_next_beat=seed_beat,
                                    allowed_actor_names=cast,
                                    author_forbidden_phrases=(
                                        author_confirmed_forbidden_phrases),
                                    allow_g_prose_only=(
                                        g_prose_only_author_replan))
                                rolling_receipts.append(rolling_receipt)
                                rolling_goals.append(dict(beat))
                            turn_addition=make_turn_instructions(
                                beat,mode=("causal_guard" if
                                           draft_mode in ("rolling_causal","emotion_rolling","foresight_rolling","continuity_guard")
                                           else draft_mode),accepted=accepted_turns,
                                author_confirmed_forbidden_phrases=(
                                    author_confirmed_forbidden_phrases))
                            if (g_rolling_author_planning and
                                turn_index>0):
                                # Real 0.AV literary RED: the next-beat AI
                                # saw original t01 prose, but the PROSE AI
                                # was deprived of it and re-cut the signal.
                                # Source is a signed literal, not a host
                                # judgement about whether repetition is bad.
                                turn_addition+=author_signed_prior_prose_for_writer(
                                    tuple(accepted_turns))
                            if draft_mode=="continuity_guard":
                                turn_addition+=(
                                    "\n【真正参与下一段创作的时态物件状态（MIT Novel Studio原子归约）】"
                                    +(temporal_prompt(current_external_story_checkpoint)
                                      if current_external_story_checkpoint else
                                      "上一段尚无已观察持有者。剑、符、信物转移必须"
                                      "写出真实动作；法力消耗后不能无来源恢复。"
                                      "无法确认就保留未知，不必强塞牺牲。"))
                                if current_external_story_checkpoint is not None:
                                    trace_frame=audit_continuity(
                                        current_external_story_checkpoint,
                                        project_id=self.assist.project_id,
                                        chapter_index=first_story_chapter_index+index-1,
                                        reference=continuity_reference)
                                    turn_addition+=("\n"+compact_context(trace_frame))
                            if (draft_mode=="continuity_guard" and
                                active_long_arc is not None):
                                active_arc_hint=relevant_revenge_hint(
                                    active_long_arc,
                                    project_id=self.assist.project_id,
                                    scene_id=self.assist.scene_id,beat=beat)
                                if active_arc_hint:
                                    # Unlike the optional style lamp, a relevant
                                    # author-registered open goal is a durable
                                    # constraint and cannot be silently dropped.
                                    turn_addition+="\n"+active_arc_hint
                            if draft_mode in ("emotion_rolling","foresight_rolling"):
                                turn_addition+=emotion_turn_instructions(
                                    tuple(accepted_turns))
                                if last_chapter_pressure and turn_index==0:
                                    turn_addition+=(
                                        "\n【上章情感与代价不得凭空消失】"+
                                        last_chapter_pressure)
                                if draft_mode=="foresight_rolling":
                                    turn_addition+=(
                                        "\n【可行未来的选择及前提（并非事实）】"+
                                        future_note)
                                    if continuing_pressure:
                                        turn_addition+=(
                                            "\n【以前章节尚未偿付的代价】"+
                                            continuing_pressure)
                            if draft_mode=="continuity_guard":
                                # The V120 direct causal debt is optional advice,
                                # not a reason to evict source-grounded memory.
                                dependency_hint=pending_dependency_hint(
                                    beat,plan_execution_checks)
                                progression_cue=(
                                    _source_progression_literary_cue(
                                        tuple(accepted_turns))
                                    if literary_progression_mode=="source_progression"
                                    else "")
                                turn_packet,lamps,delivery=(
                                    _prepare_guarded_turn_packet(
                                        body_base,plan=(
                                            g_writer_active_plan_view(plan)
                                            if g_rolling_author_planning and turn_index>0
                                            else plan),
                                        hard_turn_addition=turn_addition,
                                        facets=facets,
                                        dependency_hint=dependency_hint,
                                        project_id=self.assist.project_id,
                                        chapter_index=first_story_chapter_index+index-1,
                                        turn_index=turn_index,beat=beat,
                                        frame=(trace_frame if
                                               current_external_story_checkpoint is not None
                                               else None),
                                        previous_lamp_receipt=last_lamp_receipt,
                                        narrative_graph=active_narrative_core,
                                        narrative_scene_id=self.assist.scene_id,
                                        working_memory_context=(
                                            buffered_memory_context(
                                                active_narrative_core,
                                                project_id=self.assist.project_id,
                                                scene_id=self.assist.scene_id)
                                            if active_narrative_core is not None
                                            else ""),
                                        creative_progression_cue=progression_cue))
                                if delivery["unified_narrative_priority_dispatch"]:
                                    narrative_lane_decisions.append(
                                        delivery["unified_narrative_priority_dispatch"])
                                # _prepare signs the complete delivery receipt
                                # after cue allocation. Never mutate it afterward.
                                lamp_decisions.append(lamps)
                                prompt_delivery_receipts.append(delivery)
                                last_lamp_receipt=lamps
                            else:
                                turn_packet=_enrich(
                                    body_base,
                                    "\n【原创章计划】"+json.dumps(
                                        plan,ensure_ascii=False)+
                                    "\n【本章当前事件】"+turn_addition,
                                    facets,
                                )
                            prompt_shas.append(turn_packet.prompt_sha256)
                            replaying_revised_source=(
                                pending_revised_turn is not None and
                                pending_revised_turn[0]==turn_index)
                            replaying_original_source=(
                                pending_original_turn is not None and
                                pending_original_turn[0]==turn_index)
                            is_regenerated_turn=False
                            if replaying_revised_source:
                                # The SAME AI revised this already. Re-evaluate
                                # the edited source; do not pay to invent it again.
                                last_turn_response=pending_revised_turn[1]
                                pending_revised_turn=None
                            elif replaying_original_source:
                                # Retain byte-exact original second-turn answer.
                                # It must still pass every ordinary V96/V114/V117
                                # and unified-graph check before final save.
                                last_turn_response=pending_original_turn[1]
                                pending_original_turn=None
                            else:
                                if (draft_mode=="continuity_guard" and
                                    redraw_turn_index==turn_index):
                                    is_regenerated_turn=True
                                    if (self_edit_model_calls>=
                                        SELF_EDIT_MAX_PROVIDER_CALLS_PER_RUN):
                                        raise WritingExecutionError(
                                            "WF_WRITER_REWIND_REDRAFT_BUDGET")
                                    self_edit_model_calls+=1
                                    redraw_turn_index=None
                                last_turn_response=ask_model(
                                    turn_packet,model=self.assist.model,
                                    api_base=self.assist.api_base,max_tokens=1450,
                                )
                            if (not replaying_revised_source and
                                not replaying_original_source and
                                draft_mode in ("foresight_rolling",
                                               "continuity_guard")):
                                # A failed redraft must never overwrite the
                                # previous original provider answer.
                                raw_suffix=("-regenerated-01-raw.json"
                                            if is_regenerated_turn else "-raw.json")
                                (job/(f"chapter-{index:03d}-turn-"
                                      f"{turn_index+1:02d}"+raw_suffix)).write_text(
                                          last_turn_response,encoding="utf8")
                            if (draft_mode=="continuity_guard" and
                                self_edit_rounds>0 and
                                not replaying_revised_source and
                                not replaying_original_source):
                                old_raw=last_turn_response
                                def invoke_self_edit(packet,*,model,
                                                     api_base,max_tokens):
                                    if max_tokens not in (
                                        SELF_EDIT_MODEL_MAX_TOKENS,
                                        SELF_EDIT_MOMENT_TOKENS,
                                        SELF_EDIT_READER_MAX_TOKENS,
                                        SELF_EDIT_ATTRIBUTION_TOKENS):
                                        raise WritingExecutionError(
                                            "WF_SELF_EDIT_MODEL_BUDGET_CHANGED")
                                    return ask_model(
                                        packet,model=self.assist.model,
                                        api_base=self.assist.api_base,
                                        max_tokens=max_tokens)
                                moment=None
                                reader_result=None
                                if (reader_first_self_review and
                                    self_edit_timing=="ai_decides"):
                                    remaining=max(
                                        0,SELF_EDIT_MAX_PROVIDER_CALLS_PER_RUN-
                                        self_edit_model_calls)
                                    if remaining>=2:
                                        prior_reader_source=(
                                            accepted_turns[-1]["prose"]
                                            if accepted_turns else None)
                                        if (prior_reader_source is None and
                                            active_narrative_core is not None):
                                            previous_chapter=(
                                                first_story_chapter_index+index-2)
                                            if previous_chapter>=0:
                                                try:
                                                    prior_reader_source=recall_original(
                                                        active_narrative_core,
                                                        project_id=self.assist.project_id,
                                                        scene_id=self.assist.scene_id,
                                                        chapter_index=previous_chapter,
                                                        max_pages=30,
                                                        source_reader=(
                                                            narrative_store.read_original
                                                            if narrative_store else None),
                                                        archive_reader=(
                                                            narrative_store.read_capsule
                                                            if narrative_store else None))
                                                except (NarrativeCoreError,
                                                        R2StorageError,OSError):
                                                    prior_reader_source=None
                                        if (type(prior_reader_source) is not str or
                                            not 1<=len(prior_reader_source)<=5000):
                                            prior_reader_source=None
                                        reader_result=(
                                            _reader_separates_written_and_inferred(
                                                raw=last_turn_response,
                                                turn_packet=turn_packet,
                                                ask_model=invoke_self_edit,
                                                directory=job/(
                                                    f"chapter-{index:03d}-turn-"
                                                    f"{turn_index+1:02d}-reader-first"
                                                    +("-replay" if writer_rewind_count
                                                      else "")),
                                                cancel_check=check_cancel,
                                                earlier_source=prior_reader_source,
                                                earlier_source_sha256=(
                                                    sha256(prior_reader_source.encode(
                                                        "utf8")).hexdigest()
                                                    if prior_reader_source is not None
                                                    else None)))
                                        self_edit_model_calls+=reader_result[
                                            "model_calls"]
                                        self_edit_reader_receipts.append(
                                            reader_result["receipt"])
                                    else:
                                        self_edit_reader_receipts.append({
                                            "format":"wf.writer.reader-source-before-self-judgment.v1",
                                            "status":"NO_BUDGET_RESERVED_FOR_AUTHOR_CHOICE",
                                            "model_calls":0,
                                            "canon_writes":0,
                                            "literary_quality_verified":False})
                                if self_edit_timing=="ai_decides":
                                    remaining=max(
                                        0,SELF_EDIT_MAX_PROVIDER_CALLS_PER_RUN-
                                        self_edit_model_calls)
                                    if remaining>0:
                                        moment=_ai_decides_when_to_revisit(
                                            raw=last_turn_response,beat=beat,
                                            accepted=tuple(accepted_turns),
                                            turn_packet=turn_packet,
                                            ask_model=invoke_self_edit,
                                            source_checkpoint=(
                                                current_external_story_checkpoint),
                                            directory=job/(
                                                f"chapter-{index:03d}-turn-"
                                                f"{turn_index+1:02d}-ai-moment"
                                                +("-replay" if writer_rewind_count
                                                  else "")),
                                            cancel_check=check_cancel,
                                            reader_report=(
                                                reader_result.get("report")
                                                if reader_result is not None
                                                else None),
                                            source_identity_contract=(
                                                "bind_null_current"
                                                if reader_first_self_review
                                                else "model_sha"),
                                            earlier_source_for_attribution=(
                                                prior_reader_source
                                                if (reader_first_self_review
                                                    and reader_result is not None
                                                    and reader_result.get("report")
                                                    and reader_result["report"].get(
                                                        "cross_source_links"))
                                                else None))
                                        self_edit_model_calls+=moment["model_calls"]
                                    else:
                                        moment={
                                            "decision":"BUDGET_EXHAUSTED",
                                            "model_calls":0,
                                            "reason":None,
                                            "receipt":{
                                                "decision":"BUDGET_EXHAUSTED",
                                                "model_calls":0,
                                                "literary_quality_verified":False}}
                                    self_edit_moment_receipts.append(
                                        moment["receipt"])
                                is_previous_target=(
                                    moment is not None and
                                    moment["decision"]=="LOOK_BACK_NOW" and
                                    moment.get("target_turn")=="previous")
                                if is_previous_target:
                                    # The model alone chose to revisit source.
                                    # Keep current prose untouched unless an
                                    # earlier V119 patch really succeeds.
                                    revision_note={
                                        "format":"wf.writer.self-edit.v1",
                                        "enabled":True,"model_calls":0,
                                        "rounds":[{"status":"LOOK_BACK_NOT_APPLIED"}],
                                        "canon_writes":0,
                                        "literary_quality_verified":False}
                                    remaining=(SELF_EDIT_MAX_PROVIDER_CALLS_PER_RUN-
                                               self_edit_model_calls)
                                    if (writer_rewind_count==0 and turn_index>0
                                        and remaining>=2):
                                        # V96 evidence stores only prose/effect,
                                        # not the model's action/parent trace.
                                        # Reuse the complete SELECTED source
                                        # envelope, never infer missing fields.
                                        prior=accepted_turns[-1]
                                        original_previous_raw=selected_turn_raws[-1]
                                        prior_snapshot=turn_snapshots[turn_index-1]
                                        prior_external=prior_snapshot["external"]
                                        changed_previous,prior_revision=(
                                            _self_edit_one_turn(
                                                raw=original_previous_raw,
                                                beat=accepted_beats[-1],
                                                accepted=tuple(accepted_turns[:-1]),
                                                project_id=self.assist.project_id,
                                                scene_id=self.assist.scene_id,
                                                turn_packet=turn_packet,
                                                ask_model=invoke_self_edit,
                                                round_limit=self_edit_rounds,
                                                call_allowance=min(
                                                    self_edit_rounds,remaining-1),
                                                directory=job/(
                                                    f"chapter-{index:03d}-turn-"
                                                    f"{turn_index:02d}-lookback-01"),
                                                author_exclusions=(
                                                    author_confirmed_forbidden_phrases),
                                                previous_candidate_state=(
                                                    prior_external["reducer_result"][
                                                        "candidate_state"]
                                                    if prior_external else None),
                                                cast=cast,
                                                current_external_story_checkpoint=(
                                                    prior_external),
                                                active_narrative_core=(
                                                    active_narrative_core),
                                                story_chapter_index=(
                                                    first_story_chapter_index+
                                                    index-1),
                                                cancel_check=check_cancel,
                                                writer_attention={
                                                    "reason":moment["reason"],
                                                    "risk":moment["risk"],
                                                    "desired_effect":moment[
                                                        "desired_effect"],
                                                    "source_quote":moment.get(
                                                        "source_quote"),
                                                    "focus":moment.get("focus")}))
                                        self_edit_model_calls+=prior_revision[
                                            "model_calls"]
                                        if changed_previous!=original_previous_raw:
                                            # The new branch remains reversible
                                            # until BOTH revised previous and new
                                            # downstream prose pass ordinary
                                            # source/temporal/graph preflight.
                                            rewind_pending={
                                                "capture":_capture_unaccepted_turn_restore(
                                                    tracked=tracked_rewind_lists,
                                                    snapshots=turn_snapshots),
                                                "resume_index":turn_index,
                                                "unmodified_current_raw":
                                                    last_turn_response,
                                                "receipt_index":
                                                    len(self_edit_rewind_receipts),
                                            }
                                            # Keep the original current turn as
                                            # an abandoned downstream branch.
                                            invalidated_file=job/(
                                                f"chapter-{index:03d}-turn-"
                                                f"{turn_index+1:02d}-"
                                                "invalidated-downstream-01.json")
                                            invalidated_file.write_text(
                                                last_turn_response,encoding="utf8")
                                            snapshot=_rewind_unaccepted_turn_suffix(
                                                accepted=accepted_turns,
                                                source_sha256=moment[
                                                    "target_prose_sha256"],
                                                snapshots=turn_snapshots,
                                                tracked=tracked_rewind_lists)
                                            current_continuity_checkpoint=(
                                                snapshot["continuity"])
                                            current_external_story_checkpoint=(
                                                snapshot["external"])
                                            last_lamp_receipt=snapshot["lamp"]
                                            self_edit_rewind_receipts.append({
                                                "status":"PREVIOUS_TURN_REDRAFT_PENDING",
                                                "target_turn_index":turn_index,
                                                "source_sha256":moment[
                                                    "target_prose_sha256"],
                                                "revision":prior_revision,
                                                "invalidated_downstream_sha256":
                                                    sha256(last_turn_response.encode(
                                                        "utf8")).hexdigest(),
                                                "downstream_must_be_regenerated":True,
                                                "state_rewound_before_target":True,
                                                "old_model_reply_preserved":True,
                                                "canon_writes":0,
                                                "literary_quality_verified":False,
                                                "original_timing_receipt":moment[
                                                    "receipt"]})
                                            writer_rewind_count+=1
                                            pending_revised_turn=(
                                                turn_index-1,changed_previous)
                                            redraw_turn_index=turn_index
                                            turn_index-=1
                                            continue
                                        revision_note["rounds"][0]["status"]=(
                                            "LOOK_BACK_REVISION_REJECTED_OR_KEPT")
                                        revision_note["prior_revision"]=(
                                            prior_revision)
                                    else:
                                        revision_note["rounds"][0]["status"]=(
                                            "LOOK_BACK_NOT_ALLOWED_OR_NO_BUDGET")
                                elif (self_edit_timing=="always_offer" or
                                      moment["decision"]=="LOOK_BACK_NOW"):
                                    last_turn_response,revision_note=(
                                        _self_edit_one_turn(
                                        raw=last_turn_response,beat=beat,
                                        accepted=tuple(accepted_turns),
                                        project_id=self.assist.project_id,
                                        scene_id=self.assist.scene_id,
                                        turn_packet=turn_packet,
                                        ask_model=invoke_self_edit,
                                        round_limit=self_edit_rounds,
                                        call_allowance=max(
                                            0,SELF_EDIT_MAX_PROVIDER_CALLS_PER_RUN-
                                            self_edit_model_calls),
                                        directory=job/(
                                            f"chapter-{index:03d}-turn-"
                                            f"{turn_index+1:02d}-self-edits"
                                            +("-replay" if writer_rewind_count
                                              else "")),
                                        author_exclusions=(
                                            author_confirmed_forbidden_phrases),
                                        previous_candidate_state=(
                                            current_external_story_checkpoint[
                                                "reducer_result"]["candidate_state"]
                                            if current_external_story_checkpoint
                                            else None),
                                        cast=cast,
                                        current_external_story_checkpoint=(
                                            current_external_story_checkpoint),
                                        active_narrative_core=active_narrative_core,
                                        story_chapter_index=(
                                            first_story_chapter_index+index-1),
                                        cancel_check=check_cancel,
                                        writer_attention=(
                                            {"reason":moment["reason"],
                                             "risk":moment["risk"],
                                             "desired_effect":moment["desired_effect"],
                                             "source_quote":moment.get("source_quote"),
                                             "focus":moment.get("focus")}
                                            if moment is not None else None)))
                                else:
                                    # AI said MOVE_ON (or signal invalid/over
                                    # budget). WF must not invent a need to edit.
                                    revision_note={
                                        "format":"wf.writer.self-edit.v1",
                                        "enabled":True,
                                        "model_calls":0,
                                        "rounds":[{
                                            "round":0,
                                            "status":"AI_CHOSE_TO_MOVE_ON"
                                            if moment["decision"]=="MOVE_ON"
                                            else "REVIEW_NOT_STARTED",
                                            "model_decision":moment["decision"]}],
                                        "literary_quality_verified":False,
                                        "canon_writes":0,
                                    }
                                self_edit_model_calls+=revision_note["model_calls"]
                                self_edit_turn_receipts.append(revision_note)
                                if last_turn_response!=old_raw:
                                    (job/(
                                        f"chapter-{index:03d}-turn-"
                                        f"{turn_index+1:02d}-selfedit-final"
                                        +("-replay.json" if writer_rewind_count
                                          else ".json")
                                    )).write_text(last_turn_response,
                                                  encoding="utf8")
                            elif draft_mode=="continuity_guard" and (
                                replaying_revised_source or
                                replaying_original_source):
                                self_edit_turn_receipts.append({
                                    "format":"wf.writer.self-edit.v1",
                                    "enabled":True,"model_calls":0,
                                    "rounds":[{"status":(
                                        "ORIGINAL_SOURCE_RESTORED_AFTER_FAILED_REWIND"
                                        if replaying_original_source else
                                        "PREVIOUS_TURN_REPLAYED_FROM_AI_REVISION")}],
                                    "canon_writes":0,
                                    "literary_quality_verified":False})
                            if draft_mode in ("emotion_rolling","foresight_rolling"):
                                evidence=check_emotional_turn(
                                    last_turn_response,beat,
                                    accepted=tuple(accepted_turns),
                                    previous_chapter=previous_emotional_turns,
                                    author_confirmed_forbidden_phrases=(
                                        author_confirmed_forbidden_phrases))
                            else:
                                checked_response=last_turn_response
                                if draft_mode=="continuity_guard":
                                    # Original unmodified response was persisted
                                    # above. Only exact-source citation spelling
                                    # can be normalized; model prose never changes.
                                    checked_response,source_citation_receipt=(
                                        normalize_model_source_citations(
                                            last_turn_response,beat,
                                            accepted=tuple(accepted_turns)))
                                    if source_citation_receipt is not None:
                                        source_citation_normalizations.append(
                                            source_citation_receipt)
                                try:
                                    evidence=check_turn(
                                        checked_response,beat,
                                        mode=("causal_guard" if
                                              draft_mode in ("rolling_causal","emotion_rolling","foresight_rolling","continuity_guard")
                                              else draft_mode),
                                        accepted=tuple(accepted_turns),
                                        author_confirmed_forbidden_phrases=(
                                            author_confirmed_forbidden_phrases),
                                        max_prose_chars=(
                                            _WF96_GUARDED_TURN_CHARS
                                            if draft_mode=="continuity_guard"
                                            else _WF96_LEGACY_TURN_CHARS))
                                except V96CausalDraftError as source_trace_error:
                                    if (draft_mode!="continuity_guard" or
                                        not trace_failure_reviewable(
                                            str(source_trace_error))):
                                        # Never disguise length/schema/source
                                        # errors as a model self-citation review.
                                        raise
                                    # Keep genuine paragraphs; do not claim
                                    # model's incorrect quote proves causality.
                                    # Wrong literary trace is a review debt;
                                    # source timeline/knowledge/replay still run.
                                    evidence=review_only_model_turn(
                                        checked_response,beat,
                                        failure_code=str(source_trace_error),
                                        accepted=tuple(accepted_turns),
                                        author_confirmed_forbidden_phrases=(
                                            author_confirmed_forbidden_phrases),
                                        max_prose_chars=_WF96_GUARDED_TURN_CHARS)
                                    model_trace_review_failures.append({
                                        "turn_id":beat["id"],
                                        "code":str(source_trace_error),
                                        "prose_sha256":evidence["receipt"]["prose_sha256"],
                                        "source_body_retained":True,
                                        "causal_truth_not_verified":True,
                                        "model_retries":0,
                                    })
                                if evidence["receipt"].get(
                                        "source_turn_requires_length_review"):
                                    source_length_reviews.append({
                                        "turn_id":beat["id"],
                                        "source_prose_sha256":
                                            evidence["receipt"]["prose_sha256"],
                                        "actual_codepoints":len(evidence["prose"]),
                                        "historical_v96_limit":
                                            _WF96_LEGACY_TURN_CHARS,
                                        "unified_writer_bound":
                                            _WF96_GUARDED_TURN_CHARS,
                                        "extra_review_not_auto_literary_pass":True,
                                    })
                            if draft_mode=="continuity_guard":
                                turn_delivery=audit_scene_delivery(
                                    prose=evidence["prose"],
                                    scene_goal=beat["goal"],
                                    scene_kind=beat["kind"],
                                    anchored_effect_quotes=(
                                        (evidence["effect_quote"],)
                                        if evidence.get("effect_quote") else ()))
                                replay_check=turn_delivery["long_prose_replay"]
                                unified_scene_delivery_turn_checks.append(
                                    turn_delivery)
                                unified_prose_replay_checks.append(replay_check)
                                if replay_check["blocked"]:
                                    raise NarrativeCoreError(
                                        "WFCORE_ENTIRE_LONG_PROSE_REPEATED")
                            if draft_mode=="continuity_guard":
                                # Validate what actually reached the page. Beat
                                # goal and model's self-reported trace are NOT
                                # source evidence. Keep non-matching goals as
                                # candidate debt, not as silently completed plot.
                                prior_candidate_state=(
                                    current_external_story_checkpoint[
                                        "reducer_result"]["candidate_state"]
                                    if current_external_story_checkpoint is not None
                                    else {})
                                execution_comparison=compare_plan_to_prose(
                                    project_id=self.assist.project_id,
                                    scene_id=scene,
                                    beat=beat,prose=evidence["prose"],cast=cast,
                                    prior_candidate_state=prior_candidate_state)
                                plan_execution_checks.append(execution_comparison)
                            if (draft_mode=="continuity_guard" and
                                active_long_arc is not None):
                                long_arc_checks.append(audit_revenge_prose(
                                    active_long_arc,
                                    project_id=self.assist.project_id,
                                    scene_id=self.assist.scene_id,
                                    prose=evidence["prose"]))
                            if (draft_mode=="continuity_guard" and
                                active_narrative_core is not None):
                                review=audit_narrative_candidate(
                                    active_narrative_core,
                                    project_id=self.assist.project_id,
                                    scene_id=self.assist.scene_id,
                                    prose=evidence["prose"],cast=cast)
                                narrative_source_reviews.append(review)
                                if review["blocked"]:
                                    raise NarrativeCoreError(
                                        "WFCORE_NPC_KNOWLEDGE_CONTRADICTION:"+
                                        ",".join(review["hard_findings"]))
                            if (draft_mode=="continuity_guard" and
                                current_external_story_checkpoint is not None):
                                # Same model response, same original prose. Audit
                                # source state + chapter time + POV knowledge.
                                # Lexical ambiguity is flagged, not overblocked.
                                preflight=preflight_continuation(
                                    evidence["prose"],
                                    current_external_story_checkpoint,
                                    project_id=self.assist.project_id,
                                    chapter_index=first_story_chapter_index+index-1,
                                    reference=continuity_reference,
                                cast=cast)
                                trace_checks.append(preflight)
                                if preflight["blocked"]:
                                    raise ContinuityTraceError(
                                        "WF117_NEXT_TURN_STATE_PRECONDITION_REJECTED:"+
                                        ",".join(preflight["state_findings"]))
                            if draft_mode=="continuity_guard":
                                relation_preflight=preflight_next_prose(
                                    evidence["prose"],
                                    previous_candidate_state=prior_candidate_state,
                                    cast=cast,
                                    previous_relation_receipt=(
                                        current_external_story_checkpoint.get(
                                            "v122_physical_relation_source_receipt")
                                        if current_external_story_checkpoint
                                        is not None else None))
                                relation_hold=_physical_relation_source_hold(
                                    prose=evidence["prose"],
                                    preflight=relation_preflight)
                                if relation_hold is not None:
                                    hold_name=job/(
                                        f"chapter-{index:03d}-turn-"
                                        f"{turn_index+1:02d}-relation-HOLD.json")
                                    hold_name.write_text(json.dumps(
                                        relation_hold,ensure_ascii=False,
                                        sort_keys=True,indent=2),
                                        encoding="utf8")
                                    # The original model-authored source is
                                    # retained, not rewritten or promoted.
                                    (job/(
                                        f"chapter-{index:03d}-turn-"
                                        f"{turn_index+1:02d}-unaccepted-HOLD.md")
                                     ).write_text(evidence["prose"],encoding="utf8")
                                    raise WritingExecutionError(
                                        "WF122_SOURCE_RELATION_HOLD_AWAIT_AUTHOR_SOURCE")
                            check_cancel()
                            if review_turn is not None:
                                # A stop/discard here has not accepted this turn.
                                # A "continue" is only permission to draft more,
                                # NOT author approval of literary truth or Canon.
                                proceed=review_turn(
                                    index,turn_index+1,evidence["prose"])
                                if proceed is not True:
                                    raise WriterDraftCancelled(
                                        "WF_STUDIO_DRAFT_DISCARDED_AT_TURN")
                                check_cancel()
                            accepted_turns.append(evidence)
                            accepted_beats.append(beat)
                            if draft_mode=="continuity_guard":
                                selected_turn_raws.append(checked_response)
                            if draft_mode=="continuity_guard":
                                # Update from ACTUAL source prose, not prewritten
                                # chapter objectives or a model's self-assessment.
                                current_continuity_checkpoint=validated_checkpoint(
                                    prose=evidence["prose"],cast=cast,
                                    previous=current_continuity_checkpoint)
                                current_external_story_checkpoint=external_temporal_step(
                                    prose=evidence["prose"],cast=cast,
                                    prior=current_external_story_checkpoint)
                                turn_external_checkpoints.append(
                                    current_external_story_checkpoint)
                            turn_index+=1
                            if (rewind_pending is not None and
                                turn_index>rewind_pending["resume_index"]):
                                self_edit_rewind_receipts[
                                    rewind_pending["receipt_index"]]["status"]=(
                                        "PREVIOUS_TURN_REVISED")
                                rewind_pending=None
                        except WriterDraftCancelled:
                            # Respect an explicit author discard/cancel.
                            raise
                        except (WritingExecutionError,V96CausalDraftError,
                                V114ContinuityError,V114ExternalMemoryError,
                                ContinuityTraceError,LampDecisionError,
                                PlanExecutionError,LongArcError,
                                NarrativeCoreError,ValueError) as issue:
                            if rewind_pending is None:
                                raise
                            # Transactional rollback: restore the SAME
                            # validated pre-current source and all derived
                            # V96/V114/V117/graph-preview side receipts.
                            saved=_restore_unaccepted_turn_capture(
                                capture=rewind_pending["capture"],
                                tracked=tracked_rewind_lists,
                                snapshots=turn_snapshots)
                            current_continuity_checkpoint=saved["continuity"]
                            current_external_story_checkpoint=saved["external"]
                            last_lamp_receipt=saved["lamp"]
                            source_index=rewind_pending["resume_index"]
                            self_edit_rewind_receipts[
                                rewind_pending["receipt_index"]].update({
                                    "status":"PREVIOUS_TURN_REVERTED_AFTER_FAILURE",
                                    "failure_code":str(issue)[:160],
                                    "restored_original_source":True,
                                    "discarded_model_proposal_not_accepted":True,
                                    "no_canon_writes":True,
                                    "model_requests_not_refunded":True,
                                })
                            pending_original_turn=(
                                source_index,
                                rewind_pending["unmodified_current_raw"])
                            pending_revised_turn=None
                            redraw_turn_index=None
                            rewind_pending=None
                            turn_index=source_index
                            continue
                    body=assemble_prose(accepted_turns)
                    if draft_mode=="continuity_guard":
                        # One evaluator for chapter repetition and source
                        # delivery, replacing parallel unrelated checks.
                        whole_delivery=audit_scene_delivery(
                            prose=body,scene_goal=goal,scene_kind="chapter",
                            anchored_effect_quotes=tuple(
                                t["effect_quote"] for t in accepted_turns
                                if t.get("effect_quote")),
                            author_delivery_contract=chapter_contract)
                        complete_replay=whole_delivery["long_prose_replay"]
                        if whole_delivery["blocked"]:
                            raise NarrativeCoreError(
                                "WFCORE_ENTIRE_LONG_PROSE_REPEATED")
                        # A contract is author intent, not an accomplished
                        # scene or an automatic permanent story-world fact.
                        # Preview against the SAME unified graph; only the
                        # separate author-review path may open/settle THREAD.
                        whole_debt_proposal=(
                            propose_scene_delivery_debt(
                                active_narrative_core,
                                project_id=self.assist.project_id,
                                scene_id=self.assist.scene_id,
                                chapter_index=first_story_chapter_index+index-1,
                                prose=body,scene_goal=goal,
                                scene_kind="chapter",
                                author_delivery_contract=chapter_contract,
                                delivery_receipt=whole_delivery)
                            if chapter_contract is not None and
                               active_narrative_core is not None else None)
                    turn_evidence=receipts_only(
                        accepted_turns,mode=("causal_guard" if
                                             draft_mode in ("rolling_causal","emotion_rolling","foresight_rolling","continuity_guard")
                                             else draft_mode),
                        outline_sha=sha256(
                            turn_outline.encode("utf8")).hexdigest())
                    turn_evidence["model_prompt_sha256s"]=prompt_shas
                    turn_evidence["source_free_unverified_scene_states"]=True
                    if draft_mode=="continuity_guard":
                        turn_evidence["g_writer_v98_opt_in"]=g_rolling_author_planning
                        turn_evidence["g_writer_source_only_replans"]=(
                            rolling_receipts if g_rolling_author_planning else [])
                        turn_evidence["g_writer_provisional_beat_choices"]=(
                            rolling_goals if g_rolling_author_planning else [])
                        turn_evidence["g_writer_review_only_replan_skips"]=(
                            g_rolling_source_skips if g_rolling_author_planning else [])
                        turn_evidence["g_writer_literary_progress_unproven"]=True
                        turn_evidence["v114_source_item_memory"]=(
                            current_continuity_checkpoint)
                        turn_evidence["v114_original_novel_studio_reducer"]=(
                            current_external_story_checkpoint)
                        turn_evidence["v114_memory_backed_by_actual_events"]=True
                        turn_evidence["v114_observed_continuity_risks"]=(
                            current_continuity_checkpoint["report"]["risks"])
                        turn_evidence["v114_literary_semantics_verified"]=False
                        turn_evidence["v117_cross_chapter_preflight"]=trace_checks
                        turn_evidence["v117_extra_model_calls"]=0
                        turn_evidence["v118_event_lamp_decisions"]=lamp_decisions
                        turn_evidence["v118_lamp_extra_model_calls"]=0
                        turn_evidence["v118_no_mandatory_literary_template"]=True
                        turn_evidence["v121_prompt_delivery_receipts"]=(
                            prompt_delivery_receipts)
                        turn_evidence["literary_progression_mode"]=(
                            literary_progression_mode)
                        turn_evidence["source_progression_cue_delivery"]=(
                            [bool(v.get("creative_progression_cue_delivered"))
                             for v in prompt_delivery_receipts])
                        turn_evidence["source_progression_is_optional_craft"]=True
                        turn_evidence["v121_hard_context_priority"]=True
                        turn_evidence["v120_plan_prose_source_receipts"]=(
                            plan_execution_checks)
                        turn_evidence["v120_typed_intent_not_whole_plan"]=True
                        turn_evidence["v120_extra_model_calls"]=0
                        turn_evidence["v120_auto_rewrites"]=0
                        turn_evidence["unified_optional_craft_compatibility"]=(
                            optional_craft_compatibility)
                        turn_evidence["unified_source_citation_normalizations"]=(
                            source_citation_normalizations)
                        turn_evidence["unified_model_trace_review_failures"]=(
                            model_trace_review_failures)
                        turn_evidence["wf_self_edit_rounds_configured"]=(
                            self_edit_rounds)
                        turn_evidence["wf_self_edit_timing"]=self_edit_timing
                        turn_evidence["wf_ai_self_review_moment_receipts"]=(
                            self_edit_moment_receipts)
                        turn_evidence["wf_reader_unresolved_cross_source_count"]=sum(
                            x.get("cross_source_reader_hypotheses_unverified_count",0)
                            for x in self_edit_moment_receipts)
                        turn_evidence["wf_author_kept_unresolved_source_hypotheses"]=any(
                            x.get("author_kept_unresolved_cross_source_hypotheses",False)
                            for x in self_edit_moment_receipts)
                        turn_evidence["wf_cross_source_reader_report_not_canon"]=True
                        turn_evidence["wf_author_attribution_source_anchored_count"]=sum(
                            x.get("cross_source_author_attribution",{}).get(
                                "claimed_written_links",0)
                            for x in self_edit_moment_receipts)
                        turn_evidence["wf_author_declared_unwritten_or_unknown_count"]=sum(
                            x.get("cross_source_author_attribution",{}).get(
                                "author_declared_unwritten_or_unknown_links",0)
                            for x in self_edit_moment_receipts)
                        turn_evidence["wf_author_intentional_ellipsis_count"]=sum(
                            x.get("cross_source_author_attribution",{}).get(
                                "author_declared_intentional_ellipsis_links",0)
                            for x in self_edit_moment_receipts)
                        turn_evidence["wf_author_source_claim_evidence_statuses"]=[
                            x["cross_source_author_attribution_status"]
                            for x in self_edit_moment_receipts
                            if "cross_source_author_attribution_status" in x]
                        turn_evidence["wf_source_quote_is_not_transfer_proof"]=True
                        turn_evidence["wf_reader_first_self_review_enabled"]=(
                            reader_first_self_review)
                        turn_evidence["wf_source_reader_receipts"]=(
                            self_edit_reader_receipts)
                        turn_evidence["wf_source_reader_model_calls"]=sum(
                            x.get("model_calls",0)
                            for x in self_edit_reader_receipts)
                        turn_evidence["wf_self_edit_receipts"]=(
                            self_edit_turn_receipts)
                        turn_evidence["wf_ai_previous_turn_rewinds"]=(
                            self_edit_rewind_receipts)
                        turn_evidence["wf_rewound_old_events_not_state"]=True
                        turn_evidence["wf_self_edit_model_calls_in_chapter"]=(
                            sum(x["model_calls"] for x in
                                self_edit_turn_receipts))
                        turn_evidence["wf_self_edit_no_canon_promotion"]=True
                        turn_evidence["unified_source_length_reviews"]=(
                            source_length_reviews)
                        turn_evidence["unified_source_prose_not_discarded_for_trace"]=True
                        turn_evidence["unified_prose_replay_checks"]=(
                            unified_prose_replay_checks)
                        turn_evidence["unified_completed_chapter_replay"]=(
                            complete_replay)
                        turn_evidence["unified_scene_delivery_turn_checks"]=(
                            unified_scene_delivery_turn_checks)
                        turn_evidence["unified_scene_delivery_chapter"]=(
                            whole_delivery)
                        turn_evidence["unified_scene_debt_review_proposal"]=(
                            whole_debt_proposal)
                        turn_evidence["unified_scene_debt_auto_commits"]=0
                        if active_narrative_core is not None:
                            turn_evidence["unified_narrative_scheduler"]=(
                                narrative_lane_decisions)
                            turn_evidence["unified_narrative_source_preflight"]=(
                                narrative_source_reviews)
                            turn_evidence["unified_narrative_extra_model_calls"]=0
                            turn_evidence["unified_narrative_author_gate"]=True
                        if active_long_arc is not None:
                            turn_evidence["v123_long_arc_prose_reviews"]=(
                                long_arc_checks)
                            turn_evidence["v123_arc_source_checkpoint_sha256"]=(
                                active_long_arc["receipt_sha256"])
                            turn_evidence["v123_no_auto_goal_settlement"]=True
                    if draft_mode in ("rolling_causal","emotion_rolling","foresight_rolling"):
                        turn_evidence.update({
                            "mode":draft_mode,
                            "rolling_proposal_receipts":rolling_receipts,
                            "rolling_replan_prompt_sha256s":
                                rolling_prompt_shas,
                            "actual_proposed_turn_plan_sha256":
                                sha256(causal_canonical({
                                    "turns":accepted_beats})).hexdigest(),
                            "rewritten_future_from_actual_prose":True,
                            "semantic_causality_proven":False,
                            "confirmed_character_facts_written":0,
                            "additional_model_replans":len(rolling_receipts),
                        })
                    if draft_mode in ("emotion_rolling","foresight_rolling"):
                        turn_evidence["v102_emotional_causality"]=(
                            export_candidate_emotions(accepted_turns))
                        turn_evidence["emotion_truth_independently_verified"]=False
                    if draft_mode=="foresight_rolling":
                        checkpoint=derive_open_checkpoint(
                            story_sha=outline_hash,
                            chapter=(checkpoint["chapter"]+1
                                     if checkpoint else 1),
                            accepted=tuple(accepted_turns),
                            previous=checkpoint)
                        turn_evidence["v105_forecast_sha256"]=(
                            prospective_report["proposed_futures_sha256"])
                        if host_only_branch_receipt is not None:
                            turn_evidence["v110_host_only_branch_route"]=(
                                host_only_branch_receipt)
                            turn_evidence["model_original_future_plan_untouched"]=True
                        turn_evidence["v105_open_checkpoint_sha256"]=(
                            checkpoint["receipt_sha256"])
                        turn_evidence["long_horizon_semantics_verified"]=False
                        turn_evidence["unreviewed_open_cost_debts"]=(
                            checkpoint["open_debts_count"])
                    # The envelope hash must include ALL receipt metadata.
                    # Never add fields after calculating its identity.
                    turn_evidence["manifest_sha256"]=sha256(
                        causal_canonical({k:v for k,v in
                            turn_evidence.items() if k!="manifest_sha256"})
                    ).hexdigest()
                except (V96CausalDraftError,V98RollingPlanError,
                        V102EmotionalCausalityError,
                        V105FutureCausalityError,
                        V114ContinuityError,V114ExternalMemoryError,
                        ContinuityTraceError,LampDecisionError,
                        PlanExecutionError,LongArcError,
                        NarrativeCoreError) as error:
                    # Keep the red record, not the private failed novel.
                    # No partial draft becomes accepted or FactJournal KNOWN.
                    issue={
                        "format":"wf.writing.rejected-scene-turn.v96",
                        "chapter":index,"draft_mode":draft_mode,
                        "reason_code":str(error),
                        "model_output_sha256":sha256(
                            last_turn_response.encode("utf8")).hexdigest()
                            if isinstance(last_turn_response,str) else None,
                        "previous_valid_turn_count":len(accepted_turns),
                        "canonical_fact_writes":0,
                        "candidate_chapter_completed":False,
                        "automatic_repair_attempts":0,
                        "real_original_or_private_prose_embedded":False,
                    }
                    (job/f"chapter-{index:03d}-rejected.json").write_text(
                        json.dumps(issue,ensure_ascii=False,indent=2),
                        encoding="utf8")
                    raise WritingExecutionError(
                        "WF96_SCENE_TURN_REJECTED_"+str(error)) from None
            if not isinstance(body,str) or not 100<=len(body.strip())<=MAX_PROSE_CHARS:
                raise WritingExecutionError("model output too short, missing or too long")
            check_cancel()
            saved=save_candidate(packet,body,self.assist.model,job)
            folder=Path(saved["folder"])
            plan_file=folder/"chapter_plan.json"
            plan_file.write_text(
                json.dumps({
                    **plan,"chapter":index,"outline_sha256":outline_hash,
                    "model_generated_plan":True,
                    "verified_facets_used":[f"{x['work_id']}#{x['id']}" for x in facets],
                    "no_cross_corpus_literary_assessment":True,
                },ensure_ascii=False,indent=2),encoding="utf-8",
            )
            chapter_data={
                "chapter":index,
                "story_chapter_index":(
                    first_story_chapter_index+index-1
                    if draft_mode=="continuity_guard" else index),
                "goal":goal,"candidate":saved["candidate"],
                "manifest":saved["manifest"],"plan":str(plan_file),
                "source_refs":saved["source_refs"],
                "verified_facets":len(facets),"accepted":False,
            }
            if turn_evidence is not None:
                # Append-only candidate evidence beside the existing saved
                # model draft, not into LEARN, R2, or a second canon DB.
                evidence_path=folder/"v96_turn_evidence.json"
                evidence_path.write_text(
                    json.dumps(turn_evidence,ensure_ascii=False,indent=2),
                    encoding="utf8")
                turn_outline_path=folder/"v96_turn_outline.json"
                turn_outline_path.write_text(
                    json.dumps({"candidate_turns":(
                                     list(accepted_beats) if
                                     draft_mode in ("rolling_causal","emotion_rolling","foresight_rolling")
                                     else list(beats)),
                                "author_confirmed":False,
                                "literary_truth_verified":False,
                                **({"original_seed_plan_preserved":True}
                                   if draft_mode in ("rolling_causal","emotion_rolling","foresight_rolling") else {})},
                               ensure_ascii=False,indent=2),encoding="utf8")
                if draft_mode in ("rolling_causal","emotion_rolling","foresight_rolling"):
                    # Private local candidate plans ONLY, never knowledge CANON
                    # or a true author-approved character state.
                    private_rolling=folder/"v98_rolling_plan.json"
                    private_rolling.write_text(
                        json.dumps({
                            "initial_seed_turns":list(beats),
                            "evolved_candidate_turns":list(accepted_beats),
                            "replanned_turns":rolling_goals,
                            "source_is_actual_prose":True,
                            "semantic_truth_verified":False,
                            "no_factjournal_writes":True,
                            "all_drafts_pending_author_acceptance":True,
                        },ensure_ascii=False,indent=2),
                        encoding="utf8")
                if draft_mode in ("emotion_rolling","foresight_rolling"):
                    private_affect=folder/"v102_emotional_causality.json"
                    private_affect.write_text(
                        json.dumps(turn_evidence["v102_emotional_causality"],
                                   ensure_ascii=False,indent=2),encoding="utf8")
                if draft_mode=="foresight_rolling" and host_only_branch_receipt is not None:
                    (folder/"v110_host_only_branch_identity.json").write_text(
                        json.dumps(host_only_branch_receipt,
                                   ensure_ascii=False,indent=2),encoding="utf8")
                if draft_mode=="foresight_rolling":
                    future_file=folder/"v105_prospective_horizon.json"
                    future_file.write_text(
                        json.dumps(prospective_report,ensure_ascii=False,
                                   indent=2),encoding="utf8")
                    checkpoint_file=folder/"v105_unreviewed_open_debts.json"
                    checkpoint_file.write_text(
                        json.dumps(checkpoint,ensure_ascii=False,
                                   indent=2),encoding="utf8")
                chapter_data.update({
                    "draft_mode":draft_mode,
                    **({"v105_raw_chapter_plan":str(
                            job/f"chapter-{index:03d}-raw-plan.json"),
                        "v105_original_model_answers_prevalidation_stored":True}
                       if draft_mode=="foresight_rolling" else {}),
                    **({"v110_branch_identity_receipt":str(
                             folder/"v110_host_only_branch_identity.json"),
                         "v110_only_software_labels_changed":True}
                         if draft_mode=="foresight_rolling" and
                            host_only_branch_receipt is not None else {}),
                    **({"v105_horizon_plan":str(future_file),
                        "v105_candidate_checkpoint":str(checkpoint_file),
                        "v105_checkpoint_sha256":checkpoint["receipt_sha256"],
                        "open_longterm_candidate_debts":checkpoint["open_debts_count"],
                        "forward_feasibility_independently_verified":False}
                       if draft_mode=="foresight_rolling" else {}),
                    **({"v102_emotional_causality":str(private_affect),
                        "emotional_literary_truth_verified":False}
                        if draft_mode in ("emotion_rolling","foresight_rolling") else {}),
                    "turn_count":len(beats),
                    "wf_previous_turn_rewind_receipts":
                        self_edit_rewind_receipts
                        if draft_mode=="continuity_guard" else [],
                    "wf_reader_first_self_review_enabled":(
                        reader_first_self_review
                        if draft_mode=="continuity_guard" else False),
                    "wf_cross_source_unreviewed_reader_hypotheses":sum(
                        x.get("cross_source_reader_hypotheses_unverified_count",0)
                        for x in self_edit_moment_receipts)
                        if draft_mode=="continuity_guard" else 0,
                    "wf_cross_source_authored_prose_unmodified_on_move_on":any(
                        x.get("author_kept_unresolved_cross_source_hypotheses",False)
                        for x in self_edit_moment_receipts)
                        if draft_mode=="continuity_guard" else False,
                    "wf_author_source_attribution_receipts":[
                        x.get("cross_source_author_attribution")
                        for x in self_edit_moment_receipts
                        if x.get("cross_source_author_attribution") is not None]
                        if draft_mode=="continuity_guard" else [],
                    "wf_source_reader_model_calls":sum(
                        x.get("model_calls",0)
                        for x in self_edit_reader_receipts)
                        if draft_mode=="continuity_guard" else 0,
                    "turn_evidence":str(evidence_path),
                    "turn_outline":str(turn_outline_path),
                    "causal_logic_literary_verified":False,
                    "facts_not_committed":True,
                    **({"unified_scene_function_review_needed":
                            bool(whole_delivery["needs_review"] or
                                 model_trace_review_failures or
                                 source_length_reviews),
                        "unified_scene_function_review_findings":
                            list(dict.fromkeys(
                                whole_delivery["review_findings"]+
                                [r["code"] for r in
                                 model_trace_review_failures]+
                                (["WFCORE_OVERSIZED_TURN_SOURCE_REVIEW"]
                                 if source_length_reviews else []))),
                        "unified_source_length_review_count":
                            len(source_length_reviews),
                        "unified_model_trace_review_count":
                            len(model_trace_review_failures),
                        "unified_model_trace_source_citation_repairs":
                            len(source_citation_normalizations),
                        "unified_scene_function_receipt_sha256":
                            whole_delivery["receipt_sha256"],
                        "unified_scene_function_semantics_verified":False,
                        "unified_scene_due_contract_id":(
                            whole_delivery["registered_delivery_contract"]["id"]
                            if whole_delivery["registered_delivery_contract"]
                            else None),
                        "unified_scene_cross_chapter_debt_status":(
                            whole_debt_proposal["status"]
                            if whole_debt_proposal is not None else
                            "NO_UNIFIED_GRAPH_TO_REGISTER_DEBT"
                            if chapter_contract is not None else None),
                        "unified_scene_debt_review_receipt_sha256":(
                            whole_debt_proposal["receipt_sha256"]
                            if whole_debt_proposal is not None else None),
                        "unified_scene_debt_auto_commits":0,
                        "unified_scene_author_review_required_to_commit":(
                            chapter_contract is not None)}
                       if draft_mode=="continuity_guard" else {}),
                    **({"v98_rolling_plan":str(private_rolling),
                        "model_replan_calls":len(rolling_receipts)}
                       if draft_mode in ("rolling_causal","emotion_rolling","foresight_rolling") else {}),
                })
            if draft_mode=="continuity_guard":
                if active_long_arc is not None:
                    # Backward-compatible V123 owner only when no unified
                    # graph exists. Never maintain both memories.
                    active_long_arc=advance_open_revenge(
                        active_long_arc,
                        project_id=self.assist.project_id,
                        scene_id=self.assist.scene_id,
                        chapter_index=first_story_chapter_index+index-1,
                        prose=body)
                if active_narrative_core is not None:
                    # Prose itself is NOT an author-confirmed event. Keep
                    # long threads and NPC knowledge unchanged unless
                    # source-anchored author annotations were provided by an
                    # explicit separate review path.
                    active_narrative_core=advance_narrative_graph(
                        active_narrative_core,
                        project_id=self.assist.project_id,
                        scene_id=self.assist.scene_id,
                        chapter_index=first_story_chapter_index+index-1,
                        prose=body,events=())
                    # The candidate.md file exists BEFORE compaction. Keep
                    # its verified bytes as the immutable local source and
                    # move only bounded working-memory excerpts/capsules.
                    active_narrative_core=record_chapter_memory(
                        active_narrative_core,
                        project_id=self.assist.project_id,
                        scene_id=self.assist.scene_id,
                        chapter_index=first_story_chapter_index+index-1,
                        source_path=saved["candidate"],prose=body,
                        chapter_source_parts=tuple(
                            turn["prose"] for turn in accepted_turns),
                        chapter_temporal_checkpoints=tuple(
                            turn_external_checkpoints),
                        # A chapter-zero ROOT can carry an explicit,
                        # separately signed V117 initial story state. It
                        # must be supplied in FULL and match the graph's
                        # actual parent receipt; a bare V114 seed never
                        # proves that all ancestry is trustworthy.
                        root_resume_anchor=(
                            resume_story_checkpoint
                            if (resume_story_checkpoint is not None and
                                type(resume_story_checkpoint) is dict and
                                resume_story_checkpoint["chapter_index"]==0 and
                                first_story_chapter_index+index-1==1)
                            else None),
                        source_writer=(narrative_store.put_original
                                       if narrative_store else None),
                        source_reader=(narrative_store.read_original
                                       if narrative_store else None),
                        archive_writer=(
                            narrative_store.put_capsule
                            if narrative_store else lambda capsule:
                            _save_unified_cold_capsule(root,capsule)),
                        archive_reader=(narrative_store.read_capsule
                                        if narrative_store else None))
                state_file=folder/"v114_candidate_item_memory.json"
                state_file.write_text(
                    json.dumps(current_continuity_checkpoint,
                               ensure_ascii=False,indent=2),encoding="utf8")
                external_file=folder/"v114_novel_studio_temporal_state.json"
                external_file.write_text(
                    json.dumps(current_external_story_checkpoint,
                               ensure_ascii=False,indent=2),encoding="utf8")
                chapter_data.update({
                    "v114_candidate_item_memory":str(state_file),
                    "v114_novel_studio_temporal_state":str(external_file),
                    "v114_external_temporal_is_not_canon":True,
                    "v114_continuity_risks":len(
                        current_continuity_checkpoint["report"]["risks"]),
                    "v114_carry_memory_to_next_turn":True,
                    "v114_literary_semantics_verified":False,
                })
                # Keep candidate continuity as a bounded continuation receipt
                # within existing local chapter artifacts, no new database.
                resume=make_resume(
                    project_id=self.assist.project_id,
                    scene_id=self.assist.scene_id,
                    chapter_index=first_story_chapter_index+index-1,
                    checkpoint=current_external_story_checkpoint,
                    long_arc_checkpoint=active_long_arc,
                    unified_narrative_core=active_narrative_core)
                resume_file=folder/"v117_unreviewed_text_trace_resume.json"
                resume_file.write_text(json.dumps(
                    resume,ensure_ascii=False,indent=2),encoding="utf8")
                r2_resume_ref=None
                if narrative_store is not None:
                    try:
                        r2_resume_ref=narrative_store.put_resume(resume)
                    except (R2StorageError,ContinuityTraceError,ValueError):
                        raise WritingExecutionError(
                            "WFCORE_R2_RESUME_NOT_DURABLE_CANDIDATE_ONLY") from None
                chapter_data.update({
                    "v117_unreviewed_text_trace_resume":str(resume_file),
                    **({"v117_r2_private_resume_ref":r2_resume_ref,
                        "v117_private_cloud_checkpoint_verified":True}
                       if r2_resume_ref is not None else {}),
                    "v117_source_only_preflight_count":len(trace_checks),
                    "v117_new_model_calls_for_tracking":0,
                    "v117_source_state_still_not_canon":True,
                    **({"unified_narrative_core_sha256":
                            active_narrative_core["receipt_sha256"],
                        "unified_narrative_core_chapter":
                            active_narrative_core["chapter_index"],
                        "unified_narrative_model_calls":0,
                        "unified_narrative_canon_writes":0,
                        "unified_narrative_buffered_chapters":len(
                            active_narrative_core["memory"]["hot"]),
                        "unified_narrative_warm_capsules":len(
                            active_narrative_core["memory"]["warm"]),
                        "unified_narrative_cold_archive_pages":
                            active_narrative_core["memory"]["cold_count"]}
                       if active_narrative_core is not None else {}),
                    **({"v123_long_arc_checkpoint_sha256":
                            active_long_arc["receipt_sha256"],
                        "v123_revenge_status":active_long_arc["status"],
                        "v123_model_cannot_close_author_goal":True}
                       if active_long_arc is not None else {}),
                })
                previous_continuity_checkpoint=current_continuity_checkpoint
                previous_external_story_checkpoint=current_external_story_checkpoint
            check_cancel()
            chapters.append(chapter_data)
            if draft_mode in ("emotion_rolling","foresight_rolling"):
                # Immutable metadata+real prose of this unaccepted chapter
                # are the ONLY input to next candidate chapter's hypothesis.
                previous_emotional_turns=tuple(accepted_turns)
            previous=body[-750:]  # Bound retained cross-chapter context memory.
            if progress:
                progress(index,len(chapter_goals),"saved")
        check_cancel()
        receipt={
            "mode":"autonomous","status":"candidates_saved",
            "project_id":self.assist.project_id,
            "outline_sha256":outline_hash,
            "source_snapshot_id":self.assist.rt.pinned_snapshot_id,
            "chapter_count":len(chapters),"chapters":chapters,
            "model_used":self.assist.model,
            "wf_self_edit_model_calls":self_edit_model_calls,
            "wf_self_edit_previous_turn_rewinds":sum(
                row.get("status")=="PREVIOUS_TURN_REVISED"
                for chapter in chapters for row in
                chapter.get("wf_previous_turn_rewind_receipts",[])),
            "wf_self_edit_previous_turn_rewind_attempts":
                writer_rewind_count,
            "wf_self_edit_configured_rounds":self_edit_rounds,
            "wf_self_edit_timing":self_edit_timing,
            "wf_reader_first_self_review":reader_first_self_review,
            "wf_reader_model_calls":sum(
                row.get("wf_source_reader_model_calls",0)
                for row in chapters),
            "wf_self_edit_canon_writes":0,
            "literary_quality_verified":False,
            "all_generated_prose_requires_author_review":True,
            "host_nutrient_application_events":
                host_nutrient_application_events,
            "host_nutrient_observer_failures":
                host_nutrient_observer_failures,
            "host_nutrient_provider_wires_verified":0,
            "host_nutrient_candidates_promoted":0,
        }
        if draft_mode!="single":
            receipt.update({
                "draft_mode":draft_mode,
                "segmented_model_turns":issued_turns,
                "canonical_fact_writes":0,
                "candidate_event_logic_independently_verified":False,
                **({"rolling_replan_model_calls":rolling_replan_calls,
                    "actual_written_effects_grounded_to_prompts":True,
                    "fictional_motives_are_not_confirmed_facts":True}
                   if draft_mode in ("rolling_causal","emotion_rolling","foresight_rolling") else {}),
            })
        if draft_mode=="foresight_rolling":
            receipt["final_candidate_checkpoint_sha256"]=(
                checkpoint["receipt_sha256"] if checkpoint else None)
            receipt["open_unreviewed_debts"]=(checkpoint["open_debts_count"]
                                             if checkpoint else 0)
            receipt["forecast_was_not_future_truth"]=True
            receipt["extra_software_validation_model_calls"]=0
        if cross_chapter_plan is not None:
            if (len(chapters)!=len(cross_chapter_plan[
                   "obsolete_only_in_this_fork"]) or
                chapters[0]["story_chapter_index"]!=
                    cross_chapter_plan["target_chapter_index"]):
                raise WritingExecutionError(
                    "WF_CHAPTER_FORK_REBUILT_CHAPTER_COUNT_MISMATCH")
            first_new=Path(chapters[0]["candidate"]).read_bytes()
            if (sha256(first_new).hexdigest()==
                cross_chapter_plan["obsolete_only_in_this_fork"][0][
                    "source_sha256"]):
                raise WritingExecutionError(
                    "WF_CHAPTER_FORK_NO_SOURCE_CHANGE")
            new_final=json.loads(Path(
                chapters[-1]["v117_unreviewed_text_trace_resume"]
            ).read_text("utf8"))
            _validate_rebuilt=read_resume(
                new_final,project_id=self.assist.project_id,
                scene_id=self.assist.scene_id)
            new_core=read_core_from_resume(
                new_final,project_id=self.assist.project_id,
                scene_id=self.assist.scene_id)
            if (new_core is None or
                new_core["parent_sha256"] is None or
                new_core["receipt_sha256"]==
                    cross_chapter_plan["obsolete_only_in_this_fork"][-1][
                        "old_graph_receipt_sha256"]):
                raise WritingExecutionError(
                    "WF_CHAPTER_FORK_NEW_GRAPH_NOT_REBUILT")
            fork_receipt={
                **cross_chapter_plan,
                "format":"wf.candidate.chapter-fork-rebuilt.v1",
                "old_source_job_not_mutated":True,
                "new_branch_head_resume_sha256":new_final["receipt_sha256"],
                "new_branch_final_chapter_index":new_final["chapter_index"],
                "new_candidate_source_sha256s":[
                    sha256(Path(row["candidate"]).read_bytes()).hexdigest()
                    for row in chapters],
                "author_accepted":False,"canon_writes":0,
                "model_or_user_must_select_new_branch_for_resume":True,
                "old_descendants_remain_archived_not_source_of_new_fork":True,
                "literary_quality_verified":False,
            }
            fork_receipt["receipt_sha256"]=sha256(json.dumps(
                fork_receipt,ensure_ascii=False,sort_keys=True,
                separators=(",",":")).encode("utf8")).hexdigest()
            (job/"cross-chapter-fork-rebuilt.json").write_text(
                json.dumps(fork_receipt,ensure_ascii=False,indent=2),
                encoding="utf8")
            receipt["cross_chapter_fork_receipt"]=str(
                job/"cross-chapter-fork-rebuilt.json")
            receipt["cross_chapter_rebuilt_old_descendants_count"]=len(
                cross_chapter_plan["obsolete_only_in_this_fork"])
            receipt["cross_chapter_canon_writes"]=0
        (job/"job_manifest.json").write_text(
            json.dumps(receipt,ensure_ascii=False,indent=2),encoding="utf-8",
        )
        return {**receipt,"job_dir":str(job)}
