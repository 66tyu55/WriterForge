"""V65 user-requested, assistant-taught literary *scene applicability* curriculum.

Use as explicit instruction, not as proof that WF autonomously learned a
literary method or has improved prose quality. The writer receives at most
two conditioned ACTIONS, not any source novel or illustrative example.
Scene diagnosis is to be made by WF's planner and is epistemically fallible.
"""
from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import json
import re

PROFILE_FORMAT = "writerforge.scene-profile.v1"
PLAN_FORMAT = "writerforge.scene-craft-plan.v1"
PAIR_FORMAT = "writerforge.scene-craft-a-b-observation.v1"

MODES = frozenset({
    "setup", "quiet", "pursuit", "action", "investigation",
    "discovery", "revelation", "negotiation", "confrontation",
    "aftermath", "transition", "spectacle", "decision"
})
READER_EFFECTS = frozenset({
    "tension", "empathy", "unease", "grief", "suspense",
    "surprise", "clarity", "awe", "warmth"
})
TEMPOS = frozenset({"fast","measured","slow"})
VIEWPOINTS = frozenset({"limited","objective","omniscient"})
FEATURE_STATES = frozenset({"PRESENT","ABSENT","UNCERTAIN"})
DIAGNOSIS_ORIGINS = frozenset({"WF_PLANNER","AUTHOR_OUTLINE"})
PROFILE_FIELDS = frozenset({
    "schema","scene_id","diagnosis_origin","mode",
    "reader_effect","tempo","viewpoint","scene_goal",
    "active_obstacle","planned_change","facts"
})
MAX_SELECTED = 2
MAX_PROFILE_FACTS = 24
MAX_GUIDANCE_CHARS = 1300
DIMENSIONS = ("causality","character_agency","information",
              "emotional_effect","prose_rhythm")


class SceneCraftInputError(ValueError):
    pass


def require(condition: bool,code: str) -> None:
    if not condition:
        raise SceneCraftInputError(code)


def canonical(value) -> bytes:
    return json.dumps(value,ensure_ascii=False,sort_keys=True,
                      separators=(",",":"),allow_nan=False).encode("utf-8")


def digest(value) -> str:
    return sha256(canonical(value)).hexdigest()


def load_scene_lessons():
    """Open bundled, original teaching source. Return a NEW dict each call.

    No caching of live mutable objects and no access to private R2,
    Google Drive, novels, network or model providers.
    """
    path=Path(__file__).with_name("scene_craft_lessons_v1.json")
    data=path.read_bytes()
    require(1000<=len(data)<=75000,"SCENE_TEACHING_PACK_SIZE_INVALID")
    try:
        pack=json.loads(data)
    except (TypeError,ValueError) as exc:
        raise SceneCraftInputError("SCENE_TEACHING_PACK_JSON_INVALID") from exc
    require(isinstance(pack,dict) and
            pack.get("format")=="writerforge.scene-craft-teaching.v1" and
            pack.get("origin")=="ASSISTANT_TAUGHT_BY_USER_REQUEST" and
            pack.get("training_status")=="INSTRUCTION_NOT_LEARNER_DISCOVERED",
            "SCENE_TEACHING_PACK_PROVENANCE_INVALID")
    cards=pack.get("lessons")
    require(isinstance(cards,list) and len(cards)==13,
            "SCENE_TEACHING_PACK_CARD_COUNT_INVALID")
    ids=set()
    for row in cards:
        require(isinstance(row,dict) and set(row)=={
            "id","title","domain","modes","effects","tempos",
            "viewpoints","required","forbidden","priority",
            "instructions","pitfall","review_question","example_before",
            "example_after"}, "SCENE_TEACHING_CARD_SCHEMA_INVALID")
        code=row["id"]
        require(isinstance(code,str) and
                re.fullmatch(r"[A-Z][A-Z0-9_]{4,59}",code) and
                code not in ids,"SCENE_TEACHING_CARD_ID_INVALID")
        ids.add(code)
        for name,valid in (("modes",MODES),("effects",READER_EFFECTS),
                           ("tempos",TEMPOS),("viewpoints",VIEWPOINTS)):
            values=row[name]
            require(isinstance(values,list) and 1<=len(values)<=6 and
                    len(set(values))==len(values) and set(values)<=valid,
                    "SCENE_TEACHING_CARD_CONTEXT_INVALID")
        for name in ("required","forbidden"):
            values=row[name]
            require(isinstance(values,list) and 1<=len(values)<=5 and
                    len(set(values))==len(values) and all(
                        isinstance(x,str) and
                        re.fullmatch(r"[a-z][a-z0-9_]{2,49}",x)
                        for x in values),
                    "SCENE_TEACHING_CARD_FEATURE_INVALID")
        require(not (set(row["required"])&set(row["forbidden"])),
                "SCENE_TEACHING_CARD_CONFLICT_INVALID")
        require(isinstance(row["domain"],str) and
                re.fullmatch(r"[a-z]{4,24}",row["domain"]) and
                type(row["priority"]) is int and 1<=row["priority"]<=100,
                "SCENE_TEACHING_CARD_PRIORITY_INVALID")
        instructions=row["instructions"]
        require(isinstance(instructions,list) and
                2<=len(instructions)<=4 and
                all(isinstance(x,str) and 15<=len(x)<=160 for x in
                    instructions),"SCENE_TEACHING_CARD_STEPS_INVALID")
        for name in ("title","pitfall","review_question",
                     "example_before","example_after"):
            text=row[name]
            require(isinstance(text,str) and 8<=len(text)<=250,
                    "SCENE_TEACHING_CARD_TEXT_INVALID")
    pack["pack_sha256"]=sha256(data).hexdigest()
    return pack


