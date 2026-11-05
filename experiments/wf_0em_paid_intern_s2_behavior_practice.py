"""0.EM: bounded paid Intern-S2 writing-behavior PRACTICE, not model fine-tuning.

Uses existing DiscoveryModel / DiscoveryCallBudget. Only original synthetic
xianxia questions and GITenberg public-domain 0.EL readings cross provider.
No private WriterForge prose, R2 calls, Canon writes, host changes or retraining.
The output is an UNPROMOTED exercise receipt for later independent reading.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory

from writerforge.reverse_discovery_models import (
    DiscoveryCallBudget, DiscoveryModel, DiscoveryError,
)

MODEL = "intern-s2"
PACK_PATH = Path(__file__).with_name(
    "wf_0el_six_lived_craft_family_misreadings_and_aftercare_readings_20261103.json"
)
FROZEN_LIBRARY = "wf-0el-xuehai-literary-408-20261103-v1"
FROZEN_DIGEST = "dd1efe09346e02e149d0ef942c1f56e030d6cc791109ef5ae46397e90add62a6"
MAX_WIRE_CALLS = 8  # includes EVERY paid retry or continuation
MAX_RESERVED_COMPLETION_TOKENS = 21000
COACH_OUTPUT_TOKENS = 2600
PROSE_OUTPUT_TOKENS = 3000
EXERCISES = (
    {
        "id": "ford-tax",
        "source_id": "classic-0el-4-jm",
        "topic": "仙侠渡口谣言与征船",
        "premise": (
            "青黛城封闭渡口，要求征用全部渔船运送封魔石。"
            "船工阿福怕妻子断药、巡河使谢凝怕妖修逃走、"
            "小徒闻笙只听过人们说封魔石会吞走孩童，"
            "没有人亲眼见过妖修。暴雨将至，一只载着病人的船还没归航。"
            "写一个900字左右的原创仙侠场景，让人物做出不能轻易收回的决定。"
        ),
    },
    {
        "id": "herb-well",
        "source_id": "classic-0el-2-hh",
        "topic": "灵井治病与照料成本",
        "premise": (
            "白芷镇的灵井忽然发苦，药师苏蕴被请去救受伤的采矿少年；"
            "少年阿砚说是龙脉震动，井役胡四认为矿主偷挪了净水符，"
            "矿主的女儿只知道昨夜有人搬走一车药渣。"
            "救治需要烧掉最后一批暖炉炭，镇中老人也在等炭过冬。"
            "写一个900字左右的原创仙侠场景，人物并不知道全部真相。"
        ),
    },
)

class PracticeError(RuntimeError):
    pass

def _digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def _save(path: Path, text: str) -> dict:
    # Atomic enough for a single runner; all inputs are synthetic/public.
    path.write_text(text, encoding="utf8")
    return {"file": path.name, "sha256": _digest(text), "characters": len(text)}

def load_public_sources() -> dict:
    pack = json.loads(PACK_PATH.read_text("utf8"))
    if (pack.get("new_library") != FROZEN_LIBRARY
        or pack.get("old_entries") != 402
        or pack.get("expected_entries") != 408
        or pack.get("expected_full_readings") != 360
        or len(pack.get("items", [])) != 6):
        raise PracticeError("FROZEN_PUBLIC_SOURCE_PACK_CHANGED")
    by_id = {item["id"]: item for item in pack["items"]}
    if len(by_id) != 6:
        raise PracticeError("DUPLICATE_PUBLIC_SOURCE_ID")
    chosen = {}
    for scene in EXERCISES:
        item = by_id[scene["source_id"]]
        original = item["original"]
        if (not 400 <= len(original) <= 2600
            or len(item["anchors"]) != 3
            or not all(anchor in original for anchor in item["anchors"])
            or len(item["annotation"]) != 3
            or not item["reflection"]):
            raise PracticeError("PUBLIC_SOURCE_READING_NOT_COMPLETE")
        chosen[scene["id"]] = item
    return chosen

def coach_prompt(exercise: dict, reading: dict) -> tuple[str, str]:
    original = reading["original"]
    source = "\n".join((
        "【出处】" + reading["work"] + "／" + reading["chapter"],
        "【完整连续原文】", original, "【三条具体批注】",
        *reading["annotation"], "【开放心得】", reading["reflection"]
    ))
    system = (
        "你是为原创小说作者提供不同看法的文学读者，不是唯一裁判。"
        "保留原著的原句证据、人物有限认识与批注可能有偏差的事实。"
        "不要把历史人物偏见或小说神怪解释变成现代客观事实。"
        "只输出JSON，不评分、不声称已经提升写作能力。"
    )
    user = (
        source + "\n【可直接引用的三个逐字锚点】\n" + "\n".join(reading["anchors"]) + "\n【迁移练习题】\n" + exercise["premise"]
        + "\n请返回JSON对象，字段严格如下："
        '{"use":"USE或PARTIAL或SKIP","reason":"不少于25字",'
        '"source_anchors":["原文逐字短串1","原文逐字短串2"],'
        '"habit_questions":[{"ask":"创作前或写作中真正该问的具体问题",'
        '"not_when":"这种提问何时可能误导创作"},'
        '{"ask":"另一问题","not_when":"限制"}],'
        '"perspectives":[{"actor":"人物1","wants":"自己的目标",'
        '"knows":"亲身可知的事实","cost":"自己的可能损失"},'
        '{"actor":"人物2","wants":"...","knows":"...","cost":"..."},'
        '{"actor":"人物3","wants":"...","knows":"...","cost":"..."}],'
        '"disagreement":"两种合理但相冲突的故事解释"}。'
        "短串必须逐字存在于原文，不要只照搬已有批注，"
        "问题是可选择的行为而不是强制段落模板，"
        "如文学材料不合适，请选择SKIP并说明。"
    )
    if len(system) + len(user) > 7800:
        raise PracticeError("COACH_PROMPT_EXCEEDS_BOUND")
    return system, user

def validate_coach(doc: dict, original: str) -> dict:
    if type(doc) is not dict or doc.get("use") not in ("USE", "PARTIAL", "SKIP"):
        raise PracticeError("COACH_USE_OR_SCHEMA_INVALID")
    reason = doc.get("reason")
    if type(reason) is not str or not 20 <= len(reason) <= 460:
        raise PracticeError("COACH_REASON_INVALID")
    anchors = doc.get("source_anchors")
    if (type(anchors) is not list or len(anchors) != 2
        or any(type(x) is not str or not 4 <= len(x) <= 65 or x not in original
               for x in anchors)):
        raise PracticeError("COACH_ANCHORS_NOT_IN_SOURCE")
    questions = doc.get("habit_questions")
    if (type(questions) is not list or len(questions) != 2
        or any(type(x) is not dict or
               any(type(x.get(k)) is not str or not 12 <= len(x[k]) <= 180
                   for k in ("ask", "not_when")) for x in questions)):
        raise PracticeError("COACH_BEHAVIOR_QUESTIONS_INVALID")
    perspectives = doc.get("perspectives")
    if (type(perspectives) is not list or len(perspectives) != 3
        or any(type(x) is not dict or any(
            type(x.get(k)) is not str or not 2 <= len(x[k]) <= 200
            for k in ("actor", "wants", "knows", "cost")) for x in perspectives)
        or len({x["actor"] for x in perspectives}) != 3):
        raise PracticeError("COACH_DISTINCT_PERSPECTIVES_INVALID")
    disagreement = doc.get("disagreement")
    if type(disagreement) is not str or not 18 <= len(disagreement) <= 360:
        raise PracticeError("COACH_DIFFERENT_READINGS_MISSING")
    return {
        "use": doc["use"], "reason": reason,
        "source_anchors": anchors,
        "habit_questions": questions,
        "perspectives": perspectives,
        "disagreement": disagreement,
    }

def writer_prompt(exercise: dict, coach: dict | None) -> tuple[str, str]:
    system = (
        "你是中文原创仙侠小说作者。写完整自然的小说场景，不能"
        "照抄古籍，也不能把技法、评语或提问放在正文。"
        "人物有自己的目标与误判，仙术不能替代具体行动后果。"
        "叙事允许留白、失败、幽默和观点不一致。"
    )
    user = ("【原创任务】" + exercise["premise"] +
        "\n只写正文，不要标题，不要解释人物动机的表格，"
        "不能复制现成小说。以场景的某个具体后果收束。")
    if coach and coach["use"] != "SKIP":
        questions = "\n".join(
            "可选写作问题：" + x["ask"] + "；不适用时：" + x["not_when"]
            for x in coach["habit_questions"])
        views = "\n".join(
            x["actor"] + "想：" + x["wants"] + "；只知：" + x["knows"]
            + "；可能付出：" + x["cost"]
            for x in coach["perspectives"])
        user += ("\n【WF的暂时写作习惯练习：可质疑、可放弃、并非命令】\n"
                 + questions + "\n【互相冲突的角色立场】\n" + views
                 + "\n【尚未证明的不同解读】" + coach["disagreement"]
                 + "\n仅在确实适用时用这些问题审视故事，不能照字填空、"
                   "不能为了完成清单而牺牲语言与人物。")
    if len(system) + len(user) > 4800:
        raise PracticeError("WRITER_PROMPT_EXCEEDS_BOUND")
    return system, user

def _copied_from_source(candidate: str, original: str) -> bool:
    # A source-literal safeguard, not a literary quality score.
    clean = "".join(original.split())
    body = "".join(candidate.split())
    return any(clean[i:i+48] in body for i in range(0, max(0, len(clean)-47), 16))

def dry_run() -> dict:
    source = load_public_sources()
    observations = []
    for exercise in EXERCISES:
        a, b = coach_prompt(exercise, source[exercise["id"]])
        x, y = writer_prompt(exercise, None)
        observations.append({
            "task": exercise["id"], "source_id": exercise["source_id"],
            "source_sha256": _digest(source[exercise["id"]]["original"]),
            "coach_prompt_sha256": _digest(a + b),
            "baseline_prompt_sha256": _digest(x + y),
        })
    return {
        "format":"wf.0em.bounded-intern-s2-writing-practice.v1",
        "state":"OFFLINE_PRECHECK_COMPLETE",
        "reference_library":FROZEN_LIBRARY,
        "reference_full_library_sha256":FROZEN_DIGEST,
        "planned_teacher_calls":2, "planned_writer_calls":4,
        "max_provider_wire_calls":MAX_WIRE_CALLS,
        "max_reserved_completion_tokens":MAX_RESERVED_COMPLETION_TOKENS,
        "uses_public_domain_sources_only":True,
        "user_private_prose_sent":False, "canon_writes":0,
        "production_model_changed":False,"author_accepted":False,
        "model_weight_training":False,
        "literary_winner":"UNDETERMINED",
        "tasks":observations,
    }

def paid_run(output_dir: Path) -> dict:
    if os.getenv("WF0EM_PAID_EXPERIMENT") != "WF0EM_BOUNDED_S2_20261105":
        raise PracticeError("EXPLICIT_PAID_RUN_GATE_NOT_OPEN")
    key = os.getenv("DISCOVERY_API_KEY")
    if not key:
        raise PracticeError("DISCOVERY_KEY_NOT_AVAILABLE_IN_THIS_RUNTIME")
    if len(key)>512:
        raise PracticeError("DISCOVERY_KEY_UNEXPECTED_SHAPE")
    reference=load_public_sources()
    output_dir.mkdir(parents=True,exist_ok=True)
    budget=DiscoveryCallBudget(
        max_calls=MAX_WIRE_CALLS,
        max_reserved_output_tokens=MAX_RESERVED_COMPLETION_TOKENS,
    )
    # Intern-S2 by default may spend the whole allowance on hidden thinking.
    # Official API supports explicit thinking_mode=False for visible task output.
    teacher=DiscoveryModel(name=MODEL,role="planner",api_key=key,
                           budget=budget,thinking_mode=False)
    writer=DiscoveryModel(name=MODEL,role="writer",api_key=key,
                          budget=budget,thinking_mode=False)
    record=dry_run()
    record["state"]="IN_PROGRESS"
    record["model"]=MODEL
    record["results"]=[]
    manifest=output_dir / "manifest.json"
    for exercise in EXERCISES:
        source=reference[exercise["id"]]
        sys_prompt, user_prompt=coach_prompt(exercise,source)
        item={"task":exercise["id"],"source_id":exercise["source_id"],
              "phase":"COACH","reader_judgment":"NOT_RUN",
              "accepted":False,"literary_improvement_proven":False}
        record["results"].append(item)
        try:
            interpretation=validate_coach(
                teacher.ask(sys_prompt,user_prompt,num_predict=COACH_OUTPUT_TOKENS),
                source["original"],
            )
            item["coach"]= _save(output_dir / (exercise["id"]+"-coach.json"),
                                 json.dumps(interpretation,ensure_ascii=False,indent=2))
            item["source_choice"]=interpretation["use"]
            if interpretation["use"]=="SKIP":
                item["phase"]="SOURCE_SKIPPED_UNREVIEWED"
                continue
            item["phase"]="BASELINE"
            original=""
            for arm in ("A","B"):
                sys_write, question=writer_prompt(
                    exercise,interpretation if arm=="B" else None)
                if arm=="B":
                    item["phase"]="PRACTICE_B"
                text=writer.ask(sys_write,question,num_predict=PROSE_OUTPUT_TOKENS)["scene"]
                if _copied_from_source(text,source["original"]):
                    raise PracticeError("PROSE_SUSPECTED_LONG_SOURCE_COPY")
                item[arm]=_save(output_dir / (exercise["id"]+"-"+arm+".md"),text)
                if arm=="A":
                    original=text
            item["length_difference_ratio"]=round(
                abs(item["A"]["characters"]-item["B"]["characters"])/
                max(item["A"]["characters"],item["B"]["characters"]),3
            )
            item["same_author_model"]=True
            item["same_requested_writer_output_budget"]=True
            item["phase"]="COMPLETE_UNREVIEWED"
        except (DiscoveryError, PracticeError, ValueError, KeyError, TypeError) as exc:
            item["phase"]="FAILED_UNREVIEWED"
            # Never output content, private key, or provider error body.
            code=str(exc)
            item["failure_code"]=(
                code if code.startswith(("DISCOVERY_","MODEL_","COACH_",
                                         "PROSE_","EXPLICIT_","PUBLIC_"))
                else type(exc).__name__
            )[:100]
            break
        finally:
            record["wire_calls_reserved"]=budget.calls
            record["reserved_completion_tokens_not_usage"]=budget.reserved_output_tokens
            record["provider_reported_prompt_tokens"]=budget.total_prompt_tokens
            record["provider_reported_completion_tokens"]=budget.total_completion_tokens
            record["safe_response_observations"]=budget.response_observations
            manifest.write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding="utf8")
    record["state"]=(
        "COMPLETE_UNREVIEWED" if all(
            x["phase"]=="COMPLETE_UNREVIEWED" for x in record["results"])
        and len(record["results"])==len(EXERCISES)
        else "INCOMPLETE_OR_FAILED"
    )
    manifest.write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding="utf8")
    return record

def main() -> int:
    parser=argparse.ArgumentParser()
    parser.add_argument("--dry-run",action="store_true")
    parser.add_argument("--live",action="store_true")
    parser.add_argument("--output-dir",type=Path)
    args=parser.parse_args()
    if args.dry_run==args.live:
        raise SystemExit("choose exactly one of --dry-run or --live")
    if args.dry_run:
        d=dry_run()
        print(json.dumps(d,ensure_ascii=False,sort_keys=True))
        return 0
    if args.output_dir is None:
        raise SystemExit("paid run requires an explicit output directory")
    try:
        d=paid_run(args.output_dir)
    except PracticeError as exc:
        print(json.dumps({"status":str(exc),"provider_call_performed":False},
                         ensure_ascii=False))
        return 2
    # Public Actions logs contain counts only; model text is artifact-only.
    print(json.dumps({
        "status":d["state"],"model":MODEL,
        "exercise_count":len(d["results"]),
        "complete_pairs":sum(x["phase"]=="COMPLETE_UNREVIEWED" for x in d["results"]),
        "provider_wire_calls_reserved":d.get("wire_calls_reserved",0),
        "reserved_completion_tokens_not_usage":d.get(
            "reserved_completion_tokens_not_usage",0),
        "provider_reported_prompt_tokens":d.get("provider_reported_prompt_tokens",0),
        "provider_reported_completion_tokens":d.get("provider_reported_completion_tokens",0),
        "source_provenance":"public_domain_GITenberg","canon_writes":0,
        "literary_quality_proven":False,"model_weight_training":False,
    },ensure_ascii=False))
    return 0 if d["state"]=="COMPLETE_UNREVIEWED" else 3

if __name__=="__main__":
    raise SystemExit(main())
