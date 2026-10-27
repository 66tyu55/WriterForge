"""WF 0.BK: TRUE three-arm author-core experiment, not another fake WF prompt.

Bare author is one direct model request with the specified story/task.
WF core calls the unchanged production AutonomousWriting.run in explicit
continuity_guard+bootstrap_unified_core+G rolling mode; the G+SHADOW arm
calls that SAME real core with a digest-pinned non-executing candidate hint.

The SHADOW capsule is experimental source DATA. This never calls a registered
optional Skill, never changes ACTIVE permissions, never writes Canon/R2.
Experimental hint insertion is performed in the packet-building seam
(_enrich) with fresh prompt SHA: no post-hoc untracked prompt change.

No live provider usage is authorized here. Only synthetic host callbacks
exercise integration until a NEW explicitly approved model and full on-wire
usage attestation are available. Real prose quality remains UNPROVEN.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from hashlib import sha256
from pathlib import Path
from unittest.mock import patch
import json

from writerforge.scheduler import OptionalHostResourceLease, OptionalHostResourceUnavailable
from writerforge.writing_assist import AutonomousWriting
from writerforge.verified_flow import MAX_PROMPT_CHARS

ROOT=Path(__file__).resolve().parents[1]
V1=ROOT/".agents/skills/observe-before-next-choice/capsule.json"
V2=ROOT/"experiments/wf_0bd_portable_habit_snapshots/0d43a023bc278ac12e3165e319d2acb73dcf40c0d9af453e623c786f3b476a10/capsule.json"
V1_SHA="42cad98118dea662cea472f708ef1de22f4bb139da3210b1f5c3c1f9ac12664d"
V2_SHA="0d43a023bc278ac12e3165e319d2acb73dcf40c0d9af453e623c786f3b476a10"
FROZEN_ARMS=("bare","wf_core","wf_habit")
MAX_PER_ARM_CALLS=8
MAX_RESERVED_COMPLETION_TOKENS_PER_ARM=18000
MAX_OBSERVED_RESPONSE_BYTES=120000
BARE_MAX_COMPLETION_TOKENS=2600
CANDIDATE_MARKER="【认知候选（仅实验数据）】"
FORMAT="wf.0bk.actual-autonomous-writing-three-arm-protocol.v1"


class StudyProtocolError(ValueError):
    pass


def _digest(text:str)->str:
    return sha256(text.encode("utf8")).hexdigest()


def _need(yes:bool,code:str):
    if not yes:
        raise StudyProtocolError(code)


@dataclass(frozen=True)
class BareDraftPacket:
    prompt:str
    prompt_sha256:str


@dataclass(frozen=True)
class HostStudyCompletion:
    content:str
    model_id:str
    request_prompt_sha256:str
    source_kind:str
    provider_wire_sha256:str|None
    actual_prompt_tokens:int|None
    actual_completion_tokens:int|None


def _capsule(revision:str)->tuple[dict,str]:
    _need(revision in ("v1","v2"),"WF0BK_UNKNOWN_CANDIDATE_REVISION")
    path,expected=(V1,V1_SHA) if revision=="v1" else (V2,V2_SHA)
    raw=path.read_bytes()
    if sha256(raw).hexdigest()!=expected:
        raise StudyProtocolError("WF0BK_IMMUTABLE_SHADOW_OR_PARENT_CHANGED")
    capsule=json.loads(raw)
    _need(capsule.get("lifecycle")=="SHADOW" and
          capsule.get("id")=="observe-before-next-choice" and
          capsule.get("revision")==(1 if revision=="v1" else 2) and
          not capsule["authority"]["auto_skill_promotion"],
          "WF0BK_UNTRUSTED_CAPSULE_OR_ACTIVE_PROMOTION")
    return capsule,expected


def three_arm_preflight(*,outline:str,task:str,
                        source_prose:tuple[str,str],
                        optional_habit_revision:str="v2")->dict:
    candidate,digest=_capsule(optional_habit_revision)
    _need(type(outline) is str and 25<=len(outline.strip())<=1500 and
          type(task) is str and 18<=len(task.strip())<=300 and
          type(source_prose) is tuple and len(source_prose)==2 and
          all(type(v) is str and 12<=len(v)<=1300 for v in source_prose),
          "WF0BK_FROZEN_USER_TASK_OR_SOURCE_INVALID")
    return {
        "format":FORMAT,
        "arms":list(FROZEN_ARMS),
        "source_sha256":_digest("\n".join(source_prose)),
        "task_sha256":_digest(task),
        "outline_sha256":_digest(outline),
        "candidate_sha256":digest,
        "candidate_revision":optional_habit_revision,
        "candidate_procedure_sha256":_digest(candidate["procedure"][1]),
        "candidate_is_shadow_context_not_active_skill":True,
        "new_paid_provider_calls_authorized":0,
        "no_model_calls_in_preflight":0,
        "host_model_policy":"EXPLICIT_HOST_CALLBACK_ONLY",
        "bare_model_must_not_see_wf_context":True,
        "wf_core_execution_mode":"continuity_guard",
        "wf_core_uses_real_autonomous_writing":True,
        "wf_rolling_v98_opt_in":True,
        "wf_unified_narrative_core":True,
        "wf_v119_self_edit_used_in_this_protocol":False,
        "v119_preserved_by_untouched_production_core":True,
        "per_arm_max_model_calls":MAX_PER_ARM_CALLS,
        "per_arm_max_reserved_completion_tokens":
            MAX_RESERVED_COMPLETION_TOKENS_PER_ARM,
        "allocation_is_equal_ceiling_not_equal_consumption":True,
        "quality_improvement_proven":False,
        "independent_reader_votes":0,
        "no_automatic_repeat_or_promotion":True,
    }


def _published_source_scope(assist)->dict:
    """Compare the ACTUAL source identity in both isolated WF core databases.

    Snapshot numeric IDs alone do not prove equal source. Hash literal
    published source rows without exporting their private texts.
    A changed corpus, story scope or genre may not masquerade as a
    candidate-only treatment. This offline check has a fixed size cap.
    """
    db=assist.db
    sid=assist.rt.pinned_snapshot_id
    _need(type(sid) is int and sid>0,
          "WF0BK_PUBLISHED_SOURCE_SNAPSHOT_REQUIRED")
    tables=(
        ("xuehai_entries",
         "SELECT work_id,chapter,paragraph,sentence,text,source_hash "
         "FROM xuehai_entries WHERE snapshot_id=? "
         "ORDER BY work_id,chapter,paragraph,sentence,id",
         (sid,)),
        ("source_spans",
         "SELECT work_id,chapter,paragraph,sentence,excerpt,source_sha256 "
         "FROM source_spans ORDER BY work_id,chapter,paragraph,sentence",
         ()),
    )
    document={}
    for name,query,args in tables:
        data=db.conn.execute(query,args).fetchmany(513)
        _need(0<len(data)<=512,
              "WF0BK_PUBLISHED_SOURCE_MISSING_OR_TOO_LARGE")
        document[name]=[list(row) for row in data]
    return {
        "project_id":assist.project_id,
        "scene_id":assist.scene_id,
        "source_genre":assist.source_genre,
        "goal":assist.goal,
        "published_snapshot_id":sid,
        "published_source_snapshot_sha256":
            _digest(json.dumps(document,sort_keys=True,ensure_ascii=False,
                               separators=(",",":"))),
    }


def execute_three_arm_trial(
    *,outline:str,task:str,source_prose:tuple[str,str],
    model_id:str,call_model,fresh_assist_factory,
    output_dir:Path,host_lease:OptionalHostResourceLease|None,
    fixture_mode:bool=False,
    optional_habit_revision:str="v2",
)->dict:
    """Offline plumbing gate that executes actual WF orchestration.

    Model adapter returns explicit origin; NO fake string is accepted as a
    verified provider wire. Individual WF callbacks are captured *at the
    live author-core invocation point*, not from post-hoc static prompt files.
    """
    plan=three_arm_preflight(
        outline=outline,task=task,source_prose=source_prose,
        optional_habit_revision=optional_habit_revision)
    _need(type(model_id) is str and 3<=len(model_id)<=70 and
          callable(call_model) and callable(fresh_assist_factory),
          "WF0BK_EXPLICIT_HOST_CALLBACK_AND_FRESH_CORE_REQUIRED")
    if not fixture_mode:
        raise PermissionError("WF0BK_REAL_PROVIDER_WIRE_REQUIRED_NEW_AUTHORIZATION")
    if not isinstance(host_lease,OptionalHostResourceLease):
        raise PermissionError("WF0BK_EXPLICIT_HOST_LEASE_REQUIRED")
    for arm in FROZEN_ARMS:
        if host_lease.reason(arm) is not None:
            raise PermissionError("WF0BK_EQUAL_LOCAL_HOST_BUDGET_REQUIRED")
    dest=Path(output_dir)
    if dest.exists():
        raise FileExistsError("WF0BK_TRIAL_ALREADY_EXISTS_NO_REPLAY")
    candidate,candidate_sha=_capsule(optional_habit_revision)
    hint=(
        "\n"+CANDIDATE_MARKER+
        "此为未获准执行的SHADOW认知程序，只作为实验背景供原作者自由取舍。"
        "不可替作者决定情节、不可把人物推测写成事实，也不可自动晋级。\n"
        +candidate["procedure"][1]
    )
    _need(len(hint)<=700,"WF0BK_TREATMENT_UNBOUNDED")
    dest.mkdir(parents=True,exist_ok=False)
    results={}
    events=[]
    reservations={a:0 for a in FROZEN_ARMS}
    counts={a:0 for a in FROZEN_ARMS}
    observed_host_wires=0
    expected_wf_scope=None
    receipt={
        "format":"wf.0bk.true-real-core-three-arm-fixture.v1",
        "status":"RUNNING",
        "source_kind":"SYNTHETIC_TEST_ONLY",
        "protocol":plan,
        "arm_results":results,
        "events":events,
        "source_sha256":plan["source_sha256"],
        "candidate_sha256":candidate_sha,
        "new_paid_model_api_requests":0,
        "actual_model_callback_count":0,
        "provider_authenticated_original_wires":0,
        "literary_gain_proven":False,
        "literary_winner":None,
        "auto_promote":False,
        "canonical_fact_writes":0,
        "v119_opt_in_exercised":False,
        "production_skill_executions":0,
    }

    def persist():
        # This ledger contains only SHA references, no raw model responses or
        # private novel content. The WF candidate remains in local job dirs.
        (dest/"STATUS.json").write_text(
            json.dumps(receipt,ensure_ascii=False,sort_keys=True,indent=2)+"\n",
            encoding="utf8")

    def consume(packet,*,arm:str,model:str,max_tokens:int,api_base:str):
        nonlocal observed_host_wires
        _need(type(packet.prompt) is str and
              _digest(packet.prompt)==packet.prompt_sha256 and
              len(packet.prompt)<=MAX_PROMPT_CHARS,
              "WF0BK_ACTUAL_AUTHOR_PACKET_SHA_OR_CONTEXT_INVALID")
        _need(model==model_id and type(max_tokens) is int and
              1<=max_tokens<=4000 and type(api_base) is str,
              "WF0BK_MODEL_ID_OR_CONTEXT_CAP_DRIFT")
        if (counts[arm]>=MAX_PER_ARM_CALLS or
            reservations[arm]+max_tokens>
                MAX_RESERVED_COMPLETION_TOKENS_PER_ARM):
            raise PermissionError("WF0BK_HOST_CALL_OR_TOTAL_TOKEN_CEILING")
        # Consume once BEFORE calling the host; never refill on invalid JSON,
        # 429, crash or author stage failure.
        host_lease.spend(arm)
        counts[arm]+=1
        reservations[arm]+=max_tokens
        events.append({
            "arm":arm,
            "request_prompt_sha256":packet.prompt_sha256,
            "max_completion_tokens_reserved":max_tokens,
            "stage_number":counts[arm],
            "source_kind":"SYNTHETIC_TEST_ONLY",
            "actual_provider_wire_verified":False,
        })
        receipt["actual_model_callback_count"]+=1
        persist()
        try:
            completion=call_model(
                packet,arm=arm,model=model,max_tokens=max_tokens,
                api_base=api_base)
        except OptionalHostResourceUnavailable as error:
            host_lease.suspend_resource(arm,error)
            raise
        if (not isinstance(completion,HostStudyCompletion) or
            completion.source_kind!="SYNTHETIC_TEST_ONLY" or
            completion.model_id!=model_id or
            completion.request_prompt_sha256!=packet.prompt_sha256 or
            type(completion.content) is not str or
            not 1<=len(completion.content.encode("utf8"))<=
                MAX_OBSERVED_RESPONSE_BYTES or
            completion.provider_wire_sha256 is not None or
            completion.actual_prompt_tokens is not None or
            completion.actual_completion_tokens is not None):
            raise PermissionError("WF0BK_FIXTURE_COMPLETION_NOT_A_REAL_WIRE")
        events[-1]["model_application_response_sha256"]=_digest(
            completion.content)
        persist()
        return completion.content

    # Bare author receives literal source and task, no WF fact journal,
    # flow.prepare(), book memory, self-editor or candidate advice.
    bare_prompt=(
        "你是原创小说作者。只依据以下已写内容继续写小说，由你决定人物"
        "如何行动、是否留白和如何修订；不要复述任务，也不要列提纲。\n"
        +"\n".join(source_prose)+"\n"+task
    )
    _need(len(bare_prompt)<=MAX_PROMPT_CHARS,
          "WF0BK_BARE_AUTHOR_INPUT_OVERFLOW")
    bare=BareDraftPacket(prompt=bare_prompt,
                         prompt_sha256=_digest(bare_prompt))
    try:
        bare_text=consume(
            bare,arm="bare",model=model_id,api_base="local-fixture-only",
            max_tokens=BARE_MAX_COMPLETION_TOKENS)
        (dest/"bare-output-SYNTHETIC-only.sha256").write_text(
            _digest(bare_text)+"\n",encoding="utf8")
        results["bare"]={
            "status":"CALLBACK_COMPLETED",
            "origin":"DIRECT_AUTHOR_PROMPT_NO_WF_ENGINE",
            "no_wf_core_invoked":True,
            "author_response_sha256":_digest(bare_text),
            "author_accepted":False,
            "model_calls":counts["bare"],
        }
        persist()

        # Exactly two fresh WF cores. The candidate arm is the SAME real
        # AutonomousWriting.run route, with an inert SHADOW context added to
        # packets via the source-authoring seam. We never execute SkillRegistry
        # or grant an ACTIVE optional capability in this experiment.
        from writerforge import writing_assist as live_writer
        original_enrich=live_writer._enrich
        for arm in ("wf_core","wf_habit"):
            with fresh_assist_factory(arm) as assist:
                _need(assist.model==model_id and
                      assist.rt.pinned_snapshot_id is not None,
                      "WF0BK_ACTUAL_CORE_MODEL_OR_SNAPSHOT_MISMATCH")
                current_scope=_published_source_scope(assist)
                if expected_wf_scope is None:
                    expected_wf_scope=current_scope
                    receipt["wf_paired_published_source_sha256"]=(
                        current_scope["published_source_snapshot_sha256"])
                elif current_scope!=expected_wf_scope:
                    raise StudyProtocolError(
                        "WF0BK_PAIRED_WF_SOURCE_SCOPE_DIVERGED")
                def model_intercept(packet,*,model,api_base,max_tokens):
                    return consume(packet,arm=arm,model=model,
                                   api_base=api_base,max_tokens=max_tokens)
                def experimental_enrich(*args,**kwargs):
                    prepared=original_enrich(*args,**kwargs)
                    enriched=prepared.prompt+hint
                    if len(enriched)>MAX_PROMPT_CHARS:
                        raise StudyProtocolError(
                            "WF0BK_SHADOW_CONTEXT_EXCEEDS_REAL_CORE_LIMIT")
                    return replace(
                        prepared,prompt=enriched,
                        prompt_sha256=_digest(enriched))
                overlay=(patch.object(live_writer,"_enrich",
                                      side_effect=experimental_enrich)
                         if arm=="wf_habit" else None)
                with patch.object(live_writer,"local_chat_completion",
                                  side_effect=model_intercept):
                    if overlay is not None:
                        overlay.start()
                    try:
                        writer_result=AutonomousWriting(assist).run(
                            outline=outline+"\n【已写前文仅为候选来源】"+
                                "\n".join(source_prose),
                            chapter_goals=[task],
                            output_dir=dest/(arm+"-private-working"),
                            draft_mode="continuity_guard",
                            bootstrap_unified_core=True,
                            narrative_memory_backend="local",
                            g_rolling_author_planning=True,
                            self_edit_rounds=0,
                        )
                    finally:
                        if overlay is not None:
                            overlay.stop()
                chapters=writer_result["chapters"]
                _need(len(chapters)==1 and
                      chapters[0].get("accepted") is False and
                      writer_result.get("source_snapshot_id")==
                        assist.rt.pinned_snapshot_id,
                      "WF0BK_WF_WRITER_CORE_NOT_ACTUALLY_CALLED")
                row=chapters[0]
                saved=Path(row["candidate"])
                _need(saved.is_file() and len(saved.read_bytes())>=100 and
                      row.get("unified_narrative_core_sha256"),
                      "WF0BK_MISSING_REAL_WF_NARRATIVE_CORE_OR_DRAFT")
                results[arm]={
                    "status":"CALLBACK_COMPLETED",
                    "origin":"REAL_AUTONOMOUS_WRITING_CORE",
                    "writing_mode":"continuity_guard",
                    "published_source_snapshot_sha256":
                        current_scope["published_source_snapshot_sha256"],
                    "chapter_count":1,
                    "model_calls":counts[arm],
                    "g_rolling_replan_calls":max(0,counts[arm]-4),
                    "narrative_core_owner_count":1,
                    "unified_narrative_core_sha256":
                        row["unified_narrative_core_sha256"],
                    "candidate_sha256":sha256(saved.read_bytes()).hexdigest(),
                    "source_checked_candidate_on_disk":True,
                    "author_accepted":False,
                    "was_an_active_skill_invocation":False,
                    "experimental_candidate_context_used":arm=="wf_habit",
                }
                persist()
        receipt["status"]="SYNTHETIC_PLUMBING_ONLY_NOT_LITERARY_RESULT"
        persist()
        return receipt
    except OptionalHostResourceUnavailable:
        receipt["status"]="DORMANT_HOST_RESOURCE_NO_RETRY"
        current=next((x for x in FROZEN_ARMS if x not in results),"bare")
        results[current]={
            "status":"FAILED_NO_RETRY",
            "reason":"HOST_429",
            "model_calls":counts[current],
        }
        persist()
        raise
    except Exception as exc:
        receipt["status"]="DORMANT_CORE_OR_HOST_FAILURE_NO_RETRY"
        current=next((x for x in FROZEN_ARMS if x not in results),"bare")
        results[current]={
            "status":"FAILED_NO_RETRY",
            "reason_type":type(exc).__name__,
            "model_calls":counts[current],
        }
        persist()
        raise
