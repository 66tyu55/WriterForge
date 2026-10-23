"""Holdout: WF writes genuinely NEW fictional worlds in three genres.

No replay of old seven Atria scenes, old Shen Yan/Tang Shen characters, or
previous fixed plans. A single *real DeepSeek Flash* model proposes one chapter
plan and a two-event outline for each novel synthetic scene. Both A/B arms
then run the real AutonomousWriting.continuity_guard with the SAME frozen
model plans. Only optional source-progression craft changes between arms.

Each genre: maximum 2 planning + 4 prose provider calls; no hidden retries.
All originals, rejected drafts, provider wire and status stay private to the
new Actions artifact. Not a literary learning/pass-rate result.
"""
from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import json
import os
import re
import time

from experiments import wf_real_self_scene_diagnostics as diag
from experiments import wf_source_progression_ab as ab
from writerforge.deepseek_flash_model import DeepSeekFlashModel,FlashBudget
from writerforge.v96_causal_turns import parse_turn_outline
from writerforge.writing_assist import (
    _chapter_plan,_normalize_optional_model_craft_labels,
)
from writerforge.v114_external_story_state import require_external_runtime

CASES={
    "plot":{
        "genre":"现实剧情",
        "cast":("林岚","孟舟","许澄"),
        "seed":(
            "南溪镇的旧石桥被划了一道红色封桥线，维修公文却没有验桥人的签字。"
            "林岚负责登记渡河货物，临时停桥可能耽误山里的急诊药材。"
            "孟舟修过桥基，三天前提出补测，却不知道红线是谁涂的。"
            "许澄是镇里的库房员，握有一张没有日期的领料单，她不能确定它属于哪一轮维修。"
            "林岚害怕停桥会耽误药材，却更怕冒险放行伤及乡人。"
        ),
        "goal":"林岚在药材必须过河与桥梁可能危险之间做选择，孟舟和许澄按各自掌握的证据行动",
        "outline":(
            "现实题材的小镇修桥纠纷。三人有各自利益与认知，红线和无签字公文只是疑点，"
            "不能直接当作有人做假。让决定、后果与人际冲突自然形成，不强行侦破。"
        ),
        "event_quotes":[(
            "CHARACTER_REFLECT",
            "林岚害怕停桥会耽误药材，却更怕冒险放行伤及乡人。",
            {"actor":"林岚","dimension":"fear","value":"更怕冒险放行伤及乡人",
             "evidence_scope":"NARRATED_INNER"}),
        ],
    },
    "climax":{
        "genre":"历史高潮",
        "cast":("裴琴","蒋问","许鹤"),
        "seed":(
            "夜里山洪把堤下石阶淹去一半，城门内的水已经漫到车轴。"
            "裴琴是河工的女儿，知道旧闸拉开会分去城内洪水，却可能淹坏下游谷仓。"
            "蒋问负责守城，他要求立刻拉闸，但没有收到下游清场的回报。"
            "许鹤去下游传过警讯，回来时只有一支断了绳的铜哨，无法确认谷仓是否还有人。"
            "裴琴对蒋问立下约定：下闸以前要先查明谷仓是否有人。",
            "蒋问已经下令集合闸手，却还没有亲自去查绞盘能否承重。"
        ),
        "goal":"洪水迫近，裴琴、蒋问与许鹤在是否开旧闸的关口各自决定行动，代价不能凭计划消失",
        "outline":(
            "原创架空历史灾变高潮。让人物在真正有限的时间和信息下作有代价的抉择，"
            "禁止把早先只推测的居民安全当成已确认事实；不预设主角必须牺牲或胜利。"
        ),
        "event_quotes":[(
            "THREAD_OPEN","裴琴对蒋问立下约定：下闸以前要先查明谷仓是否有人。",
            {"thread_id":"warehouse-check","thread_kind":"PROMISE",
             "owner":"裴琴","target":"蒋问",
             "premise":"开闸前谷仓人员是否撤离尚待查证",
             "truth_scope":"AUTHOR_ASSERTED"}),
        ],
    },
    "horror":{
        "genre":"悬疑恐怖",
        "cast":("秦真","俞港","罗婆"),
        "seed":(
            "停用九年的东湾灯塔里，秦真每到子夜总听见三下敲击，间隔一次比一次长。"
            "一楼机器间的电源已经切断，二楼楼梯潮湿，三楼守灯室的门封着旧铅印。"
            "俞港曾经负责看守灯塔，他认得通往地下储藏间的通风孔，但没说过声音从哪里来。"
            "罗婆守着岛上渡口，她说昨夜没有船靠岸；她不能看见灯塔北墙后面的礁沟。"
            "秦真害怕被困在塔里，却不愿把未见到的敲击者当成鬼怪。"
        ),
        "goal":"秦真夜查灯塔敲击声，俞港和罗婆各按有限的观察参与，空间、声音和未知感应自然发展",
        "outline":(
            "原创悬疑恐怖场景：恐怖来自实际感官、空间路线与未知证据的差距；"
            "不靠大声尖叫、重复三下敲击或无端出现恶鬼制造廉价惊吓。"
            "不可直接揭晓最终敲击者，允许人物推迟或放弃进入危险房间。"
        ),
        "event_quotes":[(
            "CHARACTER_REFLECT",
            "秦真害怕被困在塔里，却不愿把未见到的敲击者当成鬼怪。",
            {"actor":"秦真","dimension":"fear","value":"害怕被困在塔里",
             "evidence_scope":"NARRATED_INNER"}),
        ],
    },
}
# Keep the new holdout genuinely out of the trained/previous cast.
LEGACY_NAMES=frozenset(("沈砚","唐蜃","叶青梧"))
GENRES=tuple(CASES)
OUTPUT=Path("wf_holdout_three_new_scenes")
MODELS=("baseline","source_progression")
MAX_PROVIDER_CALLS=6
MAX_RESERVED_OUTPUT=650+1450+4*1450


