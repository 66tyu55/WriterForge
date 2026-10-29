"""0.CG: EXISTING private R2 -> intact 126-entry Xuehai -> ACTUAL WF author entry.

Uses the REAL R2StudyVault.restore, XuehaiStore and AutonomousWriting.run,
with only the external author model substituted by fixed offline replies.
The fixed replies are plumbing fixtures, NOT evidence that a model read,
thought, improved its prose, or autonomously chose USE/SKIP.

Neither R2, Railway, model API, Canon nor narrative-memory backend is written.
All draft artifacts remain in ephemeral runner-local scratch space.
"""
from __future__ import annotations

from hashlib import sha256
from pathlib import Path
from shutil import copyfile
from tempfile import TemporaryDirectory
from unittest.mock import patch
import json

from writerforge import WriterForgeDB, RuntimeEngine, XuehaiStore
from writerforge.writing_assist import InvisibleWritingAssist, AutonomousWriting
from experiments.wf_0cf_r2_durable_literary_snapshot import (
    LIBRARY, _vault, inspect_literary_db,
)
from experiments.wf_0by_real_author_preplan_reading_smoke import run_smoke

PINNED_SNAPSHOT="d72d4ada31112409167454ada01974f7e660dd3daa22516fd962849254a2527d"
PINNED_CONTENT="2ced6f51076fa7f432a572e7c413d8f6260a32bcf19a4930780da76c39e7eebc"

# These are deliberately NOT reusing the old 0.BZ pharmacy plot.
SCENARIOS=(
    {
        "id":"signed-weather-office",
        "xuehai_cluster":"cc-01-star-rain-register",
        "goal":"天雨署晏纸收到三澜县报牒，准备给雨簿的字迹存疑封条签字",
        "outline":"钟暮在雨司的迁季簿前发现两处记录不一致，他尚不知道谁涂改了数目，必须与司书争论。",
        "decision":"USE",
        "reason":"我会留意正面公文与背后附注的可信度差异，但不沿用天雨署的人物、原文或事件结局，仍让本章角色自己决定。",
        "plan":{
            "objective":"钟暮要求先核对两份结论不一致的旧文书",
            "conflict":"司书急于结案，钟暮尚不知道附注是否可信",
            "decision":"钟暮决定暂缓签字并当面追问被涂改的月份",
            "outcome":"这次延误让同值夜者无法按时领取休沐令",
            "pov":"钟暮亲眼可见和听到的有限范围",
            "needs":["dialogue","decision"],
        },
        "prose":(
            "钟暮把工房来函倒过来，纸背沾着一小块灰，像有人用手指将未干的墨抹走了。"
            "司书已经拿起盖章的木柄，问他还有什么可查。钟暮没有说那枚灰印必是伪证，"
            "只指出两个值日人的名字被写在同一天，而他们在更漏簿上分别领的是前后两班。"
            "司书将木柄搁在桌角，让他把更漏簿拿近些。门外的钟敲了第二下，"
            "等候发休沐令的几个人都听见了。有人先开口埋怨钟暮多事。"
            "钟暮看了看那人，又低头寻找更漏簿上被折起来的一角。"
            "这一晚究竟是谁写错了班次，他还不能断言；屋里的等待却已经真切地延长了。"
        ),
    },
    {
        "id":"unknown-navigation-log",
        "xuehai_cluster":"cc-08-sky-sail-log",
        "goal":"赤星航海舵师和船医争论白石群，铜雀哑了而水桶里有盐味",
        "outline":"闻舟发现望潮台原先记下的海路与实际天色不符，不能凭猜测断定远海有人设伏。",
        "decision":"SKIP",
        "reason":"这篇航海日志保留未知的做法值得讨论，但此章更需要即时行动和具体人物关系，我决定暂不采用它的叙述结构。",
        "plan":{
            "objective":"闻舟先确认航向是否真的偏离了旧路标",
            "conflict":"舵师说夜潮是寻常变化，水手却要立即折返",
            "decision":"闻舟选择保留两份方位记录并请求再测一次",
            "outcome":"船耽误了靠近海峡前的一段顺风时间",
            "pov":"闻舟眼前听见与看到的海上现场",
            "needs":["scene","dialogue"],
        },
        "prose":(
            "晌午过后，闻舟在甲板最干的地方摊开旧航图，图上那道蓝线已经被盐染得发白。"
            "掌舵的人说水声变重只是潮向转了，守望的水手却从船舷捞起一片陌生的黑木，"
            "坚持附近另有船只。闻舟翻过木片，背面既没有刻字，也没有绳孔。"
            "他说这件东西不能证实对方是谁，先把它放在船头备用。"
            "有人不肯等，扯开半张帆，想让船快些掉头。舵师冲过去夺缆，"
            "两个人在风里僵着，谁也不愿先松手。闻舟最终叫人量一次日影，"
            "但船已经漂过了一片顺风的水面。风是过去了，黑木来自哪里仍没有定论。"
        ),
    },
)


