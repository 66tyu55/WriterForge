"""Real, narrowly controlled literary A/B inside AutonomousWriting.

The 4 source scenarios, *model-generated* chapter plans and event beats
come from the already sealed run 39961720469. Each arm freezes those same
model plans. Only one new optional source-progression second-turn writer cue
is changed. Each arm calls the SAME DeepSeek Flash twice for actual prose:
2 genres x 2 arms x 2 turns? The workflow has four separate genres.
No model-rerun for planning; no whole-book training, fake prose or second
memory. Failed original provider wires are saved before JSON validation.
Neither software passes nor these N=1 A/B pairs prove literary improvement.
"""
from __future__ import annotations

from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import io
import json
import os
import re
import zipfile

from experiments.v111_peer.neutral_bridge import fresh_neutral_published_snapshot
from experiments.wf_real_self_scene_diagnostics import (
    CASES, SYSTEMS, source_event, dump, h,
)
from writerforge import WriterForgeDB, RuntimeEngine
from writerforge.deepseek_flash_model import DeepSeekFlashModel, FlashBudget
from writerforge.narrative_core import new_graph,advance_graph,record_chapter_memory
from writerforge.v114_external_story_state import (
    require_external_runtime,external_temporal_step,
)
from writerforge.v117_continuity_trace import make_resume
from writerforge.v96_causal_turns import parse_turn_outline
from writerforge.writing_assist import (
    AutonomousWriting,InvisibleWritingAssist,
    _normalize_optional_model_craft_labels,
)

REPO="66tyu55/WriterForge"
SOURCE_RUN=39961720469
MAX_ZIP_BYTES=128*1024
LOCKED={
    "fight":(12504383809,
             "5d8415571b90b2acb2c6a5ee8949e002621052161c841b4f0b067c14e519a795"),
    "scheme":(12504693234,
              "7a9a9ec0995bb1cb297c8ae9cf2802b7c5fda09ce6caf516ceca115483d550a7"),
    "humor":(12504683581,
             "c7c8418e612f2fd9a13a6450d0295f8c0b616bf17b82accaa956858d0a577d78"),
    "psychology":(12503609960,
                  "c2b18ed49112cc449a7273200e150513477ae091febcf45f0ca11a9d589c4667"),
}
MAX_CALLS_PER_PAIR=4
MAX_MODEL_OUTPUT_PER_PAIR=1450*4
MODES=("baseline","source_progression")
TARGET=Path("wf_literary_progression_ab_results")


def strict(condition,code):
    if not condition:
        raise RuntimeError(code)


def _github_originals(genre,token):
    """Download old model-created *plans only* with SHA and provenance."""
    import requests
    ident,sha=LOCKED[genre]
    url=f"https://api.github.com/repos/{REPO}/actions/artifacts/{ident}"
    headers={
        "Authorization":"Bearer "+token,
        "Accept":"application/vnd.github+json",
        "X-GitHub-Api-Version":"2022-11-28",
    }
    metadata=requests.get(url,headers=headers,timeout=(12,45))
    metadata.raise_for_status()
    doc=metadata.json()
    strict(doc.get("id")==ident and
           doc.get("name")==f"WF-Real-Self-Written-{genre}-Originals" and
           doc.get("digest")=="sha256:"+sha and
           doc.get("expired") is False and
           (doc.get("workflow_run") or {}).get("id")==SOURCE_RUN and
           0<doc.get("size_in_bytes",0)<MAX_ZIP_BYTES,
           "WF_AB_FROZEN_MODEL_PLAN_SOURCE_MISMATCH")
    response=requests.get(url+"/zip",headers=headers,
                          timeout=(12,70),stream=True)
    response.raise_for_status()
    content=bytearray()
    try:
        for chunk in response.iter_content(16384):
            content.extend(chunk)
            strict(len(content)<=MAX_ZIP_BYTES,
                   "WF_AB_FROZEN_SOURCE_BYTES_EXCEEDED")
    finally:
        response.close()
    blob=bytes(content)
    strict(h(blob)==sha,"WF_AB_FROZEN_GITHUB_ORIGINAL_ZIP_HASH_CHANGED")
    strict(zipfile.is_zipfile(io.BytesIO(blob)),
           "WF_AB_FROZEN_GITHUB_ORIGINAL_ZIP_INVALID")
    with zipfile.ZipFile(io.BytesIO(blob)) as archive:
        strict(archive.testzip() is None and len(archive.namelist())<=35,
               "WF_AB_FROZEN_GITHUB_ORIGINAL_INTEGRITY_FAILED")
        source=archive.read("synthetic-chapter-one.md").decode("utf8")
        raw_plan=archive.read("01-CHAPTER_PLAN-original.json").decode("utf8")
        raw_beats=archive.read("02-SELF_BEAT_PLAN-original.json").decode("utf8")
        strict(source==CASES[genre]["seed"],
               "WF_AB_FROZEN_INITIAL_SCENE_HAS_DRIFTED")
    normalized,optional_recovery=_normalize_optional_model_craft_labels(raw_beats)
    beats=parse_turn_outline(normalized)
    strict(len(beats)==2 and len(raw_plan.encode("utf8"))<10000,
           "WF_AB_FROZEN_MODEL_ORIGINAL_NOT_TWO_BEATS")
    return {
        "source_artifact_id":ident,"source_artifact_zip_sha256":sha,
        "original_model_plan_sha256":h(raw_plan),
        "original_model_turn_plan_sha256":h(raw_beats),
        "normalized_turn_plan_sha256":h(normalized),
        "model_plan":raw_plan,"model_beats":normalized,
        "model_optional_craft_recovery":optional_recovery,
    }


