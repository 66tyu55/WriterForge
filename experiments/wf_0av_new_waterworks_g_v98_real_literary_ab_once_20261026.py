"""0.AV: new original same-model G vs G+V98 prose-first A/B, ONE paid run.

A (frozen G) provides a source-locked initial prefix: the same REAL
DeepSeek model's chapter plan, turn outline and first prose are replayed
byte-identically in B. All subsequent responses are new provider calls.
Thus we compare what a different NEXT-BEAT policy does after the SAME
authored consequences, not two unrelated beginnings. Shared calls are
charged once, never described as two fresh generations.

Original third-party bytes are written BEFORE JSON decoding. No retries.
The locally published one-line synthetic fixture exists only because the
existing WF WRITE path requires source evidence; it is NOT model training,
literary achievement, human-reviewed original or permanent Canon.
No R2, books, Railway, formal Canon or separate narrative memory.
"""
from __future__ import annotations

from hashlib import sha256
from pathlib import Path
from unittest.mock import patch
import json
import os
import re
import sys

from writerforge import WriterForgeDB,RuntimeEngine
from writerforge.writing_assist import AutonomousWriting,InvisibleWritingAssist
from writerforge.deepseek_flash_model import DeepSeekFlashModel,FlashBudget
from writerforge.v96_causal_turns import parse_turn_outline

ROOT=Path("wf_0av_new_waterworks_g_v98_real_literary_ab_20261026")
PROJECT="wf0av-fresh-waterworks-ab"
SCENE="waterworks-inspection-night"
MODEL="deepseek-flash"
API="https://api.deepseek.com/v1"
MAX_TOTAL_PAID_CALLS=20
MAX_TOTAL_RESERVED_COMPLETION_TOKENS=36100
SIXTH_ORIGINAL_RUN_ID=40287701471
SIXTH_SOURCE=Path('wf0av_sixth_paid_source')
SIXTH_RAW_SHA='3ee8c12e50aad171af51e6d2f1ef243d8fd2508e4a508766bb52917ce4646e13'
FIFTH_ORIGINAL_RUN_ID=40286835621
FIFTH_SOURCE=Path("wf0av_fifth_paid_source")
FOURTH_FIFTH_RAW_SHA=(
    "6ff634ca385a48a9ecaac3100b1c3f5235b4b5560da7c68db667a1eec3345fd5",
    "fe7e494f59c80c0f30fb7ff25bceb3a8c5af44287031790f8a7ce1b7a9edbdaa",
)
THIRD_ORIGINAL_RUN_ID=40285930972
THIRD_SOURCE=Path('wf0av_third_paid_source')
THIRD_RAW_SHA='7b776a0277ae8721af6c689b87da7962d9012b24751de1b76454052dc8c62de3'
PRIOR_FAILED_RUN_ID=40283464818
PRIOR_SOURCE=Path("wf0av_prior_failed_source")
PRIOR_RAW_SHA=(
    "9d6efe8e2375565cfbdc1a8ac6a30b5a6754fb6537c96835fd6fcd32f56d1a19",
    "f7b64df21080e7a196dc9e8babaebe94bb267a232ec1a9e2061c3d4598572ca4",
)
WRITER_SYSTEM=(
    "你是正在创作原创现代小说的写作模型。"
    "每轮只完成眼前交给你的一个构思或正文任务，严格输出JSON。"
    "选择、有限认知、误判、犹疑、行动及后果由你自己根据已经写出的正文决定；"
    "允许安静或留白，但不能把尚未亲眼证实的事实说成确定。"
    "绝不解释技巧，不套用他人文学作品，不机械总结，不因评审偏好强行改稿。"
    "WriterForge只管理来源和候选事务，不能替你决定剧情或文学价值。"
)
OUTLINE=(
    "【全新原创现实主义短篇实验《夜阀》，不得从任何旧WF测试小说续写】"
    "暴雨当夜，老城区的供水中转站即将停电。"
    "夜班水质员林槐在控制室看见两份签名不同却都声称有效的阀门检修记录；"
    "检修员许照在下层阀井，只能从断续对讲机听林槐说话，不能看到台账。"
    "城西医院的真实水压尚无人确认，封签是谁动过的也没人亲眼看见。"
    "人物可能选择开阀、延迟、分流、查证、与对方争执，亦可能不行动；"
    "选什么由真正作者自行决定。阀门、手电和对讲机只能按已写位置移动，"
    "不得从计划臆造已发生操作。始终贴近林槐的有限感官和对方话音。"
    "当前只是一个连续场景而非整个故事的结局，写约三至五个逐段片段；"
    "各段目标180至320个汉字，真实可读小说，不写场景规则说明。"
)
GOAL=(
    "从控制室与阀井的通信中推进林槐和许照第一次严重分歧："
    "写三到五段连续原创小说，让已发生的选择改变下一步，"
    "避免已执行的动作被当成尚未执行；不得把未获证实的医院水压、"
    "动封签者身份或井下状态突然变成林槐已知。"
    "文学重点是人物行动和克制的关系张力；结尾可以留有未决危险。"
)
SOURCE_FIXTURE="雨声进入设备间，巡检纸的一角被潮气浸软，控制台的指示灯仍然亮着。"
TASK={"format":"wf.0av.new-original-a-b-preregistered.v1",
      "task_title":"夜阀：两个有限认知者面对水务故障",
      "model":MODEL,"same_system":WRITER_SYSTEM,"same_outline":OUTLINE,
      "same_chapter_goals":GOAL,"draft_mode":"continuity_guard",
      "arm_A":"G frozen outline, same-author live replies",
      "arm_B":"same-source first plan, outline and prose; opt-in G+V98",
      "common_prefix_author_model_calls":3,
      "new_paid_responses_only_after_common_prefix_B":True,
      "expected_turns_min":3,"expected_turns_max":5,
      "per_turn_target_chinese_chars":[180,320],
      "new_run_max_paid_calls":MAX_TOTAL_PAID_CALLS,
      "new_run_max_reserved_completion_tokens":MAX_TOTAL_RESERVED_COMPLETION_TOKENS,
      "source_locked_previous_paid_calls":6,
      "combined_ceiling_including_previous_trial":26,
      "combined_completion_reservation_ceiling":44000,
      "earlier_failed_provider_run":PRIOR_FAILED_RUN_ID,
      "third_source_failed_run":THIRD_ORIGINAL_RUN_ID,
      "fourth_fifth_source_failed_run":FIFTH_ORIGINAL_RUN_ID,
      "sixth_source_failed_run":SIXTH_ORIGINAL_RUN_ID,
      "judging":"Two opposite-order BLIND same-family DeepSeek scores, never WF truth",
      "pre_registered_dimensions":[
          "人物选择真实性","后果改变下一步","动作重复","真实物品及时间连续性",
          "限知视角","语言节奏张力","有意留白保真"],
      "not_comparable_length_ratio_outside":[0.75,1.33],
      "g_rolling_default_remains_false":True,
      "no_r2_or_canon_or_railway_or_main_writes":True}

