"""0.BY: proof of actual WRITER PLANNING DELIVERY, not literary improvement.

Runs against the existing throwaway Xuehai from wf_0br_stage_classical_readings.
Patches only the paid provider call, preserving the real AutonomousWriting and
VerifiedWritingFlow context assembly. No new database, model, Canon, or memory.
"""
from __future__ import annotations
import argparse
import json
import tempfile
from pathlib import Path
from unittest.mock import patch

from writerforge import WriterForgeDB, RuntimeEngine
from writerforge.xuehai import XuehaiStore
from writerforge.writing_assist import InvisibleWritingAssist, AutonomousWriting
from writerforge.verified_flow import WritingExecutionError


GOAL = "宗门分药堂内掌事扣住药签，失踪者姐姐的弟弟想代领三枚药签"
OUTLINE = "宗门三名巡阵弟子下落不明。夏舟不愿直接注销他们的领药权，却必须与掌事对话，并承担今天仍有人等待汤药的结果。"
PLAN = {
    "objective":"夏舟尝试让失踪者的药签继续有效",
    "conflict":"今天领药的病人也在排队，掌事担忧违规",
    "decision":"夏舟决定留名作暂代保管而不是抢夺药签",
    "outcome":"掌事没有同意，但将此事留到明日重新议论",
    "pov":"夏舟的有限视角",
    "needs":["dialogue","decision"],
}
CHOICE = {
    "decision":"USE",
    "reason":"我想借鉴一纸手续给活人带来的犹豫，但保留等待治病者的立场，不复制古籍的角色或结尾。",
}
SKIP_CHOICE = {
    "decision":"SKIP",
    "reason":"这篇的责任冲突可能有启发，但我这次更愿从角色当下所见出发，不依赖借来的结构或结尾。",
}
PROSE = (
    "夏舟站在药堂门槛外，手里攥着三枚旧木签。掌事问他是谁派来的，他没有立即解释姐姐去了哪里，"
    "而是先看向门外排队的老人。那人咳得弯下腰，身后的药篓却仍空着。"
    "掌事将簿册翻到今日，指着已经写好的名字：这三个人没有回来，照旧例必须划去。"
    "夏舟在袖里摸到了姐姐留下的护腕，又慢慢松开。这个月已经有人因领不到药而发热，"
    "他也知道一味争执救不了人。最后他将木签放在桌角，只求掌事先记下自己的姓名。"
    "掌事没有答应，屋檐下的雨越落越密，夏舟仍站着等他把笔搁下。"
)


