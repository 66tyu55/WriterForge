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

from .db import WriterForgeDB
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


class AutonomousWriting:
    """Bounded outline -> narrative decisions -> actual model chapters on disk."""

    def __init__(self,assist:InvisibleWritingAssist):
        self.assist=assist

    def run(self,*,outline:str,chapter_goals:list[str],
            output_dir:str|Path,progress=None,
            draft_mode:str="single",
            author_confirmed_forbidden_phrases:tuple[str,...]=(),
            frozen_turn_outlines:tuple[str,...]|None=None,
            forward_author_pinned_facts:dict[str,str]|None=None,
            resume_candidate_checkpoint:dict|None=None) -> dict:
        # 'single' remains byte-for-byte compatible with legacy output
        # behavior. split_only vs causal_guard share the SAME JSON turn
        # planning/response interface so B/C can be fairly compared.
        if draft_mode not in ("single","split_only","causal_guard","rolling_causal","emotion_rolling","foresight_rolling"):
            raise WritingExecutionError("WF96_DRAFT_MODE_NOT_OPTED_IN")
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
        for index,goal in enumerate(chapter_goals,1):
            last_chapter_pressure=(
                pressure_context(previous_emotional_turns)
                if draft_mode in ("emotion_rolling","foresight_rolling") and
                previous_emotional_turns else "")
            continuing_pressure=(
                open_debt_context(checkpoint)
                if draft_mode=="foresight_rolling" and checkpoint else "")
            prospective_report=None
            future_note=""
            if progress:
                progress(index,len(chapter_goals),"planning")
            scene=f"{self.assist.scene_id}.chapter-{index:03}"
            base=self.assist.flow.prepare(
                scene,goal,concerns=("scene","decision"),
                genre=self.assist.source_genre,
            )
            plan_prompt=_enrich(base,
                "\n原创新作的大纲：\n"+outline
                +"\n本章目标：\n"+goal
                +"\n上一章仅为候选、尚未作者接受的末尾：\n"+previous[-700:]
                +("\n【上章尚未证实的情感后果和待处理代价】"+
                  last_chapter_pressure if last_chapter_pressure else "")
                +("\n【过去数章未偿压力的只读候选账本】"+
                  continuing_pressure if continuing_pressure else "")
                +"\n请先规划本章，不写正文。必须明确人物目的、冲突、选择、后果和视角；"
                "内部调用结构技法，不照搬原著。只返回 JSON："
                '{"objective":"...","conflict":"...","decision":"...",'
                '"outcome":"...","pov":"...","needs":["dialogue","decision"]}'
                +(horizon_prompt(pinned_world=pinned_world)
                  if draft_mode=="foresight_rolling" else ""),
                prose_task=False,
            )
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
            plan=_chapter_plan(plan_raw,goal)
            if draft_mode=="foresight_rolling":
                try:
                    plan_obj=_decode_json(plan_raw)
                    prospective_report=validate_horizon(
                        plan_obj.get("horizon"),author_pinned=pinned_world)
                    future_note=horizon_context(prospective_report)
                    if all(b["status"]=="SYMBOLICALLY_BLOCKED"
                           for b in prospective_report["branches"]):
                        raise V105FutureCausalityError(
                            "WF105_ALL_FUTURE_PATHS_SYMBOLICALLY_BLOCKED")
                except (V105FutureCausalityError,ValueError) as exc:
                    # Preserve a red receipt: never recharge by retrying.
                    issue={"format":"wf.writing.failed-foresight-preflight.v105",
                           "chapter":index,"draft_mode":draft_mode,
                           "code":str(exc) if str(exc).startswith("WF105_")
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
                accepted_turns=[]
                accepted_beats=[]
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
                                       draft_mode in ("rolling_causal","emotion_rolling","foresight_rolling")
                                       else draft_mode),accepted=accepted_turns,
                            author_confirmed_forbidden_phrases=(
                                author_confirmed_forbidden_phrases))
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
                        if draft_mode=="foresight_rolling":
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
                            evidence=check_turn(
                                last_turn_response,beat,
                                mode=("causal_guard" if
                                      draft_mode in ("rolling_causal","emotion_rolling","foresight_rolling")
                                      else draft_mode),
                                accepted=tuple(accepted_turns),
                                author_confirmed_forbidden_phrases=(
                                    author_confirmed_forbidden_phrases))
                        accepted_turns.append(evidence)
                        accepted_beats.append(beat)
                    body=assemble_prose(accepted_turns)
                    turn_evidence=receipts_only(
                        accepted_turns,mode=("causal_guard" if
                                             draft_mode in ("rolling_causal","emotion_rolling","foresight_rolling")
                                             else draft_mode),
                        outline_sha=sha256(
                            turn_outline.encode("utf8")).hexdigest())
                    turn_evidence["model_prompt_sha256s"]=prompt_shas
                    turn_evidence["source_free_unverified_scene_states"]=True
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
                        V105FutureCausalityError) as error:
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
                    **({"v98_rolling_plan":str(private_rolling),
                        "model_replan_calls":len(rolling_receipts)}
                       if draft_mode in ("rolling_causal","emotion_rolling","foresight_rolling") else {}),
                })
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