def h(raw):
    if isinstance(raw,str): raw=raw.encode("utf8")
    return sha256(raw).hexdigest()

def require(value,code):
    if not value: raise RuntimeError(code)

def save_json(path,thing):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(thing,ensure_ascii=False,sort_keys=True,
                              indent=2),encoding="utf8")

def make_local_fixture(base):
    """Identical minimal local fixture on both arms; no user originals."""
    db=WriterForgeDB(base/"local-only.sqlite")
    sid=int(db.conn.execute(
        "INSERT INTO snapshots(parent_id,status,layout,note) "
        "VALUES(NULL,'published','full','0av short synthetic input fixture')"
    ).lastrowid)
    s=SOURCE_FIXTURE
    db.conn.execute(
        "INSERT INTO studied_works(work_id,title,source_uri,source_sha256,"
        "chapter_count) VALUES(?,?,?,?,?)",
        ("wf-0av-fixture","0.AV非训练来源输入",
         "local-fixture://wf0av/no-user-books",h(s),1))
    db.conn.execute(
        "INSERT INTO source_spans(work_id,chapter,paragraph,sentence,excerpt,"
        "source_sha256,tracks_json,craft_json) VALUES(?,?,?,?,?,?,?,?)",
        ("wf-0av-fixture",1,1,1,s,h(s),"{}","{}"))
    db.conn.execute(
        "INSERT INTO studied_chapters(work_id,chapter,chapter_sha256,heading,"
        "source_spans,retrieval_entries,snapshot_id) VALUES(?,?,?,?,?,?,?)",
        ("wf-0av-fixture",1,h(s),"本地对照样本",1,1,sid))
    db.conn.execute(
        "INSERT INTO xuehai_entries(snapshot_id,work_id,chapter,paragraph,"
        "sentence,text,library_class,culture,genre,source_role,function,"
        "effect,method_cluster,source_hash) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (sid,"wf-0av-fixture",1,1,1,s,"local test fixture","中国",
         "现代小说","core","scene","unverified","local_not_training",h(s)))
    db.conn.commit()
    runtime=RuntimeEngine()
    runtime.enter_write(sid)
    assist=InvisibleWritingAssist(
        db,runtime,PROJECT,SCENE,"续写有限认知人物的水务控制室紧张场景",
        model=MODEL,api_base=API,source_genre="现代小说")
    return db,assist

