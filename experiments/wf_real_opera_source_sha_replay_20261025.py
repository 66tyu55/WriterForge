"""Exact-original stage-7 DeepSeek null-SHA decision: ZERO model replay.

Source: GitHub Actions real same-source G fiction run #40110957161,
artifact #12566716882. SHA-check full old provider wire/decoded pairs,
G novel prose and signed V117 receipt BEFORE interpreting old author answer.
Old INVALID_SIGNAL stays. The optional host contract binds only a model's
NULL mechanical SHA to its CURRENT byte-exact G prose, never fixes wrong
asserted hashes, invents a decision, or overwrites raw model replies.

An independently observed seed/prose source divergence is recorded as
quoted human-review question; it is NOT automatically a proved literary
contradiction, new story memory, or a mandatory V119 operation.
"""
from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path
from writerforge.writing_assist import _ai_decides_when_to_revisit,_decode_json
from writerforge.v96_causal_turns import check_turn
from writerforge.v117_continuity_trace import read_resume
from writerforge.narrative_core import read_core_from_resume
from writerforge.verified_flow import GroundedDraftPacket

PREVIOUS_GH_RUN=40110957161
PREVIOUS_ARTIFACT=12566716882
ORIGINAL=Path("wf_real_opera_previous_20261025")
OUTPUT=Path("wf_real_opera_sha_zero_model_replay_20261025")
ORIGINAL_STAGES=(
    "CHAPTER_PLAN","SELF_BEAT_PLAN","PROSE_1","PROSE_2",
    "CONTROL_AUTHOR","TREATMENT_READER","TREATMENT_AUTHOR")
ORIGINAL_SOURCE_SHA="2a0d2827d51dc1197065cd21126e091a3fd44c4db3bb7d92048c3167d24f4dbd"
ORIGINAL_INITIAL_SHA="c951cefd9bb4aed2ea466292a4ae61d20eb30c05a7dafcd9db8f273b15f774ce"

def h(src):
    return sha256(src.encode("utf8") if isinstance(src,str) else src).hexdigest()

def save(path,info):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(info,ensure_ascii=False,sort_keys=True,
                               indent=2),encoding="utf8")

def _private_file(root,rel,*,limit=150000):
    if not isinstance(root,Path) or not root.is_dir():
        raise ValueError("WF_OPERA_REAL_ARTIFACT_ROOT_MISSING")
    target=root/rel
    if (target.is_symlink() or not target.is_file() or
        not target.resolve().is_relative_to(root.resolve()) or
        not 0<target.stat().st_size<=limit):
        raise ValueError("WF_OPERA_REAL_ARTIFACT_FILE_MISSING_OR_UNTRUSTED")
    return target.read_bytes()

