"""V111: FAIR-QUESTION original-model WRITING comparison: WF vs GitHub Skill.

Candidate methods:
  WF: existing AutonomousWriting.run single (its normal chapter plan + prose).
  GITHUB_SKILL: pristine pinned MIT storyteller SKILL.md (text-only install).
  BARE: same DeepSeek Flash, no skill (diagnostic control).

All receive exactly the same user question "给我一个追逐打斗的玄幻1000字".
All finished-prose calls have 2600 max completion tokens. WF uses an extra
650-token plan call; cost/calls are reported separately. No model review,
post-hoc repairs, paid retries, sources, user novels or external examples.

Raw provider HTTP response CAS persisted *before* JSON decode. All successful
decoded responses persisted before WF validation. Blind review packets of
unedited originals are stored separately from secret arm map. Can only
establish performance of WF runtime+base DeepSeek model, NOT that independent
WF literature weights exist or 15 learned chapters transfer.
"""
from __future__ import annotations
import hashlib,json,os,re,secrets
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from writerforge import WriterForgeDB,RuntimeEngine
from writerforge.writing_assist import (
    InvisibleWritingAssist,AutonomousWriting,
)
from writerforge.deepseek_flash_model import (
    DeepSeekFlashModel,FlashBudget,
)
from writerforge.v79_provisional_r2_cas_journal import WFProvisionalR2CASJournal
from writerforge.v104_self_scene_protocol import encode,digest
from experiments.v111_peer.neutral_bridge import fresh_neutral_published_snapshot as fake_but_published_snapshot

EXAM="WF-V111-MATCHED-FANTASY-CHASE-1000-ORIGINAL-20261021"
TASK="给我一个追逐打斗的玄幻1000字"
MODEL="deepseek-flash"
ROLE="self_scene_writing"
ENDPOINT="https://wf-r2-api.3227482831.workers.dev"
PEER_PATH=Path(__file__).resolve().parent/"experiments/v111_peer/storyteller/SKILL.md"
LICENSE_PATH=Path(__file__).resolve().parent/"experiments/v111_peer/storyteller/LICENSE"
PEER_ORIGIN_REPO="xcrrr/claude-skills"
PEER_ORIGIN_COMMIT="145342ceff6318d2f5ffe8f95473fecc8b27d1e9"
PEER_GIT_BLOB="5f5ff537716a36188ef0627a3ded0da40ef1e5e3"
LICENSE_GIT_BLOB="7a28f2d0c34c4542a946e6ded67d8d431efbfa3a"
ARMS=("WF_SINGLE","GITHUB_STORYTELLER","BARE_DEEPSEEK")
MAX_CALLS=4
WF_PLAN_TOKENS=650
PROSE_TOKENS=2600
MAX_RESERVED_TOKENS=WF_PLAN_TOKENS+3*PROSE_TOKENS
MAX_TOTAL_CONSERVATIVE=150000
MAX_WIRE_BYTES=230000
MAX_PROSE_BYTES=30000
CHAR_TARGET=1000
CHAR_LOW=900
CHAR_HIGH=1100

def tell(o):
    print(json.dumps(o,ensure_ascii=False,sort_keys=True,
                     separators=(",",":"),allow_nan=False),flush=True)

def need(v,code):
    if not v:raise ValueError(code)

def blob_hash(content):
    return hashlib.sha1(b"blob "+str(len(content)).encode("ascii")+
                        b"\x00"+content).hexdigest()

def skill_original():
    content=PEER_PATH.read_bytes()
    rights=LICENSE_PATH.read_bytes()
    need(blob_hash(content)==PEER_GIT_BLOB and
         blob_hash(rights)==LICENSE_GIT_BLOB and
         b"MIT License" in rights and
         b"name: storyteller" in content[:500] and
         len(content)<=20000,
         "WF111_PINNED_GITHUB_STORYTELLER_SOURCE_MISMATCH")
    return content.decode("utf8","strict"),rights.decode("utf8","strict")

def user_question():
    # Identical direct question for every model invocation. Do NOT supply a
    # pre-written scenario, protagonist, fight moves, ending or plot answer.
    return TASK

