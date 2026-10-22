"""R2 narrative memories survive a different machine and preserve original text.

All regular tests use an injected fake S3 API, no Cloudflare credentials,
network or models. Unlike the former local-only memory, the read path requires
the exact original SHA and a scoped R2 store for all cold/warm source reading.
"""
from __future__ import annotations

from hashlib import sha256
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
import json
import unittest

from writerforge.r2_storage import (
    R2Config,R2NarrativeMemoryStore,R2StorageError,
)
from writerforge.narrative_core import (
    new_graph,advance_graph,record_chapter_memory,
    recall_original,relevant_history_context,read_core_from_resume,
    NarrativeCoreError,
)
from writerforge.v114_external_story_state import external_temporal_step
from writerforge.v117_continuity_trace import make_resume

P="synthetic-wf-r2-project"
S="synopsis-synthetic"
START=("沈砚把密令藏在井底。"
       "沈砚与唐蜃立约：等到重阳，要查出旧案的真凶。")
FACT="沈砚把密令藏在井底。"
THREAD="沈砚与唐蜃立约：等到重阳，要查出旧案的真凶。"


class FakeMissing(Exception):
    response={"Error":{"Code":"NoSuchKey"}}


class FakeS3:
    def __init__(self):
        self.objects={}
        self.put_count=0
        self.get_count=0
        self.fail_put=False

    def head_object(self,*,Bucket,Key):
        row=self.objects.get((Bucket,Key))
        if row is None:raise FakeMissing()
        content,metadata=row
        return {"ContentLength":len(content),"Metadata":dict(metadata)}

    def put_object(self,*,Bucket,Key,Body,ContentType=None,Metadata=None):
        if self.fail_put:
            raise OSError("synthetic R2 network interrupted")
        self.put_count+=1
        self.objects[(Bucket,Key)]=(bytes(Body),dict(Metadata or {}))
        return {"ETag":'"local-only"'}

    def get_object(self,*,Bucket,Key):
        row=self.objects.get((Bucket,Key))
        if row is None:raise FakeMissing()
        self.get_count+=1
        return {"Body":BytesIO(row[0])}


def sample_event(source,quote,kind,**kw):
    return {
        "id":kw.pop("id",kind),
        "kind":kind,
        "quote":quote,"start":source.index(quote),
        "author_confirmed":True,**kw,
    }


def make_graph():
    base=new_graph(project_id=P,scene_id=S)
    return advance_graph(base,project_id=P,scene_id=S,
        chapter_index=1,prose=START,events=[
            sample_event(START,FACT,"FACT",id="fact",
                         fact_id="well-secret",name="密令藏在井底",
                         visibility="SECRET"),
            sample_event(START,THREAD,"THREAD_OPEN",id="thread",
                         thread_id="old-promise",
                         thread_kind="PROMISE",owner="沈砚",
                         target="唐蜃",premise="重阳必须追查旧案真凶",
                         truth_scope="CHARACTER_BELIEF"),
        ])


