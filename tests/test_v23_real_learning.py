"""V23 real workflow tests, including ORIGINAL Chinese first chapter fixture."""
from __future__ import annotations
from contextlib import contextmanager
from io import BytesIO
from pathlib import Path
import json
import tempfile
import unittest
from unittest.mock import patch
from urllib.parse import urlsplit

from writerforge import (
    WriterForgeDB, RuntimeEngine, Mode, XuehaiStore, OriginalStudy, StudyError,
    XIYOUJI_WORK_ID, VerifiedWritingFlow, local_chat_completion,
    WritingExecutionError, save_candidate, accept_candidate,
    LitCriticAdapter, CriticIntegrationError,
    TasteMemory, TasteObservation, SkillRegistry, CapabilityContract,
    EvolutionEngine,
)
from writerforge.xuehai import Query
from writerforge.evolution import FailureEvent


FIXTURE = Path(__file__).parent / "fixtures" / "xiyouji_chapter_001_original_zh.txt"
SECOND = "第二回 悟彻菩提真妙理 断魔归本合元神\n\n石猴道：“师父，弟子愿学。”\n山风响，石洞深。众猴欢喜。\n"


def text2():
    return FIXTURE.read_text(encoding="utf-8") + "\n\n" + SECOND


class RealOriginalStudyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db = WriterForgeDB(Path(self.temp.name) / "real.sqlite")
        self.runtime = RuntimeEngine()
        self.runtime.enter_learn()
        self.study = OriginalStudy(self.db, self.runtime)

    def tearDown(self):
        self.db.close()
        self.temp.cleanup()

    def test_original_chinese_chapter_not_translated(self):
        text = FIXTURE.read_text(encoding="utf-8")
        self.assertTrue(text.startswith("第一回 灵根育孕"))
        self.assertIn("孙悟空", text)
        from writerforge.source_study import parse_original
        chapters = parse_original(text, require_hundred=False)
        self.assertEqual(len(chapters), 1)
        self.assertIn("灵根育孕", chapters[0].heading)

    def test_strict_100_chapters_rejects_incomplete_source(self):
        from writerforge.source_study import parse_original
        with self.assertRaisesRegex(StudyError, "all 100"):
            parse_original(FIXTURE.read_text(encoding="utf-8"))
        fake = "\n".join(
            f"第{i}回 测试卷{i}\n一个完整的章节。"
            for i in range(1,101)
        )
        self.assertEqual(len(parse_original(fake)),100)

    def test_ingest_real_chapter_then_resume_second_delta_no_full_copy(self):
        source = text2()
        first=self.study.ingest(source,require_hundred=False,max_chapters=1)
        self.assertEqual(first["studied_chapters"],1)
        self.assertGreater(first["studied_units"],100)
        self.assertEqual(first["literary_reader_first_complete"],False)
        first_snap=self.db.conn.execute(
            "SELECT id,layout FROM snapshots ORDER BY id LIMIT 1"
        ).fetchone()
        self.assertEqual(first_snap["layout"],"full")
        before_entries=self.db.conn.execute(
            "SELECT COUNT(*) n FROM xuehai_entries"
        ).fetchone()["n"]
        second=self.study.ingest(source,require_hundred=False,max_chapters=2)
        self.assertEqual(second["studied_chapters"],2)
        self.assertEqual(second["newly_studied"],1)
        self.assertEqual(second["new_retrieval_entries"],
                         self.db.conn.execute(
                            "SELECT COUNT(*) n FROM xuehai_entries WHERE chapter=2"
                         ).fetchone()["n"])
        snaps=self.db.conn.execute(
            "SELECT layout,id FROM snapshots ORDER BY id"
        ).fetchall()
        self.assertEqual([r["layout"] for r in snaps],["full","delta"])
        after_entries=self.db.conn.execute(
            "SELECT COUNT(*) n FROM xuehai_entries"
        ).fetchone()["n"]
        self.assertEqual(after_entries-before_entries,second["new_retrieval_entries"])
        # Re-running same work is an idempotent resume, not duplicate learn.
        repeated=self.study.ingest(source,require_hundred=False)
        self.assertEqual(repeated["newly_studied"],0)
        self.assertEqual(self.db.conn.execute(
            "SELECT COUNT(*) n FROM snapshots"
        ).fetchone()["n"],2)

    def test_published_snapshot_retrieves_previous_original_chapter(self):
        self.study.ingest(text2(),require_hundred=False)
        sid=self.db.conn.execute("SELECT MAX(id) id FROM snapshots").fetchone()["id"]
        self.runtime.exit()
        self.runtime.enter_write(sid)
        rows=XuehaiStore(self.db,self.runtime).query(
            Query(genre="古代白话",project_id="novel",limit=8,
                  max_per_work=8,max_per_cluster=8,text_terms=("猴","山"))
        )
        self.assertTrue(rows)
        self.assertTrue(any(r["location"][0]==1 for r in rows))
        self.assertTrue(all(len(r["evidence_excerpt"])<=80 for r in rows))
        self.assertEqual(self.db.conn.execute("PRAGMA cache_size").fetchone()[0],-8192)

    def test_changed_edition_refused_and_no_spurious_session(self):
        self.study.ingest(text2(),require_hundred=False)
        with self.assertRaisesRegex(StudyError,"edition changed"):
            self.study.ingest(text2()+"另一段。",require_hundred=False)
        self.assertEqual(self.study.status()["studied_chapters"],2)

    def test_snapshot_legacy_full_migration_and_delta_descendant(self):
        old = self.db.conn.execute(
            "INSERT INTO snapshots(parent_id,status,layout,note) VALUES(NULL,'published','full','legacy')"
        )
        original=old.lastrowid
        self.db.conn.commit()
        newer=XuehaiStore(self.db,self.runtime).create_staging_snapshot(original)
        self.assertEqual(self.db.conn.execute(
            "SELECT layout FROM snapshots WHERE id=?",(newer,)
        ).fetchone()["layout"],"delta")

    def test_output_trace_uses_actual_source_and_real_local_model_boundary(self):
        self.study.ingest(text2(),require_hundred=False)
        sid=self.db.conn.execute("SELECT MAX(id) id FROM snapshots").fetchone()["id"]
        self.runtime.exit()
        self.runtime.enter_write(sid)
        flow=VerifiedWritingFlow(self.db,self.runtime,"novel")
        packet=flow.prepare("novel.ch1.s1","两位旧友因一份账册发生冲突",
                            concerns=("dialogue",))
        self.assertGreater(len(packet.evidence),0)
        self.assertEqual(packet.snapshot_id,sid)
        self.assertIn("第",packet.prompt)
        self.assertIn("原著",packet.prompt)
        with self.assertRaises(WritingExecutionError):
            local_chat_completion(packet,model="fake",api_base="https://api.openai.com/v1")
        class Response:
            def __enter__(self): return self
            def __exit__(self,*args): return False
            def read(self,n=None):
                return json.dumps({"choices":[{"message":{"content":"他停下笔，抬眼望着旧友。"}}]},
                                  ensure_ascii=False).encode("utf-8")
        with patch("writerforge.verified_flow.urllib.request.urlopen",return_value=Response()) as mocked:
            body=local_chat_completion(packet,model="local-mock")
        self.assertEqual(body,"他停下笔，抬眼望着旧友。")
        self.assertIn("/chat/completions",mocked.call_args.args[0].full_url)
        saved=save_candidate(packet,body,"local-mock",Path(self.temp.name)/"writing_runs")
        manifest=json.loads(Path(saved["manifest"]).read_text(encoding="utf-8"))
        self.assertEqual(manifest["kind"],"writerforge_v23_verified_draft")
        self.assertFalse(manifest["accepted"])
        self.assertGreater(len(manifest["retrieval_refs"]),0)
        self.assertFalse(self.db.conn.execute(
            "SELECT 1 FROM accepted_prose"
        ).fetchone())
        with self.assertRaisesRegex(WritingExecutionError,"explicitly approve"):
            accept_candidate(self.db,self.runtime,project_id="novel",
                             manifest_path=saved["manifest"],commit_id="c1",
                             explicitly_approved=False)
        accepted=accept_candidate(self.db,self.runtime,project_id="novel",
                                  manifest_path=saved["manifest"],commit_id="c1",
                                  explicitly_approved=True)
        self.assertTrue(accepted["accepted"])
        self.assertEqual(self.db.conn.execute(
            "SELECT body FROM accepted_prose"
        ).fetchone()["body"],body)
        self.assertEqual(self.db.conn.execute(
            "SELECT authored_revisions FROM writer_companion_profiles"
        ).fetchone()["authored_revisions"],0)


