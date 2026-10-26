"""0.AM: source-first ONE real prior writer text through actual G rewind.

The historical micro-scene was written by DeepSeek Flash in 0.AH:
Actions 40201458798, immutable SHA below. The downstream *model responses*
in this test are deterministic fixtures, never mislabelled as real writing.
A genuine provider one-shot is a separate step only after these regressions.
No R2, Canon, book training, main, or Railway.
"""
from __future__ import annotations

from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch
import json

from writerforge import WriterForgeDB, RuntimeEngine
from writerforge.writing_assist import AutonomousWriting, InvisibleWritingAssist
from writerforge.v114_external_story_state import external_temporal_step
from writerforge.v117_continuity_trace import make_resume, read_resume
from writerforge.narrative_core import new_graph, read_core_from_resume
from test_v26_invisible_writer import make_db
from test_wf_0ai_decision_effect_pending import HISTORY_REAL, HISTORY_REAL_SHA

CAST=("秦渊","驿卒")
FIRST_ACTION="秦渊决定先核对驿道上的换马记录"
OLD_LIGHT="秦渊把案角的残灯移开"
NEW_LIGHT="秦渊将灯芯压低半分"
FIRST=(OLD_LIGHT+
    "，叫亲兵别再追问主帅的回信。昨夜那三封斥候回报仍在案上，"
    "北路的空白最叫他放心不下。"+FIRST_ACTION+
    "，没有立刻宣称文书已经送到。门外脚步停停走走，"
    "他只记下自己实际听到的时刻；营门外究竟是谁过桥，他还不能看见。")
OLD_NEXT=(
    "更深的夜色盖住驿道，秦渊仍坐在驿站桌旁等候。"
    "他听到院里有人搬动木桶，却没有认定那是送信骑手。"
    "一个年轻兵士问要不要再放一骑，他先让人核对马匹脚力和换马距离。"
    "窗纸映出两道人影，写下的消息还没有能越过漫长的山路。")
NEW_NEXT=(
    "秦渊压低灯芯后，桌上的阴影短了一些。"
    "秦渊摊开驿道记录，仍然数不清北路缺失的那一段。"
    "他听见院里有人搬水桶，却不再据此猜测主帅的回应。"
    "兵士默默将两匹马拴在屋檐下，是否另派骑手仍由秦渊来定。"
    "山路还在夜色里，文书并没有因为他们的焦急就提前送到。")
OUTLINE=(
    "这是此前 DeepSeek 所写且冻结的边关传令原稿。"
    "秦渊必须保持夜间传令尚未到达主帅的有限认知，"
    "人物可以在未观察到后果前决定等待、核对、追问。"
    "只续写这一条原创情境，不复制成熟小说，也不虚构主帅已经接信。")
GOAL="秦渊在旧驿站核对送信时间，察觉自己可能误解营门马蹄，尚不能知道主帅是否收到书信。"
BEATS={"turns":[
    {"id":"t01","kind":"decision","actor":"秦渊",
     "goal":"写出秦渊选择核对驿道记录而未观察到文书抵达",
     "causal_parent":None,"craft_focus":[]},
    {"id":"t02","kind":"quiet","actor":"秦渊",
     "goal":"实际第二段继续观察而非将推测晋级为传令事实",
     "causal_parent":"t01","craft_focus":[]},
]}
PLAN={
    "objective":"秦渊核对边关驿道已写文书的送达路径",
    "conflict":"马蹄声不等于已经有人收到文书",
    "decision":"先核对换马记录再判断是否发出催令",
    "outcome":"所知仍有限，必须等到实际有回报才能决策",
    "pov":"秦渊的有限视角","needs":["decision","detail"],
}


def h(s):
    return sha256(s.encode("utf8")).hexdigest()


def scene(prose,action=None,effect=None,parent=None):
    return json.dumps({
        "prose":prose,
        "trace":{"action_quote":action,"effect_quote":effect,
                 "parent_effect_quote":parent}},
        ensure_ascii=False,separators=(",",":"))


def choice(decision,target,source,quote=None):
    looking=decision=="LOOK_BACK_NOW"
    return json.dumps({
        "decision":decision,"target_turn":target,
        "source_sha256":h(source),
        "evidence_quote":quote if looking else None,
        "focus":"sentence" if looking else None,
        "why_now":("先前灯下的动作太像机械交代，缺少秦渊眼下的谨慎。"
                   if looking else "这里仍有未解问题，现有节奏允许自然继续。"),
        "what_goes_wrong_if_unchanged":(
            "如果先前动作不改，读者会以为这一刻人物毫不在意消息传播的时间。"
            if looking else None),
        "intended_reader_effect":(
            "让人物处理灯下细节的动作和核对消息的意图更自然地相接。"
            if looking else None)},
        ensure_ascii=False,separators=(",",":"))


