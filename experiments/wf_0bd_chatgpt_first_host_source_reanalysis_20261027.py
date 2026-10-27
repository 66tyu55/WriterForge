"""WF 0.BD: one ChatGPT-authored, source-locked SHADOW hypothesis, zero APIs.

A conversational GPT-6 reply was authored while reading the immutable
0.AY DeepSeek originals; it has NO independently authenticated ChatGPT wire.
Thus this is a real externally proposed *hypothesis*, not a certified new
model call, accepted literary gain, or an activated production Skill.

Reads the frozen historical Actions artifact; never regenerates/writes back
the originals. Only SHA observations and a separate non-executable candidate
are written. GLM's original 429 remains frozen and the old 0.AY experiment
is neither retried nor reclassified.
"""
from __future__ import annotations

from dataclasses import replace
from hashlib import sha256
from pathlib import Path
from difflib import SequenceMatcher
import hmac
import json

from writerforge.db import WriterForgeDB
from writerforge.evolution import (
    FirstHostNutrientLoop, HostNutrientObservation, PortableHabitCandidatePool
)

ROOT = Path(".agents/skills/observe-before-next-choice/capsule.json")
FROZEN = Path("experiments/wf_0ay_portable_habit_fresh_cross_host_fixtures_20261026.json")
ORIGINAL = Path("wf0ay_real_two_hosts_partial_source")
PROPOSAL = Path("experiments/wf_0bd_chatgpt_first_host_cognitive_proposal_20261027.json")
OUTPUT = Path("wf0bd_conversational_first_host_nutrient_source_locked_20261027")

ARCHIVED_RUN = 40354436598
ARCHIVED_ARTIFACT = 12664209371
ROOT_SHA = "42cad98118dea662cea472f708ef1de22f4bb139da3210b1f5c3c1f9ac12664d"
FROZEN_SHA = "aa16fa7696440b86a942ddd2d4071dd8d13a6b6ad561c3456a841e700bb76373"
REAL_WIRE_SHAS = {
    "control": "daa44c87493e5329b949d178a99eea00817ce8901b07b3525d1c4cbcb8ea4810",
    "habit": "81827cf112daf0241c085726c989bf44a5e086b250bd66dc8823fa54a0ec5e17",
}
REAL_PROSE_SHAS = {
    "control": "8faf6aa520f8f9da6662fc9572ed70257d9e350cc575320b8bddfc3686c565bb",
    "habit": "d64effd386c661bd6d63575b06b7641397223eb8dbf69c6aed650d3bfbd04c6b",
}
PROPOSAL_OBSERVATION_IDS = ("obs0bd-deepseek-control", "obs0bd-deepseek-habit")
OBSERVATION_KEY = b"wf0bd-synthetic-forensic-attester-NOT-an-external-model-key"
POOL_LOCAL_KEY = b"wf0bd-synthetic-local-only-reviewer-verifier"
NO_REAL_HELDOUT_PIN = sha256(
    b"0bd-NO-INDEPENDENT-HELDOUT-OR-LITERARY-EVALUATION").hexdigest()


def canonical(obj) -> bytes:
    return json.dumps(
        obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
        allow_nan=False
    ).encode("utf-8")


def digest(b: bytes) -> str:
    return sha256(b).hexdigest()


def need(condition, code):
    if not condition:
        raise ValueError(code)


def read_json(path: Path):
    return json.loads(path.read_text("utf-8"))


