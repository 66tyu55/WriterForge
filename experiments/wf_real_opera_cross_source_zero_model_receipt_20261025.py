"""Recheck old REAL author's defensible or unsupported MOVE_ON, zero inference.

Two immutable GitHub Actions artifacts:
- Full actual G writer and signed V117 from #40110957161
- Genuine same-author cross-source reader + author replies from #40151857245

Save the old literary reply exactly, verify genuine wire hashes, then
replay only strict source validators to attach an UNVERIFIED G review
receipt: the model may KEEP source although independent reader proposed
three actual anchored earlier/current discontinuities. Never auto-change
story text, classify the hypothesis as truth, or create literary scores.
"""
import json
from pathlib import Path
from hashlib import sha256
from writerforge.writing_assist import (
    _reader_separates_written_and_inferred,_ai_decides_when_to_revisit,
)
from writerforge.verified_flow import GroundedDraftPacket
from experiments.wf_real_opera_source_sha_replay_20261025 import (
    get_verified_prior,h as source_hash,
)
from experiments.wf_real_opera_cross_source_reader_followup_20261025 import (
    CAST,
)

OLD_CROSS=Path("wf_prior_opera_cross_source_20261025")
OUTPUT=Path("wf_real_opera_cross_source_reader_keep_zero_model_20261025")
CURRENT_RUN=40151857245
CURRENT_ARTIFACT=12583256056

def sha(x):
    return sha256(x.encode("utf8") if type(x) is str else x).hexdigest()

def source_file(root,name):
    target=root/name
    if (target.is_symlink() or not target.is_file() or
        not target.resolve().is_relative_to(root.resolve()) or
        not 0<target.stat().st_size<=300000):
        raise ValueError("WF_OPERA_CROSS_SOURCE_ARTIFACT_MISSING_OR_UNTRUSTED")
    return target.read_bytes()

def provenance():
    older=get_verified_prior()
    doc=json.loads(source_file(OLD_CROSS,"STATUS.json"))
    if (doc.get("status")!="REAL_READER_AND_AUTHOR_FINISHED" or
        doc.get("actual_new_provider_calls")!=2 or
        doc.get("reader_status")!="SOURCE_ANCHORED_READER_HYPOTHESES" or
        doc.get("author_original_decision")!="MOVE_ON" or
        doc.get("model_did_change_accepted_candidate") is not False or
        doc.get("current_original_sha256")!=sha(older["source"]) or
        doc.get("earlier_source_sha256")!=sha(older["seed"]) or
        type(doc.get("real_provider_wire_provenance")) is not list or
        len(doc["real_provider_wire_provenance"])!=2):
        raise ValueError("WF_OPERA_CROSS_SOURCE_TRUE_HISTORY_MISMATCH")
    for i,stage in enumerate(("CROSS_SOURCE_READER","ORIGINAL_AUTHOR_DECIDES"),1):
        event=doc["real_provider_wire_provenance"][i-1]
        reply=source_file(OLD_CROSS,f"{i:02d}-{stage}-original-answer.json")
        wire=source_file(OLD_CROSS,f"{i:02d}-{stage}-provider-wire.json")
        if (event.get("stage")!=stage or
            event.get("original_provider_wire_preserved_before_parse") is not True or
            sha(reply)!=event.get("original_reply_sha256") or
            sha(wire)!=event.get("wire_sha256")):
            raise ValueError("WF_OPERA_CROSS_SOURCE_PROVIDER_WIRE_TAMPERED")
    first=source_file(
        OLD_CROSS,"independent-signed-reader/original-reader-reply.json")
    second=source_file(
        OLD_CROSS,"original-author-own-decision/ai-when-and-why-original.json")
    if (first!=source_file(
            OLD_CROSS,"01-CROSS_SOURCE_READER-original-answer.json") or
        second!=source_file(
            OLD_CROSS,"02-ORIGINAL_AUTHOR_DECIDES-original-answer.json")):
        raise ValueError("WF_OPERA_CROSS_SOURCE_ORIGINAL_REPLY_REWRITTEN")
    return older,doc,first.decode("utf8"),second.decode("utf8")

