"""V97 ONE-SHOT real original-fiction Chinese longform A/B/C pilot protocol.

This is NOT a novel-training run. One original (synthetic-author-created)
historical ferry scenario, common frozen 5-field plan, identical fixed
three-turn outline for B and C, seven DeepSeek Flash requests MAX:
A one complete candidate, B three split-only, C three causal-guard turns.

No real book from R2 enters the prompt; Xuehai local fixture is synthetic.
All responses remain unaccepted candidates, saved privately to existing
immutable R2 CAS with no public prose. Mechanically valid trace != literary
causation. No retries, no skill/FactJournal/WRITE updates or grade promotion.
"""
from __future__ import annotations
from hashlib import sha256
import json

FORMAT="wf.writing.longform.real-abc-pilot.v97"
RUN_NAME="V97-ORIGINAL-HISTORICAL-CHINESE-ABC-ONE-SHOT-20261020"
PROVIDER="deepseek"
MODEL="deepseek-flash"
ARM_ORDER=("single","split_only","causal_guard")
ARMS={"single":"A","split_only":"B","causal_guard":"C"}
MAX_PROVIDER_REQUESTS=7
A_MAX_OUTPUT=2600
TURN_MAX_OUTPUT=1450
MAX_RESERVED_OUTPUT_TOKENS=A_MAX_OUTPUT+6*TURN_MAX_OUTPUT
MAX_CONSERVATIVE_REQUEST_BUDGET=120000
TARGET_CHARS=1500
SUBJECT="historical_ferry_original"
OUTLINE=(
    "傍晚水涨，一名抄账吏沈砚与药铺学徒阿蘅急需将药送到城内。"
    "巡桥人收起通行竹牌，但没有说明真正原因。沈砚知道牌子消失，"
    "阿蘅知道三年前水灾的账册，却都不清楚今天渡口究竟发生了什么。"
    "两人必须在天黑前选择险渡、绕路或求证；选择应产生实际代价。"
    "守桥人的真实动机留给后文，不得提前确认为内鬼或救命恩人。"
)
CHAPTER_GOAL=(
    "写一章约一千五百中文字符的原创历史悬念场景："
    "沈砚与阿蘅从桥头发现异常，因实在行动与证据不得不调整路线，"
    "最终选择先查实消息，产生新的时间压力和未解疑问。"
)
FROZEN_PLAN={
    "objective":"带药过桥入城，同时保护同行者并避免无证据指责",
    "conflict":"通行竹牌被收走且雨夜将至，绕路有时间损失，冒险过桥有危险",
    "decision":"沈砚暂时避开石桥，听阿蘅提示查阅水灾旧账，再决定核实船工消息",
    "outcome":"两人失去原定过桥时机、增加送药时间压力，但拿到追查方向",
    "pov":"限定沈砚视角；阿蘅的真实意图不能被旁白直接确认",
    "needs":["action","dialogue","decision"],
}
FROZEN_TURNS={"turns":[
    {
        "id":"t01","kind":"action","actor":"沈砚",
        "goal":"亲眼看到巡桥人撤牌与桥下异常后，沈砚主动改道旧堤并付出时间代价",
        "causal_parent":None,"craft_focus":["action","detail"],
    },{
        "id":"t02","kind":"decision","actor":"阿蘅",
        "goal":"阿蘅带出三年前水灾账册的有限证据，两人因此暂停对守桥人的指责",
        "causal_parent":"t01","craft_focus":["dialogue","restraint"],
    },{
        "id":"t03","kind":"decision","actor":"沈砚",
        "goal":"急迫的送药压力迫使沈砚决定求证船工而不是凭猜测冒险，留下开放线索",
        "causal_parent":"t02","craft_focus":["interiority","detail"],
    },
]}
ACTOR_KNOWLEDGE=(
    "角色知识界限：沈砚亲见巡桥人撤下通行竹牌，只知道当夜渡口异常；"
    "阿蘅保存旧水灾账本，但不可能预知今晚撤牌的真正原因；"
    "守桥人为何撤牌是未解悬念。故事时间在同一傍晚到夜间。"
    "人物可以说谎或误判，但不可以把未证实的传言变成全知旁白事实。"
)
SHARED_SYSTEM=(
    "你是WriterForge原创中文小说写作者，这次只写虚构故事，不回答百科。"
    "尽量使用具体行动、声音、物件与对话展现人物的犹疑、压力和真实代价；"
    "允许留白与含蓄，不讲评写作技法，不模仿任何已有小说句子。"
    "必须只返回严格JSON对象，不返回Markdown。"
    "你写下的情节不是被审核确认的历史或人物真实。"
)