def load_first_two_original_replies():
    """Read the two original failed-run WIRE bytes, no model or normalized story.

    The failure was WF V96's lack of a noncausal 'interiority' turn kind.
    This source-only replay is not a second paid plan attempt. Missing,
    different or altered raw response always stops before a new billable call.
    """
    from writerforge.v96_causal_turns import parse_turn_outline
    prior=json.loads((PRIOR_SOURCE/"STATUS.json").read_text("utf8"))
    require(prior["status"]=="REAL_AB_SAFE_PARTIAL_FAILURE_NOT_RETRIED"
            and prior["provider_calls"]==2
            and prior["failure_code"]==
                "WF96_SCENE_TURN_REJECTED_WF96_TURN_PLAN_FIELDS_ID_OR_CRAFT_INVALID"
            and prior["provider_completion_tokens_reserved"]==2100,
            "WF0AV_PREVIOUS_FAILURE_IDENTITY_NOT_SOURCE_LOCKED")
    old=prior["A_wire_events"]
    require(len(old)==2,"WF0AV_PREVIOUS_MODEL_EVENTS_CHANGED")
    recovered=[]
    copies=ROOT/"upstream-immutable-wire-copies"
    copies.mkdir(parents=True,exist_ok=False)
    for i in (1,2):
        event=old[i-1]
        source=PRIOR_SOURCE/"A"/"original-provider-wires"/f"{i:02d}-paid.json"
        raw=source.read_bytes()
        require(event["index"]==i and event["model"]==MODEL and
                event["wire_sha256"]==PRIOR_RAW_SHA[i-1] and
                h(raw)==PRIOR_RAW_SHA[i-1] and
                event["saved_before_json_decode"] is True,
                "WF0AV_PREVIOUS_WIRE_BYTES_SHA_MISMATCH")
        envelope=json.loads(raw)
        require(envelope["model"]==MODEL and
                len(envelope["choices"])==1 and
                envelope["choices"][0]["finish_reason"]=="stop",
                "WF0AV_PREVIOUS_PROVIDER_WIRE_NOT_COMPLETE")
        decoded=json.loads(envelope["choices"][0]["message"]["content"])
        replacement=json.dumps(decoded,ensure_ascii=False,separators=(",",":"))
        require(h(replacement)==event["returned_json_sha256"],
                "WF0AV_PREVIOUS_JSON_CANONICAL_SOURCE_CHANGED")
        if i==2:
            from writerforge.writing_assist import _normalize_optional_model_craft_labels
            source_compatible,optional_receipt=(
                _normalize_optional_model_craft_labels(replacement))
            turns=parse_turn_outline(source_compatible)
            require(optional_receipt is not None and
                    optional_receipt["only_model_optional_craft_fields_adjusted"],
                    "WF0AV_ORIGINAL_UNSUPPORTED_OPTIONAL_CRAFT_NOT_COMPATIBLE")
            require(len(turns)==5 and turns[3]["kind"]=="interiority"
                    and turns[0]["actor"]=="林槐/许照",
                    "WF0AV_SOURCE_PLAN_SILENTLY_REWRITTEN")
        # Retained upstream provider response is duplicated ONLY as bytes.
        dest=copies/f"{i:02d}-origin-run-{PRIOR_FAILED_RUN_ID}.json"
        require(not dest.exists(),"WF0AV_UPSTREAM_WIRE_COPY_OVERWRITTEN")
        dest.write_bytes(raw)
        recovered.append(dict(event,raw_response=replacement))
    save_json(ROOT/"RECOVERED_FIRST_TWO_SOURCE_ONLY.json",{
        "original_failed_run_id":PRIOR_FAILED_RUN_ID,
        "original_provider_wire_sha256":list(PRIOR_RAW_SHA),
        "original_paid_calls":2,
        "original_reserved_completion_tokens":2100,
        "new_calls_for_recovery":0,
        "model_said_interiority_not_host_authored":True,
        "source_plan_original_contents_preserved":True,
        "original_model_planning_text_unchanged":True})
    return tuple(recovered)

def load_third_original_response():
    """Original first paragraph is real model prose from the second paid run.

    Reuse ONLY its exact third provider wire/response. The V120 bug came
    AFTER authoring and preservation; rewriting prose would corrupt evidence.
    """
    trial=json.loads((THIRD_SOURCE/"STATUS.json").read_text("utf8"))
    require(trial["provider_calls"]==1 and trial["status"]==
                "REAL_AB_SAFE_PARTIAL_FAILURE_NOT_RETRIED" and
            trial["failure_code"]==
                "WF96_SCENE_TURN_REJECTED_WF120_BEAT_INVALID" and
            trial["total_paid_calls_including_original_red"]==3 and
            trial["provider_completion_tokens_reserved"]==1450,
            "WF0AV_PREVIOUS_THIRD_TRIAL_NOT_EXACT_FAILED_SOURCE")
    old=trial["A_wire_events"]
    require(len(old)==3 and
            [x["wire_sha256"] for x in old[:2]]==list(PRIOR_RAW_SHA) and
            all(x["paid_call"] is False for x in old[:2]),
            "WF0AV_THIRD_TRIAL_DID_NOT_REUSE_ORIGINAL_TWO")
    original=THIRD_SOURCE/"A"/"original-provider-wires"/"03-paid.json"
    raw=original.read_bytes()
    e=old[2]
    require(h(raw)==THIRD_RAW_SHA and
            e["wire_sha256"]==THIRD_RAW_SHA and
            e["model"]==MODEL and e["index"]==3 and
            e["paid_call"] is True and
            e["saved_before_json_decode"] is True,
            "WF0AV_REAL_THIRD_PROSE_WIRE_SHA_DRIFT")
    envelope=json.loads(raw)
    require(envelope["model"]==MODEL and
            envelope["choices"][0]["finish_reason"]=="stop",
            "WF0AV_THIRD_WIRE_PROVIDER_NOT_COMPLETED")
    doc=json.loads(envelope["choices"][0]["message"]["content"])
    raw_response=json.dumps(doc,ensure_ascii=False,separators=(",",":"))
    require(type(doc) is dict and type(doc.get("prose")) is str and
            type(doc.get("trace")) is dict and
            h(raw_response)==e["returned_json_sha256"],
            "WF0AV_THIRD_PROSE_BYTES_OR_DECODE_DRIFT")
    dest=ROOT/"upstream-immutable-wire-copies"/(
        f"03-origin-run-{THIRD_ORIGINAL_RUN_ID}.json")
    require(not dest.exists(),"WF0AV_REPAID_THIRD_PROSE_SOURCE")
    dest.write_bytes(raw)
    save_json(ROOT/"RECOVERED_THIRD_PROSE_SOURCE_ONLY.json",{
        "source_failed_run_id":THIRD_ORIGINAL_RUN_ID,
        "original_paid_call_number":3,
        "original_provider_wire_sha256":THIRD_RAW_SHA,
        "original_reservation_tokens":1450,
        "new_calls_to_recover":0,
        "original_prose_sha256":h(doc["prose"]),
        "model_prose_preserved_without_modification":True,
        "original_trace_preserved_without_rewriting":True,
        "status":"ACTUAL_AUTHOR_PROSE_SOURCE_ONLY"})
    return dict(e,raw_response=raw_response)


