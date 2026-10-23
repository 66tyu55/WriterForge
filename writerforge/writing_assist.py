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
    CRAFT as _WF96_OPTIONAL_CRAFT,BEAT_FIELDS as _WF96_BEAT_FIELDS,
    MAX_PLAN_JSON_BYTES as _WF96_PLAN_BUDGET,
)
from .v98_rolling_causal_planner import (
    V98RollingPlanError,MAX_ROLLING_REPLANS_PER_JOB,
    prepare_replan_instructions,validate_replan,
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
from .v119_revision_transaction import preview_revision as preview_surgical_revision
from .v120_plan_prose_gate import (
    compare_plan_to_prose, pending_dependency_hint, PlanExecutionError,
)
from .v123_long_arc import (
    verify_long_arc,read_long_arc_from_resume,relevant_revenge_hint,
    audit_revenge_prose,advance_open_revenge,LongArcError,
)
from .narrative_core import (
    validate as verify_narrative_core,
    read_core_from_resume,
    schedule as schedule_narrative,
    audit_candidate as audit_narrative_candidate,
    advance_graph as advance_narrative_graph,
    NarrativeCoreError,
    record_chapter_memory,
    buffered_memory_context,
    character_collision_context,
    relevant_history_context,
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
        working_memory_context:str=""):
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
    # Lamp text carries an added newline when present. Leave one character
    # for that newline; zero available characters yields a zero-lamp receipt.
    lamp_budget=min(MAX_LAMP_CHARS,max(0,space-1))
    lamps=plan_scene_lamps(
        project_id=project_id,chapter_index=chapter_index,
        turn_index=turn_index,beat=beat,frame=frame,
        previous=previous_lamp_receipt,max_prompt_chars=lamp_budget)
    lamp_suffix=("\n"+lamps["prompt"]) if lamps["prompt"] else ""
    delivered_addition=core_addition+used_memory+used_debt+lamp_suffix
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
            literary_progression_mode:str|None=None) -> dict:
        # In the unified writer, a source-grounded second turn now gets one
        # OPTIONAL scene progression suggestion by default. Old draft modes
        # remain unchanged; explicit "baseline" is the A/B rollback switch.
        if literary_progression_mode is None:
            literary_progression_mode=(
                "source_progression" if draft_mode=="continuity_guard"
                else "baseline")
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
        # Source-checkpoint resume is explicit, signed, project-scoped, and
        # NEVER silently imports a previous unaccepted draft as canon.
        earlier_external=None
        active_long_arc=None
        active_narrative_core=None
        first_story_chapter_index=0
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
        outline_hash=sha256(outline.encode("utf-8")).hexdigest()
        previous=""
        chapters=[]
        issued_turns=0
        rolling_replan_calls=0
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
            scene=f"{self.assist.scene_id}.chapter-{index:03}"
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
            plan_raw=local_chat_completion(
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
                body=local_chat_completion(
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
                    "actor、goal、causal_parent(前一个action/decision/"
                    "reversal的id或null)、craft_focus(0到2个："
                    "dialogue/detail/interiority/pacing/restraint/contrast/"
                    "action/none)。只做滚动短计划，不写正文；"
                    "不把模型猜测变成角色已经知道的事实。",
                    facets,prose_task=False,
                )
                turn_outline=(
                    frozen_turn_outlines[index-1]
                    if frozen_turn_outlines is not None else
                    local_chat_completion(
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
                    cast=tuple(dict.fromkeys(b["actor"] for b in beats))
                    for turn_index,seed_beat in enumerate(beats):
                        beat=seed_beat
                        if draft_mode in ("rolling_causal","emotion_rolling","foresight_rolling") and turn_index>0:
                            if rolling_replan_calls>=MAX_ROLLING_REPLANS_PER_JOB:
                                raise V98RollingPlanError(
                                    "WF98_REPLAN_MODEL_CALL_BUDGET_EXCEEDED")
                            instructions=prepare_replan_instructions(
                                accepted=tuple(accepted_turns),
                                seed_next_beat=seed_beat,
                                allowed_actor_names=cast)
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
                            last_turn_response=local_chat_completion(
                                rolling_packet,model=self.assist.model,
                                api_base=self.assist.api_base,max_tokens=650,
                            )
                            if draft_mode=="foresight_rolling":
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
                                    author_confirmed_forbidden_phrases))
                            rolling_receipts.append(rolling_receipt)
                            rolling_goals.append(dict(beat))
                        turn_addition=make_turn_instructions(
                            beat,mode=("causal_guard" if
                                       draft_mode in ("rolling_causal","emotion_rolling","foresight_rolling","continuity_guard")
                                       else draft_mode),accepted=accepted_turns,
                            author_confirmed_forbidden_phrases=(
                                author_confirmed_forbidden_phrases))
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
                            if progression_cue:
                                dependency_hint+=progression_cue
                            turn_packet,lamps,delivery=(
                                _prepare_guarded_turn_packet(
                                    body_base,plan=plan,
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
                                        else "")))
                            if delivery["unified_narrative_priority_dispatch"]:
                                narrative_lane_decisions.append(
                                    delivery["unified_narrative_priority_dispatch"])
                            if progression_cue:
                                delivery["creative_progression_cue_eligible"]=True
                                delivery["creative_progression_cue_delivered"]=(
                                    delivery["unproven_dependency_hint_delivered"])
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
                        last_turn_response=local_chat_completion(
                            turn_packet,model=self.assist.model,
                            api_base=self.assist.api_base,max_tokens=1450,
                        )
                        if draft_mode in ("foresight_rolling","continuity_guard"):
                            (job/f"chapter-{index:03d}-turn-"
                                 f"{turn_index+1:02d}-raw.json").write_text(
                                     last_turn_response,encoding="utf8")
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
                                        author_confirmed_forbidden_phrases))
                            except V96CausalDraftError as source_trace_error:
                                if draft_mode!="continuity_guard":
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
                                        author_confirmed_forbidden_phrases))
                                model_trace_review_failures.append({
                                    "turn_id":beat["id"],
                                    "code":str(source_trace_error),
                                    "prose_sha256":evidence["receipt"]["prose_sha256"],
                                    "source_body_retained":True,
                                    "causal_truth_not_verified":True,
                                    "model_retries":0,
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
                        accepted_turns.append(evidence)
                        accepted_beats.append(beat)
                        if draft_mode=="continuity_guard":
                            # Update from ACTUAL source prose, not prewritten
                            # chapter objectives or a model's self-assessment.
                            current_continuity_checkpoint=validated_checkpoint(
                                prose=evidence["prose"],cast=cast,
                                previous=current_continuity_checkpoint)
                            current_external_story_checkpoint=external_temporal_step(
                                prose=evidence["prose"],cast=cast,
                                prior=current_external_story_checkpoint)
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
                "chapter":index,"goal":goal,"candidate":saved["candidate"],
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
                    "turn_evidence":str(evidence_path),
                    "turn_outline":str(turn_outline_path),
                    "causal_logic_literary_verified":False,
                    "facts_not_committed":True,
                    **({"unified_scene_function_review_needed":
                            bool(whole_delivery["needs_review"] or
                                 model_trace_review_failures),
                        "unified_scene_function_review_findings":
                            list(dict.fromkeys(
                                whole_delivery["review_findings"]+
                                [r["code"] for r in
                                 model_trace_review_failures])),
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
            chapters.append(chapter_data)
            if draft_mode in ("emotion_rolling","foresight_rolling"):
                # Immutable metadata+real prose of this unaccepted chapter
                # are the ONLY input to next candidate chapter's hypothesis.
                previous_emotional_turns=tuple(accepted_turns)
            previous=body[-750:]  # Bound retained cross-chapter context memory.
            if progress:
                progress(index,len(chapter_goals),"saved")
        receipt={
            "mode":"autonomous","status":"candidates_saved",
            "project_id":self.assist.project_id,
            "outline_sha256":outline_hash,
            "source_snapshot_id":self.assist.rt.pinned_snapshot_id,
            "chapter_count":len(chapters),"chapters":chapters,
            "model_used":self.assist.model,
            "literary_quality_verified":False,
            "all_generated_prose_requires_author_review":True,
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
        (job/"job_manifest.json").write_text(
            json.dumps(receipt,ensure_ascii=False,indent=2),encoding="utf-8",
        )
        return {**receipt,"job_dir":str(job)}
