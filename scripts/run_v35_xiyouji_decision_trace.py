"""V35 genuine 《西遊記》 reader -> insight -> exam plan -> draft -> postmortem.

Every stage is separately persisted and fresh-GET verified in private R2.
The exam question is not disclosed before reader insights have been
independently committed. Prewriting decision records precede the actual
manuscript; post hoc explanations NEVER replace those records. These explicit
model outputs are NOT the model's hidden internal reasoning.

Complete human-readable texts are retained in PRIVATE R2 as requested.
R2 is access-controlled but these records are NOT separately client AES
encrypted unless the storage provider does so at rest. Nothing leaks to
GitHub or workflow logs.
"""
from __future__ import annotations
from pathlib import Path
from tempfile import TemporaryDirectory
from hashlib import sha256
import json,os,re,sys

from writerforge.r2_storage import R2Config,R2StudyVault,_canonical
from writerforge.source_study import parse_original
from writerforge.reverse_discovery_models import DiscoveryCallBudget,DiscoveryModel,DiscoveryError
from writerforge.v35_xiyouji_exam import task,manifest,manifest_sha
from writerforge.v35_observable_trace import (
    validate_read,validate_lessons,validate_plan,validate_draft,
    validate_after,TraceContractError,sha,canonical,
)

ROOT="writerforge/v1/examiner/v35-xiyouji-observable-prewriting"
SESSION="20261017-xiyouji-first-real-reading-prewrite-locked-v1"
STAGES=("00-original-source","01-first-reading","02-learned-craft",
        "03-frozen-prewriting-decisions","04-original-first-draft",
        "05-length-correction","06-after-draft-audit","07-examiner-consistency")
CAP=45000
SOURCE_LIMIT=2000

class SessionError(ValueError):pass

def stage_key(index:int)->str:
    if type(index) is not int or not 0<=index<len(STAGES):
        raise SessionError("STAGE_NUMBER_INVALID")
    return f"{ROOT}/{SESSION}/{index:02d}-{STAGES[index]}.json"

def restore_stage(vault,index:int,previous_sha:str|None=None)->tuple[dict,str]|None:
    key=stage_key(index)
    if vault._head(key) is None:return None
    content=vault._get_small(key,CAP)
    digest=sha(content)
    obj=json.loads(content)
    if (obj.get("format")!="writerforge.v35-observable-stage.v1"
        or obj.get("index")!=index
        or obj.get("session")!=SESSION
        or obj.get("parent_sha256")!=previous_sha):
        raise SessionError("STAGE_PARENT_OR_ID_INTEGRITY_FAILED")
    return obj,digest

def save_stage(vault,index,detail,previous_sha):
    if restore_stage(vault,index,previous_sha) is not None:
        raise SessionError("STAGE_ALREADY_COMMITTED")
    envelope={
        "format":"writerforge.v35-observable-stage.v1",
        "index":index,"session":SESSION,"label":STAGES[index],
        "parent_sha256":previous_sha,"payload":detail,
        "full_explicit_stage_record_saved":True,
        "hidden_internal_reasoning_not_claimed":True,
        "formal_skill_promoted":False,
    }
    content=canonical(envelope)
    if len(content)>CAP:raise SessionError("STAGE_OVER_45KB")
    h=sha(content)
    vault._put_small_immutable(stage_key(index),content,h)
    returned=restore_stage(vault,index,previous_sha)
    if returned is None or returned[1]!=h:
        raise SessionError("STAGE_R2_FRESH_GET_INTEGRITY_FAILURE")
    return returned