def load_fourth_fifth_original_responses():
    """Two more actual DeepSeek prose replies, already charged and source-kept.

    The old WF V118 rejected t04 AFTER A produced t01-t03. These are not
    authoring prompts to retry; they are replayed without model calls.
    """
    trial=json.loads((FIFTH_SOURCE/"STATUS.json").read_text("utf8"))
    require(trial["status"]=="REAL_AB_SAFE_PARTIAL_FAILURE_NOT_RETRIED"
            and trial["failure_code"]==
                "WF96_SCENE_TURN_REJECTED_WF118_LAMP_BAD_SCENE_CONTRACT"
            and trial["provider_calls"]==2
            and trial["total_paid_calls_including_original_red"]==5
            and trial["provider_completion_tokens_reserved"]==2900,
            "WF0AV_FIFTH_SOURCE_MISMATCH")
    events=trial["A_wire_events"]
    require(len(events)==5 and
            [x["wire_sha256"] for x in events[:3]]==
                list(PRIOR_RAW_SHA)+[THIRD_RAW_SHA] and
            all(x["paid_call"] is False for x in events[:3]),
            "WF0AV_THREE_PREVIOUS_PAID_WIRES_NOT_SOURCE_LOCKED")
    original=[]
    for i,sha in enumerate(FOURTH_FIFTH_RAW_SHA,start=4):
        event=events[i-1]
        raw=(FIFTH_SOURCE/"A"/"original-provider-wires"/
             f"{i:02d}-paid.json").read_bytes()
        require(h(raw)==sha and event["wire_sha256"]==sha and
                event["paid_call"] is True and event["index"]==i
                and event["model"]==MODEL and
                event["saved_before_json_decode"] is True,
                "WF0AV_FOURTH_FIFTH_REAL_PROVIDER_WIRE_NOT_EXACT")
        envelope=json.loads(raw)
        require(envelope["model"]==MODEL and
                envelope["choices"][0]["finish_reason"]=="stop",
                "WF0AV_OLD_MODEL_CONTINUATION_NOT_COMPLETE")
        doc=json.loads(envelope["choices"][0]["message"]["content"])
        response=json.dumps(doc,ensure_ascii=False,separators=(",",":"))
        require(type(doc) is dict and type(doc.get("prose")) is str
                and type(doc.get("trace")) is dict
                and h(response)==event["returned_json_sha256"],
                "WF0AV_REAL_PROSE_RESPONSE_JSON_DRIFT")
        destination=ROOT/"upstream-immutable-wire-copies"/(
            f"{i:02d}-origin-run-{FIFTH_ORIGINAL_RUN_ID}.json")
        require(not destination.exists(),
                "WF0AV_PAID_MODEL_REPLY_NEVER_OVERWRITE")
        destination.write_bytes(raw)
        original.append(dict(event,raw_response=response))
    save_json(ROOT/"RECOVERED_FOURTH_FIFTH_SOURCE_ONLY.json",{
        "run":FIFTH_ORIGINAL_RUN_ID,
        "already_paid_calls":2,
        "already_reserved_completion_tokens":2900,
        "provider_wire_shas":list(FOURTH_FIFTH_RAW_SHA),
        "copied_exact_provider_bytes":True,
        "model_called_again_for_these_responses":False})
    return tuple(original)


def load_sixth_original_response():
    """A's author wrote t04; old unified scene-delivery then rejected it.

    Resume from the provider's immutable wire, preserving the introspective
    passage exactly and not reissuing its original billable provider request.
    """
    trial=json.loads((SIXTH_SOURCE/"STATUS.json").read_text("utf8"))
    require(trial["status"]=="REAL_AB_SAFE_PARTIAL_FAILURE_NOT_RETRIED"
            and trial["failure_code"]==
                "WF96_SCENE_TURN_REJECTED_WFCORE_SCENE_DELIVERY_INPUT_INVALID"
            and trial["provider_calls"]==1
            and trial["total_paid_calls_including_original_red"]==6
            and trial["provider_completion_tokens_reserved"]==1450,
            "WF0AV_SIXTH_SOURCE_RUN_OR_FAILURE_DRIFT")
    events=trial["A_wire_events"]
    require(len(events)==6 and
            [x["wire_sha256"] for x in events[:5]]==
            list(PRIOR_RAW_SHA)+[THIRD_RAW_SHA]+list(FOURTH_FIFTH_RAW_SHA)
            and all(e["paid_call"] is False for e in events[:5]),
            "WF0AV_PREVIOUS_FIVE_WIRES_NO_LONGER_SOURCE_LOCKED")
    original=SIXTH_SOURCE/"A"/"original-provider-wires"/"06-paid.json"
    wire=original.read_bytes()
    ev=events[5]
    require(h(wire)==SIXTH_RAW_SHA and
            ev["wire_sha256"]==SIXTH_RAW_SHA and
            ev["paid_call"] is True and ev["index"]==6 and
            ev["model"]==MODEL and
            ev["saved_before_json_decode"] is True,
            "WF0AV_REAL_SIXTH_WIRE_HASH_CHANGED")
    envelope=json.loads(wire)
    require(envelope["model"]==MODEL and
            envelope["choices"][0]["finish_reason"]=="stop",
            "WF0AV_SIXTH_WIRE_NOT_STOPPED_NORMALLY")
    decoded=json.loads(envelope["choices"][0]["message"]["content"])
    plain=json.dumps(decoded,ensure_ascii=False,separators=(",",":"))
    require(type(decoded) is dict and type(decoded.get("prose")) is str
            and type(decoded.get("trace")) is dict
            and h(plain)==ev["returned_json_sha256"],
            "WF0AV_REAL_SIXTH_AUTHOR_PROSE_DECODE_DRIFT")
    dest=ROOT/"upstream-immutable-wire-copies"/(
        f"06-origin-run-{SIXTH_ORIGINAL_RUN_ID}.json")
    require(not dest.exists(),"WF0AV_REPAID_SIXTH_ORIGINAL_SOURCE")
    dest.write_bytes(wire)
    save_json(ROOT/"RECOVERED_SIXTH_PROSE_SOURCE_ONLY.json",{
        "original_run":SIXTH_ORIGINAL_RUN_ID,
        "wire_sha256":SIXTH_RAW_SHA,
        "author_prose_sha256":h(decoded["prose"]),
        "original_paid_calls_not_repeated":1,
        "original_reserved_completion_tokens_not_repeated":1450,
        "model_prose_not_rewritten":True})
    return dict(ev,raw_response=plain)


