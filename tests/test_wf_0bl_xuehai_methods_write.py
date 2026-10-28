"""WF 0.BL P0 RED: real-source Xuehai method -> actual author WRITE.

All sources here are newly written test material. No novel archive, R2, Canon,
paid model, AI quality claim, or synthetic 'studied masterpiece' rows.
"""
from __future__ import annotations

from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import json
import re
import unittest

from writerforge import (
    WriterForgeDB, RuntimeEngine, OriginalStudy, XuehaiStore,
    VerifiedWritingFlow, WritingExecutionError,
)
from writerforge.writing_assist import InvisibleWritingAssist, AutonomousWriting

SOURCE = (
    "第一回 炉火未定\n\n"
    "老丹师守着石炉等徒弟回来，炉沿忽然凝起一圈浅白的薄沫。"
    "他取了铜片试温，嗅到异味，却还不知道是哪味草出了差错。"
    "徒弟催着添柴，他先把柴挪远，决定留下一份药液查验。\n"
    "师兄来取丹药时，只看见火苗被压低；没人告诉他药液已坏。"
)
ALCHEMY = {
    "scene_type": "炼丹",
    "scene_facets": ["炉温", "药性", "损耗"],
    "target_genres": ["玄幻"],
    "style_scope": "ERA_NEUTRAL",
    "signal": "炉沿起细沫且气味发生变化",
    "mechanism": "角色先检验有限证据，误差改变投药顺序和损耗",
    "writer_option": "作者可让丹师暂停下一味药并面对材料不足",
    "applies_when": "正在炼丹且前一步操作影响之后的结果",
    "not_when": "场景没有炼丹工艺或不需要操作风险时",
    "pov_limit": "角色只能根据当下气味与试片判断，不能全知",
    "counterexample": "不要让七彩光芒自动代替选择与成本",
    "source_kind": "AUTHOR_CREATED_ORIGINAL",
    "source_edition": "WF原创独立测试第1稿，非古籍",
    "rights_status": "RIGHTS_VERIFIED",
    "review_status": "PILOT_APPROVED",
    "value_status": "UNPROVEN_PILOT",
    "review_receipt_sha256": sha256("仅用于隔离写作通路测试；已核对原创来源及条件".encode()).hexdigest(),
}

PLAN = json.dumps({
    "objective": "处理丹炉不稳定的当前决策",
    "conflict": "师兄催促交丹与药液异常冲突",
    "decision": "先检验药液而非交付",
    "outcome": "材料损耗与双方关系发生改变",
    "pov": "丹师能观察到炉火但不知道外面的事",
    "needs": ["decision", "scene"],
}, ensure_ascii=False)
BODY = ("丹师试过那块铜片，终于决定先停火。他知道这一停会让明天的交货落空，"
        "却并不清楚是否有人动过药匣。徒弟去拦来取货的人，两人都不肯先把原因说透。") * 3