def save_unvalidated_output(vault,target_stage:int,response,parent_sha:str|None):
    """Private, immutable raw model reply BEFORE judging it; never a skill."""
    if type(target_stage) is not int or not 1<=target_stage<=6:
        raise SessionError("INVALID_RAW_ATTEMPT_STAGE")
    record={
        "format":"writerforge.v35-model-output-before-validation.v1",
        "session":SESSION,"target_stage":target_stage,
        "parent_valid_stage_sha256":parent_sha,
        "model_explicit_response":response,
        "grammar_or_semantic_validity_not_assumed":True,
        "do_not_promote_from_raw_attempt":True,
        "hidden_reasoning_not_claimed":True,
    }
    blob=canonical(record)
    if len(blob)>CAP:
        raise SessionError("RAW_ATTEMPT_EXCEEDS_PRIVATE_R2_LIMIT")
    h=sha(blob)
    key=f"{ROOT}/{SESSION}/unvalidated/stage-{target_stage}/{h}.json"
    vault._put_small_immutable(key,blob,h)
    if vault._get_small(key,CAP)!=blob:
        raise SessionError("RAW_ATTEMPT_R2_READBACK_FAILED")
    return h

def _request_models(token,budget):
    return {
        "reader":DiscoveryModel(
            name="deepseek-v4-flash-0731",role="planner",api_key=token,budget=budget),
        "writer":DiscoveryModel(
            name="glm-5.3",role="writer",api_key=token,budget=budget,reasoning_effort="low"),
    }

def _keep_safe_failure(error):
    code=str(error)
    if (not isinstance(error,(SessionError,TraceContractError,DiscoveryError,ValueError))
        or len(code)>95 or not re.fullmatch("[A-Z0-9_]{3,95}",code)):
        return type(error).__name__
    return code

