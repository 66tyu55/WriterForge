"""Seven-category real Intern InkStone literary A/B, strictly budgeted.

One immutable synthetic chapter-1 source per genre. A: bare provider; B:
the SAME provider + actual WriterForge V114/V117/V118/unified core prompt
assembly and source-backed preflight. This is a *prompt integration experiment*,
NOT full production WF novel generation/training or a blind human literary test.

No user/private novels, no R2, no secrets printed. No automatic retry.
Only explicitly whitelisted models advertised as free on official 2026-10-23
InkStone pricing page; the live /models list must confirm availability.
Max 3 short model probes + 14 category generations. Fail closed on 429/401/403.
"""
from __future__ import annotations

from hashlib import sha256
from pathlib import Path
from urllib.request import Request, build_opener, HTTPSHandler, HTTPRedirectHandler
from urllib.error import HTTPError, URLError
import json
import os
import ssl
import sys
import time

from writerforge.verified_flow import GroundedDraftPacket
from writerforge.writing_assist import _prepare_guarded_turn_packet
from writerforge.narrative_core import (
    new_graph, advance_graph, audit_candidate, character_collision_context,
)
from writerforge.v114_external_story_state import external_temporal_step, temporal_prompt
from writerforge.v117_continuity_trace import audit_continuity, compact_context
from writerforge.v116_state_delta import preflight_next_prose

BASE_URL="https://discovery-api.intern-ai.org.cn/v1"
MAX_COMPLETIONS=14
MAX_PROBES=3
MAX_RESERVED_OUTPUT=3100
MAX_PROBE_TOKENS=900
MAX_TOTAL_RESERVED=MAX_COMPLETIONS*MAX_RESERVED_OUTPUT+MAX_PROBES*MAX_PROBE_TOKENS
MIN_CN=680
MAX_CN=1250
TARGET="写出约900个汉字的连续原创小说正文（目标800—1100汉字）"
SCENE_DIR=Path("wf_inkstone_seven_scene_results")
SYSTEM="你是原创中文小说作家。只输出连贯的小说正文，禁用标题、分镜、提纲、旁白解释及写作思路；不模仿或复制现有文学作品。"
GENRES=("剧情","高潮","打斗","计谋","恐怖","搞笑","心理")
FREE_CANDIDATES=("intern-s2","Atria-Dawn-Preview","Agents-A1")
CONFIRMED_SSE_MODEL="Atria-Dawn-Preview"
STREAM_MAX_BYTES=1_600_000
STREAM_TIMEOUT_SECONDS=235
STREAM_WALL_SECONDS=275


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl):
        return None


def sha(text):
    return sha256(text.encode("utf8")).hexdigest()


def source_event(seed,quote,kind,*,ident,**more):
    assert seed.count(quote)==1
    return {"id":ident,"kind":kind,"quote":quote,
            "start":seed.index(quote),"author_confirmed":True,**more}