class AggregateCap:
    def __init__(self):
        self.calls=0
        self.output_reservations=0
    def reserve(self,requested):
        require(self.calls<MAX_TOTAL_PAID_CALLS and
                self.output_reservations+requested<=
                    MAX_TOTAL_RESERVED_COMPLETION_TOKENS,
                "WF0AV_HARD_GLOBAL_PROVIDER_BUDGET_EXHAUSTED")
        self.calls+=1
        self.output_reservations+=requested

class WireWriter:
    def __init__(self,side,key,global_cap,replay=()):
        self.side=side
        self.root=ROOT/side
        self.root.mkdir(parents=True,exist_ok=False)
        self.global_cap=global_cap
        self.replay=tuple(replay)
        self.events=[]
        self.outputs=[]
        self.active=None
        self.budget=FlashBudget(max_calls=16,
            max_reserved_output_tokens=30000,max_total_tokens=150000)
        self.model=DeepSeekFlashModel(
            api_key=key,budget=self.budget,timeout_seconds=110,
            on_response_wire=self._preserve_raw)

    def _preserve_raw(self,wire):
        require(isinstance(wire,bytes) and self.active is not None,
                "WF0AV_PROVIDER_ORPHAN_RAW_WIRE")
        event=self.events[self.active-1]
        path=self.root/"original-provider-wires"/(
            f"{self.active:02d}-paid.json")
        require(not path.exists() and event.get("wire_sha256") is None,
                "WF0AV_PROVIDER_RAW_WIRE_OVERWRITE")
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_bytes(wire)
        event["wire_sha256"]=h(wire)
        event["saved_before_json_decode"]=True

    def ask(self,packet,*,model,api_base,max_tokens):
        require(model==MODEL and api_base==API and
                isinstance(packet.prompt,str) and
                len(self.events)<16,"WF0AV_UNEXPECTED_MODEL_OR_CALL_LIMIT")
        i=len(self.events)+1
        psha=h(packet.prompt)
        event={"index":i,"model":MODEL,"prompt_sha256":psha,
               "reserved_output_tokens":max_tokens,
               "paid_call":i>len(self.replay),"wire_sha256":None,
               "saved_before_json_decode":False}
        self.events.append(event)
        save_json(self.root/"exact-requests"/f"{i:02d}.json",{
            "prompt":packet.prompt,"prompt_sha256":psha,
            "system":WRITER_SYSTEM,"max_tokens":max_tokens,"model":MODEL})
        if i<=len(self.replay):
            prior=self.replay[i-1]
            require(psha==prior["prompt_sha256"] and
                    max_tokens==prior["reserved_output_tokens"] and
                    prior.get("wire_sha256") and
                    prior.get("saved_before_json_decode"),
                    "WF0AV_IDENTICAL_PREFIX_PROMPT_BUDGET_SOURCE_DRIFT")
            event.update({"replayed_from":"A",
                          "wire_sha256":prior["wire_sha256"],
                          "saved_before_json_decode":True,
                          "raw_bytes_owned_by":"A/original-provider-wires"})
            self.outputs.append(prior["raw_response"])
            return prior["raw_response"]
        self.global_cap.reserve(max_tokens)
        self.active=i
        try:
            doc=self.model.ask_json(role="self_scene_writing",
                system=WRITER_SYSTEM,user=packet.prompt,
                max_tokens=max_tokens)
            raw=json.dumps(doc,ensure_ascii=False,separators=(",",":"))
            event["returned_json_sha256"]=h(raw)
            event["provider_format_recovery"]=(
                self.model.last_response_format_recovery)
            event["raw_response"]=raw
            self.outputs.append(raw)
            if self.side=="A" and i==2:
                require(type(doc) is dict and type(doc.get("turns")) is list,
                        "WF0AV_REAL_AUTHOR_TURN_OUTLINE_SHAPE_FAILED")
                require(3<=len(doc["turns"])<=5,
                        "WF0AV_PRE_REGISTERED_TURN_COUNT_OUTSIDE_3_TO_5_NO_RETRY")
                # WF's native optional-craft normalizer owns plan validation.
            return raw
        finally:
            self.active=None

    def public_events(self):
        return [{k:v for k,v in e.items() if k!="raw_response"}
                for e in self.events]

def extract_turns(job_dir):
    """Expose original authored text without treating trace as literary fact."""
    files=sorted(Path(job_dir).glob("chapter-001-turn-??-raw.json"))
    answer=[]
    for path in files:
        try:
            doc=json.loads(path.read_text("utf8"))
            source=doc["prose"]
            if type(source) is str:
                answer.append({"turn_id":path.stem.split("-")[3],
                               "prose":source,"sha256":h(source),
                               "chars":len(source)})
        except (KeyError,TypeError,ValueError):
            pass
    return answer

