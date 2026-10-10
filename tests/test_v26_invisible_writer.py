"""V26: real live-editor interaction, source-proof choices, automatic chapter plans.

Uses a fake *local model response* to test execution plumbing. No model
performance or reader approval is claimed by the synthetic strings.
"""
from __future__ import annotations

from contextlib import closing
from hashlib import sha256
from http.server import HTTPServer
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Thread
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from unittest.mock import patch
import json
import sqlite3
import time
import unittest

from writerforge import WriterForgeDB, RuntimeEngine
from writerforge.encyclopedia import FictionEncyclopedia
from writerforge.writing_assist import (
    InvisibleWritingAssist,AutonomousWriting,infer_intent,
    _two_options,WritingExecutionError,
)
from writerforge.studio_server import StudioStore,StudioService,StudioHTTPServer


TWO = json.dumps({"choices":[
    {"title":"动作里的犹疑",
     "text":"她伸手扶住门框，指尖在那道旧刻痕上停了一瞬。院外有人叫她的名字，她却先替那人把落在门槛上的鞋拾了起来，直到脚步声近了，才抬眼答话。"},
    {"title":"关系里的决定",
     "text":"她把信压在桌边，抬头望向来人。那人仍在解释昨夜发生的事，她听完才把门推开，平静地说让孩子先走，自己留下承担所有后果。这句话出口，屋内忽然没人敢再劝她。"},
]},ensure_ascii=False)
PLAN=json.dumps({
    "objective":"护送少年穿越一段危险山道",
    "conflict":"老朋友要求背弃承诺才能安全逃生",
    "decision":"主角选择冒险保护身份未明的少年",
    "outcome":"暴露自己的行踪，使追兵能够逼近",
    "pov":"以镖师的行动视角贴近矛盾",
    "needs":["character","dialogue","decision"],
},ensure_ascii=False)
BODY=("夜里山道安静得只听见马铃。镖师压住少年抬起的手，让他伏在车底。"
      "前方的火把转过山梁，他看见熟人的旗号，却没有迎上去，反而把缰绳交给身后的人。"
      "这一步退让并不意味着认输，而是在等他自己选择承受的后果。")*3


def make_db(path:Path) -> int:
    db=WriterForgeDB(path)
    cur=db.conn.execute(
        "INSERT INTO snapshots(parent_id,status,layout,note) VALUES(NULL,'published','full','approved original sample')"
    )
    sid=int(cur.lastrowid)
    db.conn.execute(
        """INSERT INTO studied_works(work_id,title,source_uri,source_sha256,chapter_count)
           VALUES('book-original','古代中文样本','sample://original','sha',1)"""
    )
    db.conn.execute(
        """INSERT INTO source_spans(work_id,chapter,paragraph,sentence,excerpt,
                       source_sha256,tracks_json,craft_json)
           VALUES('book-original',1,1,1,'她站在门前，沉默半晌，才缓缓开口。','unit-sha','{}','{}')"""
    )
    db.conn.execute(
        """INSERT INTO studied_chapters(work_id,chapter,chapter_sha256,heading,
                           source_spans,retrieval_entries,snapshot_id)
           VALUES('book-original',1,'hash','开头',1,1,?)""",(sid,)
    )
    db.conn.execute(
        """INSERT INTO xuehai_entries(snapshot_id,work_id,chapter,paragraph,sentence,text,
           library_class,culture,genre,source_role,function,effect,method_cluster,
           source_hash) VALUES(?,'book-original',1,1,1,'她站在门前，沉默半晌，才缓缓开口。',
           '中国古代小说','中国','古代白话','core','dialogue','unverified',
           'classical_dialogue','key')""",(sid,)
    )
    db.conn.commit()
    db.close()
    return sid