def scenarios():
    return [
      {
        "id":"plot","genre":"剧情",
        "seed":("沈砚在旧驿站找到父亲遗留的账册，账册的最后一页被人撕去。"
                "叶青梧从山路赶来，说驿卒昨夜离开，却没有看到谁取走那一页。"
                "沈砚知道井底密令藏在青砖背面，但叶青梧尚不知道井底密令藏在青砖背面。"
                "驿站掌柜看见两人，却只关心他们何时结清房钱。"),
        "goal":"叶青梧在旧驿站追问井底密令藏在青砖背面的线索，沈砚必须决定是否告诉她",
        "pov":"叶青梧","cast":("沈砚","叶青梧","唐蜃"),
        "focus":("dialogue","detail"),
        "beat_kind":"decision",
        "events":[("FACT","沈砚知道井底密令藏在青砖背面，但叶青梧尚不知道井底密令藏在青砖背面。",
                   {"fact_id":"well-paper","name":"井底密令藏在青砖背面","visibility":"SECRET"}),
                  ("UNKNOWN","沈砚知道井底密令藏在青砖背面，但叶青梧尚不知道井底密令藏在青砖背面。",
                   {"actor":"叶青梧","fact_id":"well-paper"})],
      },
      {
        "id":"climax","genre":"高潮",
        "seed":("沈砚始终认为唐蜃参与了父亲被害的旧案，却没有掌握能证明真凶的证据。"
                "沈砚与唐蜃在祠堂门口立下约定：旧案的幕后人必须被查清。"
                "今夜祠堂失火，唯一的见证人叶青梧携半封供词赶来。"
                "唐蜃站在倒塌的牌位旁，没有逃跑，反而把剑放在地上。"),
        "goal":"沈砚和唐蜃在失火祠堂对峙，叶青梧带来的证据迫使两人重新选择",
        "pov":"沈砚","cast":("沈砚","唐蜃","叶青梧"),
        "focus":("contrast","pacing"),
        "beat_kind":"reversal",
        "events":[("THREAD_OPEN","沈砚与唐蜃在祠堂门口立下约定：旧案的幕后人必须被查清。",
                   {"thread_id":"hidden-killer","thread_kind":"MYSTERY",
                    "owner":"沈砚","target":"唐蜃",
                    "premise":"旧案幕后人尚未确认，复仇目标与真相可能分离",
                    "truth_scope":"CHARACTER_BELIEF"})],
      },
      {
        "id":"fight","genre":"打斗",
        "seed":("断桥两端只剩沈砚与唐蜃，脚下是暴雨冲涨的河水。"
                "沈砚右臂受伤后一直抬不起来，只能以左臂护住胸前。"
                "沈砚把火髓果从齿间吐到左手心，那枚果子尚未被吞服。"
                "唐蜃右臂完好，手中的弯刀已经缺了一角。"
                "桥中央悬着松动的铁链，动得越猛越可能扯断最后一根石索。"),
        "goal":"沈砚右臂受限时与唐蜃在断桥交锋，两人的决定可能改变桥的结构和彼此退路",
        "pov":"沈砚","cast":("沈砚","唐蜃"),
        "focus":("action","pacing"),
        "beat_kind":"action",
        "events":[],
      },
      {
        "id":"scheme","genre":"计谋",
        "seed":("沈砚故意让唐蜃听见他要夜袭南门的消息，真正的小队却藏在北侧水闸。"
                "叶青梧掌握了水闸开门的时辰，但她不知道唐蜃已经收买了守夜人。"
                "沈砚知道军粮印信藏在西库，但唐蜃尚不知道军粮印信藏在西库。"
                "唐蜃觉得沈砚太过直白，决定反过来试探叶青梧。"),
        "goal":"唐蜃在营帐设计反计，试探叶青梧对军粮印信藏在西库的了解，沈砚的原计划面临意外代价",
        "pov":"唐蜃","cast":("沈砚","唐蜃","叶青梧"),
        "focus":("contrast","dialogue"),
        "beat_kind":"decision",
        "events":[("FACT","沈砚知道军粮印信藏在西库，但唐蜃尚不知道军粮印信藏在西库。",
                   {"fact_id":"grain-seal","name":"军粮印信藏在西库","visibility":"SECRET"}),
                  ("UNKNOWN","沈砚知道军粮印信藏在西库，但唐蜃尚不知道军粮印信藏在西库。",
                   {"actor":"唐蜃","fact_id":"grain-seal"})],
      },
      {
        "id":"horror","genre":"恐怖",
        "seed":("旧矿井已封了三十年，村民把夜里传来的敲击声叫作井鬼。"
                "叶青梧在井口捡到一枚还沾着新泥的铜钱，而井底旧铃铛的绳索早已断裂。"
                "沈砚说自己听见过规律的三声敲击，但从未亲眼看见发出声音的人。"
                "守夜老人只反复叮嘱不要点第四盏灯，理由却始终说不清。"),
        "goal":"叶青梧深入旧矿井调查夜间三声敲击，恐惧来自所见与所知之间的差距",
        "pov":"叶青梧","cast":("叶青梧","沈砚"),
        "focus":("detail","restraint"),
        "beat_kind":"action",
        "events":[],
      },
      {
        "id":"humor","genre":"搞笑",
        "seed":("青石镇临时举办一场英雄宴，掌柜把初来乍到的沈砚误认成了朝廷巡察使。"
                "沈砚其实只想讨回自己落在柜台的一把雨伞，又怕澄清后被迫替酒钱买单。"
                "叶青梧知道这场误会，却被掌柜安排当了临时司仪。"
                "真正的巡察使唐蜃就在门外躲雨，鞋底还粘着一团糯米糕。"),
        "goal":"沈砚和叶青梧在英雄宴上试图收回雨伞又不伤掌柜面子，唐蜃的登场引发意外连锁反应",
        "pov":"沈砚","cast":("沈砚","叶青梧","唐蜃"),
        "focus":("dialogue","contrast"),
        "beat_kind":"reversal",
        "events":[],
      },
      {
        "id":"psychology","genre":"心理",
        "seed":("沈砚从父亲留下的信中得知，唐蜃曾在案发当夜救走一个孩子。"
                "他长期把唐蜃当作仇人，但这一条新线索让他的确信开始动摇。"
                "叶青梧没有催他做决定，只替他把浸湿的信纸压平。"
                "沈砚害怕自己追了十年的方向其实错了，却又不愿承认那些牺牲可能白费。"
                "唐蜃还不知道沈砚已读过这封信。"),
        "goal":"沈砚独自面对追仇十年的信念与新证据冲突，在决定是否见唐蜃之前做一个小但真实的行动选择",
        "pov":"沈砚","cast":("沈砚","唐蜃","叶青梧"),
        "focus":("interiority","restraint"),
        "beat_kind":"decision",
        "events":[("CHARACTER_REFLECT","沈砚害怕自己追了十年的方向其实错了，却又不愿承认那些牺牲可能白费。",
                   {"actor":"沈砚","dimension":"fear",
                    "value":"害怕自己追了十年的方向其实错了",
                    "evidence_scope":"NARRATED_INNER"})],
      },
    ]


