"""0.CJ independent source-first literary holdout; diagnostic, NOT tune-to-green.

Read-only existing pinned R2 literary library (126 pieces / 78 deep readings),
using the REAL existing Xuehai selector. Pre-registered test cases were
committed before this code. No paid or local LLM, no separate databases,
no R2/Canon write. Report partial and abstention distinctly from exact hits.
"""
from __future__ import annotations
from pathlib import Path
from tempfile import TemporaryDirectory
from shutil import copyfile
import json

from experiments.wf_0cf_r2_durable_literary_snapshot import (
    LIBRARY, _vault, inspect_literary_db,
)
from experiments.wf_0cg_existing_r2_to_real_writer_offline import (
    PINNED_SNAPSHOT, PINNED_CONTENT,
)
from writerforge import WriterForgeDB, RuntimeEngine, XuehaiStore
from writerforge.xuehai import Query, _author_craft_scope, _literary_craft_grams

ROOT=Path(__file__).resolve().parents[1]
FROZEN=ROOT/"experiments/wf_0cj_independent_real_classic_holdouts_20261029.json"
ROLES=("classical_original_annotation_reflection","original_annotation_reflection")


def source_cluster(db,chosen):
    if chosen is None:
        return None
    row=db.conn.execute(
        "SELECT method_cluster FROM xuehai_entries WHERE id=?",
        (chosen["entry_id"],)).fetchone()
    return row["method_cluster"] if row else None