def edit():
    start=FIRST.index(OLD_LIGHT)
    return json.dumps({
        "decision":"REVISE","scope":"sentence",
        "source_sha256":h(FIRST),"start":start,
        "end":start+len(OLD_LIGHT),
        "expected_original":OLD_LIGHT,
        "replacement":NEW_LIGHT,
        "trace":{"action_quote":FIRST_ACTION,"effect_quote":None,
                 "parent_effect_quote":None},
        "reason":"原先开场动作太机械，作者希望保持谨慎并改变后文节奏。",
    },ensure_ascii=False,separators=(",",":"))


def model_replies():
    return [
        json.dumps(PLAN,ensure_ascii=False),
        json.dumps(BEATS,ensure_ascii=False),
        scene(FIRST,FIRST_ACTION),
        choice("MOVE_ON","current",FIRST),
        scene(OLD_NEXT),
        choice("LOOK_BACK_NOW","previous",FIRST,OLD_LIGHT),
        edit(),
        scene(NEW_NEXT),
        choice("MOVE_ON","current",NEW_NEXT),
    ]


class RealArchivedHistorySourceGClosure(TestCase):
    def test_historical_author_SHA_and_pending_decision_real_G_transaction(self):
        self.assertEqual(h(HISTORY_REAL),HISTORY_REAL_SHA)
        self.assertIn("最快要到明日卯时",HISTORY_REAL)
        with TemporaryDirectory() as tmp:
            work=Path(tmp)
            dbpath=work/"local_source_only.sqlite3"
            sid=make_db(dbpath)
            db=WriterForgeDB(dbpath)
            try:
                rt=RuntimeEngine()
                rt.enter_write(sid)
                assist=InvisibleWritingAssist(
                    db,rt,"0am-history-source-candidate",
                    "history-messenger-source-replay",
                    "仅用真实原作者已经写出的文书送达时间作前史。",
                    model="fixture-same-writer",api_base="http://127.0.0.1:1234/v1")
                prior=external_temporal_step(HISTORY_REAL,cast=CAST)
                graph=new_graph(project_id=assist.project_id,
                                scene_id=assist.scene_id,chapter_index=0)
                root=make_resume(
                    project_id=assist.project_id,scene_id=assist.scene_id,
                    chapter_index=0,checkpoint=prior,
                    unified_narrative_core=graph)
                self.assertFalse(root["author_accepted"])
                raw_root=json.dumps(root,ensure_ascii=False,sort_keys=True)
                replies=model_replies()
                with patch("writerforge.writing_assist.local_chat_completion",
                           side_effect=replies) as provider:
                    result=AutonomousWriting(assist).run(
                        outline=OUTLINE+"\n【先前真实写作候选，未接受】"+HISTORY_REAL,
                        chapter_goals=[GOAL],
                        draft_mode="continuity_guard",
                        resume_story_checkpoint=root,
                        self_edit_rounds=1,self_edit_timing="ai_decides",
                        output_dir=work/"candidate-only")
                self.assertEqual(provider.call_count,len(replies))
                self.assertEqual(json.dumps(root,ensure_ascii=False,sort_keys=True),
                                 raw_root)
                self.assertEqual(root["source_checkpoint_sha256"],
                                 prior["receipt_sha256"])
                self.assertEqual(result["wf_self_edit_previous_turn_rewinds"],1)
                self.assertEqual(result["wf_self_edit_canon_writes"],0)
                actual=Path(result["chapters"][0]["candidate"]).read_text("utf8")
                self.assertIn(NEW_LIGHT,actual)
                self.assertIn("秦渊压低灯芯后",actual)
                self.assertNotIn(OLD_LIGHT,actual)
                self.assertNotIn("更深的夜色盖住驿道",actual)
                discarded=Path(result["job_dir"])/(
                    "chapter-001-turn-02-invalidated-downstream-01.json")
                self.assertTrue(discarded.exists())
                self.assertIn(OLD_NEXT,discarded.read_text("utf8"))
                resumed=json.loads(Path(result["chapters"][0][
                    "v117_unreviewed_text_trace_resume"]).read_text("utf8"))
                verified=read_resume(resumed,project_id=assist.project_id,
                                     scene_id=assist.scene_id)
                self.assertEqual(verified["receipt_sha256"],
                                 resumed["source_checkpoint_sha256"])
                next_graph=read_core_from_resume(
                    resumed,project_id=assist.project_id,
                    scene_id=assist.scene_id)
                self.assertEqual(next_graph["parent_sha256"],graph["receipt_sha256"])
                self.assertTrue(next_graph["source_temporal_link"][
                    "source_assembly_verified"])
                self.assertTrue(next_graph["source_temporal_link"][
                    "ancestry_fully_verified"])
            finally:
                db.close()


if __name__=="__main__":
    import unittest
    unittest.main()