def _validate_profile(p,*,known_features:set[str]):
    require(isinstance(p,dict) and set(p)==PROFILE_FIELDS and
            p.get("schema")==PROFILE_FORMAT,
            "SCENE_PROFILE_SCHEMA_INVALID")
    require(isinstance(p["scene_id"],str) and
            re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_-]{1,99}",
                         p["scene_id"]) is not None,
            "SCENE_PROFILE_ID_INVALID")
    require(p["diagnosis_origin"] in DIAGNOSIS_ORIGINS and
            p["mode"] in MODES and
            p["reader_effect"] in READER_EFFECTS and
            p["tempo"] in TEMPOS and
            p["viewpoint"] in VIEWPOINTS,
            "SCENE_PROFILE_CONTEXT_INVALID")
    for name in ("scene_goal","active_obstacle","planned_change"):
        t=p[name]
        require(isinstance(t,str) and 8<=len(t.strip())<=240,
                "SCENE_PROFILE_CAUSAL_PLAN_INVALID")
    facts=p["facts"]
    require(isinstance(facts,dict) and 1<=len(facts)<=MAX_PROFILE_FACTS,
            "SCENE_PROFILE_FACT_COUNT_INVALID")
    for feature,entry in facts.items():
        require(feature in known_features,"SCENE_PROFILE_FEATURE_UNKNOWN")
        require(isinstance(entry,dict) and set(entry)=={
                "state","observation"} and
                entry["state"] in FEATURE_STATES,
                "SCENE_PROFILE_FACT_SCHEMA_INVALID")
        explanation=entry["observation"]
        require(isinstance(explanation,str) and
                8<=len(explanation.strip())<=230,
                "SCENE_PROFILE_FACT_OBSERVATION_INVALID")
    # This checks format, NOT whether the narrator genuinely observed
    # what the planner claims. Literary meaning remains contestable.
    return {
        **{k:p[k] for k in PROFILE_FIELDS if k!="facts"},
        "facts":{k:{"state":facts[k]["state"],
                    "observation":facts[k]["observation"].strip()}
                 for k in sorted(facts)}
    }


def _classify(card,p):
    if p["mode"] not in card["modes"]:
        return "SKIP","MODE_MISMATCH"
    if p["reader_effect"] not in card["effects"]:
        return "SKIP","READER_EFFECT_MISMATCH"
    if p["tempo"] not in card["tempos"]:
        return "SKIP","TEMPO_MISMATCH"
    if p["viewpoint"] not in card["viewpoints"]:
        return "SKIP","POV_MISMATCH"
    facts=p["facts"]
    if any(facts.get(k,{}).get("state")=="PRESENT" for k in card["forbidden"]):
        return "SKIP","CONTRAINDICATED"
    if any(facts.get(k,{}).get("state")=="ABSENT" for k in card["required"]):
        return "SKIP","REQUIRED_CONDITION_FALSE"
    if any(facts.get(k,{}).get("state")!="PRESENT" for k in card["required"]) or any(
           facts.get(k,{}).get("state")!="ABSENT" for k in card["forbidden"]):
        return "UNCERTAIN","SCENE_EVIDENCE_UNCERTAIN"
    return "ELIGIBLE","CONDITIONS_PRESENT"