def check_cases():
    assert set(GENRES)=={"plot","climax","horror"}
    for genre,case in CASES.items():
        assert len(case["seed"])<=3500 and len(case["goal"])<=450
        assert all(who in case["seed"] for who in case["cast"])
        assert not any(name in case["seed"] for name in LEGACY_NAMES)
        assert len(case["cast"])==len(set(case["cast"]))
        for typ,quote,props in case.get("event_quotes",()):
            assert case["seed"].count(quote)==1
            assert typ in ("THREAD_OPEN","CHARACTER_REFLECT")
            assert props.get("owner",props.get("actor")) in case["cast"]
    return True


def frozen_new_plans(genre,client,state):
    case=CASES[genre]
    root=OUTPUT/genre
    origin=case["seed"]
    shared=(
        f"【原创小说上一章确已写出的前史】\n{origin}\n"
        f"【本章场景目标】{case['goal']}\n"
        f"【作者给出的题材边界】{case['outline']}\n"
        "人物能凭已有知识与自身目标反对构思，情节未来只是设想。"
        "不许照搬任何其他小说或已有 Atria 测试文字。"
    )
    stages=(
        ("CHAPTER_PLAN",650,diag.SYSTEMS["CHAPTER_PLAN"],
         shared+"\n只设计本章的自主目标、冲突、可改变的决策和候选后果，不写正文。"),
        ("SELF_BEAT_PLAN",1450,diag.SYSTEMS["SELF_BEAT_PLAN"],
         shared+"\n仅给出两个相邻事件的紧凑 JSON，两个事件都必须有"
         "明确演员。演员须来自 "+",".join(case["cast"])+
         "。不要在下一事件预先宣告前一事件已经完成。"),
    )
    outputs={}
    stage={"name":None}
    def save_original_wire(raw):
        assert type(raw) is bytes and 0<len(raw)<2000000
        (root/f"original-{stage['name']}-provider-wire.json").write_bytes(raw)
        state["provider_wire_shas"][stage["name"]]=sha256(raw).hexdigest()
    client._on_response_wire=save_original_wire
    for name,limit,system,body in stages:
        stage["name"]=name
        response=client.ask_json(
            role="self_scene_writing",system=system,
            user=body,max_tokens=limit)
        original=json.dumps(response,ensure_ascii=False,separators=(",",":"))
        (root/f"original-{name}-model.json").write_text(
            original,encoding="utf8")
        outputs[name]=original
        state["plan_response_shas"][name]=sha256(
            original.encode("utf8")).hexdigest()
    _chapter_plan(outputs["CHAPTER_PLAN"],case["goal"])
    normalized,craft_note=_normalize_optional_model_craft_labels(
        outputs["SELF_BEAT_PLAN"])
    beats=parse_turn_outline(normalized)
    assert len(beats)==2
    # No fictitious extra characters sneak into the BEAT writer.
    if any(beat["actor"] not in case["cast"] for beat in beats):
        raise ValueError("WF_HOLDOUT_MODEL_PLAN_ACTOR_OUTSIDE_SOURCE_CAST")
    return {
        "model_plan":outputs["CHAPTER_PLAN"],
        "model_beats":normalized,
        "original_model_plan_sha256":state["plan_response_shas"]["CHAPTER_PLAN"],
        "original_model_turn_plan_sha256":state["plan_response_shas"]["SELF_BEAT_PLAN"],
        "model_optional_craft_recovery":craft_note,
    }