def _source_locked() -> tuple[bytes, dict, dict, dict]:
    """Return verified original source plus two actual independent WRITER replies.

    Does not claim the ChatGPT meta proposal's wire has been authenticated.
    """
    root = ROOT.read_bytes()
    need(digest(root) == ROOT_SHA, "WF0BD_ORIGINAL_SHADOW_ROOT_CHANGED")
    original_status = read_json(ORIGINAL/"STATUS.json")
    need(original_status.get("status") ==
         "SAFE_PARTIAL_TWO_HOST_CROSS_TRANSFER_NO_RETRIES" and
         original_status.get("failure_code") ==
         "WF0AY_SECOND_HOST_HTTP_429" and
         original_status.get("model_calls") == 4 and
         len(original_status.get("completed", [])) == 3 and
         original_status.get("habit_still_shadow") is True and
         original_status.get("literary_quality_proven") is False,
         "WF0BD_REAL_0AY_HOST_RESOURCE_HISTORY_CHANGED")
    missing = (ORIGINAL/"original-provider-wires"/"discovery"/
               "flood-radio-habit.json")
    need(not missing.exists(),
         "WF0BD_FORBIDDEN_GLMMODEL_429_RESPONSE_FABRICATED")
    need(digest(FROZEN.read_bytes()) == FROZEN_SHA,
         "WF0BD_FROZEN_HISTORICAL_TASK_CHANGED")
    task = read_json(ORIGINAL/"frozen-new-tasks"/"flood-radio.json")
    need(task["task_id"] == "flood-radio" and
         len(task["prior_prose"]) == 2 and
         all(digest(row["prose"].encode("utf-8")) == row["sha256"]
             for row in task["prior_prose"]),
         "WF0BD_PREVIOUS_WRITTEN_SOURCE_NOT_AUTHENTIC")
    old_task = next(x for x in read_json(FROZEN)["tasks"]
                    if x["task_id"] == "flood-radio")
    need(task == old_task, "WF0BD_ARCHIVED_TASK_NOT_MATCHING_FROZEN_SOURCE")
    result = {}
    for arm in ("control", "habit"):
        wire = (ORIGINAL/"original-provider-wires"/"deepseek"/
                f"flood-radio-{arm}.json").read_bytes()
        need(digest(wire) == REAL_WIRE_SHAS[arm],
             "WF0BD_SOURCE_PROVIDER_WIRE_SHA_MISMATCH")
        payload = json.loads(wire)
        need(payload.get("model") == "deepseek-flash" and
             payload["choices"][0]["finish_reason"] == "stop",
             "WF0BD_SOURCE_WRITER_MODEL_INVALID")
        completion = json.loads(payload["choices"][0]["message"]["content"])
        need(set(completion) == {"prose", "chosen_step", "still_unknown"} and
             type(completion["prose"]) is str and
             digest(completion["prose"].encode("utf-8")) == REAL_PROSE_SHAS[arm],
             "WF0BD_REAL_WRITER_PROSE_CHANGED")
        unaccepted = read_json(
            ORIGINAL/"authored-unaccepted-fiction"/"deepseek"/
            "flood-radio"/f"{arm}.json")
        need(unaccepted["prose"] == completion["prose"] and
             unaccepted["chosen_step"] == completion["chosen_step"] and
             unaccepted["still_unknown"] == completion["still_unknown"] and
             unaccepted["literary_quality_proven"] is False,
             "WF0BD_MODEL_DECISION_OR_QUALITY_WAS_REWRITTEN")
        request = read_json(
            ORIGINAL/"requests"/"deepseek"/"flood-radio"/f"{arm}.json")
        envelope = canonical(request["actual_provider_input_envelope"])
        need(digest(envelope) == request["input_envelope_sha256"] and
             request["model"] == "deepseek-flash" and
             request["model_max_completion_tokens"] == 1800,
             "WF0BD_ARCHIVED_PROVIDER_REQUEST_CHANGED")
        result[arm] = {"request":envelope, "wire":wire, "result":completion}
    return root,task,result,original_status