def inspect_holdouts():
    frozen=json.loads(FROZEN.read_text("utf8"))
    assert frozen["format"]=="wf.0cj.pre-registered.classic-holdouts.v1"
    assert len(frozen["cases"])==9
    with TemporaryDirectory(prefix="wf0cj-r2-real-literary-") as scratch:
        base=Path(scratch)
        restored=_vault(cold_only=True).restore(
            library=LIBRARY,snapshot=PINNED_SNAPSHOT,destination=base/"source")
        proof=inspect_literary_db(Path(restored["db"]))
        assert proof["content_sha256"]==PINNED_CONTENT
        work=base/"no-canon.sqlite3"
        copyfile(restored["db"],work)
        db=WriterForgeDB(work)
        rt=RuntimeEngine()
        sid=XuehaiStore(db,rt).latest_published()
        rt.enter_write(sid)
        try:
            store=XuehaiStore(db,rt)
            available={}
            for role in ROLES:
                found=store.query(Query(
                    source_role=role,limit=32,
                    max_per_work=8,max_per_cluster=1))
                available[role]={source_cluster(db,item) for item in found}
            report=[]
            for task in frozen["cases"]:
                picked=store.select_literary_reading_for_author(
                    goal=task["goal"],max_chars=4900,
                    writing_problem=task["writing_problem"])
                selected=source_cluster(db,picked)
                expected=task["possible_sources"]
                if task["class"]=="should_abstain":
                    disposition=("ABSTAIN" if picked is None
                                 else "UNSUPPORTED_OFFER")
                else:
                    disposition=("SUGGESTED_SOURCE" if selected in expected
                                 else "ABSTAIN" if selected is None
                                 else "OTHER_POSSIBLY_RELATED")
                # Audit just the broad bounded SQL shortlist, not source
                # quotes or passwords. Missing candidates cannot be chosen.
                source_locations=[
                    {"candidate":name,
                     "available_in_bounded_shortlist":any(
                         name in available[role] for role in ROLES)}
                    for name in expected
                ]
                report.append({
                    "case":task["id"],
                    "pre_registered_class":task["class"],
                    "pre_registered_possible_sources":expected,
                    "wf_selected_source":selected,
                    "observed_disposition":disposition,
                    "candidate_shortlist":source_locations,
                    "received_complete_three_part_source":(
                        picked is not None and picked["annotation_count"]==3
                        and all(mark in picked["complete_reading"] for mark in
                                ("【原文】","【批注】","【心得】"))),
                    "reported_evidence_basis":(
                        picked.get("matching_basis") if picked else None),
                    "lexical_grams_matched":(
                        picked.get("matched_craft_fragments",0) if picked else 0),
                    "one_best_not_a_literary_truth":True,
                })
            # Exercising the real author entry, not a side-route query:
            # a story-flavored software task must not receive literary
            # 原文 in the actual chapter-planning provider request.
            from unittest.mock import patch
            from writerforge.writing_assist import (
                InvisibleWritingAssist, AutonomousWriting)
            technical=next(c for c in frozen["cases"]
                           if c["id"]=="new-genre-noun-not-method")
            packets=[]
            plan={
                "objective":"青年书生请摊主核对丹药出售时的药材登记",
                "conflict":"药丹包装旧损，摊主认为仍然可以使用",
                "decision":"书生决定先检查登记再考虑支付钱款",
                "outcome":"两人暂时停下买卖等待核验",
                "pov":"只记录书生眼前所见的货物和言语",
                "needs":["dialogue","decision"],
            }
            manuscript=("书生来到摊前时，看见铺垫的草席被风吹得卷起一角。"
                        "摊主从木柜里取出一枚旧丹，却说瓶封只是有些磨损，"
                        "并不能证明药已经不能用。书生没有出钱，先请他翻找"
                        "原有的进货账簿。摊主把柜门重新合上，四周的人便"
                        "都停下来听他们谈这桩交易。书生拿着钱袋没有"
                        "离开，也没有冒然判断摊主故意欺诈。")
            def script_reply(packet,*,model,api_base,max_tokens):
                packets.append(packet)
                return (json.dumps(plan,ensure_ascii=False)
                        if "请先规划本章" in packet.prompt else manuscript)
            assist=InvisibleWritingAssist(
                db,rt,"wf0cj-technical-is-not-literature","novel-prop",
                technical["goal"],model="FIXED_REPLY_NO_INFERENCE",
                api_base="http://127.0.0.1:1",source_genre="玄幻")
            with patch("writerforge.writing_assist.local_chat_completion",
                       side_effect=script_reply):
                trial=AutonomousWriting(assist).run(
                    outline=technical["goal"]+"。\\n"+
                            technical["writing_problem"],
                    chapter_goals=[technical["goal"]],
                    output_dir=base/"technical-not-literature",
                    draft_mode="single",xuehai_readings_enabled=True)
            receipt=trial["chapters"][0]["wf_literary_reading_before_planning"]
            if (len(packets)!=2 or
                receipt["delivered_to_author_planning"] or
                trial["wf_literary_readings_delivered"]!=0 or
                "【学海文学深读" in packets[0].prompt or
                trial["chapters"][0]["accepted"] is not False):
                raise AssertionError("WF0CJ_TECHNICAL_TASK_WAS_GIVEN_LITERATURE")
            # Ordinary story text containing "不要" is not necessarily an
            # explicit literary how-to. Preserve the legacy goal-based
            # reading path if author didn't ask an actual craft question.
            old_goal="天雨署晏纸收到三澜县报牒，准备给雨簿的字迹存疑封条签字"
            baseline=store.select_literary_reading_for_author(
                goal=old_goal,max_chars=4900)
            story_only=store.select_literary_reading_for_author(
                goal=old_goal,max_chars=4900,
                writing_problem="他不要师兄替自己宣誓，今天仍守着天雨署的账桌。")
            if (baseline is None or story_only is None
                or baseline["entry_id"]!=story_only["entry_id"]):
                raise AssertionError("WF0CJ_ORDINARY_STORY_GOAL_FALLBACK_BROKEN")
            # Re-read the untouched ORIGINAL restore, not the local mutable
            # copy. No new method/value evaluation is ever written.
            unchanged=inspect_literary_db(Path(restored["db"]))
            assert unchanged==proof
            return {
                "status":"WF0CJ_NEW_HOLDOUT_REAL_R2_LITERATURE_DIAGNOSTIC",
                "snapshot_sha256":PINNED_SNAPSHOT,
                "source_integrity_verified":True,
                "total_literature_entries":proof["contents"],
                "three_part_readings":proof["complete_three_part_readings"],
                "pre_registered_cases":len(report),
                "source_cases":report,
                "r2_writes":0,"canon_writes":0,
                "model_requests":0,"literary_gain_proven":False,
                "ordinary_novel_goal_fallback_preserved":True,
                "real_writer_technical_request_received_no_literary_text":True,
                "real_writer_reply_scripted_not_a_model_test":True,
                "frozen_cases_committed_before_first_run":True,
                "cases_now_used_as_repair_regression_not_new_blind_holdout":True,
            }
        finally:
            rt.exit()
            db.close()


if __name__=="__main__":
    print(json.dumps(inspect_holdouts(),ensure_ascii=False,sort_keys=True))