def make_packet(case):
    """Actually call the WF reducer, graph and bounded prompt dispatcher."""
    project="wf-synthetic-seven-scene-audit"
    scene=case["id"]
    seed=case["seed"]
    chapter=2
    graph=new_graph(project_id=project,scene_id=scene,chapter_index=0)
    approved=[]
    for idx,(kind,quote,props) in enumerate(case["events"]):
        approved.append(source_event(seed,quote,kind,ident=f"fixture-{idx+1}",**props))
    graph=advance_graph(graph,project_id=project,scene_id=scene,
                        chapter_index=1,prose=seed,events=approved)
    temporal=external_temporal_step(seed,cast=case["cast"])
    frame=audit_continuity(temporal,project_id=project,
                           chapter_index=chapter)
    # Shared chapter-one prose is IDENTICAL for bare and WF variants.
    shared=(
        f"【上一章原始正文】\n{seed}\n"
        f"【当前续写场景】{case['goal']}\n"
        f"【叙事视角】{case['pov']}；请保持人物行为具体、时间顺序清楚。\n"
        f"【写作任务】{TARGET}。允许人物依据自身认识改变计划；"
        "不能跳过真正需要展示的选择与代价。"
    )
    base=GroundedDraftPacket(
        scene_id=f"{scene}.chapter-002",project_id=project,
        snapshot_id=1,evidence=(),craft_ids=(),prompt=shared,
        prompt_sha256=sha(shared))
    beat={"id":"beat1","kind":case["beat_kind"],"actor":case["pov"],
          "goal":case["goal"],"craft_focus":list(case["focus"]),
          "causal_parent":None}
    hard=("对照上一章已经发生的状态与关系；不让计划自动兑现。"+
          temporal_prompt(temporal)+"\n"+compact_context(frame))
    wf_packet,lamps,receipt=_prepare_guarded_turn_packet(
        base,plan={"objective":case["goal"]},hard_turn_addition=hard,
        facets=(),dependency_hint="",project_id=project,
        chapter_index=chapter,turn_index=0,beat=beat,frame=frame,
        previous_lamp_receipt=None,narrative_graph=graph,
        narrative_scene_id=scene)
    return shared,wf_packet.prompt,temporal,graph,{
        "bare_prompt_sha256":sha(shared),
        "wf_prompt_sha256":sha(wf_packet.prompt),
        "wf_prompt_characters":len(wf_packet.prompt),
        "wf_prompt_verified_hard_context":receipt["hard_context_preserved"],
        "scheduler_lanes":receipt["unified_narrative_priority_dispatch"][
            "priority_order"] if receipt[
                "unified_narrative_priority_dispatch"] else [],
        "lamp_prompt_chars":lamps["prompt_chars"],
        "chapter1_sha256":sha(seed),
    }


