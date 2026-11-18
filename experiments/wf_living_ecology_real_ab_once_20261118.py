"""WriterForge living-ecology first bounded REAL independent-actor pilot.

Use only the existing paid Discovery adapter in an explicitly gated, one-shot
GitHub workflow. 3 independent NPC model calls + 2 independent author calls.
Raw provider replies and exact prompts stay in short-lived run artifact.
NOT character training, not chapter canon, not a semantic or literary pass.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
import os
from pathlib import Path

from writerforge.reverse_discovery_models import (
    DiscoveryCallBudget, DiscoveryModel, DiscoveryError,
)

MODEL = "deepseek-v4-pro-0813"
APPROVAL = "WF_ECOLOGY_ONE_SCENE_INDEPENDENT_ONCE_20261118"
ACTOR_TOKENS = 550
WRITER_TOKENS = 2400
MAX_WIRE_CALLS = 8   # 5 intended; includes any transport retry/continuation
MAX_RESERVED_OUTPUT = 12500
BASE_PUBLIC = (
    "青河渡口连续下雨三天，水势上涨。昨日的水牌仍写着“午后开闸”，"
    "官府尚没有向所有人澄清是否会改令。镇东有茶棚，街角有米铺，渡口有小船。"
    "来修铜壶的阿芷正在镇上走动。"
)
PROTAGONIST = (
    "阿芷靠修铜器给生病的母亲买药。她刚修好茶棚的铜壶，"
    "掌柜原先欠她六文工钱；她今天要去取钱、抓药。"
    "她不知道别人心里怎么想，也没有能力查清全镇发生的事。"
)
ACTORS = {
    "B": {
        "identity": "茶棚掌柜", "location": "茶棚",
        "private": "手头只有四文零钱，欠阿芷六文；听说官府可能封渡，但没见正式消息；担心生意和过往欠债。",
        "options": {
            "PAY_FOUR": "当面交给阿芷四文，尚欠两文；不是保证治好其母亲。",
            "PROMISE_LATER": "请阿芷明日再来，不付钱；承诺不保证兑现。",
            "CLOSE_STALL": "现在收拾茶棚准备闭店，不付钱。",
            "WAIT": "暂时不采取新行动，保留原欠款。",
        },
    },
    "C": {
        "identity": "渡娘", "location": "渡口",
        "private": "惦记西岸独居的外甥；水涨且河心流急。知道芦苇边有旧浅水道，但不确定今日能否平安到达。",
        "options": {
            "LEAVE_IN_REEDS": "解缆让小船沿芦苇岸离开泊位；不保证抵达西岸。",
            "MOVE_UP_BANK": "把小船移到高岸重新系牢，暂不渡河。",
            "ASK_HELP": "在码头请一位熟识水性的人帮忙，无人保证答应。",
            "WAIT": "仍然留在原泊位，不采取新行动。",
        },
    },
    "D": {
        "identity": "米铺庄二", "location": "街角米铺",
        "private": "旧米袋最怕返潮，底层货架已经发湿；担心浸泡损失。没有收到可靠的官府撤离命令。",
        "options": {
            "RAISE_GRAIN": "将几袋米搬到架高的门板上，不说明理由。",
            "CLOSE_SHOP": "把米铺门板关上一半，今日不继续接散客。",
            "SELL_NORMAL": "继续按原价卖米，不制造涨价消息。",
            "WAIT": "暂时没有可见新行动。",
        },
    },
}
# World responses are predetermined narrowly to the chosen *action*, not to
# hidden reasons. They imply no cross-scene success, secret revelation or fate.
# Writer observes only physical results at a later POV visit to each place.
ACTION_RESULTS = {
    "B": {
        "PAY_FOUR": "茶棚掌柜递给阿芷四文工钱；还欠两文。",
        "PROMISE_LATER": "掌柜让阿芷明日再来结账；没有付新钱。",
        "CLOSE_STALL": "茶棚已开始收拢炉火准备闭店；阿芷尚未收到余款。",
        "WAIT": None,
    },
    "C": {
        "LEAVE_IN_REEDS": "阿芷晚些经过码头时，看见原来泊船的位置空了；不知船为何出航，也不知抵达何处。",
        "MOVE_UP_BANK": "阿芷晚些看见小船被重新系在高岸。",
        "ASK_HELP": "阿芷晚些经过码头时，看见渡娘正在与一位船工交谈；不知结果。",
        "WAIT": None,
    },
    "D": {
        "RAISE_GRAIN": "阿芷经过街角时，看见米铺有几袋米搁在架高的门板上。",
        "CLOSE_SHOP": "阿芷经过街角时，看见米铺半扇门板已经合上。",
        "SELL_NORMAL": "阿芷路过米铺，米仍按昨日价钱卖。",
        "WAIT": None,
    },
}
ALL_OTHER_SECRETS = [a["private"] for a in ACTORS.values()]


class EcologyTrialError(ValueError):
    pass


def _sha(s):
    return sha256(s.encode("utf8") if isinstance(s, str) else s).hexdigest()


def _save(path, content):
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        raise EcologyTrialError("REFUSE_OVERWRITE_FROZEN_ARTIFACT")
    target.write_text(content, encoding="utf-8")


def _json(obj):
    return json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True)


def actor_prompt(actor_id):
    if actor_id not in ACTORS:
        raise EcologyTrialError("ACTOR_UNKNOWN")
    actor = ACTORS[actor_id]
    system = (
        "你在一个持续运转的虚构玄幻小镇里扮演一个普通人，不是编剧。"
        "你有自己的生计、人情、认识局限，主角不在场你也会考虑自己的生活。"
        "绝不读取或猜定其他角色的秘密心事。可以因恐惧、麻烦、懒惰、好心或私利做不理性的决定，"
        "也可以什么都不做。不要为了制造戏剧冲突而强行行动。"
        "回复JSON，只允许action,private_reason,assumption三个字段；"
        "action必须是所列代码之一；private_reason简短写你的真实个人权衡（不会给小说作者），"
        "assumption说明可能误判或未知的事。"
    )
    user = (f"【同一公共事实】{BASE_PUBLIC}\n"
            f"【你的身份】{actor['identity']}，所在地{actor['location']}\n"
            f"【只有你知道的私有情况】{actor['private']}\n"
            f"【本时刻可采取的动作，亦可等待】{_json(actor['options'])}\n"
            "此刻自行决定一项动作（无所谓正派反派）；不要代替其他角色安排下一步。")
    for aid, a in ACTORS.items():
        if aid != actor_id and a["private"] in system + user:
            raise EcologyTrialError("CROSS_ACTOR_PRIVATE_CONTEXT_LEAK")
    return system, user


def author_prompt(arm, exposed=None):
    if arm not in ("A", "B"):
        raise EcologyTrialError("ARM_INVALID")
    if arm == "B" and not isinstance(exposed, list):
        raise EcologyTrialError("EXPOSED_EVENTS_REQUIRED")
    system = (
        "你是中文玄幻小说作者。写一个完整自然的连续生活场景，尽量用朴素的行动、"
        "有限的观察与自然对话，不替其他人物解释内心。"
        "有些人只是过日子、无关紧要、甚至从未被主角注意。"
        "不要强迫出现大阴谋、揭示真相、伏笔回收、悬疑提示或总结。"
        "只给原创新正文，不写提纲、标题和解释。"
    )
    user = (
        f"【共同起点】{BASE_PUBLIC}\n【主角已知生活】{PROTAGONIST}\n"
        "【写作任务】以阿芷有限视角写雨中一个下午至夜晚。允许正常经营、犹豫、沉默、"
        "小事故、他人没出场。不要假设能知道任何人的私心。"
        "建议800—1300汉字；正文应该完整自然，不必让每个角色登场。"
    )
    if arm == "B":
        if len(_json(exposed)) > 1100:
            raise EcologyTrialError("POV_VIEW_TOO_LONG")
        user += "\n【本时段阿芷实际看见、听见或可核实的情况（可能为零，可忽略，不要解释原因）】\n" + _json(exposed)
    for secret in ALL_OTHER_SECRETS:
        if secret in system + user:
            raise EcologyTrialError("SECRET_LEAK_IN_AUTHOR_PROMPT")
    return system, user


def validate_choice(actor_id, decision):
    if type(decision) is not dict or set(decision) != {"action", "private_reason", "assumption"}:
        raise EcologyTrialError("ACTOR_JSON_SCHEMA_FAIL")
    if decision["action"] not in ACTORS[actor_id]["options"]:
        raise EcologyTrialError("ACTOR_ACTION_OUTSIDE_OPTIONS")
    for field in ("private_reason", "assumption"):
        if not isinstance(decision[field], str) or not 1 <= len(decision[field]) <= 550:
            raise EcologyTrialError("ACTOR_EXPLANATION_INVALID")
    return True


def public_events(decisions):
    """Only outcomes of bounded actions; no reasons or minds in POV view."""
    events = []
    for actor_id in sorted(ACTORS):
        decision = decisions[actor_id]
        validate_choice(actor_id, decision)
        action = decision["action"]
        observable = ACTION_RESULTS[actor_id][action]
        if observable is None:
            continue
        events.append({"scene_tick": "afternoon_to_evening",
                       "visible_result": observable})
    return events


def preflight():
    prompts = {aid: {"prompt_sha256": _sha("\n".join(actor_prompt(aid)))}
               for aid in sorted(ACTORS)}
    asys, auser = author_prompt("A")
    return {
        "format": "wf.ecology.real-npc-ab.one-shot.v1",
        "phase": "OFFLINE_FROZEN",
        "model": MODEL,
        "world_public_sha256": _sha(BASE_PUBLIC),
        "protagonist_sha256": _sha(PROTAGONIST),
        "actions_sha256": _sha(_json(ACTION_RESULTS)),
        "actor_prompt_sha256": prompts,
        "baseline_prompt_sha256": _sha(asys + "\n" + auser),
        "actor_count": len(ACTORS),
        "intended_model_calls": len(ACTORS)+2,
        "hard_max_wire_calls": MAX_WIRE_CALLS,
        "max_reserved_output_tokens": MAX_RESERVED_OUTPUT,
        "model_weight_training": False,
        "not_a_blind_literary_result": True,
        "private_original_text_used": False,
        "canon_writes": 0, "r2_writes": 0, "production_deploys": 0,
    }


def live(output_dir):
    if os.environ.get("WF_ECOLOGY_PAID_APPROVAL") != APPROVAL:
        raise EcologyTrialError("PAID_APPROVAL_GATE_CLOSED")
    key = os.environ.get("DISCOVERY_API_KEY")
    if not isinstance(key, str) or not key.strip() or len(key) > 512 or any(x.isspace() for x in key):
        raise EcologyTrialError("DISCOVERY_KEY_MISSING")
    output = Path(output_dir)
    if output.exists() and any(output.iterdir()):
        raise EcologyTrialError("REFUSE_REUSE_ARTIFACT_DIR")
    output.mkdir(parents=True, exist_ok=True)
    frozen = preflight()
    _save(output/"frozen_preflight.json", _json(frozen))
    budget = DiscoveryCallBudget(max_calls=MAX_WIRE_CALLS,
                                 max_reserved_output_tokens=MAX_RESERVED_OUTPUT)
    wire_seq = 0
    def capture_transport(req):
        nonlocal wire_seq
        wire_seq += 1
        # No Authorization header or API key is ever persisted.
        _save(output/f"wire_{wire_seq:02d}_request.json",
              req.data.decode("utf8"))
        response = DiscoveryModel._request(req)
        _save(output/f"wire_{wire_seq:02d}_response.json",
              response.decode("utf8"))
        return response

    model = lambda role: DiscoveryModel(name=MODEL,role=role,api_key=key,
            budget=budget,transport=capture_transport)
    report = dict(frozen, phase="PARTIAL_NOT_AUTHOR_ACCEPTED",
                  success=False, role_decisions={}, prose={})
    try:
        decisions = {}
        for actor_id in sorted(ACTORS):
            s,u = actor_prompt(actor_id)  # regenerated from isolated frozen context
            result = model("planner").ask(s,u,num_predict=ACTOR_TOKENS)
            validate_choice(actor_id,result)
            decisions[actor_id] = result
            _save(output/f"private_actor_{actor_id}.json",_json(result))
            report["role_decisions"][actor_id] = {"action":result["action"],
                   "raw_visible_output_sha256":_sha(_json(result))}
        exposed = public_events(decisions)
        _save(output/"writer_visible_only.json",_json(exposed))
        prompt_a = author_prompt("A")
        prompt_b = author_prompt("B",exposed)
        _save(output/"author_A_prompt.json",_json({"system":prompt_a[0],"user":prompt_a[1]}))
        _save(output/"author_B_prompt.json",_json({"system":prompt_b[0],"user":prompt_b[1]}))
        for arm, prompt in (("A",prompt_a),("B",prompt_b)):
            prose = model("writer").ask(*prompt,num_predict=WRITER_TOKENS)["scene"]
            _save(output/f"author_{arm}_original.md",prose)
            report["prose"][arm] = {"sha256":_sha(prose),
                        "han_characters":sum("\u4e00"<=ch<="\u9fff" for ch in prose),
                        "all_characters":len(prose)}
        count_a=report["prose"]["A"]["han_characters"]
        count_b=report["prose"]["B"]["han_characters"]
        report["relative_length_difference"]=round(abs(count_a-count_b)/max(1,count_a,count_b),4)
        report["length_comparable"]=(
            800<=count_a<=1300 and 800<=count_b<=1300
            and report["relative_length_difference"]<=0.20)
        report["success"]=True
        report["phase"]="COMPLETE_UNACCEPTED_UNGRADED"
    except Exception as exc:
        # Safeguard: the ledger survives errors; any failure is not a pass.
        report["phase"]="FAILED_PARTIAL_UNACCEPTED"
        code=str(exc)
        report["error_code"]=(code[:100] if isinstance(exc,(EcologyTrialError,DiscoveryError))
                               else type(exc).__name__)
    finally:
        report["budget"]={
            "charged_calls":budget.calls,
            "reserved_output_tokens":budget.reserved_output_tokens,
            "total_prompt_tokens_reported":budget.total_prompt_tokens,
            "total_completion_tokens_reported":budget.total_completion_tokens,
            "response_observations":budget.response_observations,
        }
        report["evaluated_by_independent_reader"]=False
        report["literary_gain_verified"]=False
        report["independent_npc_choices_from_model"]=bool(report["role_decisions"]) and len(
             report["role_decisions"])==len(ACTORS)
        _save(output/"run_report.json",_json(report))
    return report


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--dry-run",action="store_true")
    p.add_argument("--live",action="store_true")
    p.add_argument("--output-dir",type=Path)
    a=p.parse_args()
    if a.dry_run == a.live: raise SystemExit("choose exactly one of --dry-run or --live")
    if a.dry_run:
        print(_json(preflight()))
        return
    if a.output_dir is None: raise SystemExit("output-dir required")
    result=live(a.output_dir)
    print(_json({"phase":result["phase"],"success":result["success"],
                 "charged_calls":result["budget"]["charged_calls"],
                 "reserved_output_tokens":result["budget"]["reserved_output_tokens"],
                 "prose_lengths":{k:v["han_characters"] for k,v in result["prose"].items()},
                 "literary_gain_verified":False}))
    if not result["success"]: raise SystemExit("WF_ECOLOGY_PAID_PILOT_FAILED_NO_RETRY")


if __name__ == "__main__":
    main()
