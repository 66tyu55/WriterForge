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
from .verified_flow import (
    VerifiedWritingFlow, GroundedDraftPacket, WritingExecutionError,
    local_chat_completion, save_candidate, MAX_PROMPT_CHARS,
)

MAX_LIVE_CONTEXT = 1400
MAX_OUTLINE_CHARS = 6000
MAX_CHAPTERS = 6
MAX_CHAPTER_GOAL = 450
MAX_PROSE_CHARS = 16000
FACET_COUNT = 4
MAX_STORED_AUTONOMOUS_RUNS = 32  # Do not silently grow candidate history forever.


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
            facets: tuple[dict,...] = ()) -> GroundedDraftPacket:
    context=packet.prompt
    if facets:
        context+="\n已由真实来源和审核状态确认的实体属性（只借鉴机制，不能复制原句）：\n"
        context+="\n".join(
            f"- {c['category_path']} / {c['attribute']}；"
            f"说明：{c['explanation'][:100] or '来源已复核但未给出机制解释'}；"
            f"出处：{c['work_id']} 第{c['chapter']}回；审核：verified"
            for c in facets
        )
    context+="\n"+addition
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
            output_dir:str|Path,progress=None) -> dict:
        if not isinstance(outline,str) or not 15<=len(outline.strip())<=MAX_OUTLINE_CHARS:
            raise WritingExecutionError("outline requires 15..6000 characters")
        if (not isinstance(chapter_goals,list) or not 1<=len(chapter_goals)<=MAX_CHAPTERS
            or any(not isinstance(x,str) or not 8<=len(x.strip())<=450
                   for x in chapter_goals)):
            raise WritingExecutionError("provide 1..6 chapter goals of 8..450 characters each")
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
        for index,goal in enumerate(chapter_goals,1):
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
                +"\n请先规划本章，不写正文。必须明确人物目的、冲突、选择、后果和视角；"
                "内部调用结构技法，不照搬原著。只返回 JSON："
                '{"objective":"...","conflict":"...","decision":"...",'
                '"outcome":"...","pov":"...","needs":["dialogue","decision"]}'
            )
            plan_raw=local_chat_completion(
                plan_prompt,model=self.assist.model,
                api_base=self.assist.api_base,max_tokens=650,
            )
            plan=_chapter_plan(plan_raw,goal)
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
                +"\n请按照因果、人物决定和冲突结果写完整原创正文，"
                "不要解释技巧，也不要复制原著人物、设定或句子。",
                facets,
            )
            body=local_chat_completion(
                packet,model=self.assist.model,
                api_base=self.assist.api_base,max_tokens=2600,
            )
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
            chapters.append({
                "chapter":index,"goal":goal,"candidate":saved["candidate"],
                "manifest":saved["manifest"],"plan":str(plan_file),
                "source_refs":saved["source_refs"],
                "verified_facets":len(facets),"accepted":False,
            })
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
        (job/"job_manifest.json").write_text(
            json.dumps(receipt,ensure_ascii=False,indent=2),encoding="utf-8",
        )
        return {**receipt,"job_dir":str(job)}