def _runner(genre,*,mode,blind_id,plans,root,client,calls):
    case=CASES[genre]
    out=TARGET/genre/blind_id
    out.mkdir(parents=True,exist_ok=False)
    seed=case["seed"]
    with TemporaryDirectory(prefix="wf-literary-ab-"+genre+"-") as folder:
        work=Path(folder)
        source=work/"synthetic-seed.md"
        source.write_text(seed,encoding="utf8")
        snap=fresh_neutral_published_snapshot(work/"neutral.sqlite")
        db=WriterForgeDB(work/"neutral.sqlite")
        try:
            db.conn.execute(
                "UPDATE xuehai_entries SET genre=? WHERE work_id=?",
                (case["genre"],"v111-neutral-fixture"))
            db.conn.commit()
            rt=RuntimeEngine()
            rt.enter_write(snap)
            project="wf-source-literary-ab-experiment"
            scope="scene-"+genre
            core=new_graph(project_id=project,scene_id=scope)
            core=advance_graph(
                core,project_id=project,scene_id=scope,
                chapter_index=1,prose=seed,
                events=[source_event(seed,i,event)
                        for i,event in enumerate(case.get("event_quotes",()),1)])
            core=record_chapter_memory(
                core,project_id=project,scene_id=scope,chapter_index=1,
                source_path=str(source),prose=seed)
            old=external_temporal_step(
                seed,cast=("沈砚","唐蜃","叶青梧"))
            resume=make_resume(
                project_id=project,scene_id=scope,chapter_index=1,
                checkpoint=old,unified_narrative_core=core)
            helper=InvisibleWritingAssist(
                db,rt,project,scope,case["goal"],model="deepseek-flash",
                api_base="https://api.deepseek.com",source_genre=case["genre"])
            stages=["PROSE_1","PROSE_2"]
            stage={"number":0,"name":None}
            def save_wire(raw):
                strict(type(raw) is bytes and 0<len(raw)<2000000,
                       "WF_AB_PROVIDER_WIRE_INVALID")
                strict(stage["name"] in stages,
                       "WF_AB_PROVIDER_WIRE_WITHOUT_RESERVED_CALL")
                path=out/("provider-wire-"+stage["name"]+".json")
                path.write_bytes(raw)
                calls[-1]["original_provider_wire_sha256"]=h(raw)
                calls[-1]["original_wire_saved_before_validation"]=True
            client._on_response_wire=save_wire
            def adapter(packet,*,model,api_base,max_tokens,**kw):
                strict(not kw and model=="deepseek-flash" and
                       api_base=="https://api.deepseek.com",
                       "WF_AB_MODEL_ROUTING_CHANGED")
                if stage["number"]==0:
                    stage["number"]+=1
                    strict(max_tokens==650,"WF_AB_CHAPTER_PLAN_BUDGET_CHANGED")
                    return plans["model_plan"]
                idx=stage["number"]-1
                strict(idx in (0,1) and max_tokens==1450,
                       "WF_AB_MORE_THAN_TWO_PROSE_CALLS_OR_DIFFERENT_BUDGET")
                name=stages[idx]
                stage.update(number=stage["number"]+1,name=name)
                calls.append({
                    "blind_id":blind_id,"stage":name,
                    "max_tokens":max_tokens,"prompt_sha256":h(packet.prompt),
                    "original_source_plan_frozen":True,
                })
                reply=client.ask_json(
                    role="self_scene_writing",system=SYSTEMS["PROSE"],
                    user=packet.prompt,max_tokens=max_tokens)
                raw=json.dumps(reply,ensure_ascii=False,separators=(",",":"))
                (out/f"original-decoded-{name}.json").write_text(
                    raw,encoding="utf8")
                calls[-1].update({
                    "decoded_original_sha256":h(raw),
                    "provider_json_wrapper_recovery":
                        client.last_response_format_recovery,
                })
                return raw
            try:
                with patch("writerforge.writing_assist.local_chat_completion",
                           side_effect=adapter):
                    result=AutonomousWriting(helper).run(
                        outline=case["outline"]+
                                "\n此前唯一事实材料："+seed,
                        chapter_goals=[case["goal"]],
                        output_dir=work/"isolated-candidates",
                        draft_mode="continuity_guard",
                        resume_story_checkpoint=resume,
                        frozen_turn_outlines=(plans["model_beats"],),
                        literary_progression_mode=mode)
                chapter=result["chapters"][0]
                prose=Path(chapter["candidate"]).read_text("utf8")
                (out/"original-complete-candidate.md").write_text(
                    prose,encoding="utf8")
                evidence=json.loads(Path(chapter["turn_evidence"]).read_text(
                    encoding="utf8"))
                cue=evidence.get("source_progression_cue_delivery",[])
                strict((cue==[False,True] if mode=="source_progression"
                        else cue==[False,False]),
                       "WF_AB_PROGRESS_HINT_NOT_DELIVERED_AS_INTENDED")
                pair_result={
                    "status":"COMPLETE_UNACCEPTED_REAL_WF_CANDIDATE",
                    "prose_sha256":h(prose),
                    "han_chars":sum("\u3400"<=ch<="\u9fff" for ch in prose),
                    "total_chars":len(prose),
                    "cue_delivery_by_turn":cue,
                    "model_trace_review_failures":evidence.get(
                        "unified_model_trace_review_failures",[]),
                    "source_citation_normalizations":evidence.get(
                        "unified_source_citation_normalizations",[]),
                    "literal_replay_blocked":evidence.get(
                        "unified_completed_chapter_replay",{}).get("blocked"),
                    "model_calls_for_content":len(calls),
                    "literary_quality_independently_verified":False,
                    "canon_writes":0,
                }
                dump(out/"scene_evidence.json",pair_result)
                return pair_result
            except Exception as error:
                why=str(error)
                if not re.fullmatch(r"[A-Z][A-Z0-9_:\-,.]{2,190}",why):
                    why=type(error).__name__+":SCENE_DRAFT_INTERRUPTED"
                failure={
                    "status":"FAILED_OR_REJECTED_NO_MODEL_RETRY",
                    "failure_code":why,
                    "model_calls":len(calls),
                    "candidate_accepted":False,
                }
                dump(out/"scene_evidence.json",failure)
                return failure
        finally:
            strict(db.conn.execute(
                "SELECT COUNT(*) FROM accepted_prose").fetchone()[0]==0,
                "WF_AB_ACCIDENTAL_CANON_PROMOTION")
            db.close()