def run_arm(side,author):
    base=author.root
    db=None
    try:
        db,assist=make_local_fixture(base)
        with patch("writerforge.writing_assist.local_chat_completion",
                   side_effect=author.ask):
            result=AutonomousWriting(assist).run(
                outline=OUTLINE,chapter_goals=[GOAL],
                draft_mode="continuity_guard",
                bootstrap_unified_core=True,
                narrative_memory_backend="local",
                self_edit_rounds=0,
                g_rolling_author_planning=(side=="B"),
                output_dir=base/"g-candidate-only")
        require(len(result["chapters"])==1,"WF0AV_CHAPTER_COUNT")
        chapter=result["chapters"][0]
        prose=Path(chapter["candidate"]).read_text("utf8")
        evidence=json.loads(Path(chapter["turn_evidence"]).read_text("utf8"))
        turns=extract_turns(result["job_dir"])
        require(3<=len(turns)<=5,"WF0AV_AUTHORED_TURN_FILES_NOT_3_TO_5")
        save_json(base/"source-only-result.json",{
            "prose_sha256":h(prose),"chars":len(prose),
            "turns":turns,
            "g_writer_v98_opt_in":evidence.get("g_writer_v98_opt_in"),
            "replans":evidence.get("g_writer_source_only_replans",[]),
            "goals":evidence.get("g_writer_provisional_beat_choices",[]),
            "skips":evidence.get("g_writer_review_only_replan_skips",[]),
            "model_trace_review_failures":
                evidence.get("unified_model_trace_review_count"),
            "core_is_unique":True,
            "author_accepted":False,"literary_quality_verified":False})
        return {"prose":prose,"turns":turns,"evidence":evidence,
                "chapter":chapter,"sha256":h(prose)}
    finally:
        if db is not None: db.close()

def score_twice(a,b,key,cap):
    """NOT WF's own critic; only model-family-tied anonymous A/B proxy."""
    score_budget=FlashBudget(max_calls=2,
        max_reserved_output_tokens=4200,max_total_tokens=150000)
    active=[]
    def save_wire(data):
        i=active[-1]
        path=ROOT/"blind-rating-provider-wires"/f"order-{i:02d}.json"
        path.parent.mkdir(parents=True,exist_ok=True)
        require(not path.exists(),"WF0AV_JUDGE_WIRE_OVERWRITE")
        path.write_bytes(data)
    model=DeepSeekFlashModel(api_key=key,budget=score_budget,
        timeout_seconds=110,on_response_wire=save_wire)
    reports=[]
    for index,(first,second) in enumerate(((a,b),(b,a)),1):
        prompt=(
            "以下两份连续原创小说匿名稿只按实际可读文字来比较，不评价软件"
            "是否符合验证规则。严格分别给X与Y的文学百分制评分及六项0到100分："
            "人物选择、后果推动新行动、重复动作控制、限知视角、语言节奏、"
            "关系张力。指出各稿一个可逐字核查的具体原句和问题，"
            "不要假定同一稿更长就更好，允许无胜者。只输出JSON格式："
            '{"X":{"total":0,"character":0,"consequence":0,'
            '"repetition":0,"limited_pov":0,"language":0,"tension":0,'
            '"quote":"...","finding":"..."},'
            '"Y":{"total":0,"character":0,"consequence":0,'
            '"repetition":0,"limited_pov":0,"language":0,"tension":0,'
            '"quote":"...","finding":"..."},'
            '"winner":"X或Y或TIE","uncertainty":"..."}。'
            "\n=== X ===\n"+first+"\n=== Y ===\n"+second)
        cap.reserve(1700)
        save_json(ROOT/"blind-rating-exact-requests"/f"order-{index:02d}.json",
                  {"prompt":prompt,"model":MODEL,"reserved_tokens":1700,
                   "prompt_sha256":h(prompt),"order_not_shared_with_judge":
                   "AB" if index==1 else "BA"})
        active.append(index)
        try:
            raw=model.ask_json(role="self_scene_writing",
                system="你是文学原稿匿名阅稿人，逐段阅读原文，不评价工具。只输出严格JSON。",
                user=prompt,max_tokens=1700)
            save_json(ROOT/"blind-rating-decoded"/f"order-{index:02d}.json",raw)
            reports.append({"order":index,
                            "raw_response_decode_sha256":h(
                                json.dumps(raw,ensure_ascii=False,
                                           separators=(",",":"))),
                            "scores":raw})
        finally:
            active.pop()
    return {"orders":reports,"provider_budget":score_budget.public_receipt(),
            "same_model_family_bias":True,"human_grade":False,
            "order_sensitive_scores_are_not_proof":True}

