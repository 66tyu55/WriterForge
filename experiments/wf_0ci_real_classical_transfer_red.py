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
            return {"source_snapshot_exactly_verified":True,
                    "real_public_domain_works":2,
                    "literary_references_in_source":4,
                    "cases":outcome,"model_calls":0,"r2_writes":0,
                    "literary_gain_proven":False}
        finally:
            rt.exit()
            db.close()


if __name__=="__main__":
    print(json.dumps(diagnose_existing_r2(),ensure_ascii=False))