def run_smoke(db_path: Path) -> dict:
    db=WriterForgeDB(db_path)
    sid=XuehaiStore(db,RuntimeEngine()).latest_published()
    if sid is None:
        raise AssertionError("MISSING_PUBLISHED_XUEHAI")
    rt=RuntimeEngine()
    rt.enter_write(sid)
    try:
        study=XuehaiStore(db,rt).select_literary_reading_for_author(
            goal=GOAL,max_chars=4000)
        if study is None:
            raise AssertionError("RELEVANT_THREE_PART_READING_WAS_NOT_SELECTED")
        assert all(tag in study["complete_reading"] for tag in (
            "【原文】","【批注】","【心得】","药签"))
        assert study["original_chars"]>100
        assert study["annotation_count"]==3
        # The baseline and opt-in are the same model, prompt and budget; only
        # the presence of the complete Xuehai material changes.
        result=[]
        for mode,enabled,writer_choice in (
            ("baseline",False,None),("use",True,CHOICE),
            ("skip",True,SKIP_CHOICE)):
            calls=[]
            def fake_author(packet, *, model, api_base, max_tokens):
                calls.append({"prompt":packet.prompt,
                              "prompt_sha256":packet.prompt_sha256,
                              "max_tokens":max_tokens})
                if "请先规划本章" in packet.prompt:
                    body=dict(PLAN)
                    if enabled:
                        assert "【学海文学深读" in packet.prompt
                        assert all(tag in packet.prompt for tag in (
                            "【原文】","【批注】","【心得】"))
                        assert "【完整阅读】" in packet.prompt
                        assert study["complete_reading"] in packet.prompt
                        body["reading_choice"]=writer_choice
                    else:
                        assert "【学海文学深读" not in packet.prompt
                    return json.dumps(body,ensure_ascii=False)
                # The actual writer's choice travels into prose planning.
                if enabled:
                    assert '"writer_reading_choice"' in packet.prompt
                    assert writer_choice["reason"] in packet.prompt
                return PROSE
            assist=InvisibleWritingAssist(
                db,rt,"wf0by-local-pilot","pilot-scene",GOAL,
                model="mocked-no-paid-model",
                api_base="http://127.0.0.1:1",
                source_genre="玄幻")
            with tempfile.TemporaryDirectory(prefix="wf0by-") as dest:
                with patch("writerforge.writing_assist.local_chat_completion",
                           side_effect=fake_author):
                    trial=AutonomousWriting(assist).run(
                        outline=OUTLINE,chapter_goals=[GOAL],
                        output_dir=dest,draft_mode="single",
                        xuehai_readings_enabled=enabled)
                assert len(calls)==2
                assert trial["wf_literary_preplan_extra_model_calls"]==0
                assert trial["wf_literary_readings_delivered"]==int(enabled)
                assert trial["wf_literary_readings_author_used"]==int(mode=="use")
                assert trial["wf_literary_readings_author_skipped"]==int(mode=="skip")
                assert trial["wf_literary_learning_quality_verified"] is False
                chapter=trial["chapters"][0]
                reading=chapter["wf_literary_reading_before_planning"]
                assert reading["delivered_to_author_planning"] is enabled
                if enabled:
                    assert reading["reading_sha256"]==study["reading_sha256"]
                    assert reading["planning_prompt_sha256"]==calls[0]["prompt_sha256"]
                    assert reading["model_reading_decision"]==writer_choice["decision"]
                assert Path(chapter["candidate"]).read_text("utf8")==PROSE
                assert chapter["accepted"] is False
                result.append({
                    "mode":mode,"enabled":enabled,
                    "plan_prompt_sha256":calls[0]["prompt_sha256"],
                    "actual_model_calls":len(calls),
                    "source_id":reading["entry_id"],
                    "author_choice":reading["model_reading_decision"],
                    "candidate_accepted":False,
                })
        # Invalid options never reach the model or create a draft directory.
        assist=InvisibleWritingAssist(
            db,rt,"wf0by-local-pilot","pilot-scene",GOAL,
            model="mocked-no-paid-model",
            api_base="http://127.0.0.1:1",
            source_genre="玄幻")
        with tempfile.TemporaryDirectory(prefix="wf0by-invalid-") as dest:
            try:
                AutonomousWriting(assist).run(
                    outline=OUTLINE,chapter_goals=[GOAL],
                    output_dir=dest,
                    xuehai_readings_enabled="true")
            except WritingExecutionError as exc:
                assert "XUEHAI_AUTHOR_DEEP_READING_CHOICE_INVALID" in str(exc)
            else:
                raise AssertionError("INVALID_OPT_IN_WAS_ACCEPTED")
            assert not list(Path(dest).iterdir())
        return {
            "status":"REAL_AUTONOMOUS_WRITER_PREPLAN_FULL_READING_DELIVERED",
            "study_entry_id":study["entry_id"],
            "study_source":study["source"],
            "read_original_characters":study["original_chars"],
            "complete_reading_sha256":study["reading_sha256"],
            "baseline_and_reading_prompts_compared":result,
            "additional_model_calls":0,
            "real_provider_model_calls":0,
            "models_actual_literary_gain_proven":False,
            "db":"DISPOSABLE_ONLY",
            "canon_writes":0,
            "manual_writing_judgement_from_WF":0,
        }
    finally:
        rt.exit()
        db.close()


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--db",type=Path,required=True)
    args=p.parse_args()
    print(json.dumps(run_smoke(args.db),ensure_ascii=False,indent=2))