def _validate_conversational_meta(
    record: dict, *, source_window: dict[str, bytes],
    expected_observation_ids: tuple[str,str],
) -> tuple[dict, bytes]:
    """The spoken GPT-6 output is not a fake provider-authenticated wire."""
    need(type(record) is dict and set(record) == {
        "format", "source_origin", "meta_proposal_origin",
        "proposal", "inference_limits",
    }, "WF0BD_CHAT_PROPOSAL_ENVELOPE_INVALID")
    src = record["source_origin"]
    orig = record["meta_proposal_origin"]
    policy = record["inference_limits"]
    need(record["format"] ==
         "wf.0bd.conversational-host-proposal-source-bound.v1" and
         src["historical_run_id"] == ARCHIVED_RUN and
         src["historical_artifact_id"] == ARCHIVED_ARTIFACT and
         src["source_writer_host_id"] == "deepseek" and
         src["source_writer_model_id"] == "deepseek-flash" and
         src["source_task_id"] == "flood-radio" and
         src["source_control_wire_sha256"] == REAL_WIRE_SHAS["control"] and
         src["source_habit_wire_sha256"] == REAL_WIRE_SHAS["habit"] and
         src["frozen_source_sha256"] == FROZEN_SHA and
         src["absent_glm_habit_wire"] is True,
         "WF0BD_META_PROPOSAL_HISTORICAL_SOURCES_NOT_PINNED")
    need(orig.get("actual_chat_model_contribution") is True and
         orig.get("verified_meta_provider_wire_sha256") is None and
         orig.get("trusted_host_signed_completion") is False and
         orig.get("paid_external_provider_calls_in_replay") == 0 and
         orig.get("independent_evaluator_approved") is False,
         "WF0BD_UNVERIFIED_CHAT_WIRE_MISREPRESENTED")
    need(policy["expected_status"] ==
         "SHADOW_NEEDS_INDEPENDENT_EVIDENCE" and
         policy["meta_reply_self_attributed_but_not_provider_authenticated"]
         is True and
         policy["independent_literary_gain_proven"] is False and
         policy["new_external_api_calls_authorized"] == 0 and
         policy["trial_0ay_dormant_preserved"] is True and
         policy["no_canon_or_r2_writes"] is True,
         "WF0BD_UNTRUSTED_PROPOSAL_CLAIMS_PROGRESS_OR_AUTHORITY")
    proposed = record["proposal"]
    need(type(proposed) is dict and set(proposed) == {
        "format", "task_id", "source_observation_ids", "target_skill",
        "parent_capsule_sha256", "procedure_index",
        "procedure_replacement", "falsifier_index",
        "falsifier_replacement", "reason",
    }, "WF0BD_META_PROPOSAL_FIELDS_INVALID")
    need(proposed["format"] == "wf.host-nutrient-proposal.v1" and
         proposed["task_id"] == "flood-radio" and
         proposed["source_observation_ids"] == list(expected_observation_ids) and
         proposed["parent_capsule_sha256"] == ROOT_SHA and
         proposed["target_skill"] == "observe-before-next-choice" and
         proposed["procedure_index"] == 1 and
         proposed["falsifier_index"] == 0 and
         type(proposed["reason"]) is str and
         25 <= len(proposed["reason"]) <= 450,
         "WF0BD_META_PROPOSAL_CAUSAL_BINDING_INVALID")
    for field in ("procedure_replacement", "falsifier_replacement"):
        string = proposed[field]
        need(type(string) is str and 35 <= len(string) <= 450,
             "WF0BD_META_PROPOSAL_SIZE_INVALID")
        for raw in source_window.values():
            old = raw.decode("utf-8", "strict")
            hit = SequenceMatcher(None,string,old,autojunk=False).find_longest_match(
                0,len(string),0,len(old))
            need(hit.size < 18,
                 "WF0BD_COPIED_HOST_STORY_IN_COGNITIVE_SKILL")
    return proposed,canonical(proposed)