def _run_fixture_scene(*, db_path:Path, scene:dict, root:Path) -> dict:
    """Runs production writing_assist; no mock story memory or model scoring."""
    copyfile(db_path, root / (scene["id"]+".sqlite3"))
    fresh=root / (scene["id"]+".sqlite3")
    db=WriterForgeDB(fresh)
    rt=RuntimeEngine()
    sid=XuehaiStore(db,rt).latest_published()
    if not isinstance(sid,int):
        raise ValueError("WF0CG_PUBLISHED_SNAPSHOT_MISSING")
    rt.enter_write(sid)
    try:
        study=XuehaiStore(db,rt).select_literary_reading_for_author(
            goal=scene["goal"],max_chars=4900)
        if study is None:
            raise ValueError("WF0CG_NO_RELEVANT_COMPLETE_READING")
        target=db.conn.execute(
            "SELECT id FROM xuehai_entries WHERE method_cluster=? AND "
            "source_role='original_annotation_reflection'",
            (scene["xuehai_cluster"],)).fetchone()
        if target is None or study["entry_id"]!=target["id"]:
            raise ValueError("WF0CG_EXPECTED_DIFFERENT_READ_SOURCE")
        assert all(x in study["complete_reading"] for x in
                   ("【原文】","【批注】","【心得】"))
        calls=[]
        def fixed_author(packet,*,model,api_base,max_tokens):
            calls.append({"sha256":packet.prompt_sha256,"tokens":max_tokens})
            if len(calls)==1:
                if study["complete_reading"] not in packet.prompt:
                    raise AssertionError("WF0CG_R2_FULL_READING_NOT_IN_AUTHOR_PLAN")
                if "【不要混淆阅读取舍与剧情抉择】" not in packet.prompt:
                    raise AssertionError("WF0CG_AUTHOR_READING_VS_PLOT_NOT_SEPARATED")
                return json.dumps({
                    **scene["plan"],
                    "reading_choice":{
                        "decision":scene["decision"],
                        "reason":scene["reason"],
                    },
                },ensure_ascii=False)
            if len(calls)!=2:
                raise AssertionError("WF0CG_EXTRA_AUTHOR_PROVIDER_CALL")
            if '"writer_reading_choice"' not in packet.prompt:
                raise AssertionError("WF0CG_READING_CHOICE_NOT_CARRIED_TO_PROSE")
            if scene["reason"] not in packet.prompt:
                raise AssertionError("WF0CG_AUTHOR_REASON_NOT_CARRIED")
            return scene["prose"]
        assist=InvisibleWritingAssist(
            db,rt,"wf0cg-existing-r2-snapshot",
            scene["id"],scene["goal"],
            model="NO_REAL_MODEL_FIXTURE",
            api_base="http://127.0.0.1:1",
            source_genre="玄幻",
        )
        with patch("writerforge.writing_assist.local_chat_completion",
                   side_effect=fixed_author):
            out=AutonomousWriting(assist).run(
                outline=scene["outline"],
                chapter_goals=[scene["goal"]],
                output_dir=root / (scene["id"]+"-working"),
                draft_mode="single",
                xuehai_readings_enabled=True,
            )
        if (len(calls)!=2 or out["chapter_count"]!=1 or
            out["wf_literary_readings_delivered"]!=1 or
            out["wf_literary_readings_author_used"]!=int(scene["decision"]=="USE") or
            out["wf_literary_readings_author_skipped"]!=int(scene["decision"]=="SKIP") or
            out["chapters"][0]["accepted"] is not False):
            raise ValueError("WF0CG_GENUINE_AUTHOR_FLOW_CONTRACT_BROKEN")
        chapter=out["chapters"][0]
        if Path(chapter["candidate"]).read_text("utf8")!=scene["prose"]:
            raise ValueError("WF0CG_UNACCEPTED_PROSE_REWRITTEN_OR_MISSING")
        receipt=chapter["wf_literary_reading_before_planning"]
        if (receipt["reading_sha256"]!=study["reading_sha256"] or
            receipt["planning_prompt_sha256"]!=calls[0]["sha256"] or
            receipt["model_reading_decision"]!=scene["decision"] or
            receipt["model_reading_reason"]!=scene["reason"]):
            raise ValueError("WF0CG_AUTHOR_FULL_READING_CHOICE_RECEIPT_FAILED")
        return {
            "scene":scene["id"],
            "choice_from_FIXED_MODEL_REPLY":scene["decision"],
            "model_calls_substituted":2,
            "full_reading_source_sha256":study["reading_sha256"],
            "original_chars":study["original_chars"],
            "readings_before_author_planning":True,
            "candidate_text_unchanged":True,
            "candidate_author_accepted":False,
        }
    finally:
        rt.exit()
        db.close()


