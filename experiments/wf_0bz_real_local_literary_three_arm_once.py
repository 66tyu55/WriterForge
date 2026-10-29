"""0.BZ: six real writer-arm trials on two NEW fantasy scenes, no paid APIs.

This experiment compares a bare local author, unchanged WF-G, and the SAME
WF-G with 0.BY's complete preplanning Xuehai reading enabled. It runs the
existing AutonomousWriting core, not a simulated replacement. Save every raw
local-engine reply before the core parses it; failures are outcomes, not
permission to retry. No Canon, R2, production DB, new memory, or grading engine.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
from pathlib import Path
from unittest.mock import patch
import json
import shutil
import time

from writerforge import WriterForgeDB, RuntimeEngine
from writerforge.xuehai import XuehaiStore
from writerforge.writing_assist import InvisibleWritingAssist, AutonomousWriting
from experiments.wf_0bh_stronger_local_writer_once import (
    MODEL_ID, MODEL_REVISION, MODEL_SHA256, _file_sha256,
)

SEED = 20261029
MAX_COMPLETION_BUDGET = 5650
MAX_LOCAL_CALLS = 5
ARMS = ("bare", "wf_g", "wf_g_reading")
SCENES = (
    {
        "id": "medicine-rights",
        "name": "宗门药签：失踪者的领药权与活人的等待",
        "outline": "玄幻宗门三名巡阵弟子失踪，药堂打算按旧例注销其领药权。外门弟子夏舟代姐姐来取药签；排队的病人也等着唯一一炉救命汤药。夏舟不知道姐姐是否活着，掌事也没有证据证明她死了。",
        "goal": "宗门分药堂内掌事扣住药签，失踪者姐姐的弟弟夏舟想代领三枚药签，排队病人又急需领药。让夏舟在有限认知下做出要付代价的选择，不替任何人编造已经知道的结局。",
    },
    {
        "id": "mountain-array",
        "name": "护山阵：开门救人还是维持阵法",
        "outline": "山门外暴风雪将至，十余名山民求进避难。护山阵的阵井异常，值夜弟子林雁只发现铜钉发白与阵符记录不符，尚不知故障根源。师兄相信掌阵簿册，开门会耗尽维持护阵的灵石。",
        "goal": "护山阵阵井边，外门弟子林雁看见铜钉结霜，听到山民求开门，掌阵师兄坚持阵符正常。写林雁在不能断定阵法为何失灵时如何选择救人或查阵，并承担真实后果。",
    },
)


def digest(data: bytes) -> str:
    return sha256(data).hexdigest()


def dump(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf8") as f:
        json.dump(data, f, ensure_ascii=False, sort_keys=True, indent=2)
        f.write("\n")


def fail_record(state: dict, error: Exception) -> None:
    state["status"] = "FAILED_NO_RETRY"
    state["error_type"] = type(error).__name__
    state["error_message"] = str(error)[:600]


def candidate_prose(answer: str) -> str:
    for mark in ("【正文】", "正文：", "正文:"):
        if mark in answer:
            return answer.split(mark, 1)[1].strip()
    return answer.strip()


def run(*, model_path: Path, db_path: Path, output: Path) -> dict:
    if output.exists():
        raise FileExistsError("WF0BZ_OUTPUT_ALREADY_EXISTS_NO_REPLAY")
    if not model_path.is_file() or _file_sha256(model_path) != MODEL_SHA256:
        raise PermissionError("WF0BZ_UNPINNED_OR_MISSING_LOCAL_WEIGHTS")
    if not db_path.is_file():
        raise FileNotFoundError("WF0BZ_DISPOSABLE_114_ENTRY_XUEHAI_REQUIRED")

    # Preflight before ANY model completion: real opt-in reading must be
    # selectable for both distinct topics. Selection is lexical, not proof
    # of semantic literary usefulness.
    db = WriterForgeDB(db_path)
    rt = RuntimeEngine()
    sid = XuehaiStore(db, rt).latest_published()
    if sid is None:
        raise RuntimeError("WF0BZ_NO_PUBLISHED_SOURCE")
    rt.enter_write(sid)
    study = XuehaiStore(db, rt)
    preflight = []
    for scene in SCENES:
        chosen = study.select_literary_reading_for_author(
            goal=scene["goal"], max_chars=4900)
        preflight.append({
            "scene": scene["id"],
            "reading_entry_id": chosen["entry_id"] if chosen else None,
            "reading_sha256": chosen["reading_sha256"] if chosen else None,
            "reading_source": chosen["source"] if chosen else None,
            "reading_original_chars": chosen["original_chars"] if chosen else None,
            "full_three_parts": bool(chosen and
                all(x in chosen["complete_reading"] for x in
                    ("【原文】", "【批注】", "【心得】"))),
        })
    rt.exit()
    db.close()
    if not all(v["full_three_parts"] for v in preflight):
        raise RuntimeError("WF0BZ_DISTINCT_SCENES_NOT_BOTH_ELIGIBLE_FOR_FULL_READING")

    # Verify the expected corpus without changing source or publishing Canon.
    db = WriterForgeDB(db_path)
    try:
        n = db.conn.execute("SELECT COUNT(*) FROM xuehai_entries").fetchone()[0]
        n_three = db.conn.execute(
            "SELECT COUNT(*) FROM xuehai_entries WHERE source_role IN "
            "('classical_original_annotation_reflection',"
            "'original_annotation_reflection')").fetchone()[0]
        if (n, n_three) != (114, 66):
            raise RuntimeError(f"WF0BZ_NOT_FROZEN_114_66_SOURCE:{n},{n_three}")
    finally:
        db.close()

    from llama_cpp import Llama
    output.mkdir(parents=True, exist_ok=False)
    ledger = {
        "format": "wf.0bz.two-scene-local-three-arm-source.v1",
        "status": "RUNNING_UNGRADED",
        "real_local_open_weight_inference": True,
        "not_provider_http_wire": True,
        "model": MODEL_ID,
        "model_revision": MODEL_REVISION,
        "verified_weights_sha256": MODEL_SHA256,
        "seed": SEED,
        "temperature": 0,
        "same_model_all_arms": True,
        "same_scene_tasks_all_arms": True,
        "completion_token_budget_per_arm_per_scene": MAX_COMPLETION_BUDGET,
        "call_limit_per_arm_per_scene": MAX_LOCAL_CALLS,
        "budget_is_same_ceiling_not_equal_actual_usage": True,
        "published_disposable_xuehai_entries": n,
        "full_three_part_readings": n_three,
        "preflight": preflight,
        "calls": 0,
        "new_paid_model_api_calls": 0,
        "canon_writes": 0,
        "r2_accesses": 0,
        "independent_reader_votes": 0,
        "literary_improvement_proven": False,
        "results": [],
    }
    def save():
        (output / "STATUS.json").write_text(
            json.dumps(ledger, ensure_ascii=False, sort_keys=True, indent=2)+"\n",
            encoding="utf8")
    save()
    engine = Llama(model_path=str(model_path), n_ctx=16384,
                   n_threads=2, n_gpu_layers=0, verbose=False)
    try:
        for scene in SCENES:
            for arm in ARMS:
                folder = output / scene["id"] / arm
                folder.mkdir(parents=True, exist_ok=False)
                state = {
                    "scene": scene["id"], "arm": arm, "status": "RUNNING",
                    "calls": [], "completion_cap_reserved": 0,
                    "prompt_tokens": 0, "completion_tokens": 0,
                    "no_hidden_retry": True, "author_accepted": False,
                }
                ledger["results"].append(state)
                save()
                def infer(packet, *, model, api_base, max_tokens):
                    if (model != MODEL_ID or max_tokens <= 0 or
                        len(state["calls"]) >= MAX_LOCAL_CALLS or
                        state["completion_cap_reserved"] + max_tokens >
                            MAX_COMPLETION_BUDGET):
                        raise PermissionError("WF0BZ_SHARED_CALL_BUDGET_EXCEEDED")
                    prompt = packet.prompt
                    if digest(prompt.encode("utf8")) != packet.prompt_sha256:
                        raise ValueError("WF0BZ_ACTUAL_REQUEST_PROMPT_SHA_MISMATCH")
                    index = len(state["calls"]) + 1
                    # Same proven Qwen2.5 instruct envelope as earlier 0.BH.
                    wrapped = ("<|im_start|>system\n"
                               "你是中文玄幻小说的原创作者。角色只能知道故事中可得的信息。"
                               "按请求写作，不要讲解你正在执行什么系统。"
                               "<|im_end|>\n<|im_start|>user\n" + prompt +
                               "\n<|im_end|>\n<|im_start|>assistant\n")
                    state["completion_cap_reserved"] += max_tokens
                    call = {
                        "index": index,
                        "requested_max_completion_tokens": max_tokens,
                        "packet_prompt_sha256": packet.prompt_sha256,
                        "actual_request_sha256": digest(wrapped.encode("utf8")),
                        "original_reply_path": f"call_{index:02d}_raw.json",
                        "stage_hint": ("chapter_plan" if index == 1 else
                            "writer_turn_or_replan"),
                    }
                    state["calls"].append(call)
                    save()
                    t = time.perf_counter()
                    response = engine.create_completion(
                        prompt=wrapped, seed=SEED,
                        max_tokens=max_tokens, temperature=0.0,
                        top_p=1.0, stop=["<|im_end|>", "</s>"])
                    # Preserve FULL raw engine reply even if the content is
                    # invalid JSON, incomplete prose or violates G's contract.
                    dump(folder / call["original_reply_path"], response)
                    answer = response["choices"][0]["text"]
                    usage = response["usage"]
                    pt = int(usage["prompt_tokens"])
                    ct = int(usage["completion_tokens"])
                    if usage["total_tokens"] != pt + ct or ct > max_tokens:
                        raise RuntimeError("WF0BZ_UNTRUSTWORTHY_LOCAL_USAGE")
                    call.update({
                        "raw_reply_sha256": digest((folder / call["original_reply_path"]).read_bytes()),
                        "original_answer_sha256": digest(answer.encode("utf8")),
                        "finish_reason": response["choices"][0]["finish_reason"],
                        "actual_prompt_tokens": pt,
                        "actual_completion_tokens": ct,
                        "elapsed_seconds": round(time.perf_counter()-t, 3),
                    })
                    state["prompt_tokens"] += pt
                    state["completion_tokens"] += ct
                    ledger["calls"] += 1
                    save()
                    return answer

                try:
                    if arm == "bare":
                        raw = (
                            "请你独立完成玄幻短篇的一场戏，不使用任何软件辅助或阅读材料。\n"
                            "【故事既定情境】" + scene["outline"] + "\n"
                            "【本场目标】" + scene["goal"] + "\n"
                            "请先用【构思】写你自己的主要动机、未知信息、选择和代价，"
                            "随后用【正文】写一段完整小说正文（约450—750汉字）。"
                            "正文不解释写作原理，不泄漏未知真相；人物并非一定成功。"
                        )
                        bare = type("BarePacket", (), {
                            "prompt": raw,
                            "prompt_sha256": digest(raw.encode("utf8"))
                        })()
                        answer = infer(bare, model=MODEL_ID,
                                       api_base="local-no-api",
                                       max_tokens=MAX_COMPLETION_BUDGET)
                        # Keep the entire original text AND a distinct
                        # mechanically extracted prose view; never rewrite.
                        dump(folder / "bare_original_plan_and_text.json",
                             {"raw": answer,
                              "prose_section": candidate_prose(answer)})
                        state["candidate_prose_file"] = "bare_original_plan_and_text.json"
                        state["status"] = "COMPLETED_UNGRADED"
                    else:
                        # Fresh copy; no test arm can learn from another arm's
                        # saved drafts or mutate the seeded published corpus.
                        work_db = folder / "disposable_working.sqlite"
                        shutil.copyfile(db_path, work_db)
                        wf_db = WriterForgeDB(work_db)
                        wf_rt = RuntimeEngine()
                        wf_sid = XuehaiStore(wf_db, wf_rt).latest_published()
                        wf_rt.enter_write(wf_sid)
                        assist = InvisibleWritingAssist(
                            wf_db, wf_rt, "wf0bz-fantasy", scene["id"],
                            scene["goal"], model=MODEL_ID,
                            api_base="http://127.0.0.1:1/v1",
                            source_genre="玄幻")
                        try:
                            with patch("writerforge.writing_assist.local_chat_completion",
                                       side_effect=infer):
                                result = AutonomousWriting(assist).run(
                                    outline=scene["outline"],
                                    chapter_goals=[scene["goal"]],
                                    output_dir=folder / "candidate_workspace",
                                    draft_mode="continuity_guard",
                                    bootstrap_unified_core=True,
                                    narrative_memory_backend="local",
                                    g_rolling_author_planning=True,
                                    self_edit_rounds=0,
                                    xuehai_methods_enabled=False,
                                    xuehai_readings_enabled=(arm == "wf_g_reading"),
                                )
                            chapter = result["chapters"][0]
                            cand = Path(chapter["candidate"])
                            original_prose = cand.read_text("utf8")
                            dump(folder / "original_candidate_prose.json",
                                 {"prose": original_prose,
                                  "sha256": digest(original_prose.encode("utf8")),
                                  "author_accepted": False})
                            state["candidate_prose_file"] = "original_candidate_prose.json"
                            state["reading_receipt"] = chapter.get(
                                "wf_literary_reading_before_planning")
                            state["writer_model_choice"] = (state["reading_receipt"] or
                                {}).get("model_reading_decision")
                            state["g_v98_replan_calls"] = result.get(
                                "g_rolling_author_planning_replan_model_calls")
                            state["status"] = "COMPLETED_UNGRADED"
                        finally:
                            wf_rt.exit()
                            wf_db.close()
                            # The temporary core DB is experimental only,
                            # not an output manuscript or a new memory.
                            work_db.unlink(missing_ok=True)
                except Exception as exc:
                    fail_record(state, exc)
                state["total_actual_tokens"] = (
                    state["prompt_tokens"] + state["completion_tokens"])
                save()
        ledger["status"] = "REAL_LOCAL_TRIAL_FINISHED_WITH_UNGRADED_OUTCOMES"
        save()
        return ledger
    finally:
        del engine


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--model", required=True, type=Path)
    p.add_argument("--db", required=True, type=Path)
    p.add_argument("--output", default=Path("wf0bz_real_local_literary_three_arm"), type=Path)
    a = p.parse_args()
    x = run(model_path=a.model, db_path=a.db, output=a.output)
    print(json.dumps({
        "status": x["status"], "actual_local_model_calls": x["calls"],
        "arms": [(r["scene"], r["arm"], r["status"],
                  r["completion_tokens"]) for r in x["results"]],
        "paid_api_calls": 0, "literary_improvement_proven": False,
    }, ensure_ascii=False))