class SceneCraftTeacher:
    """13 assistant-taught experience hypotheses, at most 2 applied.

    Selection uses an explicit semantic diagnosis, NOT word frequency
    in a scene or blindly matching strings within the novel. The diagnosis
    itself must be produced from WF's understanding and may be wrong.
    """
    def __init__(self):
        self.pack=load_scene_lessons()
        self.lessons=self.pack["lessons"]
        self.features=set()
        for row in self.lessons:
            self.features.update(row["required"])
            self.features.update(row["forbidden"])

    def plan(self,profile,*,enabled=True,max_lessons=MAX_SELECTED):
        require(type(enabled) is bool and
                type(max_lessons) is int and 1<=max_lessons<=2,
                "SCENE_TEACHING_CONTROL_INVALID")
        p=_validate_profile(profile,known_features=self.features)
        eligible=[]
        decisions={}
        for card in self.lessons:
            if not enabled:
                result=("SKIP","USER_DISABLED")
            else:
                result=_classify(card,p)
            decisions[card["id"]]=result
            if result[0]=="ELIGIBLE":
                eligible.append(card)
        eligible.sort(key=lambda r:(-r["priority"],r["id"]))
        chosen=[]
        used_domains=set()
        for card in eligible:
            if len(chosen)>=max_lessons:
                decisions[card["id"]]=("SKIP","INTERVENTION_BUDGET")
            elif card["domain"] in used_domains:
                decisions[card["id"]]=("SKIP","SAME_DOMAIN_ALREADY_SELECTED")
            else:
                chosen.append(card)
                used_domains.add(card["domain"])
                decisions[card["id"]]=("SELECT","CONDITIONS_PRESENT")
        fragments=[]
        for row in chosen:
            steps="；".join(row["instructions"])
            fragments.append(
                f"【{row['title']}】{steps}。"
                f"避免：{row['pitfall']} 自检：{row['review_question']}")
        guidance="\n".join(fragments)
        require(len(guidance)<=MAX_GUIDANCE_CHARS,
                "SCENE_TEACHING_GUIDANCE_OVER_BUDGET")
        result={
            "format":PLAN_FORMAT,
            "scene_id":p["scene_id"],
            "profile_sha256":digest(p),
            "teaching_pack_sha256":self.pack["pack_sha256"],
            "teaching_origin":self.pack["origin"],
            "training_status":"ASSISTANT_TAUGHT_EXPERIMENTAL_ONLY",
            "selected_ids":[x["id"] for x in chosen],
            "writer_guidance":guidance,
            "decisions":[{
                "lesson_id":row["id"],"decision":decisions[row["id"]][0],
                "reason_code":decisions[row["id"]][1]
            } for row in self.lessons],
            "example_prose_not_sent_to_writer":True,
            "literary_improvement_proven":False,
            "model_calls_during_selection":0,
            "requires_observation_of_real_draft":True,
        }
        result["plan_sha256"]=digest(result)
        return result


def diagnosis_prompt(scene_goal:str,*,scene_id:str):
    """Guide WF's *own* planner to explain applicability, no model call here."""
    require(isinstance(scene_goal,str) and
            8<=len(scene_goal.strip())<=2000 and
            isinstance(scene_id,str) and
            re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{1,99}",
                         scene_id) is not None,
            "SCENE_DIAGNOSIS_INPUT_INVALID")
    pack=load_scene_lessons()
    features=sorted(set(x for row in pack["lessons"]
                        for group in ("required","forbidden")
                        for x in row[group]))
    return (
        "你是WriterForge自己的场景分析模块，不写正文，不替作者抄例文。"
        "先观察人物此刻的目标、障碍、已知与未知、可承担的代价、"
        "空间行动、上一场遗留因果以及读者预期感受。"
        "不是看到关键词就贴标签；每个PRESENT/ABSENT判断必须附具体"
        "人物/物件/行动的证据说明，没依据写UNCERTAIN而不是猜。"
        "不准为了调用伏笔技巧杜撰此前根本没发生的铺垫。"
        "仅输出可被程序校验的JSON对象，不输出创作正文。"
        f"场景ID:{scene_id}。创作目标:{scene_goal}。"
        f"字段必须是{sorted(PROFILE_FIELDS)}；"
        f"schema固定{PROFILE_FORMAT}；diagnosis_origin写WF_PLANNER；"
        f"mode从{sorted(MODES)}选一个；"
        f"reader_effect从{sorted(READER_EFFECTS)}选一个；"
        f"tempo从{sorted(TEMPOS)}选一个；"
        f"viewpoint从{sorted(VIEWPOINTS)}选一个。"
        "scene_goal/active_obstacle/planned_change各写具体8至240字。"
        "facts是有界字典，键从允许的观察项里选，不超过24项："
        f"{features}；每项仅含state(PRESENT/ABSENT/UNCERTAIN)"
        "与observation(能具体解释判断依据的8至230字)。"
        "至少提供欲选经验的前置条件和需要明确排除的禁用条件；"
        "若缺前提则允许最终弃用所有经验。"
    )


