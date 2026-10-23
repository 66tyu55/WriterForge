"""Real original WF scene-writing diagnostic; NOT a fake story mock.

Four genre-independent initial conditions probe the *actual*
AutonomousWriting.continuity_guard path with its original chapter planner,
model-created beat plan, real prose turn validation, Novel Studio reducer,
unified graph, prompt scheduler and physical/POV source checks.

Each case: at most 4 official DeepSeek Flash model calls, 5,000 max output
tokens total, no retries, no promotion, zero production writes. Synthetic
prose only. Always keep provider outputs before WF text checks.
"""
from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from hashlib import sha256
import json
import os
import re
import time
import traceback

from experiments.v111_peer.neutral_bridge import fresh_neutral_published_snapshot
from writerforge import WriterForgeDB, RuntimeEngine
from writerforge.deepseek_flash_model import DeepSeekFlashModel, FlashBudget
from writerforge.writing_assist import AutonomousWriting, InvisibleWritingAssist
from writerforge.narrative_core import new_graph, advance_graph, record_chapter_memory
from writerforge.v114_external_story_state import (
    require_external_runtime, external_temporal_step,
)
from writerforge.v117_continuity_trace import make_resume

MAX_CALLS=4
MAX_OUTPUT=650+1450+1450+1450
CASES={
    "fight":{
        "genre":"玄幻打斗",
        "seed":(
            "断桥两端只剩沈砚与唐蜃，桥下的河水已经冲到桥基。"
            "沈砚右臂被箭射伤，抬不起来，左掌握着一枚尚未服下的火髓果。"
            "唐蜃的弯刀缺了一角，他站的位置离松动的铁链只有两步。"
            "两人都不知道这座桥还可以承受多少次冲击。"
        ),
        "goal":"沈砚与唐蜃在断桥交锋，身体损伤、位置、桥体危险都必须影响各自的下一步",
        "outline":"玄幻追逐打斗，人物各自为活命争取条件。没有预设谁胜出，招式可自由发明但新的道具性质不能假装已经建立。",
    },
    "scheme":{
        "genre":"悬疑计谋",
        "seed":(
            "沈砚公开宣称要夜袭南门，真正的小队却在北侧水闸等待。"
            "叶青梧知道水闸开门的时辰，但她不知道唐蜃收买了一个守夜人。"
            "沈砚知道军粮印信藏在西库，唐蜃尚不知道军粮印信藏在西库。"
            "唐蜃对沈砚过分公开的宣告起了疑心，却没有证据判断哪句话是假话。"
        ),
        "goal":"唐蜃自己设计一次反试探，沈砚与叶青梧按各自认知应对，谋划必须有实际行动和代价",
        "outline":"原创谋略小说场景：存在不对称信息和误判，不能把角色怀疑写成上帝视角事实，也不要替人物强行宣布计划已经成功。",
        "event_quotes":[
            ("FACT","沈砚知道军粮印信藏在西库，唐蜃尚不知道军粮印信藏在西库。",
             {"fact_id":"west-seal","name":"军粮印信藏在西库",
              "visibility":"SECRET"}),
            ("UNKNOWN","沈砚知道军粮印信藏在西库，唐蜃尚不知道军粮印信藏在西库。",
             {"actor":"唐蜃","fact_id":"west-seal"}),
        ]
    },
    "humor":{
        "genre":"江湖喜剧",
        "seed":(
            "青石镇英雄宴上，掌柜把沈砚误认成了朝廷巡察使。"
            "沈砚只想讨回柜台上的雨伞，若当场澄清身份又怕被迫替酒钱买单。"
            "叶青梧知道误会，却被掌柜推去做了司仪。"
            "真正的巡察使唐蜃此时正在门外躲雨，鞋底粘着一团糯米糕。"
        ),
        "goal":"沈砚和叶青梧试图拿回雨伞，唐蜃的登场带来新的局面；让角色自己处理失误",
        "outline":"原创江湖轻喜剧。情节与笑意应通过人物动机、动作误会与实际后果自然产生，不指定任何笑话答案，不堆成故意解释尴尬。",
    },
    "psychology":{
        "genre":"心理抉择",
        "seed":(
            "沈砚从父亲遗信得知，唐蜃曾在旧案当夜救走一个孩子。"
            "他追查唐蜃十年，一直坚信对方是凶手，但信上没有写明真正的行凶者。"
            "叶青梧帮他压平湿透的信纸，既没有劝他原谅，也没有催他继续复仇。"
            "沈砚害怕十年追凶徒劳，却仍想查出父亲遇害的真相。"
            "唐蜃还不知道沈砚已经读过这封信。"
        ),
        "goal":"沈砚独自面对旧信与十年的信念冲突，下一步不必符合最初复仇计划，但必须可信",
        "outline":"原创小说人物心理场景。允许迟疑、静默、逃避和很小的心理决策，不能用循环相同独白冒充心理递进，也不要强迫反转。",
        "event_quotes":[
            ("CHARACTER_REFLECT",
             "沈砚害怕十年追凶徒劳，却仍想查出父亲遇害的真相。",
             {"actor":"沈砚","dimension":"fear",
              "value":"害怕十年追凶徒劳",
              "evidence_scope":"NARRATED_INNER"}),
        ],
    },
}