class XuehaiMethodWriteP0(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.path = Path(self.tmp.name) / "owned-source.db"
        self.db = WriterForgeDB(self.path)
        self.rt = RuntimeEngine()
        self.rt.enter_learn()
        # Ingest an ACTUAL intact, newly authored source via OriginalStudy.
        result = OriginalStudy(self.db, self.rt).ingest(
            SOURCE, work_id="wf0bl-owned-p0", title="独立原创写作来源",
            source_uri="wf-original-fixture://0bl/p0",
            require_hundred=False,
        )
        self.assertEqual(result["studied_chapters"], 1)
        parent = self.db.conn.execute(
            "SELECT snapshot_id FROM studied_chapters WHERE work_id=?",
            ("wf0bl-owned-p0",)
        ).fetchone()["snapshot_id"]
        self.store = XuehaiStore(self.db, self.rt)
        self.child = self.store.create_staging_snapshot(parent_id=parent)
        span = self.db.conn.execute(
            "SELECT * FROM source_spans WHERE work_id=? ORDER BY paragraph,sentence LIMIT 1",
            ("wf0bl-owned-p0",)
        ).fetchone()
        self.entry = self.store.add_entry(
            self.child, work_id="wf0bl-owned-p0", text=span["excerpt"],
            chapter=span["chapter"], paragraph=span["paragraph"],
            sentence=span["sentence"], library_class="原创隔离测试",
            culture="中国", genre="玄幻", source_role="core",
            function="炼丹", effect="抉择后果", method_cluster="owned-alchemy",
        )

    def tearDown(self):
        self.db.close()
        self.tmp.cleanup()

    def _publish(self, card=None):
        result = self.store.add_method_card(
            self.entry, dict(ALCHEMY if card is None else card)
        )
        self.assertRegex(result["card_sha256"], "^[0-9a-f]{64}$")
        self.store.publish(self.child)
        self.rt.exit()
        self.rt.enter_write(self.child)
        return result

    def test_approved_method_is_bounded_and_genre_falls_back(self):
        saved = self._publish()
        found = self.store.query_methods(
            goal="修真丹师正在炼丹，丹炉出现异常，必须在添药和停火之间选择",
            genre="修真",
        )
        self.assertEqual(len(found["selected"]), 1)
        self.assertEqual(found["selected"][0]["card_sha256"], saved["card_sha256"])
        self.assertIn("暂停下一味药", found["prompt_guidance"])
        self.assertIn("可自行选择不采用", found["prompt_guidance"])
        self.assertLessEqual(len(found["prompt_guidance"]), 300)
        self.assertNotIn("老丹师守着石炉", found["prompt_guidance"])
        self.assertEqual(found["receipt"]["snapshot_id"], self.child)
        self.assertEqual(found["receipt"]["selected"][0]["rights_status"], "RIGHTS_VERIFIED")
        self.assertEqual(found["receipt"]["selected"][0]["review_status"], "PILOT_APPROVED")

    def test_verified_prepare_can_use_genre_parent_without_false_no_source(self):
        self._publish()
        flow = VerifiedWritingFlow(self.db,self.rt,"p0")
        packet = flow.prepare(
            "alchemy", "修真丹师正在炼丹，炉火与药性出现冲突",
            genre="修真", xuehai_methods_enabled=True,
        )
        self.assertIn("作者可让丹师暂停", packet.prompt)
        self.assertEqual(packet.manifest()["xuehai_methods"]["genre_path"][:3],
                         ["修真","仙侠","玄幻"])

    def test_classical_only_cannot_be_accidentally_injected_into_xuanhuan(self):
        card=dict(ALCHEMY)
        card["style_scope"]="CLASSICAL_ONLY"
        self._publish(card)
        found=self.store.query_methods(goal="正在炼丹，丹炉需要停火",genre="玄幻")
        self.assertEqual(found["selected"], [])

    def test_revocation_disables_published_card_without_rewriting_source(self):
        saved=self._publish()
        self.rt.exit()
        self.rt.enter_learn()
        self.assertTrue(self.store.revoke_method_card(self.entry))
        self.rt.exit()
        self.rt.enter_write(self.child)
        result=self.store.query_methods(goal="正在炼丹，火候异常",genre="玄幻")
        self.assertEqual(result["selected"], [])
        self.assertTrue(any(x.get("reason")=="REVOKED" for x in result["receipt"]["rejected"]))
        prior=self.db.conn.execute("SELECT card_sha256 FROM xuehai_method_cards WHERE entry_id=?",
                                   (self.entry,)).fetchone()["card_sha256"]
        self.assertEqual(prior,saved["card_sha256"])

    def test_quiet_household_and_wuxia_are_none_not_keyword_shopping(self):
        self._publish()
        quiet = self.store.query_methods(goal="平静的家中有人问明日的早饭",genre="修真")
        self.assertEqual(quiet["selected"], [])
        self.assertEqual(quiet["prompt_guidance"], "")
        other = self.store.query_methods(goal="丹炉前修理小物件",genre="武侠")
        self.assertEqual(other["selected"], [])

    def test_unapproved_or_unlicensed_are_never_in_prompt(self):
        for label, field in [
            ("rights", "rights_status"), ("review", "review_status")
        ]:
            with self.subTest(label=label):
                card = dict(ALCHEMY)
                card[field] = "RIGHTS_UNVERIFIED" if field=="rights_status" else "PENDING"
                # Stored for auditing, NEVER selected.
                self._publish(card)
                pkt = VerifiedWritingFlow(self.db,self.rt,"p0").prepare(
                    "alchemy", "正在炼丹，丹炉异样需改变选择", genre="玄幻",
                    xuehai_methods_enabled=True,
                )
                self.assertNotIn("作者可让丹师暂停",pkt.prompt)
                self.assertEqual(pkt.manifest()["xuehai_methods"]["selected"], [])
                break

    def test_staging_never_usable_even_if_card_claims_review(self):
        self.store.add_method_card(self.entry, dict(ALCHEMY))
        self.rt.exit()
        self.rt.enter_write(self.child)
        with self.assertRaisesRegex(ValueError, "published"):
            self.store.query_methods(goal="正在炼丹",genre="玄幻")
        with self.assertRaises(WritingExecutionError):
            VerifiedWritingFlow(self.db,self.rt,"p0")

    def test_source_provenance_and_card_hash_fail_closed(self):
        card = dict(ALCHEMY)
        card["source_kind"] = "REFERENCE_ONLY_RIGHTS_UNVERIFIED"
        with self.assertRaises(ValueError):
            self.store.add_method_card(self.entry,card)
        # A real row without source study/spans cannot be promoted by a fake flag.
        fake_id = self.store.add_entry(
            self.child,work_id="missing-source-work",text="没有实际来源的假样本",
            genre="玄幻",culture="中国",
        )
        with self.assertRaisesRegex(ValueError,"SOURCE"):
            self.store.add_method_card(fake_id, dict(ALCHEMY))
        self._publish()
        # Post-review DB mutation must not reframe the approved method.
        self.db.conn.execute(
            "UPDATE xuehai_method_cards SET writer_option=? WHERE entry_id=?",
            ("未经审核的替换指令",self.entry),
        )
        self.db.conn.commit()
        found=self.store.query_methods(goal="正在炼丹，丹炉异样",genre="玄幻")
        self.assertEqual(found["selected"], [])
        self.assertNotIn("未经审核",found["prompt_guidance"])

    def test_real_verified_prepare_and_autonomous_author_body_use(self):
        saved=self._publish()
        flow=VerifiedWritingFlow(self.db,self.rt,"p0")
        body=flow.prepare(
            "alchemy", "炼丹火候不稳，角色在停火和添药之间选择",
            genre="玄幻",xuehai_methods_enabled=True,
        )
        self.assertIn("作者可让丹师暂停",body.prompt)
        self.assertNotIn("老丹师守着石炉",body.prompt)
        self.assertEqual(
            body.prompt_sha256,sha256(body.prompt.encode()).hexdigest(),
        )
        self.assertEqual(
            body.manifest()["xuehai_methods"]["selected"][0]["card_sha256"],
            saved["card_sha256"],
        )
        assist=InvisibleWritingAssist(
            self.db,self.rt,"p0","alchemy","让丹师根据炉火作决定",
            model="synthetic-fixture-only",api_base="http://127.0.0.1:1234/v1",
            source_genre="玄幻",
        )
        with patch("writerforge.writing_assist.local_chat_completion",side_effect=[PLAN,BODY]) as model:
            result=AutonomousWriting(assist).run(
                outline="炼丹出现异常，交货承诺和药材损失逼丹师作选择。",
                chapter_goals=["炼丹：丹炉温度变化，必须先决定是否添药"],
                output_dir=Path(self.tmp.name)/"generated",
                draft_mode="single",
                xuehai_methods_enabled=True,
            )
        self.assertEqual(model.call_count,2)
        planning=model.call_args_list[0].args[0]
        drafting=model.call_args_list[1].args[0]
        self.assertNotIn("作者可让丹师暂停", planning.prompt)
        self.assertIn("作者可让丹师暂停", drafting.prompt)
        self.assertEqual(drafting.prompt_sha256,sha256(drafting.prompt.encode()).hexdigest())
        self.assertEqual(result["chapters"][0]["accepted"], False)
        record=json.loads(Path(result["chapters"][0]["manifest"]).read_text("utf8"))
        self.assertEqual(record["xuehai_methods"]["selected"][0]["card_sha256"],saved["card_sha256"])
        self.assertFalse(record["xuehai_methods"]["literary_benefit_proven"])


if __name__ == "__main__":
    unittest.main()