class PersistenceRecoveryTests(unittest.TestCase):
    def test_taste_evolution_registry_use_actual_sqlite_after_reopen(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/"memory.db"
            db=WriterForgeDB(path)
            taste=TasteMemory(db,"project-a")
            taste.add(TasteObservation(
                "character refusal","B","A",("more active choice",),
                tags=("dialogue",),
            ))
            reg=SkillRegistry(db,"project-a")
            reg.register(CapabilityContract("dialogue",2,"line as action"))
            evol=EvolutionEngine(db=db,scope="project-a")
            for n in range(3):
                evol.record_failure(FailureEvent("dialogue","EMPTY_DIALOGUE",f"chapter-{n}"))
            db.close()
            db=WriterForgeDB(path)
            self.assertEqual(
                len(TasteMemory(db,"project-a").query(tags=("dialogue",))),1
            )
            self.assertEqual(SkillRegistry(db,"project-a").get("dialogue").level,2)
            self.assertEqual(EvolutionEngine(db=db,scope="project-a")
                             .failure_clusters()[0].count,3)
            self.assertEqual(TasteMemory(db,"project-b").query(),[])
            db.close()


class LitCriticIntegrationTests(unittest.TestCase):
    def test_local_review_persists_json_and_markdown_without_changing_source(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            (root/"CANON.md").write_text("# canon\n")
            (root/"STYLE.md").write_text("# style\n")
            scene=root/"scene-01.txt"
            scene.write_text("他在风里收起刀。\n",encoding="utf-8")
            calls=[]
            class Response:
                def __init__(self,payload):self.data=json.dumps(payload).encode()
                def __enter__(self):return self
                def __exit__(self,*args):return False
                def read(self,n):return self.data
            def fake(req,timeout=0):
                url=req.full_url
                calls.append((req.get_method(),url))
                if url.endswith("/analyze"):
                    return Response({"status":"success","total_findings":1})
                if "/sessions/42" in url:
                    return Response({"session":{"id":42},"findings":[{
                        "number":1,"severity":"major","lens":"dialogue",
                        "scene_path":str(scene),"line_start":1,"line_end":1,
                        "evidence":"收起刀","impact":"人物动机不明确",
                        "options":["让动作改变局势"],"status":"pending",
                    }]})
                if "/sessions?" in url:
                    seen=sum(1 for x in calls if x[1].endswith("/analyze"))
                    if seen:
                        return Response({"sessions":[{"id":41,"scene_paths":[str(scene)]},
                                                     {"id":42,"scene_paths":[str(scene)]}]})
                    return Response({"sessions":[{"id":41,"scene_paths":[str(scene)]}]})
                raise AssertionError(url)
            with patch("writerforge.litcritic_adapter.urllib.request.urlopen",side_effect=fake):
                result=LitCriticAdapter().review(
                    project_path=root,scene_path=scene,output_dir=root/"reports"
                )
            self.assertEqual(result["count"],1)
            self.assertTrue(Path(result["json"]).exists())
            self.assertIn("人物动机不明确",Path(result["markdown"]).read_text(encoding="utf-8"))
            self.assertFalse(json.loads(Path(result["json"]).read_text(encoding="utf-8"))["author_decisions"])
            self.assertEqual(scene.read_text(encoding="utf-8"),"他在风里收起刀。\n")
            self.assertEqual(len(calls),4)

    def test_refuses_remote_review_and_missing_local_setup(self):
        with self.assertRaises(CriticIntegrationError):
            LitCriticAdapter(base_url="https://evil.example.com/api")
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)
            scene=p/"scene.txt"
            scene.write_text("正文",encoding="utf-8")
            with self.assertRaisesRegex(CriticIntegrationError,"CANON.md"):
                LitCriticAdapter().review(project_path=p,scene_path=scene,output_dir=p/"r")


if __name__=="__main__":
    unittest.main()