class StopBatch(RuntimeError):
    pass


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl):
        return None


def request(path,key,payload=None,timeout=90):
    url=BASE_URL+path
    headers={"Authorization":"Bearer "+key,
             "Accept":"application/json"}
    if payload is not None:
        headers["Content-Type"]="application/json"
    data=(json.dumps(payload,ensure_ascii=False).encode("utf8")
          if payload is not None else None)
    req=Request(url,headers=headers,data=data,
                method="POST" if data is not None else "GET")
    opener=build_opener(NoRedirect(),HTTPSHandler(
        context=ssl.create_default_context()))
    try:
        with opener.open(req,timeout=timeout) as r:
            raw=r.read(1024*1024+1)
    except HTTPError as exc:
        # Do not dump provider response bodies (possible secrets/messages).
        return {"ok":False,"http_status":exc.code,"kind":"HTTP"}
    except (TimeoutError,URLError,OSError) as exc:
        return {"ok":False,"kind":type(exc).__name__}
    if len(raw)>1024*1024:
        return {"ok":False,"kind":"OVERSIZE_RESPONSE"}
    try:
        doc=json.loads(raw)
    except (UnicodeError,ValueError):
        return {"ok":False,"kind":"INVALID_JSON"}
    if type(doc) is not dict:
        return {"ok":False,"kind":"UNEXPECTED_DOCUMENT"}
    return {"ok":True,"body":doc}


def chat(key,model,prompt,max_tokens,*,probe=False):
    params={
        "model":model,
        "messages":[{"role":"system","content":SYSTEM},
                    {"role":"user","content":prompt}],
        "temperature":0.78 if not probe else 0.2,
        "max_tokens":max_tokens,
        "stream":False,
    }
    if model=="intern-s2":
        # Only for direct short-text probes. The gateway did not honor the
        # intended nonthinking mode on 2026-10-23 (reasoning exhausted cap).
        params["thinking_mode"]=False
    if not probe and model==CONFIRMED_SSE_MODEL:
        return stream_chat(key,model,prompt,max_tokens)
    trial=request("/chat/completions",key,params,
                  timeout=85 if probe else 115)
    if not trial["ok"]:
        return trial
    doc=trial["body"]
    variants=doc.get("choices") or []
    chosen=variants[0] if variants and type(variants[0]) is dict else {}
    msg=chosen.get("message") or {}
    answer=msg.get("content") if type(msg) is dict else None
    if type(answer) is list:
        # Some compatible chat endpoints return text parts rather than one
        # string. Only actual text is allowed; never treat hidden reasoning
        # or tool-call payloads as a completed literary answer.
        answer="".join(part.get("text","") for part in answer
                       if type(part) is dict and
                       type(part.get("text")) is str)
    usage=doc.get("usage") or {}
    clean_usage={
        k:v for k,v in (usage.items() if type(usage) is dict else [])
        if k in ("prompt_tokens","completion_tokens","total_tokens")
        and type(v) is int and 0<=v<=200000}
    return {
        "ok":True,"text":answer if type(answer) is str else "",
        "usage":clean_usage,
        "finish_reason":chosen.get("finish_reason"),
        "response_model":str(doc.get("model",model))[:100],
        "message_content_type":type(msg.get("content")).__name__
            if type(msg) is dict else "missing",
        "choice_count":len(variants),
        "reasoning_tokens":(
            (usage.get("completion_tokens_details") or {}).get(
                "reasoning_tokens")
            if type(usage) is dict and type(
                usage.get("completion_tokens_details")) is dict else None),
    }