def get_verified_prior(root=ORIGINAL):
    """All seven source/decision wires, G manuscript and V117 from one job."""
    record=json.loads(_private_file(root,"STATUS.json"))
    expected=("CHAPTER_PLAN","SELF_BEAT_PLAN","PROSE_1","PROSE_2",
              "CONTROL_AUTHOR","TREATMENT_READER","TREATMENT_AUTHOR")
    events=record.get("real_model_evidence")
    if (record.get("status")!="G_REAL_SOURCE_AND_TWO_AUTHENTIC_REVIEW_ARMS_SAVED"
        or record.get("model")!="deepseek-flash"
        or record.get("actual_provider_calls")!=7
        or record.get("single_source_for_control_and_treatment")!=ORIGINAL_SOURCE_SHA
        or record.get("actual_wf_G_original_generated") is not True
        or record.get("control",{}).get("author_decision")!="MOVE_ON"
        or record.get("reader_first_treatment",{}).get("author_decision")!="INVALID_SIGNAL"
        or type(events) is not list or len(events)!=len(expected)):
        raise ValueError("WF_OPERA_REAL_RUN_CONTEXT_INVALID")
    for n,stage in enumerate(expected,1):
        ev=events[n-1]
        raw=_private_file(root,
             f"provider-wires/{n:02d}-{stage}-original-model.json")
        wire=_private_file(root,
             f"provider-wires/{n:02d}-{stage}-provider-wire.json")
        if (ev.get("stage")!=stage or
            ev.get("original_provider_wire_saved") is not True or
            h(wire)!=ev.get("provider_wire_sha256") or
            h(raw)!=ev.get("original_model_reply_sha256")):
            raise ValueError("WF_OPERA_REAL_PROVIDER_WIRE_CHANGED")
    prose=_private_file(root,"TRUE_IDENTICAL_FIRST_TURN_SOURCE.md").decode("utf8")
    seed=_private_file(root,"SYNTHETIC_SEED_NOT_REAL_NOVEL.md").decode("utf8")
    first=_private_file(root,"TRUE_ORIGINAL_TURN_ENVELOPE.json").decode("utf8")
    old=_private_file(root,"provider-wires/07-TREATMENT_AUTHOR-original-model.json").decode("utf8")
    model_decision=_private_file(
        root,"treatment_reader_first_then_author/writer-own-decision/"
             "ai-when-and-why-original.json").decode("utf8")
    if (h(prose)!=ORIGINAL_SOURCE_SHA or
        _decode_json(first)["prose"].strip()!=prose or
        h(seed)!=record.get("seed_sha256") or
        old!=model_decision or
        _decode_json(old).get("decision")!="MOVE_ON" or
        _decode_json(old).get("source_sha256") is not None):
        raise ValueError("WF_OPERA_REAL_SOURCE_OR_MODEL_DECISION_CHANGED")
    beat=json.loads(_private_file(root,"ACTUAL_WF_BEAT_SOURCE.json"))
    if check_turn(first,beat,mode="causal_guard",accepted=())["prose"]!=prose:
        raise ValueError("WF_OPERA_REAL_V96_CHANGED")
    candidates=list((root/"G-private-raw-record").glob(
        "auto-*/winter-opera-hall_chapter-002-*/v117_unreviewed_text_trace_resume.json"))
    if len(candidates)!=1:
        raise ValueError("WF_OPERA_REAL_V117_MISSING")
    resume=json.loads(candidates[0].read_text("utf8"))
    scene="winter-opera-hall"
    project="wf-original-night-opera-new-one-shot"
    read_resume(resume,project_id=project,scene_id=scene)
    core=read_core_from_resume(resume,project_id=project,scene_id=scene)
    if (core is None or core["memory"]["hot"][-1]["source_sha256"]!=
        record["actual_wf_G_original_chapter_sha256"]):
        raise ValueError("WF_OPERA_REAL_GRAPH_MANUSCRIPT_FINGERPRINT_CHANGED")
    reader=record["reader_first_treatment"].get("reader_report")
    if (type(reader) is not dict or reader.get("source_sha256")!=ORIGINAL_SOURCE_SHA
        or reader.get("all_semantics_are_model_generated_not_verified") is not True):
        raise ValueError("WF_OPERA_REAL_READER_NOT_SOURCE_LINKED")
    return {
        "status":record,"source":prose,"seed":seed,"beat":beat,
        "first_raw":first,"reader_report":reader,
        "author_raw":old,"resume":resume,"graph":core,
    }