def compare_scene_drafts(*,scene_id,scene_profile_sha256,
                         teaching_pack_sha256,selected_lesson_ids,
                         baseline_draft,taught_draft,
                         ratings=None,max_relative_length_difference=.15):
    """Metadata-only control for a future actual same-task A/B review.

    No LLM calls, no fabricated literary score, no prose or novel stored.
    A single future critic's scores are only case-scoped observations.
    """
    require(isinstance(scene_id,str) and
            re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{1,99}",
                         scene_id) is not None and
            all(isinstance(s,str) and
                re.fullmatch(r"[a-f0-9]{64}",s)
                for s in (scene_profile_sha256,teaching_pack_sha256)) and
            isinstance(selected_lesson_ids,list) and
            0<len(selected_lesson_ids)<=MAX_SELECTED and
            len(set(selected_lesson_ids))==len(selected_lesson_ids) and
            all(isinstance(t,str) and
                re.fullmatch(r"[A-Z][A-Z0-9_]{4,59}",t)
                for t in selected_lesson_ids),
            "SCENE_PAIR_METADATA_INVALID")
    require(isinstance(baseline_draft,str) and
            isinstance(taught_draft,str) and
            type(max_relative_length_difference) in (int,float) and
            .05<=max_relative_length_difference<=.15,
            "SCENE_PAIR_TEXT_OR_GATE_INVALID")
    size={"baseline":len(baseline_draft),"taught":len(taught_draft)}
    maximum=max(size.values())
    ratio=abs(size["baseline"]-size["taught"])/maximum if maximum else 1
    require(ratio<=max_relative_length_difference,
            "SCENE_PAIR_LENGTH_MISMATCH_UNSCORABLE")
    require(all(250<=v<=4500 for v in size.values()),
            "SCENE_PAIR_DRAFT_OUTSIDE_BOUNDS")
    hashes={
        "baseline":sha256(baseline_draft.encode("utf-8")).hexdigest(),
        "taught":sha256(taught_draft.encode("utf-8")).hexdigest()
    }
    require(hashes["baseline"]!=hashes["taught"],
            "SCENE_PAIR_IDENTICAL_DRAFTS_NO_EFFECT")
    ordered=sorted(hashes,key=lambda k:hashes[k])
    labels={"A":ordered[0],"B":ordered[1]}
    result={
        "format":PAIR_FORMAT,"scene_id":scene_id,
        "scene_profile_sha256":scene_profile_sha256,
        "teaching_pack_sha256":teaching_pack_sha256,
        "selected_lesson_ids":selected_lesson_ids,
        "draft_sha256":hashes,"draft_characters":size,
        "relative_length_difference":round(ratio,5),
        "review_blinding_labels_by_sha256":{
            tag:hashes[name] for tag,name in labels.items()},
        "length_comparable":True,
        "literary_improvement_proven":False,
        "single_case_only":True,
        "original_drafts_not_retained":True,
    }
    if ratings is None:
        result["comparison_status"]="TEXT_PAIR_READY_FOR_BLIND_REVIEW"
        result["per_dimension_taught_minus_baseline"]=None
    else:
        require(isinstance(ratings,dict) and set(ratings)=={"A","B"},
                "SCENE_PAIR_REVIEW_SCHEMA_INVALID")
        for label in ("A","B"):
            dim=ratings[label]
            require(isinstance(dim,dict) and set(dim)==set(DIMENSIONS)
                    and all(type(x) is int and 0<=x<=100
                            for x in dim.values()),
                    "SCENE_PAIR_REVIEW_DIMENSIONS_INVALID")
        deltas={
            d:ratings["A" if labels["A"]=="taught" else "B"][d]-
              ratings["A" if labels["A"]=="baseline" else "B"][d]
            for d in DIMENSIONS
        }
        negatives=sum(x<0 for x in deltas.values())
        positives=sum(x>0 for x in deltas.values())
        result["per_dimension_taught_minus_baseline"]=deltas
        result["comparison_status"]=(
            "TASK_SCOPED_REGRESSION" if negatives>=1
            else "POSSIBLE_TASK_SCOPED_BENEFIT_NOT_PROVEN" if positives>=3
            else "NO_CLEAR_BENEFIT")
        result["reviewer_scores_are_subjective"]=True
    result["report_sha256"]=digest(result)
    return result