def main(genre):
    strict(genre in CASES and genre in LOCKED,"WF_AB_UNKNOWN_CASE")
    strict(bool(os.environ.get("DEEPSEEK_API_KEY")),
           "WF_AB_EXISTING_DEEPSEEK_KEY_NOT_PRESENT")
    strict(bool(os.environ.get("GITHUB_TOKEN")),
           "WF_AB_GITHUB_ARTIFACT_READ_NOT_AVAILABLE")
    require_external_runtime()
    base=TARGET/genre
    base.mkdir(parents=True,exist_ok=False)
    plans=_github_originals(genre,os.environ["GITHUB_TOKEN"])
    # Pre-determined, balanced, no result-informed variant order.
    first=(MODES if int(h(genre+"|order")[0],16)%2==0 else MODES[::-1])
    pairs={}
    budget=FlashBudget(
        max_calls=MAX_CALLS_PER_PAIR,
        max_reserved_output_tokens=MAX_MODEL_OUTPUT_PER_PAIR,
        max_total_tokens=150000,
    )
    client=DeepSeekFlashModel(budget=budget,timeout_seconds=120)
    for blind_id,mode in zip(("W1","W2"),first):
        calls=[]
        pairs[blind_id]=_runner(
            genre,mode=mode,blind_id=blind_id,plans=plans,
            root=base,client=client,calls=calls)
        pairs[blind_id]["model_stage_receipts"]=calls
    equal=(all(row["status"]=="COMPLETE_UNACCEPTED_REAL_WF_CANDIDATE"
               for row in pairs.values()) and
           all(row["model_calls_for_content"]==2 for row in pairs.values()) and
           budget.calls_reserved==4)
    # Only anonymous manuscript files appear in the reading order.
    pair_text=[
        "# WriterForge real blind A/B — "+genre,
        "",
        "Both arms are original model prose from the same fixed story source, "
        "identical model-authored plan, the same DeepSeek Flash and 1450-token "
        "limit per turn. Names W1/W2 are intentionally not the feature labels.",
        "",
        "## Prior first chapter (same in both variants)",
        CASES[genre]["seed"],
    ]
    for blind_id in ("W1","W2"):
        path=base/blind_id/"original-complete-candidate.md"
        pair_text.extend([
            "",
            "## "+blind_id,
            path.read_text("utf8") if path.exists() else
              "[NO ACCEPTED CANDIDATE; see failure receipt]",
        ])
    (base/"BLIND_PAIR.md").write_text(
        "\n".join(pair_text)+"\n",encoding="utf8")
    manifest={
        "format":"wf.experiment.real-literary-source-progression-ab.v1",
        "genre":genre,
        "model":"deepseek-flash",
        "source_generation_run_id":SOURCE_RUN,
        "identical_frozen_model_plan_SHA":plans[
            "original_model_plan_sha256"],
        "identical_frozen_model_turn_plan_SHA":plans[
            "original_model_turn_plan_sha256"],
        "source_artifact_id":plans["source_artifact_id"],
        "artifacts_original_sha256":plans["source_artifact_zip_sha256"],
        "same_source_seed_sha256":h(CASES[genre]["seed"]),
        "paired_budget_four_calls_max":MAX_CALLS_PER_PAIR,
        "fixed_provider_max_output_each_prose_call":1450,
        "actual_provider_call_count":budget.calls_reserved,
        "no_extra_model_critics":True,
        "fair_pair_generated":equal,
        "blind_labels_not_quality_ranks":True,
        "human_independent_blind_review":"NOT_PERFORMED",
        "literary_improvement_proven":False,
        "production_main_or_railway_unchanged":True,
        "user_novel_corpus_used":False,
        "results":pairs,
        "reported_provider_usage":budget.public_receipt(),
    }
    dump(base/"PAIR_STATUS.json",manifest)
    mapping={
        "genre":genre,"W1":first[0],"W2":first[1],
        "mapping_for_unblinding_after_reading_only":True,
        "plan_normalization_receipt":plans["model_optional_craft_recovery"],
    }
    dump(base/"UNBLIND_MAPPING.json",mapping)
    print("WF_REAL_LITERARY_AB_STATUS "+json.dumps({
        "genre":genre,"fair_pair_generated":equal,
        "W1":pairs["W1"]["status"],"W2":pairs["W2"]["status"],
        "W1_han":pairs["W1"].get("han_chars"),
        "W2_han":pairs["W2"].get("han_chars"),
        "model_calls":budget.calls_reserved,
        "estimated_output_budget":MAX_MODEL_OUTPUT_PER_PAIR,
        "literary_quality_independently_verified":False,
        "no_new_retries":True,
    },ensure_ascii=False,separators=(",",":")),flush=True)


if __name__=="__main__":
    scene=os.getenv("WF_AB_GENRE","")
    main(scene)