STAGES=("CHAPTER_PLAN","SELF_BEAT_PLAN","PROSE_1","PROSE_2")
TOKENS=(650,1450,1450,1450)
SYSTEMS={
 "CHAPTER_PLAN":(
   "你是WriterForge实际原创章规划调用。这不是模拟。仅输出JSON对象，"
   "恰好含objective、conflict、decision、outcome、pov、needs字段。"
   "前五字段为2-180字自然中文字符串，needs为1-3项有效的类别数组。"
   "这是尚未写出的计划，不可假称人物已经做完。无预设胜利或结局。"),
 "SELF_BEAT_PLAN":(
   "你是WriterForge自己的滚动事件构思器。只输出严格JSON对象，恰好"
   "有turns数组，其中恰好2个叙事事件。第1项id=t01，"
   "第2项id=t02。每项恰好有id、kind、actor、goal、"
   "causal_parent、craft_focus六字段。kind从"
   "action/decision/reversal/setup/dialogue/quiet/aftermath/transition"
   "中自选；actor是真实出场姓名；goal须为8字以上的动作或思考。"
   "causal_parent可为null，第2项如需因果链接只能为t01，且"
   "t01的kind必须是action/decision/reversal；craft_focus从"
   "dialogue/detail/interiority/pacing/restraint/contrast/action/none"
   "选0-2项。不写正文，让人物自主决定行动。"),
 "PROSE":(
   "你是WriterForge自己的真实小说正文模型。只输出严格JSON对象，"
   "恰好两个字段：prose和trace。prose为约300-550汉字的中文"
   "原创连续小说正文，不准标题、分析、评分、提纲或手法解释。"
   "trace是包含action_quote、effect_quote、"
   "parent_effect_quote三个键的JSON对象。"
   "若本段事件为action/decision/reversal，前两项是正文中唯一"
   "出现的6-96字原句，先动作/心理选择后具体后果；否则允许为null。"
   "只有前段真正写出且要求相连的因果才逐字填写parent_effect_quote，"
   "否则为JSON null。语义可以暂缓选择、伏笔可以不当场解开。"
   "句子要有生活感、人物动机、空间顺序，不准为了提示词生硬堆细节。"),
}


def h(value):
    return sha256(value.encode("utf8") if isinstance(value,str) else value).hexdigest()


def dump(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value,ensure_ascii=False,sort_keys=True,
                               indent=2),encoding="utf8")


def source_event(seed,index,event):
    kind,quote,fields=event
    assert seed.count(quote)==1
    return {"id":f"seed-{index}","kind":kind,
            "quote":quote,"start":seed.index(quote),
            "author_confirmed":True,**fields}