def main():
    require(not ROOT.exists(),"WF0AV_EVIDENCE_NEVER_OVERWRITE")
    ROOT.mkdir(parents=True)
    save_json(ROOT/"PREREGISTERED_TASK.json",TASK)
    status={
        "format":"wf.0av.real-new-G-versus-G-plus-V98-literary-ab.v1",
        "status":"PRE_REGISTERED_NO_CALLS",
        "model":MODEL,"A":None,"B":None,
        "provider_calls":0,"budget_limit":MAX_TOTAL_PAID_CALLS,
        "prior_paid_calls_not_recharged":6,
        "prior_reserved_completion_tokens_not_recharged":7900,
        "provider_completion_tokens_reserved":0,
        "judge":None,"literary_uplift_proven":False,
        "human_blind_grade":False,"originals_not_overwritten":True,
        "R2_reads":0,"R2_writes":0,"Canon_writes":0,
        "Railway_deployments":0,"main_modified":False,
    }
    cap=AggregateCap()
    a_writer=b_writer=None
    try:
        require(not any(os.environ.get(k) for k in (
            "WRITERFORGE_R2_ACCOUNT_ID","WRITERFORGE_R2_ACCESS_KEY_ID",
            "OPENAI_API_KEY","DISCOVERY_API_KEY","OPENROUTER_API_KEY")),
            "WF0AV_EXTERNAL_SOURCE_OR_OTHER_VENDOR_NOT_ALLOWED")
        key=os.environ.get("DEEPSEEK_API_KEY","")
        require(len(key)>=16,"WF0AV_EXISTING_DEEPSEEK_SECRET_MISSING")
        previous_two=load_first_two_original_replies()
        a_writer=WireWriter("A",key,cap,replay=previous_two+(
            load_third_original_response(),)+
            load_fourth_fifth_original_responses()+
            (load_sixth_original_response(),))
        a=run_arm("A",a_writer)
        require(len(a_writer.events)>=5,
                "WF0AV_A_NO_MULTITURN_PROVIDER_PREFIX")
        prefix=[dict(a_writer.events[i],
                     raw_response=a_writer.outputs[i]) for i in range(3)]
        save_json(ROOT/"shared-first-three-paid-prefix-source.json",{
            "source_arm":"A","calls":3,
            "wire_sha256s":[x["wire_sha256"] for x in prefix],
            "prompt_sha256s":[x["prompt_sha256"] for x in prefix],
            "repaid_for_B":False,"same_author_originals_preserved":True})
        b_writer=WireWriter("B",key,cap,replay=prefix)
        b=run_arm("B",b_writer)
        ca,cb=len(a["prose"]),len(b["prose"])
        ratio=cb/max(ca,1)
        comparisons={
            "A_prose_sha256":a["sha256"],"B_prose_sha256":b["sha256"],
            "A_chars":ca,"B_chars":cb,"B_over_A_chars_ratio":ratio,
            "A_turn_chars":[t["chars"] for t in a["turns"]],
            "B_turn_chars":[t["chars"] for t in b["turns"]],
            "A_new_paid_model_calls":a_writer.budget.calls_reserved,
            "A_previous_two_planning_calls_replayed":2,
            "A_previous_third_original_prose_call_replayed":1,
            "third_original_prose_raw_wire_sha256":THIRD_RAW_SHA,
            "A_previous_fourth_and_fifth_original_prose_calls_replayed":2,
            "fourth_fifth_original_prose_wire_sha256s":list(FOURTH_FIFTH_RAW_SHA),
            "sixth_real_prose_original_wire_sha256":SIXTH_RAW_SHA,
            "original_red_wire_sha256s":list(PRIOR_RAW_SHA),
            "combined_paid_calls_including_original_red":cap.calls+6,
            "combined_reserved_output_tokens_including_original_red":(
                cap.output_reservations+7900),
            "B_new_paid_model_calls":b_writer.budget.calls_reserved,
            "B_shared_source_calls_not_rebilled":3,
            "A_provider_usage":a_writer.budget.public_receipt(),
            "B_provider_usage":b_writer.budget.public_receipt(),
            "B_actual_source_anchored_replans":len(
                b["evidence"].get("g_writer_source_only_replans",[])),
            "B_source_only_skips":b["evidence"].get(
                "g_writer_review_only_replan_skips",[]),
            "B_selected_beats":b["evidence"].get(
                "g_writer_provisional_beat_choices",[]),
            "A_trace_review_count":a["evidence"].get(
                "unified_model_trace_review_count"),
            "B_trace_review_count":b["evidence"].get(
                "unified_model_trace_review_count"),
            "length_comparable":0.75<=ratio<=1.33,
            "v98_planning_cost_separately_counted":True,
            "no_r2_or_canon_writes":True,
            "literary_value_unproven_by_source_receipts":True}
        save_json(ROOT/"SOURCE_AND_COST_COMPARISON.json",comparisons)
        text=(
            "# 0.AV 真实同源续写文学对照（未经作者接受）\n\n"
            "共同前缀由真实DeepSeek只付费创作一次，并逐字重放B；"
            "下面每段来自正式WF G路径的真实provider回包。\n\n")
        for side,arm in (("A 旧G冻结计划",a),("B G+V98滚动作者计划",b)):
            text+="## "+side+"\n\n"
            for i,t in enumerate(arm["turns"],1):
                text+=f"### 第{i}段 · SHA {t['sha256']}\n\n"+t["prose"]+"\n\n"
        text+="## 来源状态和实际规划成本\n\n"+json.dumps(
            comparisons,ensure_ascii=False,indent=2)
        (ROOT/"READABLE_REAL_AUTHOR_AB.md").write_text(text,encoding="utf8")
        status.update({"status":"TWO_REAL_AUTHOR_BRANCHES_COMPLETED",
                       "A":{"sha256":a["sha256"],"chars":ca},
                       "B":{"sha256":b["sha256"],"chars":cb},
                       "comparison":comparisons})
        if comparisons["length_comparable"]:
            try:
                status["judge"]=score_twice(a["prose"],b["prose"],key,cap)
                status["status"]="TWO_ARMS_TWO_BLIND_ORDER_REPORTS"
            except Exception as judge_error:
                status["judge_failure"]=str(judge_error)
                status["status"]="TWO_ARMS_GRADED_PARTIAL_NO_RETRY"
        else:
            status["judge_skipped"]="NOT_COMPARABLE_LENGTH"
        for side,arm in (("A",a),("B",b)):
            print("WF0AV_READABLE_"+side+" "+json.dumps({
                "prose_sha256":arm["sha256"],
                "chars":len(arm["prose"]),
                "turns":[{"t":i+1,"chars":t["chars"],
                          "sha256":t["sha256"],
                          "first_160":t["prose"][:160]}
                         for i,t in enumerate(arm["turns"])]},
                ensure_ascii=False),flush=True)
        print("WF0AV_LITERARY_AB "+json.dumps({
            "A_chars":ca,"B_chars":cb,
            "B_replans":comparisons["B_actual_source_anchored_replans"],
            "B_skips":comparisons["B_source_only_skips"],
            "B_selected_beats":comparisons["B_selected_beats"],
            "judge":status.get("judge"),
            "length_comparable":comparisons["length_comparable"]},
            ensure_ascii=False),flush=True)
    except Exception as error:
        status["status"]="REAL_AB_SAFE_PARTIAL_FAILURE_NOT_RETRIED"
        value=str(error)
        status["failure_code"]=(value if re.fullmatch(
            r"WF[A-Z0-9_:.\-]{3,180}",value)
            else type(error).__name__+":NO_BILLABLE_RETRY")
    finally:
        status["provider_calls"]=cap.calls
        status["total_paid_calls_including_original_red"]=cap.calls+6
        status["provider_completion_tokens_reserved"]=(
            cap.output_reservations)
        status["total_reserved_tokens_including_original_red"]=(
            cap.output_reservations+7900)
        for label,writer in (("A",a_writer),("B",b_writer)):
            if writer is not None:
                status[label+"_wire_events"]=writer.public_events()
                status[label+"_real_model_budget"]=writer.budget.public_receipt()
        save_json(ROOT/"STATUS.json",status)
        print("WF0AV_STATUS "+json.dumps({
            "status":status["status"],"paid_calls":cap.calls,
            "paid_calls_including_prior_red":cap.calls+6,
            "completion_tokens_reserved":cap.output_reservations,
            "A_prose":status["A"],"B_prose":status["B"],
            "error":status.get("failure_code"),
            "judge_error":status.get("judge_failure"),
            "literal_writer_quality_proven":False},ensure_ascii=False),
            flush=True)
    if status["status"]=="REAL_AB_SAFE_PARTIAL_FAILURE_NOT_RETRIED":
        raise RuntimeError("WF0AV_SAFE_PARTIAL_EVIDENCE_RETAINED_NO_RETRY")

