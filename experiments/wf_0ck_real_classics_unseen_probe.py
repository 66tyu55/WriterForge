"""0.CK unseen-after-0.CJ diagnostic on real, pinned historical sources.

Freeze code and questions BEFORE FIRST RUN.  Do not tune 0.CJ code in response
to these results. A plausible reference != verified literary quality.
No model API; user-private modern novels never exported.
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

UNSEEN=(
    {
        "id":"righteous-man-not-yet-righteous",
        "kind":"POSSIBLE_CLASSIC",
        "suggested":["classic-0bs-s04"],
        "goal":"一名豪侠刚在酒楼入座，忽听到隔壁哭声；他的同伴和小二都盯着他。",
        "problem":"如何让一个自称豪爽的人在酒楼里显出对位卑者的急躁和压迫，"
                  "又不急着证明他以后必然仗义；座次、说话和摔碗都能成为人物矛盾的一部分。",
    },
    {
        "id":"praise-also-performing-for-elder",
        "kind":"POSSIBLE_CLASSIC",
        "suggested":["classic-0bs-h04"],
        "goal":"一个少年初次入仙门大家族，众人拿不同辈分的称谓介绍一位女执事。",
        "problem":"想写出一段夸奖新人时同时照顾在场长辈的言辞，"
                  "让亲近中有身份分寸，人物的眼泪和转笑也可以是真情或表演，"
                  "不要让旁白提前裁定。",
    },
    {
        "id":"coat-swap-reveals-social-mask",
        "kind":"POSSIBLE_CLASSIC",
        "suggested":["classic-fantasy-jh-3"],
        "goal":"灵舟两名师弟到一座只认衣饰品阶的仙城，外来者换上旧衣后受到冷待。",
        "problem":"怎样让同一个人换了衣服就被众人改换态度，以实际待遇揭示"
                  "外表客气而心中势利，并让旁观者怀疑是否自己的说话冒犯了对方。",
    },
    {
        "id":"character-json-for-tooling",
        "kind":"EXPECTED_ABSTAIN",
        "suggested":[],
        "goal":"仙侠剧本角色有姓名、身份和道具，项目需要统一数据格式。",
        "problem":"如何把人物与剧情节点序列化成JSON字段，存储每一次角色选择、人物关系、行动后果，"
                  "请输出符合Schema的示例数据结构和完整代码，不需要小说正文。",
    },
    {
        "id":"dialogue-css-bubbles",
        "kind":"EXPECTED_ABSTAIN",
        "suggested":[],
        "goal":"一款武侠RPG需要在剧情对话框展示角色的头像与台词。",
        "problem":"怎样给对白文字添加CSS文字气泡、点击态和禁用态，让对话场景的控件支持触屏；"
                  "只返回HTML和CSS样式代码。",
    },
    {
        "id":"novel-plot-sql-ddl",
        "kind":"EXPECTED_ABSTAIN",
        "suggested":[],
        "goal":"奇幻小说的角色谱系需要转成关系数据库，便于网页查看。",
        "problem":"如何设计人物关系与因果后果的SQL表结构，给出CREATE TABLE语句、"
                  "主键和外键约束，不是对小说人物进行文学点评。",
    },
    {
        "id":"quiet-everyday-fragment",
        "kind":"OPEN_LITERARY",
        "suggested":[],
        "goal":"一名外门学徒回宗门后坐在灶台旁，看师兄为一碗饭添水。",
        "problem":"如何写一个并不需要反转的安静日常，"
                  "让人物在不多言的照顾里产生一点变化，不把温柔描写成英雄壮举。",
    },
)


def run():
    with TemporaryDirectory(prefix="wf0ck-unseen-reality-") as tmp:
        root=Path(tmp)
        restored=_vault(cold_only=True).restore(
            library=LIBRARY,snapshot=PINNED_SNAPSHOT,destination=root/"r2")
        proof=inspect_literary_db(Path(restored["db"]))
        assert proof["content_sha256"]==PINNED_CONTENT
        db_path=root/"disposable.sqlite3"
        copyfile(restored["db"],db_path)
        db=WriterForgeDB(db_path)
        rt=RuntimeEngine()
        sid=XuehaiStore(db,rt).latest_published()
        rt.enter_write(sid)
        try:
            store=XuehaiStore(db,rt)
            rows=[]
            for x in UNSEEN:
                selected=store.select_literary_reading_for_author(
                    goal=x["goal"],writing_problem=x["problem"],max_chars=4900)
                cluster=None
                if selected:
                    source=db.conn.execute(
                        "SELECT method_cluster FROM xuehai_entries WHERE id=?",
                        (selected["entry_id"],)).fetchone()
                    cluster=source["method_cluster"] if source else None
                if x["kind"]=="EXPECTED_ABSTAIN":
                    status="ABSTAIN" if selected is None else "WRONG_LITERARY_INSERTION"
                elif x["kind"]=="POSSIBLE_CLASSIC":
                    status=("MATCHED_PLAUSIBLE_SOURCE" if cluster in x["suggested"]
                            else "NO_SOURCE" if cluster is None
                            else "ANOTHER_SUGGESTION_NOT_A_LITERARY_VERDICT")
                else:
                    status="OPTIONAL_READING" if selected else "NO_READING"
                rows.append({
                    "case":x["id"],
                    "task_class":x["kind"],
                    "pre_registered_possible_sources":x["suggested"],
                    "selected_source":cluster,
                    "status":status,
                    "complete_original_delivered_if_selected":(
                        not selected or all(
                            tag in selected["complete_reading"]
                            for tag in ("【原文】","【批注】","【心得】"))),
                    "source_relevance_is_unverified":True,
                })
            assert inspect_literary_db(Path(restored["db"]))==proof
            return {
                "status":"WF0CK_NEW_UNSEEN_REAL_LITERATURE_HOLDOUT_OBSERVED",
                "source_verified_r2_snapshot":PINNED_SNAPSHOT,
                "literary_sources":proof["contents"],
                "three_part_readings":proof["complete_three_part_readings"],
                "unseen_pre_registered_cases":len(rows),
                "outcomes":rows,
                "any_literary_truth_claim":False,
                "trained_any_model":False,
                "r2_writes":0,"model_calls":0,"canon_writes":0,
                "original_first_holdout_run_id":40869281958,
                "original_unseen_result_preserved":True,
                "now_a_repair_regression_not_a_new_blind_holdout":True,
                "rule_modified_after_seeing_results":True,
            }
        finally:
            rt.exit()
            db.close()


if __name__=="__main__":
    print(json.dumps(run(),ensure_ascii=False,sort_keys=True))
