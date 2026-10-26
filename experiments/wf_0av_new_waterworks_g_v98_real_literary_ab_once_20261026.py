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
MAX_TOTAL_PAID_CALLS=26
MAX_TOTAL_RESERVED_COMPLETION_TOKENS=44000
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
      "max_paid_calls":MAX_TOTAL_PAID_CALLS,
      "max_reserved_completion_tokens":MAX_TOTAL_RESERVED_COMPLETION_TOKENS,
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
        a_writer=WireWriter("A",key,cap)
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
            "A_real_paid_model_calls":a_writer.budget.calls_reserved,
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
        status["provider_completion_tokens_reserved"]=(
            cap.output_reservations)
        for label,writer in (("A",a_writer),("B",b_writer)):
            if writer is not None:
                status[label+"_wire_events"]=writer.public_events()
                status[label+"_real_model_budget"]=writer.budget.public_receipt()
        save_json(ROOT/"STATUS.json",status)
        print("WF0AV_STATUS "+json.dumps({
            "status":status["status"],"paid_calls":cap.calls,
            "completion_tokens_reserved":cap.output_reservations,
            "A_prose":status["A"],"B_prose":status["B"],
            "error":status.get("failure_code"),
            "judge_error":status.get("judge_failure"),
            "literal_writer_quality_proven":False},ensure_ascii=False),
            flush=True)
    if status["status"]=="REAL_AB_SAFE_PARTIAL_FAILURE_NOT_RETRIED":
        raise RuntimeError("WF0AV_SAFE_PARTIAL_EVIDENCE_RETAINED_NO_RETRY")

if __name__=="__main__":
    if "--preflight" in sys.argv:
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