def run_one(genre):
    check_cases()
    if genre not in CASES:
        raise ValueError("WF_HOLDOUT_UNKNOWN_GENRE")
    if not os.getenv("DEEPSEEK_API_KEY"):
        raise RuntimeError("WF_HOLDOUT_EXISTING_MODEL_KEY_MISSING")
    require_external_runtime()
    root=OUTPUT/genre
    root.mkdir(parents=True,exist_ok=False)
    diag.CASES[genre]=CASES[genre]
    assert ab.CASES is diag.CASES
    ab.TARGET=OUTPUT
    budget=FlashBudget(
        max_calls=MAX_PROVIDER_CALLS,
        max_reserved_output_tokens=MAX_RESERVED_OUTPUT,
        max_total_tokens=150000)
    model=DeepSeekFlashModel(budget=budget,timeout_seconds=120)
    status={
        "format":"wf.holdout.actual-three-new-scene-pairs.v1",
        "genre":genre,"initial_prose_sha256":sha256(
            CASES[genre]["seed"].encode("utf8")).hexdigest(),
        "maximum_model_requests":MAX_PROVIDER_CALLS,
        "maximum_reserved_outputs":MAX_RESERVED_OUTPUT,
        "no_model_retries":True,
        "new_author_created_seed_not_prior_seven_genres":True,
        "trained_novel_corpus_not_used":True,
        "provider_wire_shas":{},"plan_response_shas":{},
        "status":"NOT_STARTED",
        "literary_improvement_verified":False,
        "no_canon_writes":True,
    }
    start=time.monotonic()
    try:
        plans=frozen_new_plans(genre,model,status)
        # Pseudo-random order determined before any draft result exists.
        first=(MODELS if int(sha256(
            (genre+"|new_holdout_order").encode()).hexdigest()[0],16)%2==0
            else MODELS[::-1])
        pair={}
        for blind_id,mode in zip(("W1","W2"),first):
            calls=[]
            pair[blind_id]=ab._runner(
                genre,mode=mode,blind_id=blind_id,plans=plans,
                root=root,client=model,calls=calls)
            pair[blind_id]["model_stage_receipts"]=calls
        equal=(
            budget.calls_reserved==MAX_PROVIDER_CALLS and
            all(x["status"]=="COMPLETE_UNACCEPTED_REAL_WF_CANDIDATE"
                for x in pair.values()) and
            all(x["model_calls_for_content"]==2
                for x in pair.values()))
        status.update({
            "status":"PAIR_COMPLETED" if equal else "PAIR_INCOMPLETE",
            "real_fair_pair_generated":equal,
            "blind_results":{
                k:{"status":v["status"],"han_chars":v.get("han_chars"),
                   "model_trace_reviews":len(v.get(
                       "model_trace_review_failures",[])),
                   "literal_replay_blocked":v.get("literal_replay_blocked")}
                for k,v in pair.items()},
            "actual_provider_calls":budget.calls_reserved,
        })
        (root/"BLIND_PAIR.md").write_text(
            "\n\n".join([
                "# Holdout blind pair — "+genre,
                "These are complete original model prose drafts. Do not read"
                " UNBLIND_MAPPING.json before independent comparison.",
                "## Shared prior story chapter\n"+CASES[genre]["seed"],
            ] + [
                "## "+key+"\n"+
                (root/key/"original-complete-candidate.md").read_text(
                    encoding="utf8")
                if (root/key/"original-complete-candidate.md").exists()
                else "## "+key+"\n[CANDIDATE FAILED; see evidence]"
                for key in ("W1","W2")
            ])+"\n",encoding="utf8")
        (root/"UNBLIND_MAPPING.json").write_text(
            json.dumps({
                "W1":first[0],"W2":first[1],
                "same_generated_plans_for_both":True,
                "pre_read_hidden_labels":True,
            },ensure_ascii=False,sort_keys=True,indent=2),encoding="utf8")
    except Exception as exc:
        message=str(exc)
        if not re.fullmatch(r"(?:WF_|WFCORE_|WF96_|WF_FLASH_)[A-Z0-9_]{3,150}",message):
            message=type(exc).__name__+":HOLDOUT_STOP_NO_RETRY"
        status.update({"status":"FAILED_NO_RETRY",
                       "reason":message,
                       "actual_provider_calls":budget.calls_reserved})
    finally:
        status["provider_usage"]=budget.public_receipt()
        status["elapsed_seconds"]=round(time.monotonic()-start,1)
        (root/"STATUS.json").write_text(json.dumps(
            status,ensure_ascii=False,sort_keys=True,
            indent=2),encoding="utf8")
        print("WF_NEW_SCENE_HOLDOUT_STATUS "+json.dumps({
            "genre":genre,"status":status["status"],
            "actual_provider_calls":budget.calls_reserved,
            "pair":status.get("blind_results"),
            "retry_count":0,"literary_truth_verified":False,
        },ensure_ascii=False,separators=(",",":")),flush=True)
    return 0


if __name__=="__main__":
    run_one(os.getenv("WF_HOLDOUT_GENRE",""))
