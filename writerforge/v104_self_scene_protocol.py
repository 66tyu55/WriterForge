"""V104: WF chooses ten story situations and writes ten raw one-shot short pieces.

The sole provider is the ALREADY-CONNECTED WF DeepSeekFlashModel executor.
No other model, critic, source corpus, grading prompts, examples, samples,
prose repair, feedback, author-supplied plots or post-hoc rewriting enter the
student's requests. Model training weights are NOT part of WriterForge;
this experiment cannot prove model-independent reasoning or skill learning.

The procedural WF host owns the unique frozen 1+10 slots and all validation.
"""
from __future__ import annotations
from hashlib import sha256
from difflib import SequenceMatcher
import json
import re

RUN_ID="WF-V104-SELF-DIRECTED-10-COLD-SCENES-20261021"
MODEL="deepseek-flash"
GENRE_REQUESTS=1
DRAFT_REQUESTS=10
MAX_CALLS=GENRE_REQUESTS+DRAFT_REQUESTS
PLAN_MAX_OUTPUT_TOKENS=3000
DRAFT_MAX_OUTPUT_TOKENS=2400
MAX_RESERVED_OUTPUT=PLAN_MAX_OUTPUT_TOKENS+DRAFT_REQUESTS*DRAFT_MAX_OUTPUT_TOKENS
MAX_CONSERVATIVE_TOKENS=125000
TARGET_CHARACTERS=590
SOFT_MIN_CHARACTERS=360
SOFT_MAX_CHARACTERS=900
MAX_PLAN_BYTES=24000
MAX_DRAFT_BYTES=18000
MAX_PROSE_REPORT_BYTES=15000
MAX_META_LENGTH=150
_MIN_SOURCE_CHARS=6
_MAX_SOURCE_CHARS=125

class V104ExamError(ValueError):
    pass

def need(ok,code):
    if not ok:raise V104ExamError(code)

def encode(value):
    return json.dumps(value,sort_keys=True,ensure_ascii=False,
                      separators=(",",":"),allow_nan=False).encode("utf8")

def digest(b):
    return sha256(b).hexdigest()

def short(value,minimum=_MIN_SOURCE_CHARS):
    return (type(value) is str and minimum<=len(value.strip())
            <=_MAX_SOURCE_CHARS and "\ufffd" not in value
            and "\x00" not in value and "\n" not in value
            and not any(ord(c)<32 for c in value))

def precommit():
    return {
        "format":"wf.exam.ten-independent-scenes.precommit.v104",
        "run_id":RUN_ID,"model":MODEL,
        "student_role":"WF_SELF_SELECTS_TEN_SCENE_PREMISES",
        "only_inference_executor":"WF_REGISTERED_DEEPSEEK_FLASH",
        "external_judging_models":0,
        "external_source_retrieval":0,
        "external_author_prose_examples":0,
        "assistant_written_plot_answers":0,
        "WF_source_novel_passages_sent":0,
        "legacy_training_15_chapters_changed":0,
        "old_v97_v103_replays":0,
        "drafts_are_isolated_from_previous_draft_outputs":True,
        "planning_calls":1,"short_story_calls":DRAFT_REQUESTS,
        "max_calls":MAX_CALLS,
        "plan_output_token_reservation":PLAN_MAX_OUTPUT_TOKENS,
        "each_prose_output_token_reservation":DRAFT_MAX_OUTPUT_TOKENS,
        "total_output_token_reservation":MAX_RESERVED_OUTPUT,
        "conservative_input_plus_output_limit":MAX_CONSERVATIVE_TOKENS,
        "target_prose_characters_including_punctuation":TARGET_CHARACTERS,
        "soft_minimum_characters":SOFT_MIN_CHARACTERS,
        "soft_maximum_characters":SOFT_MAX_CHARACTERS,
        "no_retries_no_revisions_no_forced_length_fixes":True,
        "raw_provider_answers_saved_private_before_validation":True,
        "no_story_quality_labels_before_review":True,
        "model_weight_finetuning":False,
        "literary_understanding_verified":False,
        "skill_promotion":"LOCKED",
    }

PLANNER_SYSTEM=(
    "你是 WriterForge 创作流程里的原创场景构想环节。"
    "不要使用联网检索、小说片段或别人提供的故事模板。"
    "全部场景、时代、人物矛盾由你当下自主决定，"
    "场景之间必须尽量不同，不许为了格式填充成同一个故事。"
    "你不是考官，也不能评价自己是否学会了文学。"
    "只返回一个合法的 JSON 对象。"
)
PLANNER_TASK=(
    "WF现在需要独立创作10个不同场景的小说小短文。"
    "先自主选择10个明显不同的场景构想，时代、类型、"
    "人物之间的真实冲突应当有差异。"
    "这里只提出简短场景构想，不提供正文、结局、"
    "“标准答案”、文笔范例，也不要列出统一套用的写作手法。"
    '只返回JSON对象：{"scenes":['
    '{"id":"s01","genre":"自己决定的体裁",'
    '"setting":"地点和当下局面",'
    '"conflict":"人物真正面对的阻力",'
    '"stakes":"此刻在乎的事物"},...]}。'
    "id必须依序为s01至s10，恰好10项。"
    "每项四个文字字段都简短但具体，避免同义改写。"
)
WRITER_SYSTEM=(
    "你是WriterForge的小说正文生成执行器。"
    "仅根据当前WF自己选出的场景构想自由构思并写原创小说。"
    "不检索其他作品、不引用故事范例、不使用前面九篇"
    "或其他模型审稿意见、不复用之前的角色和情节。"
    "你不是评论家，也不需要展示步骤或给自己打分。"
    "只输出一个合法JSON对象，其中仅有prose。"
)

