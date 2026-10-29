"""0.CI RED discovery: actual 0.CF R2 literature selection across other fictional worlds.

Source studies are the four SHA-pinned actual public-domain original excerpts
from 《三國志演義》 and 《老殘遊記》 with line-anchored annotations/reflections.
These are possible craft analogies, NOT universally correct literary judgments.
No actual LLM, no R2 writes, and no public/private manuscript output.
"""
from __future__ import annotations

from tempfile import TemporaryDirectory
from pathlib import Path
from shutil import copyfile
import json

from writerforge import WriterForgeDB, RuntimeEngine, XuehaiStore
from experiments.wf_0cf_r2_durable_literary_snapshot import (
    LIBRARY, _vault, inspect_literary_db,
)
from experiments.wf_0cg_existing_r2_to_real_writer_offline import (
    PINNED_SNAPSHOT, PINNED_CONTENT,
)

CASES=(
    {
        "id":"clan_unreliable_witness",
        "expected":"r2-laocan-02-clean-official-bandits",
        "goal":"玄幻宗门水牢里，弟子秋河追查一场失踪案，必须向值夜师兄问清来龙去脉。",
        "writing_problem":"想写出传闻和当事人的转述并非已经查实的事实；行动之后出现反效果与报复，但主人公不知道证词是否可靠。",
    },
    {
        "id":"spell_decoy_and_bystanders",
        "expected":"r2-sanguo-01-cao-lubu-decoy",
        "goal":"炼器宗门的护送队途经断桥，擅弓的弟子准备一个虚假的阵势与追兵周旋。",
        "writing_problem":"如何让对手此前的误判变成下一步设局的根据，具体展示误导信号与行动顺序，同时注意旁人被牵连的代价。",
    },
    {
        "id":"mountain_recruits_with_resources",
        "expected":"r2-sanguo-02-three-brothers-oath",
        "goal":"秘境外三名素不相识的修士遇在一起，都想取回被盗的试炼手札。",
        "writing_problem":"不要让三人突然结义，只因一句志向便立刻合作；要让不同人物带着各自资财、过去经历和风险，形成可以行动的盟约。",
    },
    {
        "id":"unknown_mage_anticipated",
        "expected":"r2-laocan-01-minghu-expectation",
        "goal":"古城的掌灯少年等待一位从未谋面的游方术士来救城中失火的旧塔。",
        "writing_problem":"人物尚未登场，怎样先借街谈巷议、众人安排时间和旁观者期待层层塑造名声，而不是旁白直接夸奖。",
    },
)


# Unseen after the 0.CI 4-case ranking repair. Purely diagnostic holdout:
# NEVER tune the four source rules against these replies in this run.
HOLDOUTS=(
    {
        "id":"ritual_respect_without_consent",
        "possible_reference":"classic-fantasy-jh-4",
        "goal":"修真宗门授一名学徒玉甲称号，礼官态度恭敬却强制他佩戴束住手臂的护具。",
        "writing_problem":"想写出礼貌的称呼和一重重手续如何逐步剥夺当事人拒绝的机会；"
                          "尊称与不能自行决定身体的处境形成反差，而非只写粗暴恶人。",
    },
    {
        "id":"misread_warning_under_surveillance",
        "possible_reference":"classic-fantasy-jh-3",
        "goal":"圣城派巡夜者监视同门女修，师弟误将她提醒避祸的话上报，女修反遭惩戒。",
        "writing_problem":"如何使人在受监视时把好友的好意误判为试探并主动上报，"
                          "使真正想帮助他的人付出代价；后来一句后悔不能抹去伤害。",
    },
    {
        "id":"power_interprets_own_words",
        "possible_reference":"classic-fantasy-fs-1",
        "goal":"仙宫议事时掌门把一句轻薄诗文刻在祖师石壁，侍立长老不敢劝阻。",
        "writing_problem":"怎样让有权者任意解释自己所写的字句，众人表面不反对却并不等于同意；"
                          "沉默来自权势压力，不必靠旁白提前宣告灭亡。",
    },
)