def common_prose_instruction():
    return (
        "你是中文小说写作者。请直接给出完整原创小说正文，不解释技巧、不评分、"
        "不提模型、不给出文外说明。目标1000个中文含标点字符，允许追逐打斗和"
        "角色自己决定的玄幻力量规则。所写人物、地点、招式、后果均由你独立创造。"
        "只返回严格JSON对象且恰好一个字段prose，其值是完整正文。"
        "不得附加角色表、审稿、自我打分、修订稿。"
    )

def peer_system(source):
    # External instructions apply ONLY to the isolated peer arm.
    return (common_prose_instruction()+
            "\n【本实验唯一安装的第三方GitHub写作Skill，以下原文按其创作指导使用】\n"+
            source+
            "\n【输出合同优先】最终只返回JSON的prose，不输出Skill自身的例文"
            "或Craft notes，不能运行任何外部命令或读取更多Skill文件。")

def bare_system():
    return common_prose_instruction()

def freeze(skill_bytes):
    return {
        "format":"wf.eval.v111.fantasy-chase.preregistered",
        "experiment":EXAM,
        "exact_common_user_question":TASK,
        "same_model":MODEL,
        "provider":"official_deepseek",
        "provider_alias_change_not_independently_verified":True,
        "source_branch":"v111-matched-fantasy-chase-wf-vs-github-skill",
        "external_skill_repository":PEER_ORIGIN_REPO,
        "external_skill_commit":PEER_ORIGIN_COMMIT,
        "external_skill_github_blob_sha1":PEER_GIT_BLOB,
        "external_license_github_blob_sha1":LICENSE_GIT_BLOB,
        "external_skill_sha256":digest(skill_bytes.encode("utf8")),
        "externally_installed_skill_text_only_not_executed":True,
        "peer_skill_isolated_from_WF_writing":True,
        "arm_order_before_first_request":list(ARMS),
        "one_question_three_arms":True,
        "WF_actual_codepath":"AutonomousWriting.single",
        "WF_neutral_fixture_not_15_authored_chapters":True,
        "same_max_prose_tokens_each_arm":PROSE_TOKENS,
        "WF_extra_plan_call_tokens":WF_PLAN_TOKENS,
        "max_provider_calls":MAX_CALLS,
        "max_reserved_output_tokens":MAX_RESERVED_TOKENS,
        "max_conservative_total_tokens":MAX_TOTAL_CONSERVATIVE,
        "target_codepoints_including_punctuation":CHAR_TARGET,
        "comparable_per_arm_range":[CHAR_LOW,CHAR_HIGH],
        "max_relative_length_gap":0.10,
        "no_auto_retry_no_cropping_no_postprocessing":True,
        "original_wire_before_JSON_decode":True,
        "raw_model_response_before_WF_validation":True,
        "third_party_judge_model_calls":0,
        "author_accepted":False,
        "literary_grade":"UNDETERMINED",
        "real_15_chapter_history_unchanged":True,
        "v49_failed_preserved":True,
        "literary_window":"LOCKED",
    }

def verify_r2(cas,sha):
    need(type(sha) is str and re.fullmatch(r"[0-9a-f]{64}",sha),
         "WF111_CAS_SHA_NOT_VALID")
    b=cas._get_content(sha)
    need(digest(b)==sha,"WF111_PRIVATE_CAS_REMOTE_CORRUPTED")
    return b

def seal(cas,payload,code):
    need(type(payload) is bytes and 0<len(payload)<=250000,
         "WF111_PRIVATE_R2_BLOB_TOO_BIG")
    sha,_=cas._put_content(payload)
    need(verify_r2(cas,sha)==payload,code)
    return sha

def prose_observation(answer):
    if type(answer) is not dict or set(answer)!={"prose"} or type(answer["prose"]) is not str:
        return {"status":"PROSE_JSON_SCHEMA_FAILED",
                "actual_codepoints":None,"actual_han_chars":None,
                "body_sha256":None,"raw_prose":None}
    txt=answer["prose"]
    need(len(txt.encode("utf8"))<=MAX_PROSE_BYTES,
         "WF111_MODEL_ORIGINAL_PROSE_BYTES_LIMIT")
    return {
        "status":("LENGTH_WITHIN_TARGET" if CHAR_LOW<=len(txt)<=CHAR_HIGH
                  else "LENGTH_OFF_TARGET"),
        "actual_codepoints":len(txt),
        "actual_han_chars":sum(
            "\u4e00"<=char<="\u9fff" for char in txt),
        "body_sha256":digest(txt.encode("utf8")),
        "raw_prose":txt,
    }