def canonical(value):
    return json.dumps(value,sort_keys=True,ensure_ascii=False,
                      separators=(",",":"),allow_nan=False).encode("utf8")

def sha(raw):
    return sha256(raw).hexdigest()

def frozen_plan_json():
    return json.dumps(FROZEN_PLAN,ensure_ascii=False,separators=(",",":"))

def frozen_turns_json():
    return json.dumps(FROZEN_TURNS,ensure_ascii=False,separators=(",",":"))

def shared_story():
    return (
        "【原创世界和人物硬边界】\n"+OUTLINE+"\n"+ACTOR_KNOWLEDGE+
        "\n【共同章节目标】"+CHAPTER_GOAL+
        "\n【所有对照组共同的章节目标计划】"+frozen_plan_json()
    )

def make_precommit():
    return {
        "format":FORMAT,
        "run_name":RUN_NAME,
        "model":MODEL,
        "provider":PROVIDER,
        "genre":"原创历史悬念",
        "story_original_and_synthetic":True,
        "shared_story_sha256":sha(shared_story().encode("utf8")),
        "frozen_plan_sha256":sha(frozen_plan_json().encode("utf8")),
        "frozen_turns_sha256":sha(frozen_turns_json().encode("utf8")),
        "arm_order":list(ARM_ORDER),
        "hypothesis_about_1000_char_drift_unverified":True,
        "target_chinese_characters_including_punctuation":TARGET_CHARS,
        "max_paid_requests":MAX_PROVIDER_REQUESTS,
        "max_tokens_single":A_MAX_OUTPUT,
        "max_tokens_each_split_turn":TURN_MAX_OUTPUT,
        "max_reserved_output_tokens":MAX_RESERVED_OUTPUT_TOKENS,
        "max_conservative_input_output_tokens":
             MAX_CONSERVATIVE_REQUEST_BUDGET,
        "same_frozen_turns_for_B_and_C":True,
        "single_A_receives_same_story_but_no_new_event_gate":True,
        "all_unaccepted_original_fiction":True,
        "independent_human_literary_review":False,
        "automatic_retry_and_autopromotion_disabled":True,
        "r2_existing_15_chapter_learn_chain_untouched":True,
        "real_user_novel_source_transmitted":False,
        "model_calls_before_precommit":0,
    }

def request_bound(system,user,max_tokens):
    """Conservative upper bound using UTF-8 bytes, not guessed LLM tokens."""
    return len(canonical({
        "system":system,"user":user,
        "model":MODEL,"max_tokens":max_tokens,
    }))+1024+max_tokens

def mechanical_prose_fields(answer,*,is_turn):
    if type(answer) is not dict:
        raise ValueError("WF97_MODEL_RESPONSE_NOT_JSON_OBJECT")
    if is_turn:
        if set(answer)!={"prose","trace"}:
            raise ValueError("WF97_MODEL_TURN_SCHEMA_INVALID")
    elif set(answer)!={"prose"}:
        raise ValueError("WF97_MODEL_SINGLE_SCHEMA_INVALID")
    prose=answer["prose"]
    if type(prose) is not str or "\ufffd" in prose or not (
        100<=len(prose)<=17000):
        raise ValueError("WF97_PROSE_LENGTH_OR_UNICODE_INVALID")
    return prose