def diagnose_existing_r2():
    with TemporaryDirectory(prefix="wf0ci-real-literature-") as tmp:
        base=Path(tmp)
        r2=_vault(cold_only=True).restore(
            library=LIBRARY,snapshot=PINNED_SNAPSHOT,destination=base/"r2")
        proof=inspect_literary_db(Path(r2["db"]))
        assert proof["content_sha256"]==PINNED_CONTENT
        local=base/"local-only.sqlite3"
        copyfile(r2["db"],local)
        db=WriterForgeDB(local)
        rt=RuntimeEngine()
        sid=XuehaiStore(db,rt).latest_published()
        rt.enter_write(sid)
        try:
            outcome=[]
            for item in CASES:
                original=XuehaiStore(db,rt).select_literary_reading_for_author(
                    goal=item["goal"],max_chars=4900)
                mixed=XuehaiStore(db,rt).select_literary_reading_for_author(
                    goal=item["goal"]+" "+item["writing_problem"],max_chars=4900)
                transferred=XuehaiStore(db,rt).select_literary_reading_for_author(
                    goal=item["goal"],max_chars=4900,
                    writing_problem=item["writing_problem"])
                def method_cluster(reading):
                    if reading is None:
                        return None
                    row=db.conn.execute(
                        "SELECT method_cluster FROM xuehai_entries WHERE id=?",
                        (reading["entry_id"],)).fetchone()
                    return row["method_cluster"]
                from writerforge.xuehai import (
                    _literary_craft_grams,_author_craft_scope)
                craft_scope=_author_craft_scope(item["writing_problem"])
                parts=[
                    _literary_craft_grams(v)
                    for v in __import__("re").split("[，,；;]",craft_scope)
                    if len(v.strip())>=5]
                def source_support(entry):
                    if entry is None:
                        return None
                    study=XuehaiStore(db,rt).read_literary_reading(entry["entry_id"])
                    note="\\n".join(study["annotations"])+"\\n"+study["reflection"]
                    g=_literary_craft_grams(note)
                    hits=_literary_craft_grams(craft_scope)&g
                    return {
                        "clauses_supported":sum(bool(v&g) for v in parts),
                        "craft_fragments":len(hits),
                        "match_2grams":sorted(w for w in hits if len(w)==2)[:30],
                    }
                expected_row=db.conn.execute(
                    "SELECT id FROM xuehai_entries WHERE method_cluster=?",
                    (item["expected"],)).fetchone()
                expected_entry=(
                    {"entry_id":expected_row["id"]} if expected_row else None)
                outcome.append({
                    "case":item["id"],"expected_possible_literary_reference":item["expected"],
                    "current_goal_only":method_cluster(original),
                    "naively_joined_goal_plus_problem":method_cluster(mixed),
                    "source_annotation_and_reflection_selected":
                        method_cluster(transferred),
                    "craft_evidence_basis":(
                        transferred.get("matching_basis") if transferred else None),
                    "matched_craft_fragments":(
                        transferred.get("matched_craft_fragments",0)
                        if transferred else 0),
                    "craft_transfer_meets_possible_literary_reference":
                        method_cluster(transferred)==item["expected"],
                    "selected_source_support":source_support(transferred),
                    "pre_registered_source_support":source_support(expected_entry),
                    "current_goal_only_meets_registered_reference":
                        method_cluster(original)==item["expected"],
                    "no_semantic_quality_judgment":True,
                })
            # Independently phrased classical material never used for
            # the four-case rule repair. Record both successes and failures.
            unseen=[]
            for candidate in HOLDOUTS:
                picked=XuehaiStore(db,rt).select_literary_reading_for_author(
                    goal=candidate["goal"],max_chars=4900,
                    writing_problem=candidate["writing_problem"])
                picked_cluster=(db.conn.execute(
                    "SELECT method_cluster FROM xuehai_entries WHERE id=?",
                    (picked["entry_id"],)).fetchone()["method_cluster"]
                    if picked else None)
                unseen.append({
                    "case":candidate["id"],
                    "possible_source":candidate["possible_reference"],
                    "observed_source":picked_cluster,
                    "matched_possible_source":picked_cluster==candidate["possible_reference"],
                    "independent_literary_verdict":False,
                })
            # This is WF's actual writing entrance, not just its selector.
            # A FIXED writer reply cannot prove model understanding, but can
            # prove the selected REAL classic's complete text reached planning.
            from unittest.mock import patch
            from writerforge.writing_assist import (
                InvisibleWritingAssist,AutonomousWriting)
            case=CASES[0]
            chosen=XuehaiStore(db,rt).select_literary_reading_for_author(
                goal=case["goal"],max_chars=4900,
                writing_problem=case["writing_problem"])
            selected_cluster=db.conn.execute(
                "SELECT method_cluster FROM xuehai_entries WHERE id=?",
                (chosen["entry_id"],)).fetchone()["method_cluster"]
            if selected_cluster!=case["expected"]:
                raise AssertionError("WF0CI_WRITER_CRAFT_SOURCE_NOT_THE_REAL_CLASSIC")
            wire=[]
            plan={
                "objective":"秋河请求先查明失踪者最后由谁亲眼看见",
                "conflict":"当事人转述的证词尚未核实，追究也可能招致报复",
                "decision":"秋河先收下证词并向另一位值守弟子交叉查问",
                "outcome":"查证占用时间，使水牢外的守夜轮班受到影响",
                "pov":"秋河仅凭现场观察与他人所说判断",
                "needs":["dialogue","decision"],
                "reading_choice":{
                    "decision":"USE",
                    "reason":"借鉴多重转述造成的悬疑，不复写老残的人物或结局，保留事件事实尚未证实的空间。",
                },
            }
            prose=(
                "秋河抵达水牢时，铜灯已烧到第二道刻痕。门边的值守弟子说师兄昨夜自己走了，"
                "可他讲不出对方何时交还腰牌。秋河没有当面说那人撒谎，先将桌上的值班簿向前推去，"
                "请他指认最后一次巡门的时辰。那弟子说火候过了寅时，墙外却有人在敲更鼓。"
                "他们的争执招来另一名守夜者，对方刚听见师兄的名字就要回屋。"
                "秋河只得拦下他问了第二遍，铜灯旁的排班牌因此迟迟没人换。"
                "灯灭时，他所知道的仍只有两份互相矛盾的说法。"
            )
            def fixed_writer(packet,*,model,api_base,max_tokens):
                wire.append(packet)
                if len(wire)==1:
                    if chosen["complete_reading"] not in packet.prompt:
                        raise AssertionError("WF0CI_REAL_ORIGINAL_AND_NOTES_NOT_DELIVERED")
                    return json.dumps(plan,ensure_ascii=False)
                if len(wire)!=2 or plan["reading_choice"]["reason"] not in packet.prompt:
                    raise AssertionError("WF0CI_AUTHOR_CHOICE_NOT_CARRIED_TO_PROSE")
                return prose
            assist=InvisibleWritingAssist(
                db,rt,"wf0ci-source-only","witness",case["goal"],
                model="FIXED_AUTHOR_REPLY_NOT_REAL_LLM",
                api_base="http://127.0.0.1:1",
                source_genre="玄幻")
            with patch("writerforge.writing_assist.local_chat_completion",
                       side_effect=fixed_writer):
                job=AutonomousWriting(assist).run(
                    outline=case["goal"]+"。\n"+case["writing_problem"],
                    chapter_goals=[case["goal"]],
                    output_dir=base/"unaccepted-writer",
                    draft_mode="single",
                    xuehai_readings_enabled=True)
            receipt=job["chapters"][0]["wf_literary_reading_before_planning"]
            if (len(wire)!=2
                or job["wf_literary_readings_author_used"]!=1
                or receipt["entry_id"]!=chosen["entry_id"]
                or receipt["matching_basis"]!="ANNOTATIONS_REFLECTIONS_TEXT_OVERLAP"
                or job["chapters"][0]["accepted"] is not False
                or Path(job["chapters"][0]["candidate"]).read_text("utf8")!=prose):
                raise AssertionError("WF0CI_REAL_WRITING_PIPELINE_OR_SOURCE_MISMATCH")
            weak=XuehaiStore(db,rt).select_literary_reading_for_author(
                goal=case["goal"],writing_problem="希望这一章写得更好",
                max_chars=4900)
            if weak is not None:
                raise AssertionError("WF0CI_GENERIC_IMPROVEMENT_AS_CRAFT_EVIDENCE")
            return {"source_snapshot_exactly_verified":True,
                    "real_public_domain_works":2,
                    "literary_references_in_source":4,
                    "cases":outcome,
                    "new_unseen_classical_holdouts":unseen,
                    "model_calls":0,"r2_writes":0,
                    "actual_writer_entry_reached_with_real_public_source":True,
                    "writer_reply_scripted_no_real_model":True,
                    "full_original_and_three_annotations_in_first_prompt":True,
                    "nonspecific_craft_question_no_forced_reading":True,
                    "unaccepted_literary_candidate_unchanged":True,
                    "canon_writes":0,
                    "literary_gain_proven":False}
        finally:
            rt.exit()
            db.close()


if __name__=="__main__":
    print(json.dumps(diagnose_existing_r2(),ensure_ascii=False))