class LiveAssistanceTests(unittest.TestCase):
    def setUp(self):
        self.folder=TemporaryDirectory()
        self.path=Path(self.folder.name)/"source.sqlite3"
        self.sid=make_db(self.path)
        self.db=WriterForgeDB(self.path)
        self.rt=RuntimeEngine()
        self.rt.enter_write(self.sid)
        self.assist=InvisibleWritingAssist(
            self.db,self.rt,"novel","s1","两个故友因不同的承诺产生冲突",
            model="local-fixture",api_base="http://127.0.0.1:1234/v1",
        )

    def tearDown(self):
        self.db.close()
        self.folder.cleanup()

    def test_live_event_triggers_character_trait_without_a_shelf_search(self):
        text="一个性格倔强的女子"
        intent=infer_intent(text)
        self.assertEqual((intent.category,intent.kind),("性格","character"))
        with patch("writerforge.writing_assist.local_chat_completion",return_value=TWO) as model:
            result=self.assist.suggest(text)
        self.assertTrue(result["triggered"])
        self.assertEqual(len(result["choices"]),2)
        self.assertEqual(result["verified_category_references"],0)
        self.assertTrue(result["original_manuscript_unchanged"])
        self.assertFalse(result["manual_search_required"])
        self.assertEqual(result["source_references"],1)
        self.assertGreater(len(model.call_args.args[0].craft_ids),0)
        self.assertIn(text,model.call_args.args[0].prompt)
        self.assertIsNone(self.db.conn.execute("SELECT 1 FROM accepted_prose").fetchone())

    def test_unknown_ordinary_words_never_fabricate_facets_or_call_model(self):
        with patch("writerforge.writing_assist.local_chat_completion") as model:
            result=self.assist.suggest("山")
            self.assertFalse(result["triggered"])
            self.assertEqual(result["choices"],[])
            model.assert_not_called()
        self.assertIsNone(infer_intent("那少年与龙门的招牌擦肩而过"))
        self.assertEqual(infer_intent("天劫将至").category,"设定")
        self.assertEqual(infer_intent("一头妖兽露出獠牙").kind,"creature")

    def test_verified_facets_only_and_unverified_evidence_excluded(self):
        enc=FictionEncyclopedia(self.db)
        entity=enc.entity(work_id="book-original",name="门前女子",
                          kind="character",genre="古代白话",gender="female")
        evidence=enc.observe(
            entity_id=entity,chapter=1,paragraph=1,sentence=1,
            category_path="性格/女性/克制",attribute="行为",
            quotation="她站在门前",explanation="用等待而不是形容词写出克制",
            origin="model_candidate",
        )
        with patch("writerforge.writing_assist.local_chat_completion",return_value=TWO):
            proposed=self.assist.suggest("她是一个性格温柔的女子")
            self.assertEqual(proposed["verified_category_references"],0)
            self.assertNotIn("用等待而不是",proposed["choices"][0]["text"])
            enc.review(evidence,approved=True,reason="逐句人工核对来源并确认性格描述",
                       reviewer_confirmed=True)
            approved=self.assist.suggest("她是一个性格温柔的女子")
            self.assertEqual(approved["verified_category_references"],1)
        self.assertEqual(approved["source_references"],1)
        self.assertIsNone(self.db.conn.execute("SELECT 1 FROM accepted_prose").fetchone())

    def test_invalid_duplicate_or_copied_model_options_rejected(self):
        source=("这是来自古籍的完整原文片段不得被照搬进去的特别长的测试句子",)
        copied=json.dumps({"choices":[
            {"title":"一","text":source[0]+"主人公走了出去。"},
            {"title":"二","text":"一阵寒风吹来，他突然明白了自己应当怎样继续前进。"},
        ]},ensure_ascii=False)
        with self.assertRaisesRegex(WritingExecutionError,"copied"):
            _two_options(copied,source)
        duplicate=json.dumps({"choices":[{"title":"一","text":BODY},
                                       {"title":"二","text":BODY}]},ensure_ascii=False)
        with self.assertRaisesRegex(WritingExecutionError,"similar"):
            _two_options(duplicate,())

    def test_auto_outline_planning_and_chapters_are_real_model_outputs(self):
        responses=[PLAN,BODY,PLAN,BODY]
        with patch("writerforge.writing_assist.local_chat_completion",
                   side_effect=responses) as model:
            result=AutonomousWriting(self.assist).run(
                outline="少年护镖穿越山道。山中旧友背离承诺，年轻镖师必须为自己的选择承担代价。",
                chapter_goals=[
                    "第一章：接下镖件并发现少年隐瞒姓名",
                    "第二章：与旧友发生冲突并做出危险抉择",
                ],
                output_dir=Path(self.folder.name)/"auto",
            )
        self.assertEqual(model.call_count,4)
        self.assertEqual(result["chapter_count"],2)
        self.assertTrue(result["all_generated_prose_requires_author_review"])
        self.assertFalse(result["literary_quality_verified"])
        for chapter in result["chapters"]:
            self.assertFalse(chapter["accepted"])
            self.assertEqual(Path(chapter["candidate"]).read_text(encoding="utf-8"),BODY)
            plan=json.loads(Path(chapter["plan"]).read_text(encoding="utf-8"))
            self.assertIn("decision",plan)
            meta=json.loads(Path(chapter["manifest"]).read_text(encoding="utf-8"))
            self.assertGreater(len(meta["retrieval_refs"]),0)
            self.assertEqual(meta["model"],"local-fixture")
        self.assertIsNone(self.db.conn.execute("SELECT 1 FROM accepted_prose").fetchone())

    def test_limit_large_autonomous_runs(self):
        with self.assertRaisesRegex(WritingExecutionError,"1..6"):
            AutonomousWriting(self.assist).run(
                outline="完整的大纲描述人物动机、角色关系与不同章节间的冲突。",
                chapter_goals=["本章包含清晰冲突和选择"]*7,
                output_dir=self.folder.name,
            )