def stream_chat(key,model,prompt,max_tokens,*,reasoning_effort=None):
    """Real SSE parser verified by run 39936371137; no invisible retries.

    HTTP200 with empty content, a truncated generation or an interrupted SSE
    stream is NOT a successful story. Only visible content is manuscript.
    """
    params={
        "model":model,
        "messages":[{"role":"system","content":SYSTEM},
                    {"role":"user","content":prompt}],
        "temperature":0.7,"stream":True,
        "max_tokens":max_tokens,
        "stream_options":{"include_usage":True},
    }
    if reasoning_effort is not None:
        # Must be independently checked on Discovery before use in a
        # comparative experiment. All A/B calls within a pair should use
        # identical provider parameters. 'low' is the upstream Atria effort
        # setting, but gateway compatibility is not assumed.
        if reasoning_effort!="low":
            raise ValueError("WF_UNVERIFIED_ATRIA_REASONING_EFFORT")
        params["reasoning_effort"]=reasoning_effort
    req=Request(BASE_URL+"/chat/completions",method="POST",
                headers={"Authorization":"Bearer "+key,
                         "Content-Type":"application/json",
                         "Accept":"text/event-stream"},
                data=json.dumps(params,ensure_ascii=False).encode("utf8"))
    opener=build_opener(NoRedirect(),HTTPSHandler(
        context=ssl.create_default_context()))
    text_parts=[]
    bytes_seen=0
    sse_count=0
    finish=None
    usage={}
    done=False
    reason_chars=0
    start=time.monotonic()
    failure=None
    try:
        with opener.open(req,timeout=STREAM_TIMEOUT_SECONDS) as response:
            for raw in response:
                bytes_seen+=len(raw)
                if bytes_seen>STREAM_MAX_BYTES:
                    failure="STREAM_TOTAL_BYTES_EXCEEDED"
                    break
                if time.monotonic()-start>STREAM_WALL_SECONDS:
                    failure="STREAM_WALL_LIMIT_REACHED"
                    break
                line=raw.decode("utf8","replace").strip()
                if not line.startswith("data:"):
                    continue
                payload=line[5:].strip()
                if payload=="[DONE]":
                    done=True
                    break
                if not payload:
                    continue
                try:
                    document=json.loads(payload)
                except ValueError:
                    failure="STREAM_BAD_SSE_JSON"
                    break
                sse_count+=1
                if type(document.get("usage")) is dict:
                    usage=document["usage"]
                choices=document.get("choices") or []
                if type(choices) is not list:
                    failure="STREAM_BAD_CHOICE_SCHEMA"
                    break
                for choice in choices[:1]:
                    if type(choice) is not dict:
                        continue
                    delta=choice.get("delta") or {}
                    if type(delta) is not dict:
                        continue
                    fragment=delta.get("content")
                    if type(fragment) is str:
                        text_parts.append(fragment)
                    elif type(fragment) is list:
                        text_parts.extend(
                            p["text"] for p in fragment
                            if type(p) is dict and type(p.get("text")) is str)
                    for field in ("reasoning","reasoning_content"):
                        val=delta.get(field)
                        if type(val) is str:
                            reason_chars+=len(val)
                    if choice.get("finish_reason") is not None:
                        finish=choice["finish_reason"]
    except HTTPError as exc:
        return {"ok":False,"kind":"HTTP","http_status":exc.code,
                "sse_events":sse_count,
                "partial_text":"".join(text_parts)}
    except (TimeoutError,URLError,OSError) as exc:
        failure=type(exc).__name__
    prose="".join(text_parts)
    reported={k:usage[k] for k in (
        "prompt_tokens","completion_tokens","total_tokens")
        if type(usage.get(k)) is int}
    ret={
        "ok":bool(done and finish=="stop" and not failure and prose.strip()),
        "kind":failure or ("STREAM_UNFINISHED" if not done else
                          "FINISH_"+str(finish) if finish!="stop" else
                          "EMPTY_VISIBLE_CONTENT"),
        "text":prose if done and finish=="stop" and not failure else "",
        "partial_text":prose if failure or finish!="stop" or not done else "",
        "finish_reason":finish,"usage":reported,
        "done_seen":done,"sse_events":sse_count,
        "reasoning_characters":reason_chars,
        "elapsed_seconds":round(time.monotonic()-start,1),
        "response_model":model,
    }
    return ret