def run(*, output: Path=OUTPUT, write_files: bool=True) -> dict:
    """No model endpoints; source-locked current-chat proposal -> SHADOW only."""
    need(not output.exists(), "WF0BD_NEVER_OVERWRITE_PREVIOUS_NUTRIENTS")
    root,task,results,status = _source_locked()
    document=read_json(PROPOSAL)
    source = canonical(task["prior_prose"])
    source_window = {
        "source":source,
        "control":results["control"]["result"]["prose"].encode("utf-8"),
        "habit":results["habit"]["result"]["prose"].encode("utf-8"),
    }
    proposed,proposal_bytes = _validate_conversational_meta(
        document,source_window=source_window,
        expected_observation_ids=PROPOSAL_OBSERVATION_IDS)

    # GitHub is the source authority only for archival writer bytes. The
    # meta-proposal is a new conversational, NON-provider-authenticated reply.
    # Never set the source-writer host to "chatgpt" or pretend DeepSeek wrote
    # the proposal. Writer source host and meta author have different roles.
    output.mkdir(parents=True, exist_ok=False)
    db=WriterForgeDB(output/"first_host_source_sha_only.sqlite")
    try:
        pool=PortableHabitCandidatePool(
            pinned_roots={ROOT_SHA:root},
            reviewer_verifier_key=POOL_LOCAL_KEY,
            frozen_heldout_sha256=NO_REAL_HELDOUT_PIN)
        loop=FirstHostNutrientLoop(
            db=db,scope="wf0bd-source-only",
            verifier_key=OBSERVATION_KEY,
            root_capsule_bytes=root,
            expected_capsule_sha256=ROOT_SHA,
            candidate_pool=pool)

        for arm,obs_id in zip(("control","habit"),PROPOSAL_OBSERVATION_IDS):
            row = results[arm]
            receipt = HostNutrientObservation(
                observation_id=obs_id,
                experiment_id="wf0bd-source-reanalysis",
                host_id="deepseek",
                model_id="deepseek-flash",
                task_id="flood-radio",arm=arm,
                source_sha256=digest(source),
                request_sha256=digest(row["request"]),
                provider_wire_sha256=digest(row["wire"]),
                prose_sha256=digest(source_window[arm]),
                status="SUCCESS", failure_code=None,
                verification_origin="archived_provider_wire",
                signature="")
            receipt=replace(receipt,signature=hmac.new(
                OBSERVATION_KEY,canonical(receipt.signing_payload()),
                "sha256").hexdigest())
            loop.ingest(
                receipt,source_bytes=source,request_bytes=row["request"],
                provider_wire_bytes=row["wire"],
                authored_prose_bytes=source_window[arm])
        need(loop.disposition("wf0bd-source-reanalysis")["verified_successes"]==2,
             "WF0BD_NOT_VERIFIED_SOURCE_PAIR")

        # ChatGPT's authored proposal is used as UNTRUSTED DATA, not a model
        # callback or extra paid call. This is NOT the acquire_once() route:
        # it cannot manufacture a new provider-wire or charge host resource.
        old = json.loads(root.decode("utf-8"))
        new = json.loads(root.decode("utf-8"))
        new["revision"]+=1
        new["procedure"][1]=proposed["procedure_replacement"]
        new["falsifiers"][0]=proposed["falsifier_replacement"]
        capsule=canonical(new)
        evidence = {
            "original_run":ARCHIVED_RUN,
            "original_artifact":ARCHIVED_ARTIFACT,
            "original_source_host":"deepseek",
            "archived_writer_provider_wire_sha256s":
                [REAL_WIRE_SHAS["control"],REAL_WIRE_SHAS["habit"]],
            "source_observation_ids": list(PROPOSAL_OBSERVATION_IDS),
            "meta_author":"GPT-6 ChatGPT conversational model",
            "meta_provider_wire_verified":False,
            "chat_proposal_document_sha256":digest(PROPOSAL.read_bytes()),
            "chat_proposal_struct_sha256":digest(proposal_bytes),
            "zero_new_provider_requests":True,
            "independent_literary_evidence":False,
        }
        evidence_sha=digest(canonical(evidence))
        candidate=pool.propose(
            proposer_skill="chatgpt-interactive",
            target_skill="observe-before-next-choice",
            parent_sha256=ROOT_SHA,
            candidate_bytes=capsule,evidence_sha256=evidence_sha,
            proposal_id="chatgpt-radio-outcome-stages")
        need(candidate.changed_fields == ("falsifiers","procedure") and
             pool.status(candidate.candidate_sha256) == "SHADOW",
             "WF0BD_NO_VERIFIED_CANDIDATE_MUTATION")
        manifest=pool.export_manifest()
        manifest_raw=canonical(manifest)
        saved_sha=digest(manifest_raw)
        # Demonstrate reconstruction WITHOUT the conversational model,
        # without source prose and without the historical provider-wire.
        recovered=PortableHabitCandidatePool.from_manifest(
            manifest,pinned_roots={ROOT_SHA:root},
            reviewer_verifier_key=POOL_LOCAL_KEY,
            frozen_heldout_sha256=NO_REAL_HELDOUT_PIN,
            expected_manifest_sha256=saved_sha)
        need(recovered.export_candidate(candidate.candidate_sha256)
             ["capsule_utf8"].encode("utf-8") == capsule,
             "WF0BD_HOST_EXIT_CANDIDATE_LOST")
        need(digest(root)==ROOT_SHA and
             old["lifecycle"]==new["lifecycle"]=="SHADOW" and
             new["authority"]==old["authority"] and
             new["provenance"]==old["provenance"] and
             new["stopping"]==old["stopping"],
             "WF0BD_FORBIDDEN_POLICY_OR_ARCHIVED_ROOT_MUTATION")

        summary={
            "format":"wf.0bd.first-host-conversational-hypothesis.v1",
            "status":"SOURCE_VERIFIED_CHAT_PROPOSAL_SHADOW_UNGRADED",
            "source_writer_host":"deepseek",
            "source_model":"deepseek-flash",
            "source_original_run":ARCHIVED_RUN,
            "original_experiment_state":"DORMANT_HOST_RESOURCE_UNCHANGED",
            "source_pair_original_wires_verified":2,
            "source_observation_ids":list(PROPOSAL_OBSERVATION_IDS),
            "chatgpt_meta_reply_authenticated_provider_wire":False,
            "proposal_author_kind":"INTERACTIVE_CHATGPT_SELF_ATTRIBUTED",
            "chatgpt_meta_proposal_sha256":digest(proposal_bytes),
            "candidate_sha256":candidate.candidate_sha256,
            "parent_capsule_sha256":ROOT_SHA,
            "manifest_sha256":saved_sha,
            "candidate_state":"SHADOW",
            "candidate_reopened_without_host":True,
            "original_v1_unchanged":True,
            "new_paid_provider_calls":0,
            "replayed_host_model_callbacks":0,
            "new_literary_draft_calls":0,
            "independent_literary_evidence":False,
            "quality_improvement_proven":False,
            "cross_agent_execution_proven":False,
            "host_permission_to_activate":False,
            "actual_independent_heldout_suite":False,
            "novel_or_canon_writes":0,
            "r2_reads_or_writes":0,
            "evidence_sha256":evidence_sha,
        }
        if write_files:
            (output/"source_evidence_sha_only.json").write_text(
                json.dumps(evidence,ensure_ascii=False,indent=2)+"\n",
                encoding="utf-8")
            (output/"source_bound_candidate_capsule.json").write_bytes(capsule)
            (output/"portable_manifest.json").write_bytes(manifest_raw)
            (output/"STATUS.json").write_text(
                json.dumps(summary,ensure_ascii=False,indent=2)+"\n",
                encoding="utf-8")
        print("WF0BD_CONVERSATIONAL_HOST_NUTRIENT "+json.dumps({
            k:summary[k] for k in (
                "status","source_pair_original_wires_verified",
                "candidate_sha256","candidate_state",
                "new_paid_provider_calls","quality_improvement_proven",
                "original_experiment_state")},sort_keys=True),flush=True)
        return summary
    finally:
        db.close()


if __name__=="__main__":
    run()
