"""V27 literary-learning LADDER, not a fake "trained author" switch.

The model starts with a single original source unit, then generates gradually:
source comprehension + original short sentence -> one reviewed facet -> two
different facet categories -> three+ -> paragraph -> complete scene.

A source span proves the QUOTE EXISTS, not what it MEANS. Deep category
combinations require V25 HUMAN-VERIFIED facets. If those don't exist, training
stops and names the missing prerequisite. A local model's own review is saved
as an UNVERIFIED hypothesis. Independent lit-critic can report shortcomings
on paragraph/scene levels, but feedback never auto-promotes a writing skill.

This is practice using a model and a local SQLite learning store. It is NOT
model-parameter fine-tuning and does not waive the 50-work global review gate.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from hashlib import sha256
from pathlib import Path
from uuid import uuid4
import json
import re

from .db import WriterForgeDB
from .encyclopedia import FictionEncyclopedia, FacetQuery, ROOTS
from .runtime import RuntimeEngine, Mode
from .verified_flow import (
    VerifiedWritingFlow, local_chat_completion, MAX_PROMPT_CHARS,
    WritingExecutionError,
)
from .litcritic_adapter import LitCriticAdapter, CriticIntegrationError


STAGES = (
    ("短句理解", 1, 12, 65),
    ("单类成句", 1, 35, 120),
    ("两类相融", 2, 65, 180),
    ("多类相融", 3, 100, 300),
    ("完整段落", 3, 180, 700),
    ("因果场景", 3, 420, 2200),
)
MAX_SOURCE_UNITS = 1
MAX_SOURCE_CHARS = 160
MAX_CATALOG_SAMPLES = 400
MAX_SAVED_TRAINING_RUNS_PER_PROJECT = 400
MAX_CONCISE_REVIEW = 2000
MAX_GENERATION_STEPS = 6


class LadderError(RuntimeError):
    pass


@dataclass(frozen=True)
class LadderTask:
    stage: int
    label: str
    work_id: str
    goal: str
    source_location: tuple[int, int, int]
    source_excerpt: str
    facet_cards: tuple[dict, ...]
    readiness: str
    reason: str

    def trace(self) -> dict:
        return {
            "stage":self.stage,"label":self.label,"work_id":self.work_id,
            "source_location":list(self.source_location),
            "source_excerpt_sha256":sha256(self.source_excerpt.encode("utf-8")).hexdigest(),
            "selected_facets":[{
                "evidence_id":r["id"],"source_work":r["work_id"],
                "category":r["category_path"],
                "source_location":[r["chapter"],r["paragraph"],r["sentence"]],
            } for r in self.facet_cards],
            "required_distinct_facet_categories":STAGES[self.stage-1][1] if self.stage>1 else 0,
            "readiness":self.readiness,"reason":self.reason,
            "classification_is_not_proven_by_keyword":True,
        }


class LiteraryLadder:
    def __init__(self, db: WriterForgeDB, runtime: RuntimeEngine, project_id: str):
        self.db,self.runtime,self.project_id=db,runtime,project_id
        runtime.require(Mode.WRITE)
        if not project_id or len(project_id)>128:
            raise LadderError("invalid training project")
        pinned=db.conn.execute(
            "SELECT status FROM snapshots WHERE id=?",(runtime.pinned_snapshot_id,),
        ).fetchone()
        if pinned is None or pinned["status"]!="published":
            raise LadderError("a real published original study snapshot is required")

    def _source(self,work_id:str):
        # Strictly source-grounded: select the first concise original unit.
        return self.db.conn.execute(
            """SELECT chapter,paragraph,sentence,excerpt,source_sha256
               FROM source_spans WHERE work_id=? AND length(excerpt) BETWEEN 12 AND 150
               ORDER BY chapter,paragraph,sentence LIMIT 1""", (work_id,),
        ).fetchone()

    def _facets(self,work_id:str) -> tuple[dict,...]:
        enc=FictionEncyclopedia(self.db)
        cards=[]
        offset=0
        while offset<MAX_CATALOG_SAMPLES:
            result=enc.query(FacetQuery(
                work_id=work_id,status="verified",limit=100,offset=offset,
            ))
            cards.extend(result["items"])
            offset+=len(result["items"])
            if not result["has_more"] or not result["items"]:
                break
        # Verified source SHA, specific work identity and source excerpt
        # are checked again by the V25 query when it returns each card.
        return tuple(cards)

    def tasks(self,*,work_id:str,goal:str) -> list[LadderTask]:
        if not isinstance(work_id,str) or not work_id or len(work_id)>128:
            raise LadderError("work_id required")
        if not isinstance(goal,str) or not 10<=len(goal.strip())<=450:
            raise LadderError("specific creative goal must be 10..450 chars")
        work=self.db.conn.execute(
            "SELECT title FROM studied_works WHERE work_id=?",(work_id,),
        ).fetchone()
        if work is None:
            raise LadderError("unknown work: cannot invent source")
        source=self._source(work_id)
        if source is None:
            raise LadderError("no eligible original source units")
        all_cards=self._facets(work_id)
        distinct={}
        for row in all_cards:
            root=row["category_path"].split("/")[0]
            # Never treat one entity occurrence as several independent kinds;
            # we need distinct REVIEWED top-level semantic dimensions.
            if root not in distinct:
                distinct[root]=row
        choices=list(distinct.values())
        tasks=[]
        for stage,(label,minimum,_low,_high) in enumerate(STAGES,1):
            selected=tuple(choices[:minimum]) if stage>=2 else ()
            ready=stage==1 or len(selected)==minimum
            tasks.append(LadderTask(
                stage=stage,label=label,work_id=work_id,goal=goal.strip(),
                source_location=(source["chapter"],source["paragraph"],source["sentence"]),
                source_excerpt=source["excerpt"],facet_cards=selected if ready else (),
                readiness="ready" if ready else "blocked_unverified_facets",
                reason="有来源的短句，可先做低风险理解练习" if stage==1 else (
                    f"从同书取到 {len(selected)} 个不同的已人工复核大类"
                    if ready else
                    f"只有 {len(choices)} 个不同大类有已人工复核证据，当前关卡需要 {minimum} 个；先校验类别"
                ),
            ))
        return tasks

    @staticmethod
    def _copy_guard(text:str,source:str,facets:tuple[dict,...]):
        # Ignore accidental tiny common phrases; flag long direct spans.
        references=(source,)+(tuple(f["quotation"] for f in facets))
        for fragment in references:
            if not fragment:
                continue
            for i in range(0,max(0,len(fragment)-17),3):
                if fragment[i:i+18] in text:
                    raise LadderError("generated text copies >=18 consecutive original source characters")

    @staticmethod
    def _analysis(raw:str,source:str) -> dict:
        if not isinstance(raw,str) or len(raw)>5500:
            raise LadderError("invalid source comprehension response")
        try:
            parsed=json.loads(raw.strip().removeprefix('~~~json').removesuffix('~~~'))
        except ValueError as exc:
            raise LadderError("first stage must return strict JSON") from exc
        if not isinstance(parsed,dict):
            raise LadderError("first stage must be an object")
        quote=parsed.get("evidence")
        category=parsed.get("category")
        claim=parsed.get("certainty")
        text=parsed.get("text")
        if (not isinstance(quote,str) or len(quote)<2 or quote not in source
            or category not in ROOTS|{"不确定"}
            or claim not in ("explicit","inferred","uncertain")
            or not isinstance(text,str)):
            raise LadderError("unproven category or evidence in model analysis")
        if not STAGES[0][2]<=len(text.strip())<=STAGES[0][3]:
            raise LadderError("original short-sentence length is out of stage bounds")
        note=parsed.get("reason")
        if not isinstance(note,str) or not 2<=len(note.strip())<=250:
            raise LadderError("source explanation missing/too long")
        return {"category":category,"evidence":quote,"certainty":claim,
                "reason":note.strip(),"text":text.strip(),
                "status":"model_proposal_not_semantically_verified"}

    def _prompt(self,task:LadderTask,model:str,source_genre:str):
        from .writing_assist import _craft_needs
        flow=VerifiedWritingFlow(self.db,self.runtime,self.project_id)
        base=flow.prepare(
            "ladder."+task.work_id+"."+str(task.stage),
            task.goal,concerns=_craft_needs(("description","character","scene")),
            genre=source_genre,
        )
        if task.stage==1:
            addition=(
                "\n【逐句理解练习】来自已存在的原著源单位（不是经过审稿的分类）：\n"
                +task.source_excerpt
                +"\n区分原文事实与人物推测，允许回答“不确定”。"
                "先提供一小段与原文完全不同人物、地点的原创短句，"
                "并指出从原文中能直接引用的一小段证据。"
                "仅返回合法 JSON 对象，字段为 category（大类或不确定）、"
                "evidence（原样子串）、certainty（explicit|inferred|uncertain）、"
                "reason（为什么这样判断）、text（原创短句12-65字）。"
                "注意：类别只是待验证提案，禁止把人名中的龙判为妖兽。"
            )
        else:
            low,high=STAGES[task.stage-1][2:]
            cards="\n".join(
                "- 类别："+f["category_path"]+"；属性："+f["attribute"]+
                "；作用："+(f["explanation"] or "未提供解释")[:110]+
                "；原著来源："+f["work_id"]+" 第"+str(f["chapter"])+"回"
                for f in task.facet_cards
            )
            difficulty={
                2:"只使用这一种已核对的类别写成原创完整句，不堆砌形容词。",
                3:"把两个不同类别连成一个有真实因果的原创描写，不能并列贴标签。",
                4:"三个以上类别必须服务同一人物目的，彼此影响，不能像素材清单。",
                5:"写出动作、感觉、人物判断与段落转折；避免句子机械堆叠。",
                6:"写一个完整因果场景：目的、冲突、人物选择、不可逆后果。",
            }[task.stage]
            addition=(
                "\n【阶梯文学组合练习】\n"+cards+
                "\n这些例子来自同一原著，但不代表来自同一个场景或有同一世界观关系。"
                "只能借鉴技法，禁止照搬原著的名称、物种设定和语句。"
                "\n训练任务："+task.goal+"\n组合要求："+difficulty+
                f"\n长度要求：{low}到{high}个汉字左右。直接给原创正文，不附分析。"
            )
        prompt=base.prompt+addition
        if len(prompt)>MAX_PROMPT_CHARS:
            raise LadderError("training prompt exceeds context safety cap")
        return replace(base,prompt=prompt,
                       prompt_sha256=sha256(prompt.encode("utf-8")).hexdigest())

    def run(self,*,work_id:str,goal:str,model:str,
            api_base:str="http://127.0.0.1:1234/v1",
            source_genre:str="古代白话",through_stage:int=1,
            critic_project:Path|str|None=None,
            output_dir:Path|str="writing_runs/literary_ladder") -> dict:
        """Train only consecutive READY stages. Stops at first missing proof.

        Stages 1-4: model outputs are practice, not external verification.
        Stages 5-6: optional REAL lit-critic review + one bounded revision.
        Every attempt has immutable receipt and a durable SQLite audit row.
        """
        self.runtime.require(Mode.WRITE)
        if not isinstance(through_stage,int) or not 1<=through_stage<=6:
            raise LadderError("through_stage must be 1..6")
        if not isinstance(model,str) or not model:
            raise LadderError("explicit real model identity required")
        exercises=self.tasks(work_id=work_id,goal=goal)
        records=[]
        root=Path(output_dir)
        root.mkdir(parents=True,exist_ok=True)
        for task in exercises[:through_stage]:
            if task.readiness!="ready":
                records.append({"stage":task.stage,"status":task.readiness,
                                "reason":task.reason})
                break
            attempts=self.db.conn.execute(
                "SELECT COUNT(*) AS n FROM literary_training_attempts WHERE project_id=?",
                (self.project_id,),
            ).fetchone()["n"]
            if attempts>=MAX_SAVED_TRAINING_RUNS_PER_PROJECT:
                raise LadderError("project has reached 400 training trials; archive and review before more")
            packet=self._prompt(task,model,source_genre)
            output=local_chat_completion(
                packet,model=model,api_base=api_base,
                max_tokens=1500 if task.stage<=4 else 3500,
            )
            note={}
            if task.stage==1:
                analyzed=self._analysis(output,task.source_excerpt)
                body=analyzed["text"]
                note["source_analysis"]=analyzed
            else:
                body=output.strip()
                low,high=STAGES[task.stage-1][2:]
                if not low<=len(body)<=high:
                    raise LadderError("generated stage length outside bound")
            self._copy_guard(body,task.source_excerpt,task.facet_cards)
            run_id=uuid4().hex
            receipt={
                "run_id":run_id,"project_id":self.project_id,
                "stage":task.stage,"label":task.label,"task":task.trace(),
                "model_used":model,"prompt_sha256":packet.prompt_sha256,
                "body_sha256":sha256(body.encode("utf-8")).hexdigest(),
                "source_genre":source_genre,
                "assessment_type":"not_yet_independent_literary_evaluation",
                "skill_promoted":False,"50_book_assessment_performed":False,
                **note,
            }
            folder=root/run_id
            folder.mkdir(exist_ok=False)
            (folder/"draft.md").write_text(body,encoding="utf-8")
            critic_status=("not_run_short_stage" if task.stage<5
                           else "independent_critic_not_configured")
            receipt["status"]=critic_status
            # Save the provisional result BEFORE a third-party evaluator is
            # called, so timeout/HTTP failures cannot erase an actual trial.
            self.db.conn.execute(
                """INSERT INTO literary_training_attempts(
                   run_id,project_id,work_id,stage,prompt_sha256,body_sha256,
                   status,model,body,receipt_json
                   ) VALUES(?,?,?,?,?,?,?,?,?,?)""",
                (run_id,self.project_id,work_id,task.stage,packet.prompt_sha256,
                 receipt["body_sha256"],critic_status,model,body,
                 json.dumps(receipt,ensure_ascii=False)),
            )
            self.db.conn.commit()
            try:
                if task.stage>=5 and critic_project is not None:
                    critic_status="review_requested"
                    project=Path(critic_project).resolve()
                    # No invented CANON/STYLE for a supposedly real critic.
                    if not all((project/name).is_file() for name in ("CANON.md","STYLE.md")):
                        raise LadderError("real critic project requires CANON.md and STYLE.md")
                    trial_dir=project/"writerforge-training-trials"
                    trial_dir.mkdir(exist_ok=True)
                    scene=trial_dir/(run_id+".txt")
                    scene.write_text(body,encoding="utf-8")
                    result=LitCriticAdapter().review(
                        project_path=project,scene_path=scene,
                        output_dir=folder/"reviews",mode="quick",
                    )
                    critic_status="real_litcritic_report_received_not_validated_by_reader"
                    receipt["critique_report_path"]=str(result["json"])
                    report=json.loads(Path(result["json"]).read_text(encoding="utf-8"))
                    issues=report.get("findings",[])
                    if not isinstance(issues,list):
                        raise LadderError("independent report lacked a list of findings")
                    if issues:
                        problems="\n".join(
                            "- "+str(e.get("impact",""))[:140]
                            for e in issues[:8] if isinstance(e,dict)
                        )
                        revised_text=(
                            packet.prompt+"\n当前原创稿：\n"+body[:2500]
                            +"\n独立编辑指出的问题（不是绝对真理）：\n"
                            +problems
                            +"\n只修准确且可验证的问题，保留人物因果，返回修订后的原创正文。"
                        )
                        if len(revised_text)>MAX_PROMPT_CHARS:
                            raise LadderError("review-guided revision prompt exceeds model context cap")
                        revised_prompt=replace(
                            packet,prompt=revised_text,
                            prompt_sha256=sha256(revised_text.encode("utf-8")).hexdigest(),
                        )
                        revised=local_chat_completion(
                            revised_prompt,model=model,api_base=api_base,max_tokens=3500,
                        ).strip()
                        low,high=STAGES[task.stage-1][2:]
                        if not low<=len(revised)<=high:
                            raise LadderError("critic-guided revision was invalid length")
                        self._copy_guard(revised,task.source_excerpt,task.facet_cards)
                        (folder/"revision_candidate.md").write_text(
                            revised,encoding="utf-8",
                        )
                        receipt["revision_candidate_sha256"]=sha256(
                            revised.encode("utf-8")
                        ).hexdigest()
                        critic_status="independent_review_then_revision_unverified"
            except Exception as exc:
                # Do not misrepresent an unavailable reviewer as a successful
                # judgment. A failed call is durable but cannot advance mastery.
                critic_status="critic_failed"
                receipt["failure_type"]=type(exc).__name__
                raise
            finally:
                receipt["status"]=critic_status
                (folder/"receipt.json").write_text(
                    json.dumps(receipt,ensure_ascii=False,indent=2),
                    encoding="utf-8",
                )
                self.db.conn.execute(
                    """UPDATE literary_training_attempts
                       SET status=?,receipt_json=? WHERE run_id=?""",
                    (critic_status,json.dumps(receipt,ensure_ascii=False),run_id),
                )
                self.db.conn.commit()
            records.append({"stage":task.stage,"status":"practiced_not_mastered",
                            "critic_status":critic_status,
                            "run_id":run_id,"receipt":str(folder/"receipt.json"),
                            "source_facets":len(task.facet_cards)})
        return {"project_id":self.project_id,"work_id":work_id,"attempts":records,
                "global_50_book_review_performed":False,
                "model_finetuned":False,
                "literary_skill_promoted":False}