def run():
    original,previous,reader_answer,author_answer=provenance()
    if OUTPUT.exists():
        raise ValueError("WF_OPERA_CROSS_SOURCE_NO_OVERWRITE")
    OUTPUT.mkdir(parents=True)
    source,seed=original["source"],original["seed"]
    msg="这是一份已写原文，请同一个模型自主区分证据与文学留白。"
    packet=GroundedDraftPacket(
        project_id="wf-original-night-opera-new-one-shot",
        scene_id="winter-opera-hall",snapshot_id=0,
        evidence=(),craft_ids=(),prompt=msg,prompt_sha256=sha(msg))
    history=[]
    def reader_saved(packet,*,model,api_base,max_tokens):
        assert (model is None and api_base is None and
                max_tokens==1000 and seed in packet.prompt and
                source in packet.prompt)
        history.append("old-real-reader-reply-replayed")
        return reader_answer
    reader=_reader_separates_written_and_inferred(
        raw=original["first_raw"],turn_packet=packet,
        ask_model=reader_saved,directory=OUTPUT/"replayed-only-reader",
        earlier_source=seed,earlier_source_sha256=sha(seed))
    if (reader["status"]!="SOURCE_ANCHORED_READER_HYPOTHESES" or
        len(reader["report"]["cross_source_links"])!=3):
        raise ValueError("WF_OPERA_CROSS_SOURCE_REPLAY_NOT_VERIFIED")
    def author_saved(packet,*,model,api_base,max_tokens):
        assert (model is None and api_base is None and
                max_tokens==600 and
                "reader_cross_source_links" in packet.prompt)
        history.append("old-real-author-reply-replayed")
        return author_answer
    author=_ai_decides_when_to_revisit(
        raw=original["first_raw"],beat=original["beat"],accepted=(),
        turn_packet=packet,ask_model=author_saved,
        directory=OUTPUT/"replayed-only-author",
        reader_report=reader["report"],
        source_identity_contract="bind_null_current")
    if (author["decision"]!="MOVE_ON" or
        author["target_prose_sha256"]!=sha(source) or
        author["receipt"]["cross_source_reader_hypotheses_unverified_count"]!=3 or
        author["receipt"]["author_kept_unresolved_cross_source_hypotheses"] is not True):
        raise ValueError("WF_OPERA_AUTHOR_SOURCE_REVIEW_HYPOTHESIS_NOT_PERSISTED")
    (OUTPUT/"OLD_REAL_READER_WIRE_DECODED_UNCHANGED.json").write_text(
        reader_answer,encoding="utf8")
    (OUTPUT/"OLD_REAL_AUTHOR_WIRE_DECODED_UNCHANGED.json").write_text(
        author_answer,encoding="utf8")
    (OUTPUT/"OLD_MODEL_CURRENT_SOURCE_UNCHANGED.md").write_text(
        source,encoding="utf8")
    report={
        "format":"wf.original.opera.cross-source-human-review-not-model-verdict.v1",
        "old_real_source_run":40110957161,
        "old_new_cross_source_run":CURRENT_RUN,
        "old_real_cross_artifact":CURRENT_ARTIFACT,
        "current_prose_sha256":sha(source),
        "old_model_author_action":"MOVE_ON",
        "source_anchored_prior_current_hypotheses":3,
        "unresolved_readonly_reader_hypotheses":reader["report"]["cross_source_links"],
        "author_kept_private_draft_with_unverified_source_links":True,
        "same_old_model_reply_not_rewritten":True,
        "no_automatic_canon_or_repair":True,
        "original_provider_wire_still_archived":True,
        "new_real_provider_calls":0,
        "hypotheses_were_not_confirmed_as_story_fact":True,
        "independent_literary_quality_verified":False,
    }
    (OUTPUT/"STATUS.json").write_text(
        json.dumps(report,ensure_ascii=False,sort_keys=True,indent=2),
        encoding="utf8")
    print(json.dumps({
        "stage":"AUTHENTIC_G_SOURCE_CROSS_READER_OLD_AUTHOR_MOVE_ON_ZERO_NEW_MODEL",
        "calls":0,"old_author":"MOVE_ON","unproven_cross_source_links":3,
        "still_no_accepted_edit":True,"original_source_sha256":sha(source),
        "raw_original_replies_and_wires_preserved":True,
    },ensure_ascii=False),flush=True)
    return report

if __name__=="__main__":
    run()
