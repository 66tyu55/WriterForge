"""0.BL: the actual V98 G core author receives only opted-in published methods.

Three arms are synthetic fixture-only, not a new local-model literary trial.
No real model, no provider tokens, no R2, no Canon or review-promotion.
"""
from __future__ import annotations

from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import unittest

from writerforge import WriterForgeDB,RuntimeEngine,OriginalStudy,XuehaiStore
from writerforge.writing_assist import InvisibleWritingAssist,AutonomousWriting
from experiments.wf_0bk_actual_writer_three_arm_host_gate import BareDraftPacket
from test_wf_0bk_true_three_arm_author_core import SyntheticHost,OUTLINE,SOURCE

STORY=(
    "第一回 石桥疑云\n\n"
    "守桥人留下告示，少年仍有疑虑。女子准备查阅账册，却并不知道谁改动了桥索。"
    "水中有一块断木撞上桥墩；她听着绳索响动，决定先询问最后一位过桥的脚夫。"
)
GOAL="石桥：先处理真实桥边动作，再处理旧账册记载的往事，保留不同立场。"
METHOD={
    "scene_type":"石桥","scene_facets":["桥索","旧告示"],
    "target_genres":["古代白话"],"style_scope":"ERA_NEUTRAL",
    "signal":"告示与桥索现状不符",
    "mechanism":"现场证据迫使角色判断是否渡河并承担风险",
    "writer_option":"作者可以让持册者先核验过桥人的信息再决定去留",
    "applies_when":"渡桥风险与不可靠的告示形成眼前冲突",
    "not_when":"没有桥索风险或告示与人物选择无关时",
    "pov_limit":"只凭亲历判断，不可预知改桥索者身份",
    "counterexample":"不要让旁白直接报出未查明的真相",
    "source_kind":"AUTHOR_CREATED_ORIGINAL",
    "source_edition":"WF独立原创桥边机制样本第一稿",
    "rights_status":"RIGHTS_VERIFIED",
    "review_status":"PILOT_APPROVED",
    "value_status":"UNPROVEN_PILOT",
    "review_receipt_sha256":sha256("仅授权在隔离测试中使用原创样本".encode()).hexdigest(),
}

class TrueGWithXuehaiFixture(unittest.TestCase):
    def setUp(self):
        self.t=TemporaryDirectory()
        self.root=Path(self.t.name)

    def tearDown(self):
        self.t.cleanup()

    def fresh(self,arm):
        db=WriterForgeDB(self.root/(arm+".sqlite"))
        rt=RuntimeEngine()
        rt.enter_learn()
        res=OriginalStudy(db,rt).ingest(
            STORY,work_id="wf0bl-own-bridge",
            title="独立原创桥边源",source_uri="wf-original-fixture://0bl/bridge",
            require_hundred=False)
        self.assertEqual(res["studied_chapters"],1)
        parent=db.conn.execute(
            "SELECT snapshot_id FROM studied_chapters WHERE work_id='wf0bl-own-bridge'"
        ).fetchone()["snapshot_id"]
        x=XuehaiStore(db,rt)
        sid=x.create_staging_snapshot(parent_id=parent)
        span=db.conn.execute(
            "SELECT * FROM source_spans WHERE work_id='wf0bl-own-bridge' "
            "ORDER BY paragraph,sentence LIMIT 1"
        ).fetchone()
        entry=x.add_entry(
            sid,work_id="wf0bl-own-bridge",text=span["excerpt"],
            chapter=span["chapter"],paragraph=span["paragraph"],
            sentence=span["sentence"],genre="古代白话",culture="中国",
            source_role="core",function="石桥",method_cluster="bridge-scene")
        x.add_method_card(entry,dict(METHOD))
        x.publish(sid)
        rt.exit()
        rt.enter_write(sid)
        return db,InvisibleWritingAssist(
            db,rt,"novel","s1",GOAL,model="fixture-author",
            api_base="http://127.0.0.1:1234/v1",
            source_genre="古代白话")

    def test_bare_and_two_true_G_core_arms_with_only_prose_method_delta(self):
        host=SyntheticHost()
        raw="你是小说作者。请基于前文创作新正文。\n"+"\n".join(SOURCE)+"\n"+GOAL
        bare=BareDraftPacket(raw,sha256(raw.encode()).hexdigest())
        b=host(bare,arm="bare",model="fixture-author",
               max_tokens=2600,api_base="local-only")
        self.assertEqual(b.source_kind,"SYNTHETIC_TEST_ONLY")
        packets_by_arm={}
        for arm,enable in (("wf_core",False),("wf_xuehai",True)):
            db,assist=self.fresh(arm)
            calls=[]
            def callback(packet,*,model,api_base,max_tokens):
                calls.append(packet)
                return host(packet,arm=arm,model=model,
                            max_tokens=max_tokens,api_base=api_base).content
            try:
                with patch("writerforge.writing_assist.local_chat_completion",
                           side_effect=callback):
                    out=AutonomousWriting(assist).run(
                        outline=OUTLINE+"\n【已写前文仅为候选来源】"+"\n".join(SOURCE),
                        chapter_goals=[GOAL],
                        output_dir=self.root/(arm+"-working"),
                        draft_mode="continuity_guard",
                        bootstrap_unified_core=True,
                        narrative_memory_backend="local",
                        g_rolling_author_planning=True,self_edit_rounds=0,
                        xuehai_methods_enabled=enable,
                    )
                self.assertEqual(out["chapter_count"],1)
                self.assertFalse(out["chapters"][0]["accepted"])
                self.assertTrue(out["chapters"][0]["unified_narrative_core_sha256"])
                self.assertEqual(len(calls),5)
                self.assertTrue(all(sha256(p.prompt.encode()).hexdigest()==
                                    p.prompt_sha256 for p in calls))
                packets_by_arm[arm]=calls
            finally:
                db.close()
        self.assertEqual([len(host.by_arm[a]) for a in
                          ("bare","wf_core","wf_xuehai")],[1,5,5])
        self.assertFalse(any("作者可以让持册者" in p.prompt for p in
                             packets_by_arm["wf_core"]))
        learned=packets_by_arm["wf_xuehai"]
        # Only actual prose body; planning/replanning remains the same core.
        self.assertEqual(sum("作者可以让持册者" in p.prompt for p in learned),1)
        self.assertNotIn("作者可以让持册者",learned[0].prompt)
        self.assertTrue(any("可自行选择不采用" in p.prompt for p in learned))
        self.assertTrue(any("【本章总目标，未完成的规划不是故事事实】"
                            in p.prompt for p in learned))
        # All output strings were scripted: zero actual literary evidence.
        self.assertIsNone(b.provider_wire_sha256)

if __name__=="__main__":
    unittest.main()