def run(vault,models_factory):
    if vault.config.bucket!="writerforge-private-library":
        raise SessionError("PRIVATE_R2_BUCKET_MANDATORY")
    prev=None
    for index in range(len(STAGES)):
        current=restore_stage(vault,index,prev)
        if current is None:break
        prev=current[1]
    else:
        return audit(vault)

    # A previously STARTED pilot may not silently replay paid model calls.
    started=f"{ROOT}/{SESSION}/started.json"
    if vault._head(started) is not None:
        raise SessionError("PREVIOUS_V35_ATTEMPT_CANNOT_BE_RECHARGED")
    claim=canonical({"session":SESSION,"exam_manifest_sha256":manifest_sha(),
                     "one_model_experiment_only":True})
    vault._put_small_immutable(started,claim,sha(claim))
    budget=DiscoveryCallBudget(max_calls=8,max_reserved_output_tokens=50000)
    reader,writer=models_factory(budget)
    last_index=-1
    parent=None
    try:
        with TemporaryDirectory(prefix="wf-v35-genuine-xiyouji-") as tmp:
            restored=vault.restore(library="xiyouji-23962",destination=tmp)
            source_path=restored.get("source")
            if not source_path or not Path(source_path).is_file():
                raise SessionError("SIGNED_XIYOUJI_SOURCE_MISSING")
            raw=Path(source_path).read_bytes()
            source_sha=sha(raw)
            original=raw.decode("utf-8-sig")
            chapters=parse_original(original)
            if len(chapters)!=100:
                raise SessionError("NOT_A_COMPLETE_100_CHAPTER_ORIGINAL")
            window={n:chapters[n-1].text[:SOURCE_LIMIT] for n in (1,2)}
            if any(len(x)<1000 for x in window.values()):
                raise SessionError("ORIGINAL_READING_WINDOW_INCOMPLETE")
            source={
                "edition":"GITenberg_ProjectGutenberg_23962_Chinese_original",
                "source_study_r2_manifest_snapshot":restored["snapshot"],
                "source_sha256":source_sha,
                "original_chapters_verified":100,
                "actual_model_read_chapters":[1,2],
                "actual_model_read_window_chars":{str(n):len(window[n]) for n in window},
                "actual_model_read_windows":{str(n):window[n] for n in window},
                "model_did_not_read_all_hundred_chapters":True,
                "model_called":False,
            }
            rec,parent=save_stage(vault,0,source,None)
            last_index=0
            # This is actual source reading, not source keyword segmentation.
            read=reader.ask(
                "你是WriterForge内部文学原著读者。只阅读刚提供的"
                "《西遊記》原著两个连续阅读窗口。不要声称读完100回。"
                "以明确JSON写出你实际观察到的叙事行为，"
                "不要把读者猜想当成既定真相。字段必须完全符合协议。",
                "两个原著阅读窗口："+json.dumps(source["actual_model_read_windows"],
                    ensure_ascii=False)+
                "\n仅返回JSON唯一顶层 observations，为2到4项，每项字段严格："
                "chapter(数字1或2), source_quote(该章原文8-55个连续字符),"
                "narrative_function(这个细节如何推进情节),"
                "character_knowledge(角色当时知道与不知道什么),"
                "possible_alternative_reading(另一种可能解释或未知限制)。"
                "每章至少有一项。不要输出原著后续你没有在窗口读到的事实。",
                num_predict=4700)
            save_unvalidated_output(vault,1,read,parent)
            reading=validate_read(read,window)
            rec,parent=save_stage(vault,1,reading,parent)
            last_index=1
            # Learning still sees READ record, NOT the future exam question.
            insights_raw=reader.ask(
                "你是WriterForge自己的文学经验抽象模块。"
                "仅根据已经读到并核实的原著观察提炼可迁移叙事经验。"
                "这些都是待验证的假设，不是已掌握的正式技能。"
                "不要引用未读章节，不要把原著情节复制到新作品。"
                "只输出要求的JSON。",
                "本次真实阅读记录："+json.dumps(reading["observations"],
                    ensure_ascii=False)+
                "\n返回JSON，唯一顶层 lessons，含1到2项，每项严格字段："
                "source_observation_index(从0开始), technique(抽象叙事手法),"
                "why(该局部文本为什么可能有这样的效果),"
                "use_when(何时可用), avoid_when(何时不宜用),"
                "verification_question(新故事里怎么验证它确实产生效果)。"
                "每段解释清晰具体，不许夸称为文学通用真理。",
                num_predict=4500)
            save_unvalidated_output(vault,2,insights_raw,parent)
            insights=validate_lessons(insights_raw,len(reading["observations"]))
            rec,parent=save_stage(vault,2,insights,parent)
            last_index=2
            # Only NOW reveal the examiner's random pre-committed task.
            exam={"manifest":manifest(),"manifest_sha256":manifest_sha(),
                  "examiner_task":task(),
                  "source_excerpt_visible_to_writer":False}
            plan_raw=reader.ask(
                "你是WriterForge的创作准备模块。现在才首次看到考官题目。"
                "在下笔之前明确记录你的创作决策，而不是提供不可见的私下推理。"
                "必须说明至少四种人物/场景/感官/行动角度的选择、原因、"
                "曾考虑却拒绝的替代写法、预期读者效果。"
                "这份记录随后将被锁定，不能写完小说才回头修改。"
                "不要创作正文，不要引用或照搬《西遊記》原文，只输出JSON。",
                "考官预设独立题目："+task()+
                "\n学海候选手法："+json.dumps(insights["lessons"],ensure_ascii=False)+
                "\n返回JSON，唯一顶层 decisions，含4至7项，每项严格字段："
                "angle(goal/knowledge/causality/scene/sensory/dialogue/"
                "foreshadowing/emotion八个之一，不得重复),"
                "chosen_approach(准备怎么描写), reason(为什么这样写),"
                "rejected_alternative(为什么没选另一个方法),"
                "expected_story_effect(希望读者产生什么体验),"
                "learned_lesson_id(L1/L2/NONE)，"
                "至少有goal、knowledge、causality三种角度。",
                num_predict=4600)
            save_unvalidated_output(vault,3,plan_raw,parent)
            plan=validate_plan(plan_raw,{x["id"] for x in insights["lessons"]})
            prewrite={"exam":exam,"plan":plan,
                      "frozen_before_any_glm_writer_call":True}
            rec,parent=save_stage(vault,3,prewrite,parent)
            last_index=3
            # Critically: source passages no longer enter writing prompt.
            prompt={
                "task":task(),
                "candidate_craft_not_certain":insights["lessons"],
                "frozen_prewrite_decisions":plan["decisions"],
                "source_novel_text_exposed":False,
                "only_complete_original_chinese_first_chapter":True,
                "characters_including_punctuation_target":1120,
                "hard_characters_including_punctuation":[950,1300],
            }
            initial_response=writer.ask(
                "你是WF自己的小说作家。根据已经锁定的考前构思写原创第一章。"
                "不得照抄《西游记》的句子、角色、地名或事件，不要写分析。"
                "950到1300个含标点字符，目标1120；情节完整，结尾自然收束"
                "并留下从前文细节可回查的悬念。只输出真正小说正文。",
                json.dumps(prompt,ensure_ascii=False),num_predict=8500)
            save_unvalidated_output(vault,4,initial_response,parent)
            initial=initial_response["scene"]
            draft=validate_draft(initial,window)
            rec,parent=save_stage(vault,4,draft,parent)
            last_index=4
            revised=None
            if not draft["within_absolute_length_bounds"]:
                response=writer.ask(
                    "你是WF自我编辑模块，不能修改此前保存的原始稿或考前构思。"
                    "仅对自己的原稿做完整的独立修订，确保950至1300"
                    "个含标点字符且接近1120。不截断结尾、不重复凑字数，"
                    "保留人物认知、行动代价与可回查的伏笔。只输出修订后的正文。",
                    json.dumps({"own_draft_only":initial,"original_characters":len(initial),
                        "missing_or_excess_from_1120":1120-len(initial),
                        "target_characters":1120,"hard_bounds":[950,1300],
                        "frozen_plan_sha256":sha(canonical(prewrite))},
                        ensure_ascii=False),num_predict=7200)
                save_unvalidated_output(vault,5,response,parent)
                revised=validate_draft(response["scene"],window)
            current_text=revised["body"] if revised else initial
            edit_doc={
                "edited":revised is not None,
                "retained_original_draft_stage_sha256":sha(canonical(draft)),
                "edited_draft":revised,
                "final_body_sha256":sha(current_text),
                "final_characters":len(current_text),
                "final_valid_absolute_length":950<=len(current_text)<=1300,
                "did_not_overwrite_first_draft":True,
            }
            rec,parent=save_stage(vault,5,edit_doc,parent)
            last_index=5
            # Post-hoc rationale cannot edit prewriting decisions.
            after_raw=reader.ask(
                "你是WF的写后检查模块。写前构思已经不可更改。"
                "审视哪项真的体现在正文里、哪项没有做到，"
                "明确承认人物因果、节奏、悬念和视角出现的不足。"
                "不得编造事先做过的考虑，不得宣布自己已经学会写作。"
                "用自己的正文准确引用可查的短证据，只返回JSON。",
                "写前冻结决策："+json.dumps(plan["decisions"],ensure_ascii=False)+
                "\n本轮实际写完的最终正文："+current_text+
                "\n返回JSON严格顶层 checks 与 biggest_mistake。"
                "checks为2至5项，各含angle(必须来自写前决策),"
                "actual_draft_quote(正文中8至65个连续字符),"
                "followed_prewrite_plan(布尔),"
                "observed_gap(和预期的差异或失败),"
                "possible_next_revision(未来可试的修改)。"
                "biggest_mistake为最关键且明确的失误，不得打分吹捧。",
                num_predict=5400)
            save_unvalidated_output(vault,6,after_raw,parent)
            after=validate_after(after_raw,current_text,plan)
            after["refers_to_final_body_sha256"]=sha(current_text)
            after["locked_preplan_stage_sha256"]=sha(canonical(prewrite))
            rec,parent=save_stage(vault,6,after,parent)
            last_index=6
            plan_angles={d["angle"] for d in plan["decisions"]}
            checked_angles={d["angle"] for d in after["checks"]}
            program_audit={
                "phase":"HOST_EXAMINER_OBSERVATIONAL_CHECK",
                "number_of_source_observations":len(reading["observations"]),
                "source_quotes_exact_verified":True,
                "candidate_techniques_derived":len(insights["lessons"]),
                "prewrite_decisions_frozen":len(plan["decisions"]),
                "prewrite_decision_angles":sorted(plan_angles),
                "postwrite_angles_with_verified_draft_quotes":sorted(checked_angles),
                "prewrite_decisions_not_referenced_afterwards":sorted(
                    plan_angles-checked_angles),
                "decisions_self_claimed_followed":sum(
                    x["followed_prewrite_plan"] for x in after["checks"]),
                "decisions_self_reported_unfulfilled":sum(
                    not x["followed_prewrite_plan"] for x in after["checks"]),
                "final_length_valid":950<=len(current_text)<=1300,
                "no_original_story_passages_sent_to_writer":True,
                "hidden_reasoning_not_recorded_or_claimed":True,
                "independent_semantic_or_literary_quality_review":False,
                "experimental_literary_skill_promotion_allowed":False,
                "first_window":"NOT_PASSED","second_window":"LOCKED",
                "external_model_request_counts":{
                    "planner":budget.calls_by_role.get("planner",0),
                    "writer":budget.calls_by_role.get("writer",0)},
                "reported_usage":{
                    "input_tokens":budget.total_prompt_tokens,
                    "completion_tokens":budget.total_completion_tokens},
            }
            rec,parent=save_stage(vault,7,program_audit,parent)
            last_index=7
        return audit(vault)
    except Exception as error:
        safe=_keep_safe_failure(error)
        failure={
            "stage":"V35_PILOT_FAILED_WITH_PRIOR_STAGES_IMMUTABLE",
            "after_last_confirmed_stage":last_index,
            "failure_code":safe,
            "total_model_requests":budget.calls,
            "last_confirmed_sha256":parent,
            "draft_or_source_text_in_failure":False,
            "no_promotion":True,
        }
        content=canonical(failure)
        vault._put_small_immutable(f"{ROOT}/{SESSION}/failed-{sha(content)}.json",
                                   content,sha(content))
        print(json.dumps(failure,ensure_ascii=False,sort_keys=True),flush=True)
        raise