def _han_count(body):
    return sum("\u3400"<=c<="\u9fff" for c in body)


def diagnose(case,body,temporal,graph,*,variant,usage,finish_reason):
    prose=body.strip()
    source=case["seed"]
    prior=temporal["reducer_result"]["candidate_state"]
    try:
        physical=preflight_next_prose(
            prose,previous_candidate_state=prior,cast=case["cast"])
        psychological=audit_candidate(
            graph,project_id="wf-synthetic-seven-scene-audit",
            scene_id=case["id"],prose=prose,cast=case["cast"])
        hard=list(dict.fromkeys(physical["findings"]+
                                psychological["hard_findings"]))
        review=list(dict.fromkeys(
            physical["review_findings"]+
            psychological["review_findings"]))
    except Exception as exc:
        hard=["CHECKER_EXCEPTION_"+type(exc).__name__]
        review=["CHECKER_NOT_VERIFIED"]
    return {
        "variant":variant,
        "genre":case["genre"],
        "han_characters":_han_count(prose),
        "total_characters":len(prose),
        "length_target_680_to_1250":MIN_CN<=_han_count(prose)<=MAX_CN,
        "provider_finish_reason":finish_reason,
        "reported_usage":usage,
        "source_sha256":sha(source),
        "output_sha256":sha(prose),
        "hard_source_warnings":hard,
        "needs_review":review,
        "source_mechanics_clean":not hard and "CHECKER_NOT_VERIFIED" not in review,
        "literary_quality_blind_judged":False,
        "prose_in_saved_private_artifact":True,
    }


def save_now(data,raw):
    SCENE_DIR.mkdir(exist_ok=True)
    (SCENE_DIR/"SUMMARY.json").write_text(
        json.dumps(data,ensure_ascii=False,sort_keys=True,indent=2),
        encoding="utf8")
    (SCENE_DIR/"ORIGINAL_GENERATIONS.json").write_text(
        json.dumps(raw,ensure_ascii=False,sort_keys=True,indent=2),
        encoding="utf8")