def exercise_existing_r2_author_pipeline():
    with TemporaryDirectory(prefix="wf0cg-existing-private-r2-author-") as folder:
        root=Path(folder)
        vault=_vault(cold_only=True)
        restored=vault.restore(
            library=LIBRARY,
            snapshot=PINNED_SNAPSHOT,
            destination=root/"restored")
        restored_db=Path(restored["db"])
        first=inspect_literary_db(restored_db)
        if (restored["snapshot"]!=PINNED_SNAPSHOT or
            first["content_sha256"]!=PINNED_CONTENT or
            first["contents"]!=126 or
            first["complete_three_part_readings"]!=78):
            raise ValueError("WF0CG_R2_CONTENT_PIN_MISMATCH")
        # Use the existing 0.BY author smoke against a COPY of the actual
        # restored 126-entry database: baseline / USE / SKIP; copy rejection.
        old= root/"0by-legacy-context-test.sqlite3"
        copyfile(restored_db,old)
        first_three=run_smoke(old)
        if (first_three["real_provider_model_calls"]!=0 or
            [row["author_choice"] for row in
             first_three["baseline_and_reading_prompts_compared"]]!=
             ["NOT_ASKED","USE","SKIP"] or
            first_three["verbatim_model_copy_rejected"] is not True):
            raise ValueError("WF0CG_R2_AUTHOR_BASELINE_VS_READING_REGRESSED")
        cross=[_run_fixture_scene(db_path=restored_db,
                                 scene=scene,root=root)
               for scene in SCENARIOS]
        second=inspect_literary_db(restored_db)
        if second!=first:
            raise ValueError("WF0CG_R2_COLD_SOURCE_MUTATED_BY_AUTHOR_RUN")
        return {
            "status":"WF0CG_EXISTING_R2_LITERATURE_USED_IN_REAL_AUTHOR_PIPELINE_FIXTURE_ONLY",
            "r2_pinned_snapshot":PINNED_SNAPSHOT,
            "content_sha256":PINNED_CONTENT,
            "literary_entries":first["contents"],
            "complete_three_part_readings":first["complete_three_part_readings"],
            "baseline_USE_SKIP_also_replayed":True,
            "two_distinct_scene_author_tests":cross,
            "author_model_responses_fixed_not_real":True,
            "actual_paid_or_local_model_inferences":0,
            "scripted_author_model_reply_calls":12,
            "true_literary_skill_gain_demonstrated":False,
            "production_railway_touched":False,
            "r2_writes":0,
            "canon_writes":0,
            "previous_remote_source_unchanged":True,
        }


if __name__=="__main__":
    print(json.dumps(exercise_existing_r2_author_pipeline(),
                     ensure_ascii=False,sort_keys=True))