def run():
    need(all(os.environ.get(k) for k in
             ("DEEPSEEK_API_KEY","WF_API_TOKEN","WF_INDEX_UPLOAD_TOKEN")),
         "WF111_EXISTING_THREE_API_CREDENTIALS_REQUIRED")
    skill,license_text=skill_original()
    cas=WFProvisionalR2CASJournal(endpoint=ENDPOINT)
    cas.require_writer_ready()
    original=encode(freeze(skill))
    psha,created=cas._put_content(original)
    need(created is True and psha==digest(original) and
         verify_r2(cas,psha)==original,
         "WF111_ONCE_ONLY_PRECOMMIT_REFUSES_DOUBLE_BILL")
    budget=FlashBudget(max_calls=MAX_CALLS,
                       max_reserved_output_tokens=MAX_RESERVED_TOKENS,
                       max_total_tokens=MAX_TOTAL_CONSERVATIVE)
    phase={"id":0,"stage":None,"wire":None,"attempt":None}
    receipts=[]
    arm_summaries=[]
    prose_by_arm={}
    def on_response_wire(raw):
        need(type(raw) is bytes and 0<len(raw)<=MAX_WIRE_BYTES,
             "WF111_RECEIVED_PROVIDER_WIRE_TOO_BIG_TO_SEAL")
        need(phase["attempt"] and phase["wire"] is None,
             "WF111_UNEXPECTED_DUPLICATE_PROVIDER_WIRE")
        sha=seal(cas,raw,"WF111_PROVIDER_WIRE_PRIVATE_READBACK_FAILED")
        phase["wire"]=sha
        tell({"status":"WF111_RAW_PROVIDER_WIRE_PRIVATE_SEALED",
              "call_index":phase["id"],"stage":phase["stage"],
              "wire_cas_sha256":sha,"raw_wire_not_public":True})

    model=DeepSeekFlashModel(budget=budget,timeout_seconds=120,
                            on_response_wire=on_response_wire)

    def ask(*,stage,role,system,prompt,out_tokens):
        need(stage in ("WF_CHAPTER_PLAN","WF_PROSE","PEER_PROSE","BARE_PROSE")
             and role==ROLE and type(prompt) is str and 0<len(prompt)<=11000
             and type(system) is str and 10<=len(system)<=22000,
             "WF111_PROVIDER_PROMPT_FORMAT_INVALID")
        new_id=phase["id"]+1
        need(new_id<=MAX_CALLS,"WF111_GLOBAL_CALL_LIMIT")
        identity={
            "format":"wf.eval.v111.one-request-intent",
            "experiment_precommit_sha256":psha,
            "call_index":new_id,"stage":stage,
            "model":MODEL,"max_output_tokens":out_tokens,
            "system_sha256":digest(system.encode("utf8")),
            "user_prompt_sha256":digest(prompt.encode("utf8")),
            "provider":"DeepSeekFlashModel.ask_json",
            "no_auto_retry":True,
        }
        rb=encode(identity)
        adr,one=cas._put_content(rb)
        need(one is True and adr==digest(rb)
             and verify_r2(cas,adr)==rb,
             "WF111_REPEAT_REQUEST_SLOT_NOT_ALLOWED")
        phase.update({"id":new_id,"stage":stage,"wire":None,"attempt":adr})
        tell({"status":"WF111_ATTEMPT_R2_RESERVED_BEFORE_PROVIDER",
              "stage":stage,"call_index":new_id,
              "attempt_cas_sha256":adr,"precommit_sha256":psha})
        try:
            raw=model.ask_json(role=ROLE,system=system,
                               user=prompt,max_tokens=out_tokens)
        except Exception as err:
            safe=str(err)
            if not re.fullmatch("WF_FLASH_[A-Z0-9_]{3,150}",safe):
                safe="WF111_PROVIDER_TRANSPORT_OR_PRIVATE_EVIDENCE_FAILURE"
            receipt={
                "stage":stage,"call_index":new_id,
                "attempt_cas_sha256":adr,
                "wire_cas_sha256":phase["wire"],
                "decoded_cas_sha256":None,
                "status":"FAILED_OR_UNDECODABLE",
                "error_code":safe,
            }
            receipts.append(receipt)
            tell({"status":"WF111_ONE_PROVIDER_REQUEST_FAILED_NO_RETRY",
                  "stage":stage,"call_index":new_id,
                  "wire_cas_sha256":phase["wire"],
                  "error_code":safe})
            raise
        need(phase["wire"] is not None,"WF111_NO_WIRE_RECEIPT_ON_SUCCESS")
        doc=encode({
            "format":"wf.eval.v111.one-unmodified-model-answer",
            "precommit_sha256":psha,
            "request_intent_cas_sha256":adr,
            "provider_wire_cas_sha256":phase["wire"],
            "original_answer":raw,
            "not_manually_corrected":True,
        })
        dec=seal(cas,doc,"WF111_DECODED_JSON_NOT_R2_VERIFIED")
        receipts.append({
            "stage":stage,"call_index":new_id,
            "attempt_cas_sha256":adr,"wire_cas_sha256":phase["wire"],
            "decoded_cas_sha256":dec,"status":"DECODED_NOT_YET_LITERARY_JUDGED",
        })
        tell({"status":"WF111_JSON_PRIVATE_SEALED_BEFORE_VALIDATION",
              "stage":stage,"call_index":new_id,
              "decoded_cas_sha256":dec})
        return raw

    # Existing WF program in the original production SINGLE mode; no
    # borrowed peer skill, previous generated story or author-injected beat.
    with TemporaryDirectory(prefix="wf111-actual-program-") as temporary:
        folder=Path(temporary)
        neutral=folder/"synthetic-published-bridge.sqlite"
        # Only software-compatibility fixture, not real learned WF literature.
        snapshot=fake_but_published_snapshot(neutral)
        db=WriterForgeDB(neutral)
        runtime=RuntimeEngine()
        runtime.enter_write(snapshot)
        ass=InvisibleWritingAssist(db,runtime,"v111-benchmark-only",
            "v111-one-fantasy-chase",TASK,
            model=MODEL,api_base="http://127.0.0.1:1234/v1",
            source_genre="玄幻")
        def wf_transport(packet,*,model,api_base,max_tokens,**kwargs):
            need(model==MODEL and kwargs=={} and
                 packet.project_id=="v111-benchmark-only",
                 "WF111_WF_WRITER_PROVIDER_ISOLATION_BROKEN")
            step=("WF_CHAPTER_PLAN" if phase["id"]==0 else "WF_PROSE")
            expected=(WF_PLAN_TOKENS if step=="WF_CHAPTER_PLAN" else PROSE_TOKENS)
            need(max_tokens==expected,
                 "WF111_WRITER_OFFLINE_CALL_SCHEDULE_CHANGED")
            system=( "你是WriterForge创作流程的原创章计划模型。只依据当前WF提示"
                     "自主组织场景目标、人物冲突与推进。不写正文、不引用外部技能。"
                     "只输出合法JSON对象。"
                     if step=="WF_CHAPTER_PLAN" else
                     common_prose_instruction())
            reply=ask(stage=step,role=ROLE,system=system,
                      prompt=packet.prompt,out_tokens=max_tokens)
            if step=="WF_CHAPTER_PLAN":
                return json.dumps(reply,ensure_ascii=False,
                                  separators=(",",":"))
            observation=prose_observation(reply)
            need(observation["raw_prose"] is not None,
                 "WF111_WF_PROVIDER_PROSE_NOT_SINGLE_JSON")
            return observation["raw_prose"]

        try:
            with patch("writerforge.writing_assist.local_chat_completion",
                       side_effect=wf_transport):
                outcome=AutonomousWriting(ass).run(
                    outline=TASK,chapter_goals=[TASK],
                    output_dir=folder/"candidate-only",
                    draft_mode="single")
            ch=outcome["chapters"][0]
            txt=Path(ch["candidate"]).read_text("utf8")
            body_sha=seal(cas,txt.encode("utf8"),
                          "WF111_WF_UNMODIFIED_ORIGINAL_PROSE_NOT_R2")
            prose_by_arm["WF_SINGLE"]=txt
            arm_summaries.append({
                "arm":"WF_SINGLE","status":"WRITTEN",
                "prose_private_cas_sha256":body_sha,
                "prose_sha256":digest(txt.encode("utf8")),
                "real_codepoints":len(txt),
                "actual_han_chars":sum("\u4e00"<=c<="\u9fff" for c in txt),
                "author_accepted":False,
                "published_source_was_neutral_fixture":True})
        except Exception as err:
            arm_summaries.append({
                "arm":"WF_SINGLE","status":"FAILED",
                "safe_failure":"WF111_WF_GENERATION_OR_STRUCTURE_FAILED",
                "prose_private_cas_sha256":None,
                "no_second_try":True})
            tell({"status":"WF111_WF_ARM_FAILED_NO_RETRY",
                  "raw_decoded_replies_saved":len(receipts)})
        finally:
            n=db.conn.execute("SELECT COUNT(*) FROM accepted_prose").fetchone()[0]
            db.close()
            need(n==0,"WF111_ACCIDENTAL_CANON_WRITE_OR_AUTHOR_ACCEPTANCE")
    # Peer only loads the exact pinned GitHub Skill text; NEVER injected WF.
    for arm in ("GITHUB_STORYTELLER","BARE_DEEPSEEK"):
        if phase["id"]>=MAX_CALLS:
            arm_summaries.append({"arm":arm,"status":"CALL_BUDGET_EXHAUSTED"})
            continue
        system=(peer_system(skill) if arm=="GITHUB_STORYTELLER"
                else bare_system())
        stage="PEER_PROSE" if arm=="GITHUB_STORYTELLER" else "BARE_PROSE"
        try:
            response=ask(stage=stage,role=ROLE,system=system,
                         prompt=user_question(),out_tokens=PROSE_TOKENS)
            observation=prose_observation(response)
            need(observation["raw_prose"] is not None,
                 "WF111_PEER_OR_BASE_MODEL_PROSE_SCHEMA_FAILED")
            txt=observation["raw_prose"]
            ptr=seal(cas,txt.encode("utf8"),
                     "WF111_ORIGINAL_EXTERNAL_ARM_PROSE_NOT_R2")
            prose_by_arm[arm]=txt
            arm_summaries.append({
                "arm":arm,"status":"WRITTEN",
                "prose_private_cas_sha256":ptr,
                "prose_sha256":observation["body_sha256"],
                "real_codepoints":observation["actual_codepoints"],
                "actual_han_chars":observation["actual_han_chars"],
                "author_accepted":False,
            })
        except Exception:
            arm_summaries.append({"arm":arm,"status":"FAILED",
                                  "safe_failure":"WF111_EXTERNAL_ARM_OR_JSON_FAILED",
                                  "no_second_try":True})
            tell({"status":"WF111_EXTERNAL_ARM_FAILED_NO_RETRY",
                  "arm":arm,"raw_request_receipts_saved":len(receipts)})
    # Anonymous full-text packets are separated from owner arm map.
    # Reviewers cannot see the model arm, skill name, plan request count or
    # software test results in a packet.
    available=[(a,prose_by_arm[a]) for a in ARMS if a in prose_by_arm]
    shuffled=list(available)
    secrets.SystemRandom().shuffle(shuffled)
    blinded=[]
    mapping=[]
    for index,(arm,body) in enumerate(shuffled,1):
        label=f"匿名作品{index:02d}"
        data={
            "format":"wf.eval.v111.anonymous-original-novel",
            "label":label,
            "shared_task":TASK,
            "prose":body,
            "literary_quality_judged":"NOT_PERFORMED",
        }
        sha=seal(cas,encode(data),
                 "WF111_ANON_ORIGINAL_PROSE_NOT_COLD_READABLE")
        blinded.append({"label":label,"full_prose_cas_sha256":sha})
        mapping.append({
            "label":label,"arm":arm,"length":len(body),
            "prose_sha256":digest(body.encode("utf8")),
            "blind_packet_cas_sha256":sha,
        })
    judge={
        "format":"wf.eval.v111.blind-original-fantasy-review-index",
        "question":TASK,"packets":blinded,
        "judging_stage":"NOT_PERFORMED",
        "review_dims":["空间移动与追逐连续性","攻击与防御的可执行因果",
                       "玄幻力量规则和能力限制","人物目标与临场选择",
                       "真实代价和后续作用","自然语言节奏与玄幻意象"],
        "blind_method_identity_hidden":True,
    }
    judge_sha=seal(cas,encode(judge),
                   "WF111_PRIVATE_BLIND_READER_INDEX_NOT_RECOVERABLE")
    private_owner={
        "format":"wf.eval.v111.owner-only-method-unblind",
        "blind_index_cas_sha256":judge_sha,
        "mapping":mapping,
        "unblind_after_review_only":True,
        "method_identity_not_in_judge_packets":True,
    }
    owner_sha=seal(cas,encode(private_owner),
                   "WF111_OWNER_ONLY_METHOD_MAP_NOT_R2")
    lengths=[len(x) for x in prose_by_arm.values()]
    gap=(max(lengths)-min(lengths))/max(lengths) if len(lengths)>=2 else None
    eligible=(len(lengths)==3 and
              all(CHAR_LOW<=v<=CHAR_HIGH for v in lengths) and gap<=0.1)
    result={
        "format":"wf.eval.v111.three-arm-original-model-experiment",
        "precommit_cas_sha256":psha,
        "original_pinned_github_skill_sha256":digest(skill.encode("utf8")),
        "original_skill_path":"experiments/v111_peer/storyteller/SKILL.md",
        "raw_provider_request_receipts":receipts,
        "arms":arm_summaries,
        "independent_blind_review_index_cas_sha256":judge_sha,
        "owner_only_unblind_map_cas_sha256":owner_sha,
        "all_three_prose_length_comparable":eligible,
        "max_relative_length_gap":gap,
        "model_request_count":budget.calls_reserved,
        "provider_usage":budget.public_receipt(),
        "WF_actual_literary_learning_proven":False,
        "model_weights_equal_by_alias_not_cryptographically_verified":True,
        "no_external_judge_model_calls":True,
        "no_auto_retry_or_llm_rewrite":True,
        "original_fifteen_training_chapters_touched":0,
        "old_failed_record_changed":False,
        "qualified_literary_winner":"UNDETERMINED",
    }
    msha=seal(cas,encode(result),"WF111_MANIFEST_PRIVATE_R2_NOT_VERIFIED")
    tell({
        "status":"WF111_WF_VS_GITHUB_STORYTELLER_VS_BASE_ALL_RECEIPTS_SEALED",
        "manifest_cas_sha256":msha,
        "blind_original_index_cas_sha256":judge_sha,
        "owner_only_unblind_cas_sha256":owner_sha,
        "common_user_task":TASK,
        "model":MODEL,
        "actual_paid_model_requests":budget.calls_reserved,
        "reported_prompt_tokens":budget.prompt_tokens_reported,
        "reported_completion_tokens":budget.completion_tokens_reported,
        "arm_completion_status":[{"arm":v["arm"],
                                  "status":v["status"],
                                  "length":v.get("real_codepoints")}
                                 for v in arm_summaries],
        "three_way_length_eligible":eligible,
        "actual_literary_human_review":"NOT_PERFORMED",
        "skill_not_installed_in_WF_runtime":True,
        "original_WF_learned_skill_not_proven":True,
        "newly_trained_chapters":0,
        "no_future_paid_automatic_retries":True,
    })
    return 0

if __name__=="__main__":
    tell({"status":"WF111_THREE_ARM_REAL_WRITING_START",
          "external_skill_only_standalone_peer":True,
          "user_exact_question":TASK,"max_paid_calls":MAX_CALLS,
          "no_auto_retries":True})
    try:rc=run()
    except Exception as ex:
        msg=str(ex)
        if not re.fullmatch(
             r"(?:WF111|WF_FLASH|WF105|WF96|WF102|WF_V79|WF_INDEX)_[A-Z0-9_]{1,150}",
             msg):
            msg="WF111_STOPPED_UNCLASSIFIED_NO_RETRY"
        tell({"status":"WF111_REAL_WRITING_ABORTED_NO_RETRY",
              "safe_error_code":msg,
              "private_originals_not_replaced":True})
        rc=1
    tell({"status":"WF111_EXPERIMENT_EXIT","code":rc})
    raise SystemExit(rc)