def main():
    if SCENE_DIR.exists():
        raise RuntimeError("WF_EXPERIMENT_ALREADY_EXISTS_NO_AUTO_REPEAT")
    SCENE_DIR.mkdir()
    key=os.environ.get("DISCOVERY_API_KEY","")
    all_cases=scenarios()
    assert len(all_cases)==7 and len({x["id"] for x in all_cases})==7
    selected=os.getenv("WF_SCENE_CATEGORY","")
    if selected:
        if selected not in {x["id"] for x in all_cases}:
            raise ValueError("WF_UNKNOWN_LITERARY_SCENE_CATEGORY")
        cases=[c for c in all_cases if c["id"]==selected]
    else:
        cases=all_cases
    max_generate=len(cases)*2
    allowed_calls=max_generate+(0 if os.getenv(
        "WF_BATCH_CONFIRMED_STREAM_MODEL") else MAX_PROBES)
    report={
        "format":"wf.experiment.seven-literary-scenes.discovery.ab.v1",
        "started_utc":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime()),
        "genres":list(GENRES),"provider":"Intern InkStone / Discovery",
        "same_model_across_categories":True,
        "policy":"one_same-model_bare_vs_wf_guided_per_genre",
        "generation_call_ceiling":max_generate,
        "probe_call_ceiling":MAX_PROBES,
        "per_generation_max_tokens":MAX_RESERVED_OUTPUT,
        "total_reserved_output_token_ceiling":(
            max_generate*MAX_RESERVED_OUTPUT+
            (0 if os.getenv("WF_BATCH_CONFIRMED_STREAM_MODEL")
             else MAX_PROBES*MAX_PROBE_TOKENS)),
        "synthetic_sources_only":True,
        "original_user_novels_sent":False,
        "R2_writes":0,"canon_writes":0,"railway_deploys":0,
        "literary_blind_judging_completed":False,
        "calls_attempted":0,
        "pairs_complete":0,
        "status":"INITIALIZED",
        "model":None,
        "cases":[],
    }
    generated=[]
    save_now(report,generated)
    if not key or len(key)<12:
        report["status"]="CREDENTIAL_NOT_AVAILABLE_NO_CALLS"
        save_now(report,generated)
        return 2
    model_list=request("/models",key,timeout=45)
    if not model_list["ok"]:
        report["status"]="MODEL_LIST_UNAVAILABLE"
        report["model_list_error"]={
            k:v for k,v in model_list.items() if k!="body"}
        save_now(report,generated)
        return 3
    available=[
        x.get("id") for x in model_list["body"].get("data",[])
        if type(x) is dict and type(x.get("id")) is str]
    probe_used=0
    chosen=None
    explicitly_confirmed=os.getenv("WF_BATCH_CONFIRMED_STREAM_MODEL","")
    if explicitly_confirmed:
        if explicitly_confirmed!=CONFIRMED_SSE_MODEL or (
            explicitly_confirmed not in available):
            report["status"]="CONFIRMED_SSE_MODEL_NOT_AVAILABLE"
            save_now(report,generated)
            return 5
        chosen=explicitly_confirmed
        report["verified_stream_reference_run"]=39936371137
    for name in ([] if chosen else FREE_CANDIDATES):
        if name not in available or probe_used>=MAX_PROBES:
            continue
        probe_used+=1
        trial=chat(key,name,
                   "请简短回答：小说人物会根据什么决定下一步行动？"
                   "用30个汉字以内给一个清晰句子。不能只给推理。"
                   "必须输出最终文字。",
                   MAX_PROBE_TOKENS,probe=True)
        report["calls_attempted"]+=1
        info={"model":name,"success":bool(
            trial.get("ok") and trial.get("text","").strip())}
        if not info["success"]:
            info.update({
                "http_status":trial.get("http_status"),
                "error_kind":trial.get("kind"),
                "finish_reason":trial.get("finish_reason"),
                "choice_count":trial.get("choice_count"),
                "content_type":trial.get("message_content_type"),
                "reported_usage":trial.get("usage",{}),
                "reasoning_tokens":trial.get("reasoning_tokens"),
            })
        report.setdefault("probes",[]).append(info)
        save_now(report,generated)
        if info["success"]:
            chosen=name
            break
        if trial.get("http_status") in (401,403,429):
            report["status"]="PROBE_AUTH_OR_RATE_LIMIT_STOP"
            save_now(report,generated)
            return 4
    if not chosen:
        report["status"]="NO_RESPONSIVE_FREE_MODEL_NO_BATCH"
        save_now(report,generated)
        return 5
    report["model"]=chosen
    for index,case in enumerate(cases):
        original_position=[c["id"] for c in all_cases].index(case["id"])
        bare_prompt,wf_prompt,temporal,graph,promptmeta=make_packet(case)
        item={
            "id":case["id"],"genre":case["genre"],
            "chapter_one_source_sha256":sha(case["seed"]),
            "source_was_synthetic":True,"prompt_receipt":promptmeta,
            "samples":[],"pair_status":"IN_PROGRESS",
        }
        report["cases"].append(item)
        save_now(report,generated)
        # Alternate order to limit systematic warm-server/order effects.
        order=("bare","wf") if original_position%2==0 else ("wf","bare")
        for variant in order:
            prompt=bare_prompt if variant=="bare" else wf_prompt
            # Hard cap includes even requests that time out or return 429.
            if report["calls_attempted"]>=allowed_calls:
                report["status"]="TOTAL_CALL_LIMIT_REACHED"
                save_now(report,generated)
                return 6
            report["calls_attempted"]+=1
            start=time.monotonic()
            result=chat(key,chosen,prompt,MAX_RESERVED_OUTPUT)
            elapsed=round(time.monotonic()-start,1)
            if not result.get("ok") or not result.get("text","").strip():
                item["samples"].append({
                    "variant":variant,"success":False,
                    "http_status":result.get("http_status"),
                    "error_kind":result.get("kind","EMPTY_CONTENT"),
                    "duration_seconds":elapsed,
                    "partial_visible_han":_han_count(
                        result.get("partial_text","")),
                    "finish_reason":result.get("finish_reason"),
                    "sse_events":result.get("sse_events"),
                    "reported_usage":result.get("usage",{}),
                    "reasoning_characters":result.get("reasoning_characters",0),
                })
                item["pair_status"]="INCOMPLETE_PROVIDER_FAILURE"
                report["status"]="STOPPED_ON_PROVIDER_FAILURE_NO_RETRY"
                save_now(report,generated)
                return 7
            text=result["text"]
            observ=diagnose(
                case,text,temporal,graph,variant=variant,
                usage=result["usage"],
                finish_reason=result["finish_reason"])
            observ["success"]=True
            observ["duration_seconds"]=elapsed
            observ["sse_events"]=result.get("sse_events",0)
            observ["provider_done_seen"]=result.get("done_seen",False)
            observ["reasoning_characters"]=result.get(
                "reasoning_characters",0)
            item["samples"].append(observ)
            generated.append({
                "genre":case["genre"],"id":case["id"],
                "variant":variant,"model":chosen,
                "sample_sha256":observ["output_sha256"],
                "prose":text,
                "seed":case["seed"],
                "scene_goal":case["goal"],
                "prompt_sha256":sha(prompt),
                # Keep the actual prompts privately inside the artifact for
                # reproducibility; never put raw prose in public logs.
                "input_prompt":prompt,
            })
            save_now(report,generated)
            # Do not risk rate limits with back-to-back bursts.
            time.sleep(1.2)
        if len(item["samples"])==2:
            item["pair_status"]="TWO_ORIGINAL_SAMPLES_SAVED"
            report["pairs_complete"]+=1
            save_now(report,generated)
    report["status"]=(
        "SEVEN_PAIRS_SAVED_NO_BLIND_REVIEW_YET"
        if not selected else "ONE_CATEGORY_PAIR_SAVED_NO_BLIND_REVIEW_YET")
    report["completed_utc"]=time.strftime(
        "%Y-%m-%dT%H:%M:%SZ",time.gmtime())
    save_now(report,generated)
    # Log safe mechanical observations only. The user may download the 14
    # full pieces from the workflow artifact; never print private prose.
    print(json.dumps({
        "status":report["status"],"model":report["model"],
        "pairs_complete":report["pairs_complete"],
        "calls_attempted":report["calls_attempted"],
        "genres":[{"genre":x["genre"],"pair_status":x["pair_status"],
                   "variants":[{"variant":s.get("variant"),
                                "han":s.get("han_characters"),
                                "hard":s.get("hard_source_warnings",[])}
                               for s in x["samples"]]}
                  for x in report["cases"]],
    },ensure_ascii=False))
    return 0


if __name__=="__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        # Failures are never evidence of model skill. Do not log provider
        # response text, credentials or prose.
        SCENE_DIR.mkdir(exist_ok=True)
        err={"status":"BATCH_PYTHON_FAILED",
             "exception_type":type(exc).__name__,
             "original_user_novels_sent":False}
        (SCENE_DIR/"FATAL_STATUS.json").write_text(
            json.dumps(err,ensure_ascii=False),encoding="utf8")
        print(json.dumps(err,ensure_ascii=False))
        sys.exit(20)