def audit(vault):
    prev=None
    completed=[]
    for i in range(len(STAGES)):
        restored=restore_stage(vault,i,prev)
        if restored is None:break
        rec,h=restored
        p=rec["payload"]
        completed.append({
            "stage":STAGES[i],"sha256":h,
            "stored_payload_bytes":len(canonical(p)),
            "record_is_independently_readable":True,
            "chars_of_read_source":(
                p.get("actual_model_read_window_chars") if i==0 else None),
            "prewrite_angles":(
                [x["angle"] for x in p["plan"]["decisions"]] if i==3 else None),
            "draft_characters":p.get("characters_including_punctuation") if i==4 else None,
            "final_characters":p.get("final_characters") if i==5 else None,
            "visible_decision_matches":(
                p.get("decisions_self_claimed_followed") if i==7 else None),
        })
        prev=h
    return {
        "stage":"V35_XIYOUJI_PREWRITE_PROCESS_OBSERVABILITY_AUDIT",
        "records":completed,"stages_completed":len(completed),
        "all_eight_stage_checkpoints_committed":len(completed)==len(STAGES),
        "read_book_original_chapters_current_trial":[1,2],
        "not_misrepresented_as_reading_all_100_chapters":True,
        "essay_and_explicit_decision_records_saved_separately":len(completed)>=5,
        "prewriting_record_immutable_before_draft":len(completed)>=5,
        "user_requested_full_stage_contents_in_private_R2":True,
        "private_bucket_not_claimed_client_encrypted":True,
        "hidden_model_chain_of_thought_not_claimed":True,
        "independent_literary_improvement_verified":False,
        "official_skill_core_promoted":False,
        "first_window":"NOT_PASSED","second_window":"LOCKED",
    }

def main():
    token=os.environ.get("DISCOVERY_API_KEY","")
    if not isinstance(token,str) or len(token)<12:
        raise SessionError("DISCOVERY_KEY_MISSING")
    vault=R2StudyVault(R2Config.from_environment())
    def factory(budget):
        roles=_request_models(token,budget)
        return roles["reader"],roles["writer"]
    return run(vault,factory)

if __name__=="__main__":
    try:
        print(json.dumps(main(),ensure_ascii=False,sort_keys=True),flush=True)
    except Exception as error:
        print(json.dumps({"stage":"V35_FAILED","code":_keep_safe_failure(error),
                          "previous_stages_persist_even_after_failure":True},
                         ensure_ascii=False),file=sys.stderr,flush=True)
        raise SystemExit(1)