def replay(root=ORIGINAL,out=OUTPUT):
    original=get_verified_prior(root)
    source,decision=original["source"],original["author_raw"]
    if out.exists():
        raise ValueError("WF_OPERA_REPLAY_NEVER_OVERWRITE")
    out.mkdir(parents=True)
    packet=GroundedDraftPacket(
        project_id="wf-original-night-opera-new-one-shot",
        scene_id="winter-opera-hall",snapshot_id=0,
        evidence=(),craft_ids=(),
        prompt="当前小说原稿由真正写作模型独立创作。",
        prompt_sha256=h("当前小说原稿由真正写作模型独立创作。"))
    def saved_reply(pkt,*,model,api_base,max_tokens):
        if (model is not None or api_base is not None or max_tokens!=600
            or source not in pkt.prompt):
            raise RuntimeError("WF_OPERA_REPLAY_SOURCE_OR_CALL_CHANGED")
        return decision
    kwargs=dict(
        raw=original["first_raw"],beat=original["beat"],
        accepted=(),turn_packet=packet,
        ask_model=saved_reply,
        reader_report=original["reader_report"])
    strict=_ai_decides_when_to_revisit(
        **kwargs,directory=out/"strict-original-default")
    binding=_ai_decides_when_to_revisit(
        **kwargs,directory=out/"only-null-current-bound",
        source_identity_contract="bind_null_current")
    if (strict["decision"]!="INVALID_SIGNAL" or
        binding["decision"]!="MOVE_ON" or
        binding["target_prose_sha256"]!=ORIGINAL_SOURCE_SHA or
        binding["receipt"]["null_source_sha256_bound_from_current_source"] is not True):
        raise ValueError("WF_OPERA_REAL_NULL_SHA_ZERO_MODEL_REPLAY_NOT_PROVEN")
    (out/"EXACT_REAL_OLD_DEEPSEEK_REPLY_UNMODIFIED.json").write_text(
        decision,encoding="utf8")
    (out/"GENUINE_G_SOURCE_OLD_UNCHANGED.md").write_text(
        source,encoding="utf8")
    # Mechanical quotes in the already verified original seed and new prose
    # document a reviewable change, not a literary verdict.
    earlier_quote="衣袖里藏着一张尚未交出去的赎身票据。"
    later_quote="票据还压在箱底一件戏服底下"
    seed=original["seed"]
    if (seed.count(earlier_quote)!=1 or source.count(later_quote)!=1):
        raise ValueError("WF_OPERA_REAL_PRIOR_ITEM_QUOTES_CHANGED")
    preview={
        "kind":"UNRESOLVED_EARLIER_TO_CURRENT_ITEM_LOCATION",
        "old_source_sha256":h(seed),
        "new_source_sha256":h(source),
        "earlier_exact_quote":earlier_quote,
        "earlier_quote_offset":seed.index(earlier_quote),
        "current_exact_quote":later_quote,
        "current_quote_offset":source.index(later_quote),
        "was_item_physically_transferred_in_unseen_interval":"UNKNOWN",
        "only_literary_author_can_decide_missing_event":True,
        "is_proof_of_literary_error":False,
        "new_memory_written":False,"source_edits":0,"model_calls":0,
    }
    save(out/"EARLIER_CURRENT_EXACT_SOURCE_RISK_NOT_LITERARY_VERDICT.json",preview)
    meta={
        "format":"wf.real.G.same-source-author-null-SHA-offline-replay.v1",
        "real_original_run":PREVIOUS_GH_RUN,
        "real_original_artifact":PREVIOUS_ARTIFACT,
        "original_model_reply_sha256":h(decision),
        "model_actual_decision":"MOVE_ON",
        "original_strict_wf_decision":strict["decision"],
        "explicit_null_current_bound_decision":binding["decision"],
        "source_bound_from_verified_G_original":True,
        "wrong_supplied_source_sha_not_repaired":True,
        "unchanged_source_sha256":h(source),
        "old_original_author_response_not_edited":True,
        "new_model_calls":0,"source_events_written":0,
        "user_R2_writes":0,"canon_writes":0,"main_unchanged":True,
        "independent_literary_quality_verified":False,
        "reviewable_earlier_to_current_item_evidence":True,
        "unresolved_item_source_risk_is_a_hypothesis":True,
    }
    save(out/"STATUS.json",meta)
    print(json.dumps({
        "stage":"ONE_OLD_REAL_NULL_SHA_AUTHOR_REPLY_REPLAYED_ZERO_MODEL",
        "old":strict["decision"],"host_bound":binding["decision"],
        "real_author_was_MOVE_ON":True,"model_calls":0,
        "item_locations_need_human_or_model_review":True,
    },ensure_ascii=False),flush=True)
    return meta

if __name__=="__main__":
    replay()