def source_six_only_preflight():
    """Execute exact saved first SIX author replies through real G; zero APIs.

    The seventh attempted call must be intercepted BEFORE any provider call,
    proving repaired V96/NarrativeCore/V120/V118/scene-delivery retain prose.
    """
    global ROOT
    ROOT=Path("wf0av_source_six_offline_validation_only")
    require(not ROOT.exists(),"WF0AV_SOURCE_PREFLIGHT_NEVER_REPLAY_OVERWRITE")
    ROOT.mkdir(parents=True)
    first_two=load_first_two_original_replies()
    third=load_third_original_response()
    fourth_fifth=load_fourth_fifth_original_responses()
    sixth=load_sixth_original_response()
    saved=first_two+(third,)+fourth_fifth+(sixth,)
    require(len(saved)==6,"WF0AV_SIX_ORIGINAL_WIRES_NOT_ALL_LOADED")
    cap=AggregateCap()
    cap.calls=MAX_TOTAL_PAID_CALLS
    dry=WireWriter("D","offline-no-network-key-valid-0123456789",
                   cap,replay=saved)
    try:
        run_arm("D",dry)
    except Exception as error:
        msg=str(error)
        require("WF0AV_HARD_GLOBAL_PROVIDER_BUDGET_EXHAUSTED" in msg
                and len(dry.events)==7
                and all(e.get("paid_call") is False
                        for e in dry.events[:6]),
                "WF0AV_SIX_SOURCE_ONLY_DID_NOT_PASS_TO_NEXT_AUTHOR_TURN:"
                    +type(error).__name__+":"+msg[:150])
    else:
        # Complete prose with just 3 turns is NOT allowed by the source plan.
        raise RuntimeError("WF0AV_DRYRUN_SIX_SOURCE_UNEXPECTED_FULL_COMPLETION")
    save_json(ROOT/"OFFLINE_SOURCE_SIX_PASS.json",{
        "model_calls":0,"model_secret_used":False,
        "original_provider_wires":6,
        "all_original_prompt_SHA_validated":True,
        "actual_author_prose_turns_retained":4,
        "next_author_model_call_blocked_before_network":True,
        "writer_V96_core_V120_V118_source_parse_passed":True,
        "canon_writes":0,"r2_writes":0})
    print("WF0AV_ACTUAL_SOURCE_ONLY_SIX_WIRES_PASS_NO_NEW_MODEL_CALLS")


if __name__=="__main__":
    if "--source-six-preflight" in sys.argv:
        source_six_only_preflight()
    elif "--preflight" in sys.argv:
        import inspect
        from writerforge.v98_rolling_causal_planner import (
            g_source_replan_eligibility)
        require("g_rolling_author_planning" in
                inspect.signature(AutonomousWriting.run).parameters,
                "WF0AV_G_V98_NOT_INSTALLED")
        require(inspect.signature(AutonomousWriting.run).
                parameters["g_rolling_author_planning"].default is False,
                "WF0AV_G_V98_DEFAULT_MUST_REMAIN_OFF")
        require(len(OUTLINE)>50 and len(GOAL)>25 and
                SOURCE_FIXTURE not in OUTLINE,
                "WF0AV_PRE_REGISTERED_SCENE_INVALID")
        print("WF0AV_OFFLINE_PREREGISTRATION_AND_G_SOURCE_GATE_OK")
    else:
        main()
