"""WF 0.EN: two original xianxia holdouts with bounded same-model A/B.

Reuse ACTUAL prior paid coach, no new teacher calls or private data. Exactly
two optional writing questions are transferred, NOT its scenario-specific cast.
Writer outputs remain unaccepted; length mismatch fails comparison eligibility.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
from experiments.wf_0em_paid_intern_s2_behavior_practice import (
    load_public_sources, validate_coach, _save, PracticeError
)
from writerforge.reverse_discovery_models import (
    DiscoveryModel, DiscoveryCallBudget, DiscoveryError
)

MODEL="deepseek-v4-pro-0813"
PRIOR_RUN=42007328800
PRIOR_COACH_SHA="e444d2c8fce5bac1ea5b833b78a1c9af108952eab8f52a2cc8def29919817021"
PRIOR_HABITS_SHA="10e1109669b8c452bb2aaac04e5bac142a7cde6f382d999972540822b487ccc8"
LIBRARY="wf-0el-xuehai-literary-408-20261103-v1"
APPROVAL="WF0EN_TWO_SCENE_PAID_HOLDOUT_20261105"
WRITER_TOKENS=2600
MAX_CALLS=6
MAX_RESERVED=15600
MIN_LENGTH=900
MAX_LENGTH=1400
MAX_RATIO=.20

SCENES=(
    {"id":"well-winter-coal","title":"灵井救病与冬炭",
     "premise":(
        "白芷镇的灵井忽然发苦，采矿少年阿砚坠井受伤。"
        "药师苏蕴可以借炉火开灵脉保命，却要烧掉最后一批暖炉炭。"
        "井役胡四听人说矿主夜里挪走了净水符，自己并没看见；"
        "矿主女儿聂禾亲眼见一车药渣被搬走，却不知是谁指使。"
        "山下老人缺炭将挨冻，没有人证实井水发苦的真正原因。"
        "写一个完整原创仙侠场景，人物须做出不能立即撤销的决定。")},
    {"id":"bridge-evacuation","title":"兽潮传言与旧桥撤村",
     "premise":(
        "青羽关传来兽潮警报，镇守使要求木匠尤通弃工坊撤村。"
        "尤通徒弟失踪，他知道旧桥木桩已朽，却怕离开后找不到徒弟。"
        "寡妇贺蘅亲眼见桥墩裂缝，驿卒桑野只听军令说妖兽过了山脊，"
        "村童向秋捡了半张阵图却看不懂印记。桥连着药田与撤离车队，"
        "没人亲眼见过兽潮，夜里桥板开始异响。"
        "写一个完整原创玄幻场景，争执要改变人物实际行动，"
        "结尾留下某人承担的真实代价。")}
)
# This is our explicitly human-authored transfer of existing paid advice,
# NOT a new verbatim DeepSeek answer or an invented literature original.
TRANSFER=(
    "人物此刻真正亲眼知道什么，哪些只是从别人听来或自己猜的？"
    "直觉推动高潮时可以不逐项核对，别把角色写成无所不知。",
    "眼前决定消耗谁的时间、体力、财物、行动权或信任？"
    "谁先承担后果？寓言场景不必机械列损失清单。"
)

class HoldoutError(RuntimeError): pass

def digest(blob: bytes) -> str:
    return hashlib.sha256(blob).hexdigest()

def verify_old_coach(directory: Path) -> dict:
    try:
        raw=(directory/"validated-prior-coach.json").read_bytes()
        evidence=json.loads((directory/"replay-manifest.json").read_text("utf8"))
        decoded=json.loads(raw)
    except (OSError,ValueError,TypeError) as exc:
        raise HoldoutError("REAL_PAID_COACH_ARTIFACT_MISSING") from exc
    if (digest(raw)!=PRIOR_COACH_SHA
        or evidence.get("previous_coach_sha256")!=PRIOR_COACH_SHA
        or evidence.get("phase")!="COMPLETE_UNREVIEWED"
        or evidence.get("source_library")!=LIBRARY
        or evidence.get("model")!=MODEL
        or evidence.get("previous_run_id")!=42006546104
        or set(evidence.get("writing_outputs",{}))!={"A","B"}):
        raise HoldoutError("PAID_COACH_OR_MANIFEST_FINGERPRINT_MISMATCH")
    for arm in ("A","B"):
        raw_prose=(directory/("ford-tax-"+arm+".md")).read_bytes()
        if digest(raw_prose)!=evidence["writing_outputs"][arm]["sha256"]:
            raise HoldoutError("PRIOR_WRITING_FINGERPRINT_MISMATCH")
    source=load_public_sources()["ford-tax"]["original"]
    coach=validate_coach(decoded,source)
    if coach["use"]!="USE":
        raise HoldoutError("PREVIOUS_MODEL_DID_NOT_USE_SOURCE")
    actual=digest(json.dumps(coach["habit_questions"],ensure_ascii=False,
         separators=(",",":")).encode("utf8"))
    if actual!=PRIOR_HABITS_SHA:
        raise HoldoutError("PAID_HABITS_NOT_ORIGINAL")
    return coach

def scene_prompt(scene: dict, arm: str) -> tuple[str,str]:
    if arm not in ("A","B"):
        raise HoldoutError("ARM_UNKNOWN")
    system=("你是一位有生活经验的原创中文玄幻小说作者。"
        "用实际动作与自然话语让人物活起来，允许隐含、失败、"
        "幽默、差异和尚未破解的事实。只输出纯正文，不写标题、提纲、评论。")
    user=("【小说题目】"+scene["premise"]+
        "\n【共同篇幅约束】本篇以1100汉字为中心，严格限制在900至1400个汉字。"
        "不要写成长篇，拒绝结尾总结和套话；必须有现场过程、具体选择和后果。"
        "不要引用任何已发表小说或解释文学技巧。")
    if arm=="B":
        user+=("\n【仅在合适时可采用的两个写作习惯，不是填空规则】\n"
            +"\n".join(TRANSFER)
            +"\n不同人物可以合理地互相反对，不强制和解，也不能"
            "把上一份渡口练习的人物、事件、具体看法搬到本题。"
            "不必在正文提及这些写作提示。")
    return system,user

def relative_difference(a: int,b: int) -> float:
    return round(abs(a-b)/max(a,b),4) if a and b else 1.0

def preflight(prior: Path) -> dict:
    coach=verify_old_coach(prior)
    scenes=[]
    for scene in SCENES:
        prompts={}
        for arm in ("A","B"):
            sys,user=scene_prompt(scene,arm)
            if len(sys+user)>2800:
                raise HoldoutError("PROMPT_TOO_LONG")
            prompts[arm]={
                "sha256":digest((sys+user).encode("utf8")),
                "characters":len(sys+user)}
        scenes.append({"id":scene["id"],"title":scene["title"],
                       "prompt_receipts":prompts})
    return {
        "format":"wf.0en.paid-behavior-holdout.v1",
        "phase":"OFFLINE_VALIDATED_ONLY",
        "old_run":PRIOR_RUN,"old_coach_sha256":PRIOR_COACH_SHA,
        "old_source_library":LIBRARY,
        "original_model_questions":coach["habit_questions"],
        "explicit_human_transfer_questions":list(TRANSFER),
        "teacher_calls":0,"writer_model":MODEL,
        "writer_model_same_for_A_and_B":True,
        "requested_tokens_per_arm":WRITER_TOKENS,
        "max_wire_calls_including_retry":MAX_CALLS,
        "max_reserved_output_tokens_not_usage":MAX_RESERVED,
        "expected_chinese_characters":[MIN_LENGTH,MAX_LENGTH],
        "max_relative_length_difference":MAX_RATIO,
        "new_private_text_uploaded":False,"base_weights_modified":False,
        "canon_writes":0,"r2_writes":0,"author_accepted":False,
        "quality_improvement_proven":False,"scenes":scenes,
    }

def live(prior: Path, output: Path) -> dict:
    if os.getenv("WF0EN_PAID_APPROVAL")!=APPROVAL:
        raise HoldoutError("EXPLICIT_PAID_GATE_CLOSED")
    key=os.getenv("DISCOVERY_API_KEY")
    if not key or len(key)>512 or any(ch.isspace() for ch in key):
        raise HoldoutError("DISCOVERY_KEY_MISSING")
    data=preflight(prior)
    output.mkdir(parents=True,exist_ok=True)
    (output/"frozen-plan.json").write_text(
        json.dumps(data,ensure_ascii=False,indent=2),encoding="utf8")
    budget=DiscoveryCallBudget(max_calls=MAX_CALLS,
        max_reserved_output_tokens=MAX_RESERVED)
    writer=DiscoveryModel(name=MODEL,role="writer",api_key=key,budget=budget)
    data["phase"]="IN_PROGRESS_UNACCEPTED"
    data["results"]=[]
    try:
        for scene in SCENES:
            item={"id":scene["id"],"topic":scene["title"],
                  "phase":"STARTED","arms":{},"review":"NOT_STARTED"}
            data["results"].append(item)
            for arm in ("A","B"):
                sys,user=scene_prompt(scene,arm)
                prose=writer.ask(sys,user,num_predict=WRITER_TOKENS)["scene"]
                if len(prose)<220 or len(prose)>4500:
                    raise HoldoutError("INVALID_MODEL_PROSE_LENGTH")
                item["arms"][arm]=_save(
                    output/(scene["id"]+"-"+arm+".md"),prose)
                item["phase"]="ARM_"+arm+"_SAVED_UNACCEPTED"
            a=item["arms"]["A"]["characters"]
            b=item["arms"]["B"]["characters"]
            item["length_ratio"]=relative_difference(a,b)
            item["length_comparable"]=(
                MIN_LENGTH<=a<=MAX_LENGTH and MIN_LENGTH<=b<=MAX_LENGTH
                and item["length_ratio"]<=MAX_RATIO)
            item["comparison"]="ELIGIBLE_FOR_BLINDED_READING" if (
                item["length_comparable"]) else "LENGTH_CONFOUNDED"
            item["phase"]="COMPLETE_UNREVIEWED"
    except (HoldoutError,DiscoveryError,PracticeError,ValueError,TypeError,KeyError) as exc:
        data["phase"]="FAILED_PARTIAL_UNACCEPTED"
        code=str(exc)
        data["error_code"]=code if code.startswith(
            ("DISCOVERY_","HOLDOUT_","MODEL_","INVALID_")) else type(exc).__name__
    else:
        data["phase"]="COMPLETE_UNREVIEWED"
    finally:
        data["wire_calls_reserved"]=budget.calls
        data["reserved_output_tokens_not_usage"]=budget.reserved_output_tokens
        data["reported_prompt_tokens"]=budget.total_prompt_tokens
        data["reported_completion_tokens"]=budget.total_completion_tokens
        data["safe_wire_observations"]=budget.response_observations
        (output/"manifest.json").write_text(
            json.dumps(data,ensure_ascii=False,indent=2),encoding="utf8")
    return data

def main() -> int:
    ap=argparse.ArgumentParser()
    ap.add_argument("--source-dir",type=Path,required=True)
    ap.add_argument("--output-dir",type=Path)
    ap.add_argument("--live",action="store_true")
    args=ap.parse_args()
    try:
        if not args.live:
            doc=preflight(args.source_dir)
            print(json.dumps({"status":doc["phase"],"scenes":len(SCENES),
                "arms":2*len(SCENES),"teacher_calls":0,
                "max_wire_calls":MAX_CALLS,"length_target":[MIN_LENGTH,MAX_LENGTH]},
                ensure_ascii=False))
            return 0
        if args.output_dir is None:
            raise HoldoutError("OUTPUT_DIRECTORY_REQUIRED")
        doc=live(args.source_dir,args.output_dir)
        print(json.dumps({
            "status":doc["phase"],
            "scenes_completed":sum(x.get("phase")=="COMPLETE_UNREVIEWED"
                                 for x in doc["results"]),
            "near_length_pairs":sum(x.get("length_comparable",False)
                                    for x in doc["results"]),
            "character_counts":{x["id"]:{a:v["characters"]
                                       for a,v in x["arms"].items()}
                                for x in doc["results"]},
            "wire_calls_reserved":doc.get("wire_calls_reserved",0),
            "reserved_output_tokens_not_usage":doc.get(
                "reserved_output_tokens_not_usage",0),
            "reported_prompt_tokens":doc.get("reported_prompt_tokens",0),
            "reported_completion_tokens":doc.get("reported_completion_tokens",0),
            "error_code":doc.get("error_code"),
            "new_teacher_calls":0,"canon_writes":0,
            "quality_proven":False},ensure_ascii=False))
        return 0 if doc["phase"]=="COMPLETE_UNREVIEWED" else 3
    except (HoldoutError,PracticeError) as exc:
        print(json.dumps({"status":str(exc),"model_calls":0},ensure_ascii=False))
        return 2

if __name__=="__main__":
    raise SystemExit(main())