class DurableR2StoryMemory(unittest.TestCase):
    def setUp(self):
        self.temp=TemporaryDirectory()
        self.root=Path(self.temp.name)
        self.backend=FakeS3()
        self.cfg=R2Config(
            account_id="a"*32,bucket="writerforge-private-library",
            access_key_id="synthetic",secret_access_key="synthetic")
        self.writer=R2NarrativeMemoryStore(
            self.cfg,project_id=P,scene_id=S,client=self.backend)

    def tearDown(self):
        self.temp.cleanup()

    def reader(self):
        # A restarted machine gets ONLY the configured private bucket and
        # the same project/scene: no access to previous writer-local files.
        return R2NarrativeMemoryStore(
            self.cfg,project_id=P,scene_id=S,client=self.backend)

    def saved(self,graph,chapter,prose,keep_file=True):
        name=self.root/f"chapter-{chapter:03d}.md"
        name.write_text(prose,encoding="utf8")
        out=record_chapter_memory(
            graph,project_id=P,scene_id=S,chapter_index=chapter,
            source_path=str(name),prose=prose,
            source_writer=self.writer.put_original,
            source_reader=self.writer.read_original,
            archive_writer=self.writer.put_capsule,
            archive_reader=self.writer.read_capsule)
        if not keep_file:
            name.unlink()
        return out

    def test_cloud_cas_28_chapters_originals_absent_after_upload(self):
        graph=self.saved(make_graph(),1,START,keep_file=False)
        original_state=external_temporal_step(START,cast=("沈砚","唐蜃"))
        for i in range(2,29):
            prose=f"第{i}章，叶青梧抬头听风，远处钟鸣渐低。"
            graph=advance_graph(
                graph,project_id=P,scene_id=S,
                chapter_index=i,prose=prose)
            graph=self.saved(graph,i,prose,keep_file=False)
        mem=graph["memory"]
        self.assertEqual(mem["cold_count"],17)
        self.assertEqual(len(mem["hot"]),3)
        self.assertEqual(len(mem["warm"]),8)
        self.assertTrue(all(x["source_path"].startswith(
            "r2://writerforge-private-library/writerforge/v1/narrative-memory/v1/"
        ) for x in mem["hot"]+mem["warm"]))
        self.assertTrue(mem["cold_head"]["path"].startswith("r2://"))
        resume=make_resume(
            project_id=P,scene_id=S,chapter_index=28,
            checkpoint=original_state,unified_narrative_core=graph)
        cloud_pointer=self.writer.put_resume(resume)
        self.assertTrue(cloud_pointer.startswith("r2://"))
        new_client=self.reader()
        loaded=new_client.read_resume(cloud_pointer)
        rebuilt=read_core_from_resume(loaded,project_id=P,scene_id=S)
        self.assertEqual(rebuilt["receipt_sha256"],graph["receipt_sha256"])
        # Nothing on the new machine depends on original local candidate.md.
        restored=recall_original(
            rebuilt,project_id=P,scene_id=S,chapter_index=1,
            source_reader=new_client.read_original,
            archive_reader=new_client.read_capsule)
        self.assertEqual(restored,START)
        hint=relevant_history_context(
            rebuilt,project_id=P,scene_id=S,
            scene_goal="沈砚重逢唐蜃，重阳要追查旧案，还记得密令藏在井底",
            source_reader=new_client.read_original,
            archive_reader=new_client.read_capsule)
        self.assertIn("原文第1章",hint)
        self.assertIn("沈砚",hint)
        self.assertIn("密令",hint)
        self.assertNotIn("真凶是唐蜃",hint)
        self.assertGreater(self.backend.get_count,5)
        self.assertEqual(self.writer.vault.config.bucket,self.cfg.bucket)
        self.assertNotIn("secret_access_key",repr(resume))

    def test_original_cas_idempotent_scope_verified_and_no_foreign_bucket(self):
        local=self.root/"source.md"
        local.write_text(START,encoding="utf8")
        digest=sha256(START.encode()).hexdigest()
        ref=self.writer.put_original(str(local),digest)
        count=self.backend.put_count
        self.assertEqual(self.writer.put_original(str(local),digest),ref)
        self.assertEqual(self.backend.put_count,count)
        other=R2NarrativeMemoryStore(
            self.cfg,project_id="other-novel",scene_id=S,
            client=self.backend)
        with self.assertRaisesRegex(R2StorageError,"CROSS_SCOPE"):
            other.read_original(ref,digest)
        self.assertEqual(self.writer.read_original(ref,digest),START)
        with self.assertRaisesRegex(R2StorageError,"CROSS_SCOPE"):
            self.writer.read_original(
                ref.replace(self.cfg.bucket,"other-bucket"),digest)
        self.assertTrue(all(
            key.startswith("writerforge/v1/narrative-memory/v1/")
            for _,key in self.backend.objects))

    def test_remote_original_tampering_fails_closed(self):
        local=self.root/"a.md"
        local.write_text(START,encoding="utf8")
        digest=sha256(START.encode()).hexdigest()
        ref=self.writer.put_original(str(local),digest)
        oldkey=next(iter(self.backend.objects))
        contents,meta=self.backend.objects[oldkey]
        self.backend.objects[oldkey]=(contents+b"x",meta)
        with self.assertRaisesRegex(R2StorageError,
                                    "BAD_METADATA|SHA_CHANGED"):
            self.reader().read_original(ref,digest)

    def test_no_remote_reader_never_treats_r2_uri_as_local_path(self):
        graph=self.saved(make_graph(),1,START,keep_file=False)
        with self.assertRaisesRegex(NarrativeCoreError,"R2_SOURCE_READER"):
            recall_original(graph,project_id=P,scene_id=S,chapter_index=1)

    def test_bad_upload_prevents_checkpoint_and_does_not_erase_source(self):
        graph=make_graph()
        self.backend.fail_put=True
        local=self.root/"saved.md"
        local.write_text(START,encoding="utf8")
        with self.assertRaises(OSError):
            record_chapter_memory(
                graph,project_id=P,scene_id=S,chapter_index=1,
                source_path=str(local),prose=START,
                source_writer=self.writer.put_original,
                source_reader=self.writer.read_original,
                archive_writer=self.writer.put_capsule,
                archive_reader=self.writer.read_capsule)
        self.assertTrue(local.is_file())
        self.assertEqual(graph["memory"]["last_recorded_chapter"],None)
        self.assertEqual(self.backend.objects,{})

    def test_resume_no_cross_project_and_immutable_content(self):
        graph=self.saved(make_graph(),1,START)
        state=external_temporal_step(START,cast=("沈砚","唐蜃"))
        resume=make_resume(project_id=P,scene_id=S,
                           chapter_index=1,checkpoint=state,
                           unified_narrative_core=graph)
        ref=self.writer.put_resume(resume)
        self.assertEqual(self.writer.put_resume(resume),ref)
        other=R2NarrativeMemoryStore(
            self.cfg,project_id=P,scene_id="wrong-scene",
            client=self.backend)
        with self.assertRaisesRegex(R2StorageError,"CROSS_SCOPE"):
            other.read_resume(ref)
        tampered=json.loads(json.dumps(resume,ensure_ascii=False))
        tampered["unified_narrative_core"]["chapter_index"]=900
        with self.assertRaises((ValueError,R2StorageError)):
            self.writer.put_resume(tampered)

    def test_offline_local_memory_never_requires_cloud(self):
        graph=make_graph()
        path=self.root/"local.md"
        path.write_text(START,encoding="utf8")
        local=record_chapter_memory(
            graph,project_id=P,scene_id=S,chapter_index=1,
            source_path=str(path),prose=START)
        self.assertEqual(
            recall_original(local,project_id=P,scene_id=S,chapter_index=1),
            START)
        self.assertEqual(len(self.backend.objects),0)


if __name__=="__main__":
    unittest.main()