class LiveHTTPTests(unittest.TestCase):
    def setUp(self):
        self.folder=TemporaryDirectory()
        self.root=Path(self.folder.name)
        self.path=self.root/"source.db"
        make_db(self.path)
        self.service=StudioService(
            db_path=self.path,project="novel",scene="scene-001",
            goal="表现角色在承诺和危险之间的冲突",
            model="fixture-llm",output_dir=self.root/"working",
        )
        self.server=StudioHTTPServer("127.0.0.1",0,self.service)
        self.thread=Thread(target=self.server.serve_forever,daemon=True)
        self.thread.start()
        self.base=f"http://127.0.0.1:{self.server.server_address[1]}"
        self.token=self.service._token

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(3)
        self.folder.cleanup()

    def request(self,path,body=None,token=True):
        payload=None if body is None else json.dumps(body,ensure_ascii=False).encode("utf-8")
        headers={}
        if payload is not None:
            headers["Content-Type"]="application/json"
        if token:
            headers["X-WriterForge-Token"]=self.token
        req=Request(self.base+path,data=payload,headers=headers,
                    method="GET" if body is None else "POST")
        with urlopen(req,timeout=10) as response:
            raw=response.read()
            return json.loads(raw) if path!="/" else raw.decode("utf-8")

    def test_browser_serves_real_input_handler_and_not_manual_search(self):
        html=self.request("/",token=False)
        self.assertIn('manuscript.addEventListener("input"',html)
        self.assertIn("setTimeout(()=>suggest(context,editEpoch),900)",html)
        self.assertIn("采用第 ",html)
        self.assertIn("按照故事大纲自行工作",html)
        bootstrap=self.request("/api/bootstrap",token=False)
        self.assertEqual(bootstrap["status"],"studio_connected_to_published_xuehai")
        self.assertEqual(bootstrap["model"],"fixture-llm")

    def test_autosave_reload_revision_conflicts_and_consent(self):
        text="她是一个性格倔强的女子"
        first=self.request("/api/autosave",{"text":text,"expected_revision":0})
        self.assertEqual(first["revision"],1)
        self.assertEqual(self.request("/api/bootstrap",token=False)["draft"]["text"],text)
        with self.assertRaises(HTTPError) as cm:
            self.request("/api/autosave",{"text":"过期改写","expected_revision":0})
        self.assertEqual(cm.exception.code,409)
        with self.assertRaises(HTTPError) as cm:
            self.request("/api/autosave",{"text":"abuse","expected_revision":1},token=False)
        self.assertEqual(cm.exception.code,403)
        self.assertEqual((self.service.store.path/"draft.md").read_text(encoding="utf-8"),text)
        with patch("writerforge.writing_assist.local_chat_completion",return_value=TWO):
            hint=self.request("/api/suggest",{"text":text})
        self.assertEqual(len(hint["choices"]),2)
        history=self.request("/api/choice",{
            "choice_index":1,"prompt_sha256":hint["prompt_sha256"]
        })
        self.assertTrue(history["recorded"])
        self.assertFalse(history["learning_rule_automatically_promoted"])
        self.assertEqual(self.request("/api/bootstrap",token=False)["draft"]["text"],text)
        with closing(sqlite3.connect(self.path)) as con:
            self.assertEqual(con.execute("SELECT COUNT(*) FROM accepted_prose").fetchone()[0],0)

    def test_two_browser_modes_autonomous_job_and_read_only_preview(self):
        responses=[PLAN,BODY]
        with patch("writerforge.writing_assist.local_chat_completion",side_effect=responses):
            job=self.request("/api/autodraft",{
                "outline":"镖师隐瞒过往，被迫护送一名少年跨越封锁线；身后的朋友总在索要回报。",
                "chapters":["第一章：接到镖书，发现押送者其实是旧友之子"]
            })
            for _ in range(60):
                status=self.request("/api/job")
                if status["status"] in ("completed","failed"):
                    break
                time.sleep(.05)
        self.assertEqual(status["status"],"completed",status.get("error"))
        chapter=self.request("/api/chapter/1")
        self.assertEqual(chapter["text"],BODY)
        self.assertFalse(chapter["accepted"])
        self.assertEqual(len(status["result"]["chapters"]),1)
        self.assertTrue(Path(status["result"]["chapters"][0]["candidate"]).is_file())


if __name__ == "__main__":
    unittest.main()
