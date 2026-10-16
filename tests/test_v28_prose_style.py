"""Prose and voice baseline tests. Synthetic text only; no copyrighted novel."""
from __future__ import annotations

from contextlib import redirect_stdout
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import io
import json
import unittest

from writerforge import RuntimeEngine, WriterForgeDB
from writerforge.cli import main as cli_main
from writerforge.prose_style import (
    ProseStyleStore, ProseStyleError, format_prose_reference,
    rejects_verbatim_copy,
)
from writerforge.verified_flow import (
    VerifiedWritingFlow, WritingExecutionError, local_chat_completion,
)
from writerforge.writing_assist import _enrich


REFERENCE = (
    "夜雨停下后，檐角的水还在滴。"
    "他把湿透的账簿摊在桌上，先看见一道被水洇开的指印。"
    "隔壁门轴响了一声，随后又没了动静。他没有抬头。"
    "直到灯芯发出细微的爆响，才伸手压住最末一页。"
) * 3


def studied_db(path: Path) -> tuple[WriterForgeDB, int]:
    db = WriterForgeDB(path)
    cursor = db.conn.execute(
        "INSERT INTO snapshots(parent_id,status,layout,note) VALUES(NULL,'published','full','synthetic')"
    )
    snapshot = int(cursor.lastrowid)
    db.conn.execute(
        """INSERT INTO studied_works(work_id,title,source_uri,source_sha256,chapter_count)
           VALUES('fixture-original','合成来源','fixture://source','sha',1)"""
    )
    db.conn.execute(
        """INSERT INTO studied_chapters(
           work_id,chapter,chapter_sha256,heading,source_spans,retrieval_entries,snapshot_id)
           VALUES('fixture-original',1,'sha','序章',1,1,?)""",
        (snapshot,),
    )
    db.conn.execute(
        """INSERT INTO xuehai_entries(
           snapshot_id,work_id,chapter,paragraph,sentence,text,library_class,culture,
           genre,source_role,function,effect,method_cluster,source_hash)
           VALUES(?,'fixture-original',1,1,1,'她站在门前，沉默半晌，才缓缓开口。',
                  '中国古典小说','中国','古代白话','core','dialogue','unverified',
                  'classical_dialogue','hash')""",
        (snapshot,),
    )
    db.conn.commit()
    return db, snapshot


class StyleReferenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.dbpath = Path(self.temp.name) / "writing.sqlite3"
        self.db, sid = studied_db(self.dbpath)
        self.rt = RuntimeEngine()
        self.rt.enter_write(sid)

    def tearDown(self):
        self.db.close()
        self.temp.cleanup()

    def _packet(self, project="novel"):
        return VerifiedWritingFlow(self.db, self.rt, project).prepare(
            "ch1.scene1", "人物因账册里的名字争执，必须作出选择",
            concerns=("dialogue",),
        )

    def test_bad_ai_draft_never_becomes_approved_style_automatically(self):
        self.db.conn.execute(
            """INSERT INTO accepted_prose(project_id,scope_id,body,body_hash)
               VALUES(?,?,?,?)""",
            ("novel","ch0",REFERENCE,sha256(REFERENCE.encode()).hexdigest()),
        )
        self.db.conn.commit()
        p=self._packet()
        self.assertEqual(p.manifest()["prose_style"]["mode"],"free_model")
        self.assertIsNone(p.prose_reference_text)
        self.assertNotIn("【范例正文】",p.prompt)
        # Learned keyword tags, source excerpts and craft IDs are provenance
        # but not automatic instructions that flatten a model's natural prose.
        self.assertGreater(len(p.evidence),0)
        self.assertGreater(len(p.craft_ids),0)
        self.assertNotIn("结构类别=",p.prompt)
        self.assertNotIn("classical_dialogue",p.prompt)
        self.assertNotIn(p.evidence[0]["evidence_excerpt"],p.prompt)
        self.assertFalse(p.manifest()["source_evidence_shown_to_model"])
        self.assertFalse(p.manifest()["craft_labels_shown_to_model"])
        self.assertNotIn("30%对话",p.prompt)
        self.assertNotIn("每章至少",p.prompt)

    def test_author_approval_required_and_reference_bounded(self):
        styles=ProseStyleStore(self.db,"novel")
        with self.assertRaisesRegex(ProseStyleError,"explicit"):
            styles.approve(REFERENCE,author_confirmed=False)
        with self.assertRaisesRegex(ProseStyleError,"120..1200"):
            styles.approve("写"*1201,author_confirmed=True)
        self.assertFalse(styles.status()["active"])

    def test_approved_reference_is_last_generation_context_and_persists(self):
        approved=ProseStyleStore(self.db,"novel").approve(
            REFERENCE,author_confirmed=True
        )
        self.assertEqual(approved["style_reference_version"],1)
        packet=self._packet()
        self.assertTrue(packet.prompt.endswith(REFERENCE))
        self.assertIn("句式节奏、段落呼吸、叙述距离",packet.prompt)
        self.assertEqual(packet.manifest()["prose_style"]["mode"],"explicit_author_approved")
        self.assertEqual(packet.prose_reference_sha256,sha256(REFERENCE.encode()).hexdigest())
        self.assertNotIn("reference_text",packet.manifest()["prose_style"])
        self.db.close()
        self.db=WriterForgeDB(self.dbpath)
        self.assertTrue(ProseStyleStore(self.db,"novel").status()["active"])
        self.assertTrue(self._packet().prompt.endswith(REFERENCE))
        self.assertIsNone(ProseStyleStore(self.db,"another-project").load())

    def test_style_is_not_loaded_during_json_only_plot_planning(self):
        ProseStyleStore(self.db,"novel").approve(REFERENCE,author_confirmed=True)
        packet=self._packet()
        plan=_enrich(packet,"\n只输出章节规划 JSON",prose_task=False)
        self.assertNotIn(REFERENCE,plan.prompt)
        prose=_enrich(packet,"\n主角推门后发现书页被人抽换")
        self.assertTrue(prose.prompt.endswith(REFERENCE))
        self.assertIn("主角推门后发现",prose.prompt)
        self.assertEqual(prose.prose_reference_sha256,packet.prose_reference_sha256)

    def test_explicit_scope_binding_invalidated_when_accepted_prose_changes(self):
        scene_body="起初：" + REFERENCE + "\n后来他放下账簿。"
        digest=sha256(scene_body.encode()).hexdigest()
        self.db.conn.execute(
            "INSERT INTO accepted_prose(project_id,scope_id,body,body_hash) VALUES(?,?,?,?)",
            ("novel","scene-approved",scene_body,digest),
        )
        self.db.conn.commit()
        styles=ProseStyleStore(self.db,"novel")
        styles.approve(REFERENCE,author_confirmed=True,accepted_scope="scene-approved")
        self.assertTrue(styles.status()["active"])
        next_body="整段已经被作者彻底改写，旧文风范例应失效。"
        self.db.conn.execute(
            """UPDATE accepted_prose SET body=?,body_hash=?,revision=revision+1
               WHERE project_id=? AND scope_id=?""",
            (next_body,sha256(next_body.encode()).hexdigest(),"novel","scene-approved"),
        )
        self.db.conn.commit()
        self.assertIsNone(styles.load())
        self.assertTrue(styles.status()["stored_but_stale_or_invalid"])
        self.assertNotIn(REFERENCE,self._packet().prompt)
        self.assertTrue(styles.disable())
        self.assertFalse(styles.status()["active"])

    def test_failed_scope_approval_does_not_pollute_another_project(self):
        styles=ProseStyleStore(self.db,"second")
        with self.assertRaisesRegex(ProseStyleError,"absent"):
            styles.approve(REFERENCE,author_confirmed=True,accepted_scope="nonexistent")
        self.assertFalse(styles.status()["active"])

    def test_reject_verbatim_style_copy_but_not_fresh_prose(self):
        self.assertTrue(rejects_verbatim_copy("先写新的情节。"+REFERENCE,
                                              REFERENCE))
        self.assertFalse(rejects_verbatim_copy("读者终于明白这个人为什么选择隐瞒。",
                                               REFERENCE))
        ProseStyleStore(self.db,"novel").approve(REFERENCE,author_confirmed=True)
        packet=self._packet()
        class Response:
            def __enter__(self):return self
            def __exit__(self,*args):return False
            def read(self,n=None):
                return json.dumps({"choices":[{"message":{"content":"这段是照抄："+REFERENCE}}]},
                                  ensure_ascii=False).encode()
        with patch("writerforge.verified_flow.urllib.request.urlopen",return_value=Response()):
            with self.assertRaisesRegex(WritingExecutionError,"copied long prose"):
                local_chat_completion(packet,model="synthetic-local-model")
        self.assertEqual(self.db.conn.execute("PRAGMA quick_check").fetchone()[0],"ok")

    def test_cli_approval_status_and_disable_never_print_raw_reference(self):
        sample=Path(self.temp.name)/"author-approved-sample.txt"
        sample.write_text(REFERENCE,encoding="utf-8")
        def command(*argv):
            buffer=io.StringIO()
            with redirect_stdout(buffer):
                cli_main(["--db",str(self.dbpath),*argv])
            return json.loads(buffer.getvalue())
        first=command("prose-style-approve","--project","novel","--file",str(sample),
                      "--confirm-quality-reviewed")
        self.assertEqual(first["status"],"author_approved_reference")
        self.assertNotIn(REFERENCE,json.dumps(first,ensure_ascii=False))
        self.assertTrue(command("prose-style-status","--project","novel")["active"])
        self.assertTrue(command("prose-style-disable","--project","novel")["revoked"])
        self.assertFalse(command("prose-style-status","--project","novel")["active"])


if __name__=="__main__":
    unittest.main()
