"""V25 encyclopedia: correct taxonomy, retain ALL occurrences, verified-only writing.

All quoted sentences are synthetic; no modern copyrighted novel prose is
committed into the public WriterForge repository.
"""
from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import sqlite3
import unittest

from writerforge import WriterForgeDB, RuntimeEngine
from writerforge.encyclopedia import (
    FictionEncyclopedia, FacetQuery, EncyclopediaError,
    validate_category_path,
)
from writerforge.verified_flow import VerifiedWritingFlow


BEAST = "火蟒虎通体毛发赤红，虎首，尾如火蟒，乃是深山里的妖兽。"
BEAST2 = "火蟒虎受伤后仍然护着幼崽，发出低沉咆哮。"
WILD = "蝎虎形似猛虎，长着一根蝎尾，是一头凶猛野兽。"
WOMAN = "青檀轻声安慰同伴，却执意自己走进风雪里。"
POOL = "偏僻山洞中央有一汪石池，水面漂浮着淡淡寒气。"
RANK = "宗门公布天骄榜，按试炼名次排列，榜首得入禁地。"
TRIB = "雷声落下之后，第四道天劫劈向山门，迫使修士退避。"


class FacetedLibraryTests(unittest.TestCase):
    def setUp(self):
        self.root=TemporaryDirectory()
        self.path=Path(self.root.name)/"facs.sqlite3"
        self.db=WriterForgeDB(self.path)
        self.rt=RuntimeEngine()
        self.rt.enter_learn()
        self.enc=FictionEncyclopedia(self.db,self.rt)
        for work_id in ("modern-test","another-novel"):
            self.db.conn.execute(
                """INSERT INTO studied_works(work_id,title,source_uri,source_sha256,chapter_count,script)
                   VALUES(?,?,?,?,?,'simplified_chinese')""",
                (work_id,"合成玄幻测试书","private://fiction-test","sha",45),
            )
        self.db.conn.execute(
            "INSERT INTO snapshots(parent_id,status,layout,note) VALUES(NULL,'published','full','synthetic')"
        )
        self.sid=self.db.conn.execute("SELECT MAX(id) FROM snapshots").fetchone()[0]
        for pos,chunk in ((1,BEAST),(2,BEAST2),(3,WILD),(4,WOMAN),(5,POOL),(6,RANK),(7,TRIB)):
            self.db.conn.execute(
                """INSERT INTO source_spans(work_id,chapter,paragraph,sentence,
                       excerpt,source_sha256,tracks_json,craft_json)
                   VALUES('modern-test',1,?,1,?,?,'{}','{}')""",
                (pos,chunk,"hash-"+str(pos)),
            )
        self.db.conn.execute(
            """INSERT INTO studied_chapters(work_id,chapter,chapter_sha256,heading,
                      source_spans,retrieval_entries,snapshot_id)
               VALUES('modern-test',1,'sha','test',7,7,?)""",(self.sid,),
        )
        self.db.conn.execute(
            """INSERT INTO xuehai_entries(snapshot_id,work_id,chapter,paragraph,sentence,
               text,library_class,culture,genre,source_role,function,effect,method_cluster,source_hash)
               VALUES(?,'modern-test',1,1,1,?,'现代网文','中国','玄幻','core',
                      'action_sequence','unverified','demo','sourcekey')""",
            (self.sid,BEAST),
        )
        self.db.conn.commit()

    def tearDown(self):
        self.db.close()
        self.root.cleanup()

    def _creature(self):
        return self.enc.entity(
            work_id="modern-test",name="火蟒虎",kind="creature",genre="玄幻",subtype="妖兽",
        )

    def _beast_entry(self,entity,paragraph=1,category="外貌/妖兽/虎形",
                     attribute="毛发",quotation=BEAST):
        return self.enc.observe(
            entity_id=entity,chapter=1,paragraph=paragraph,sentence=1,
            category_path=category,attribute=attribute,quotation=quotation,
            explanation="原文将兽首、体色与火蟒状尾巴组合",origin="model_candidate",
        )

    def test_every_occurrence_saved_and_paginated_not_collapsed(self):
        beast=self._creature()
        first=self._beast_entry(beast)
        second=self._beast_entry(
            beast,paragraph=2,category="行为/妖兽/护幼",
            attribute="护幼行为",quotation=BEAST2,
        )
        self.assertNotEqual(first,second)
        self.assertEqual(self._beast_entry(beast),first)  # dedup exact reruns
        view=self.enc.query(FacetQuery(entity_name="火蟒虎",status="all",limit=1))
        self.assertEqual(view["total_matches"],2)
        self.assertTrue(view["has_more"])
        nextpage=self.enc.query(FacetQuery(entity_name="火蟒虎",status="all",limit=1,offset=1))
        self.assertEqual(nextpage["total_matches"],2)
        self.assertNotEqual(view["items"][0]["id"],nextpage["items"][0]["id"])
        self.assertFalse(nextpage["has_more"])
        overview=self.enc.entity_overview(kind="creature")
        self.assertEqual(overview["entities"][0]["occurrences"],2)
        self.assertEqual(overview["entities"][0]["verified_occurrences"],0)
        self.assertEqual(self.enc.query(FacetQuery(entity_name="火蟒虎"))["total_matches"],0)
        self.enc.review(first,approved=True,reason="本人核对第1章外貌与实体",reviewer_confirmed=True)
        self.assertEqual(self.enc.query(FacetQuery(category_path="外貌/妖兽"))["total_matches"],1)
        self.enc.review(second,approved=True,reason="本人核对另一次护幼行为",reviewer_confirmed=True)
        self.assertEqual(self.enc.query(FacetQuery(entity_name="火蟒虎"))["total_matches"],2)
        self.assertEqual(
            {x["category_path"] for x in self.enc.query(FacetQuery(entity_name="火蟒虎"))["items"]},
            {"外貌/妖兽/虎形","行为/妖兽/护幼"},
        )

    def test_beast_vs_wild_animal_is_not_merged(self):
        tiger=self.enc.entity(work_id="modern-test",name="蝎虎",kind="creature",
                              genre="玄幻",subtype="野兽")
        with self.assertRaisesRegex(EncyclopediaError,"妖兽"):
            self.enc.observe(entity_id=tiger,chapter=1,paragraph=3,sentence=1,
                             category_path="外貌/妖兽/虎形",attribute="蝎尾",quotation=WILD)
        entry=self.enc.observe(
            entity_id=tiger,chapter=1,paragraph=3,sentence=1,
            category_path="外貌/野兽/虎形",attribute="蝎尾",quotation=WILD,
        )
        self.assertTrue(entry)
        self.assertEqual(
            self.enc.query(FacetQuery(category_path="外貌/妖兽",status="all"))["total_matches"],0
        )
        self.assertEqual(
            self.enc.query(FacetQuery(category_path="外貌/野兽",status="proposed"))["total_matches"],1
        )

    def test_female_character_cannot_be_confused_with_unverified_gender(self):
        unknown=self.enc.entity(work_id="modern-test",name="青檀",kind="character",
                                genre="玄幻")
        with self.assertRaisesRegex(EncyclopediaError,"female"):
            self.enc.observe(entity_id=unknown,chapter=1,paragraph=4,sentence=1,
                             category_path="性格/女性/坚韧",attribute="坚持",quotation=WOMAN)
        female=self.enc.entity(work_id="another-novel",name="青檀",kind="character",
                               genre="玄幻",gender="female")
        # Same name in different book is not globally conflated.
        self.assertNotEqual(unknown,female)
        with self.assertRaisesRegex(EncyclopediaError,"source"):
            self.enc.observe(entity_id=female,chapter=1,paragraph=4,sentence=1,
                             category_path="性格/女性/坚韧",attribute="坚持",quotation=WOMAN)
        with self.assertRaisesRegex(EncyclopediaError,"metadata differs"):
            self.enc.entity(work_id="modern-test",name="青檀",kind="character",
                            genre="玄幻",gender="female")
        self.assertEqual(self.enc.entity_overview(kind="character")["total_entities"],2)

    def test_place_and_ranked_system_are_distinct_category_shelves(self):
        place=self.enc.entity(work_id="modern-test",name="石池",kind="place",genre="玄幻")
        board=self.enc.entity(work_id="modern-test",name="天骄榜",kind="system",genre="玄幻")
        storm=self.enc.entity(work_id="modern-test",name="天劫",kind="event",genre="玄幻")
        entries=[
            self.enc.observe(entity_id=place,chapter=1,paragraph=5,sentence=1,
                             category_path="地点/独特地点/洞天",attribute="环境",quotation=POOL),
            self.enc.observe(entity_id=board,chapter=1,paragraph=6,sentence=1,
                             category_path="设定/玄幻/榜单",attribute="试炼名次",quotation=RANK),
            self.enc.observe(entity_id=storm,chapter=1,paragraph=7,sentence=1,
                             category_path="设定/玄幻/自然天劫",attribute="雷劫",quotation=TRIB),
        ]
        self.assertEqual(len(set(entries)),3)
        for entry in entries:
            self.enc.review(entry,approved=True,reason="逐句核对实体、类别与出处",
                            reviewer_confirmed=True)
        self.assertEqual(self.enc.query(FacetQuery(category_path="设定/玄幻"))["total_matches"],2)
        self.assertEqual(self.enc.query(FacetQuery(category_path="地点/独特地点"))["total_matches"],1)
        with self.assertRaisesRegex(EncyclopediaError,"mismatch"):
            self.enc.observe(entity_id=storm,chapter=1,paragraph=7,sentence=1,
                             category_path="地点/独特地点",attribute="闪电",quotation=TRIB)

    def test_wrong_quote_and_wrong_category_rejected_without_database_growth(self):
        beast=self._creature()
        with self.assertRaisesRegex(EncyclopediaError,"not found"):
            self.enc.observe(entity_id=beast,chapter=1,paragraph=1,sentence=1,
                             category_path="外貌/妖兽",attribute="毛发",
                             quotation="原著从未出现这行字")
        with self.assertRaisesRegex(EncyclopediaError,"category"):
            self.enc.observe(entity_id=beast,chapter=1,paragraph=1,sentence=1,
                             category_path="啊随便输入/妖兽",attribute="毛发",
                             quotation=BEAST)
        self.assertEqual(self.enc.query(FacetQuery(status="all"))["total_matches"],0)

    def test_reject_stale_source_after_original_changed(self):
        beast=self._creature()
        entry=self._beast_entry(beast)
        self.db.conn.execute(
            "UPDATE source_spans SET source_sha256='changed' WHERE work_id='modern-test' AND paragraph=1"
        )
        self.db.conn.commit()
        with self.assertRaisesRegex(EncyclopediaError,"revised"):
            self.enc.review(entry,approved=True,reason="原文已修改",reviewer_confirmed=True)
        self.assertEqual(self.enc.query(FacetQuery(status="all"))["total_matches"],0)

    def test_alias_scoped_to_same_entity_without_erasing_other_work(self):
        beast=self._creature()
        self.enc.alias(beast,"火尾妖虎")
        ev=self._beast_entry(beast)
        self.enc.review(ev,approved=True,reason="原著实体外貌已核查",reviewer_confirmed=True)
        self.assertEqual(
            self.enc.query(FacetQuery(entity_name="火尾妖虎"))["total_matches"],1
        )
        self.assertEqual(
            self.enc.query(FacetQuery(entity_name="蝎虎"))["total_matches"],0
        )

    def test_no_ai_rule_auto_verification_and_rejected_items_hidden(self):
        beast=self._creature()
        id_=self._beast_entry(beast)
        with self.assertRaisesRegex(EncyclopediaError,"human"):
            self.enc.review(id_,approved=True,reason="机器已经猜到了",reviewer_confirmed=False)
        self.enc.review(id_,approved=False,reason="虽然来源正确，但此处类别有争议",
                        reviewer_confirmed=True)
        self.assertEqual(self.enc.query(FacetQuery(entity_name="火蟒虎"))["total_matches"],0)
        self.assertEqual(self.enc.query(FacetQuery(entity_name="火蟒虎",status="rejected"))["total_matches"],1)

    def test_verified_facets_enter_real_draft_context_not_unverified_candidates(self):
        beast=self._creature()
        verified=self._beast_entry(beast)
        pending=self._beast_entry(beast,paragraph=2,category="行为/妖兽/护幼",
                                 attribute="护幼行为",quotation=BEAST2)
        self.enc.review(verified,approved=True,reason="我已确认毛发特征",reviewer_confirmed=True)
        self.rt.exit()
        self.rt.enter_write(self.sid)
        flow=VerifiedWritingFlow(self.db,self.rt,"my-wuxia")
        packet=flow.prepare("ch1.s1","原创场景有两头野外妖兽",concerns=("description",),
                            genre="玄幻",reference_category="外貌/妖兽",
                            reference_name="火蟒虎")
        self.assertEqual(len(packet.encyclopedia_refs),1)
        self.assertEqual(packet.encyclopedia_refs[0]["id"],verified)
        self.assertIn("火蟒虎",packet.prompt)
        self.assertNotIn("护幼行为",packet.prompt)
        self.assertEqual(len(packet.manifest()["encyclopedia_refs"]),1)

    def test_hundreds_of_same_subject_occurrences_are_kept_and_pageable(self):
        beast=self._creature()
        for number in range(8,133):
            body=f"火蟒虎在山中第{number}次出现，毛色与之前略有差异。"
            self.db.conn.execute(
                """INSERT INTO source_spans(
                   work_id,chapter,paragraph,sentence,excerpt,
                   source_sha256,tracks_json,craft_json
                   ) VALUES('modern-test',1,?,1,?,?,'{}','{}')""",
                (number,body,"spanhash-"+str(number)),
            )
        self.db.conn.commit()
        for number in range(8,133):
            body=f"火蟒虎在山中第{number}次出现，毛色与之前略有差异。"
            self.enc.observe(
                entity_id=beast,chapter=1,paragraph=number,sentence=1,
                category_path="外貌/妖兽/毛色",attribute="毛色变化",quotation=body,
                origin="rule_candidate",
            )
        first=self.enc.query(FacetQuery(entity_name="火蟒虎",status="proposed",limit=100))
        self.assertEqual(first["total_matches"],125)
        self.assertEqual(first["returned"],100)
        self.assertTrue(first["has_more"])
        second=self.enc.query(FacetQuery(entity_name="火蟒虎",status="proposed",
                                         offset=100,limit=100))
        self.assertEqual(second["returned"],25)
        self.assertFalse(second["has_more"])
        ids={x["id"] for x in first["items"]+second["items"]}
        self.assertEqual(len(ids),125)
        self.assertEqual(self.enc.entity_overview()["entities"][0]["occurrences"],125)
        self.assertEqual(self.enc.query(FacetQuery(entity_name="火蟒虎"))["total_matches"],0)

    def test_duplicate_alias_of_other_subject_is_rejected(self):
        first=self._creature()
        other=self.enc.entity(work_id="modern-test",name="蝎虎",kind="creature",
                              genre="玄幻",subtype="野兽")
        self.enc.alias(first,"火尾")
        with self.assertRaisesRegex(EncyclopediaError,"ambiguous alias"):
            self.enc.alias(other,"火尾")

    def test_r2_semantic_digest_changes_for_new_category_and_review(self):
        from writerforge.r2_storage import _logical_study_digest
        first=_logical_study_digest(self.path)
        beast=self._creature()
        second=_logical_study_digest(self.path)
        self.assertNotEqual(first,second)
        entry=self._beast_entry(beast)
        third=_logical_study_digest(self.path)
        self.assertNotEqual(second,third)
        self.enc.review(entry,approved=True,
                        reason="人工复核来源片段与妖兽外貌对应",
                        reviewer_confirmed=True)
        fourth=_logical_study_digest(self.path)
        self.assertNotEqual(third,fourth)
        self.assertEqual(_logical_study_digest(self.path),fourth)

    def test_reopen_persistence_and_allow_all_categories_at_any_depth(self):
        tiger=self._creature()
        ev=self._beast_entry(tiger)
        self.enc.review(ev,approved=True,reason="确认毛发描述",reviewer_confirmed=True)
        self.db.close()
        self.db=WriterForgeDB(self.path)
        self.enc=FictionEncyclopedia(self.db)
        self.assertEqual(self.enc.query(FacetQuery(category_path="外貌"))["total_matches"],1)
        self.assertEqual(self.enc.query(FacetQuery(category_path="外貌/妖兽"))["total_matches"],1)
        self.assertTrue(validate_category_path("设定/玄幻/榜单/天骄榜"))
        self.assertEqual(self.enc.entity_overview()["total_entities"],1)


if __name__=="__main__":
    unittest.main()