def check_plan(obj):
    """Verifies independent slots, not originality, quality or semantic diversity."""
    need(type(obj) is dict and set(obj)=={"scenes"} and
         type(obj["scenes"]) is list and len(obj["scenes"])==10,
         "WF104_PLAN_SHAPE_OR_TEN_COUNT")
    need(len(encode(obj))<=MAX_PLAN_BYTES,"WF104_PLAN_UNBOUNDED")
    proposals=[]
    fingerprints=[]
    for i,item in enumerate(obj["scenes"],1):
        need(type(item) is dict and
             set(item)=={"id","genre","setting","conflict","stakes"} and
             item["id"]==f"s{i:02d}" and
             all(short(item[k],minimum=(2 if k=="genre" else 6))
                 for k in ("genre","setting","conflict","stakes")),
             "WF104_SCENE_SLOT_OR_FIELD_INVALID")
        proposals.append(dict(item))
        fingerprints.append(digest(encode({
            k:item[k] for k in ("genre","setting","conflict","stakes")})))
    # Do not reject conceptual similarities after paying to create the plan.
    # The evidence of repetition is important for the author to see.
    return tuple(proposals),{
        "distinct_exact_scene_concepts":len(set(fingerprints)),
        "same_concept_sha_collisions":len(fingerprints)-len(set(fingerprints)),
        "semantically_distinct_ten_verified":False,
    }

def prompt_scene(item):
    need(type(item) is dict and
         set(item)=={"id","genre","setting","conflict","stakes"},
         "WF104_SCENE_PLAN_FIELDS_UNSAFE")
    for k in ("genre","setting","conflict","stakes"):
        need(short(item[k],minimum=(2 if k=="genre" else 6)),
             "WF104_SCENE_BOUNDS")
    # No prose samples, no exact sentences, no technique or twist quota.
    # All plot decisions, pacing, voice, resolution belong to WF's generator.
    return (
        "【本次只有一个场景，下面是WF刚刚自主选的原始构想】\n"
        +json.dumps(item,ensure_ascii=False,separators=(",",":"))
        +"\n独立创作约590个中文含标点字符的自然短篇场景。"
        "在人物自身的欲望、信息、地点、可行行动和现实阻力下"
        "自由决定事件如何发生；如果出现代价和后果，应当由行动引出，"
        "不能靠解释词硬拼、不需要为凑结构安排反转或死亡。"
        "可以有安静的场景或开放式结尾。"
        "所有人物、动作、对白、转折和具体文字必须是本轮新写的。"
        "不得给出写作说明、分析、自评或修改后版本。"
        '严格返回JSON：{"prose":"完整原创正文"}。'
    )

def record_prose(model_output):
    """Keep actual malformed results as red; no automatic rewrite/retry."""
    if type(model_output) is not dict or set(model_output)!={"prose"}:
        return {"status":"WF104_PROSE_NOT_EXACT_SINGLE_FIELD",
                "prose":None,"actual_characters":None,
                "prose_sha256":None}
    text=model_output["prose"]
    if type(text) is not str:
        return {"status":"WF104_PROSE_NOT_STRING","prose":None,
                "actual_characters":None,"prose_sha256":None}
    size=len(text)
    if len(text.encode("utf8"))>MAX_PROSE_REPORT_BYTES:
        return {"status":"WF104_PROSE_TOO_MANY_BYTES",
                "prose":text,"actual_characters":size,
                "prose_sha256":digest(text.encode("utf8"))}
    if size<SOFT_MIN_CHARACTERS or size>SOFT_MAX_CHARACTERS:
        status="WF104_PROSE_WRITTEN_LENGTH_OFF_TARGET"
    elif "\ufffd" in text or "\x00" in text:
        status="WF104_PROSE_INVALID_UNICODE"
    else:
        status="WF104_RAW_UNACCEPTED_CANDIDATE"
    return {"status":status,"prose":text,
            "actual_characters":size,
            "prose_sha256":digest(text.encode("utf8"))}

def reused_fragments(prose_by_scene,window=15):
    """Cheap exact-splice clue, not a copyright detector or meaning judge."""
    need(type(prose_by_scene) in (list,tuple) and
         len(prose_by_scene)<=DRAFT_REQUESTS and
         all(type(s) is str for s in prose_by_scene),
         "WF104_REPETITION_INPUT_BOUND")
    need(type(window) is int and 10<=window<=25,
         "WF104_REPETITION_WINDOW_INVALID")
    seen={}
    collisions={}
    for i,text in enumerate(prose_by_scene):
        grams={text[k:k+window] for k in
               range(0,max(0,len(text)-window+1))}
        for gram in grams:
            if gram in seen:
                other=seen[gram]
                if other!=i:
                    group=(other+1,i+1)
                    # A numeric indicator only; never put the prose in receipts.
                    collisions[group]=collisions.get(group,0)+1
            else:
                seen[gram]=i
    return {
        "repeated_15_character_windows_by_pair":[
            {"a":a,"b":b,"reused_window_count":v}
            for (a,b),v in sorted(collisions.items())
        ],
        "model_collage_or_plagiarism_proven":False,
        "shared_generic_chinese_phrases_can_trigger":True,
    }