def diagnostic(scene):
    if scene not in CASES:
        raise RuntimeError("WF_GENRE_CASE_UNKNOWN")
    case=CASES[scene]
    project="wf-real-self-scenes-20261023"
    sid="genre-"+scene
    output=Path("wf_self_scene_results")/scene
    output.mkdir(parents=True,exist_ok=False)
    require_external_runtime()
    seed=case["seed"]
    (output/"synthetic-chapter-one.md").write_text(seed,encoding="utf8")
    calls=[]
    budget=FlashBudget(
        max_calls=MAX_CALLS,
        max_reserved_output_tokens=MAX_OUTPUT,
        max_total_tokens=150000,
    )
    model=DeepSeekFlashModel(budget=budget,timeout_seconds=120)
    status={"scene":scene,"genre":case["genre"],
            "wf_actual_route":"AutonomousWriting.continuity_guard",
            "actual_writer_framework_invoked":False,
            "initial_source_sha256":h(seed),
            "max_provider_calls":MAX_CALLS,
            "max_reserved_output_tokens":MAX_OUTPUT,
            "retries":0,"real_model":"deepseek-flash",
            "not_fake_provider":True,"source_is_synthetic":True,
            "no_user_novels_or_real_training_claimed":True,
            "neutral_published_bridge_not_real_literary_learning":True,
            "no_canon_or_production_writes":True,
            "literary_quality_unverified":True}
    db=None
    start=time.monotonic()
    try:
        # This neutral published source is mandatory runtime plumbing; it
        # provides ZERO real learned literary craft. Do not claim otherwise.
        with TemporaryDirectory(prefix="wf-real-self-scenes-") as folder:
            root=Path(folder)
            snapshot=fresh_neutral_published_snapshot(root/"neutral.sqlite")
            db=WriterForgeDB(root/"neutral.sqlite")
            # Match the neutral bridge's sole fixture to this request's
            # literary genre. It remains a NON-TEACHING software fixture.
            db.conn.execute(
                "UPDATE xuehai_entries SET genre=? WHERE work_id=?",
                (case["genre"],"v111-neutral-fixture"))
            db.conn.commit()
            rt=RuntimeEngine()
            rt.enter_write(snapshot)
            core=new_graph(project_id=project,scene_id=sid)
            core=advance_graph(
                core,project_id=project,scene_id=sid,
                chapter_index=1,prose=seed,
                events=[source_event(seed,i,event)
                        for i,event in enumerate(case.get("event_quotes",()),1)])
            core=record_chapter_memory(
                core,project_id=project,scene_id=sid,
                chapter_index=1,source_path=str(
                    output/"synthetic-chapter-one.md"),
                prose=seed)
            prior=external_temporal_step(
                seed,cast=("沈砚","唐蜃","叶青梧"))
            resume=make_resume(
                project_id=project,scene_id=sid,chapter_index=1,
                checkpoint=prior,unified_narrative_core=core)
            helper=InvisibleWritingAssist(
                db,rt,project,sid,case["goal"],
                model="deepseek-flash",
                api_base="https://api.deepseek.com",
                source_genre=case["genre"])
            status["actual_writer_framework_invoked"]=True

            def request_model(packet,*,model: str,api_base: str,
                              max_tokens: int,**extra):
                index=len(calls)
                if (index>=MAX_CALLS or model!="deepseek-flash" or
                    api_base!="https://api.deepseek.com" or extra or
                    index>=len(STAGES)):
                    raise RuntimeError("WF_REAL_SCENE_PROVIDER_BUDGET_OR_ROUTE_CHANGED")
                stage=STAGES[index]
                if max_tokens!=TOKENS[index]:
                    raise RuntimeError("WF_REAL_SCENE_HOST_CALL_SCHEDULE_CHANGED")
                calls.append({"stage":stage,
                              "prompt_sha256":h(packet.prompt),
                              "requested_output_tokens":max_tokens,
                              "model_response_status":"REQUESTED"})
                system=SYSTEMS["PROSE"] if stage.startswith("PROSE") else SYSTEMS[stage]
                original=model_client.ask_json(
                    role="self_scene_writing",system=system,
                    user=packet.prompt,max_tokens=max_tokens)
                response=json.dumps(original,ensure_ascii=False,
                                    separators=(",",":"))
                (output/f"{index+1:02d}-{stage}-original.json").write_text(
                    response,encoding="utf8")
                calls[-1].update({
                    "model_response_status":"RECEIVED_UNMODIFIED",
                    "response_sha256":h(response),
                    "response_characters":len(response),
                })
                return response

            # The model itself creates BOTH chapter and event plans,
            # then the actual WriterForge engine checks the two prose turns.
            model_client=model
            with patch("writerforge.writing_assist.local_chat_completion",
                       side_effect=request_model):
                result=AutonomousWriting(helper).run(
                    outline=case["outline"]+
                            "\n此前唯一事实材料："+seed,
                    chapter_goals=[case["goal"]],
                    output_dir=root/"fresh-candidates",
                    draft_mode="continuity_guard",
                    resume_story_checkpoint=resume)
            chapter=result["chapters"][0]
            draft=Path(chapter["candidate"]).read_text("utf8")
            (output/"wf-original-chapter.md").write_text(draft,encoding="utf8")
            turns=json.loads(Path(chapter["turn_evidence"]).read_text("utf8"))
            summary={
                "status":"REAL_WF_CANDIDATE_GENERATED",
                "full_original_prose_sha256":h(draft),
                "prose_chars":len(draft),
                "han_chars":sum("\u3400"<=x<="\u9fff" for x in draft),
                "turn_count":chapter["turn_count"],
                "scene_review_codes":chapter.get(
                    "unified_scene_function_review_findings",[]),
                "plan_prose_checks":turns.get(
                    "v120_plan_prose_source_receipts",[]),
                "replay_detection":turns.get(
                    "unified_completed_chapter_replay",{}),
                "prompt_delivery_receipts":turns.get(
                    "v121_prompt_delivery_receipts",[]),
                "turn_receipts":turns.get("turn_receipts",[]),
                "writer_is_honest_about_quality":not result.get(
                    "literary_quality_verified",False),
            }
            # Keep the real non-synthetic provider replies and the
            # actual output for manual literary diagnosis; no R2 writes.
            dump(output/"wf-check-results.json",summary)
            status.update({
                "status":summary["status"],
                "prose_sha256":summary["full_original_prose_sha256"],
                "han_chars":summary["han_chars"],
                "source_audit_codes":summary["scene_review_codes"],
                "turn_count":summary["turn_count"],
            })
            print("WF_REAL_ORIGINAL_START scene="+scene,flush=True)
            print(draft,flush=True)
            print("WF_REAL_ORIGINAL_END scene="+scene,flush=True)
    except Exception as exc:
        # The original JSON requests remain in the output dir even if a
        # later WF validator refuses the prose. Never regenerate to conceal
        # a failure or call a reviewer to bless a malformed candidate.
        why=str(exc)
        if not re.fullmatch(r"[A-Z][A-Z0-9_:\-,.]{2,200}",why):
            why=type(exc).__name__+":WRITER_RUN_FAILED"
        status.update({"status":"REAL_WF_ORIGINAL_REJECTED",
                       "failure":why})
    finally:
        if db is not None:
            status["accepted_prose_rows"]=db.conn.execute(
                "SELECT count(*) FROM accepted_prose").fetchone()[0]
            db.close()
        status["calls"]=calls
        status["provider_budget"]=budget.public_receipt()
        status["elapsed_seconds"]=round(time.monotonic()-start,1)
        dump(output/"STATUS.json",status)
        print("WF_REAL_SCENE_STATUS "+json.dumps(
            status,ensure_ascii=False,separators=(",",":")),
            flush=True)
    return 0  # Diagnostic collected, even if creative output was rejected.


if __name__=="__main__":
    scene=os.environ.get("WF_SELF_SCENE","")
    if not scene:
        raise SystemExit("WF_REAL_SCENE_NO_SELECTED_CASE")
    raise SystemExit(diagnostic(scene))
