"""V28 fake-model/fake-review and fake-R2 regression tests; NO novel text used.

A synthetic authority proves only engineering transitions, never literary quality.
"""
from __future__ import annotations

from hashlib import sha256
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
import json
import sqlite3
import time
import unittest

from writerforge.reverse_craft import (
    ReverseCraftCoordinator, ReverseCraftError, WORK, EDITION, _hash,
)
from writerforge.reverse_core_vault import ReverseCoreVault
from writerforge.r2_storage import R2Config, R2StorageError


class MissingKey(Exception):
    response={"Error":{"Code":"404"}}


class FakeR2:
    def __init__(self):
        self.storage={}
        self.corrupt_reads=False
        self.uploads=0

    def head_object(self, *, Bucket, Key):
        try: payload,meta=self.storage[(Bucket,Key)]
        except KeyError: raise MissingKey()
        return {"ContentLength":len(payload),"Metadata":meta}

    def put_object(self, *, Bucket, Key, Body, ContentType=None, Metadata=None):
        if (Bucket,Key) in self.storage:
            raise AssertionError("immutable blob unexpectedly overwritten")
        self.storage[(Bucket,Key)]=(bytes(Body),dict(Metadata or {}))
        self.uploads+=1

    def get_object(self, *, Bucket, Key):
        payload=self.storage[(Bucket,Key)][0]
        if self.corrupt_reads:
            payload+=b"x"
        return {"Body":BytesIO(payload)}


class SyntheticTestAuthority:
    """Never supply this class to a production deployment."""
    def verify(self, report):
        return report.get("test_only_signed") is True


def report(score=92, *, transfer=False, reviewer="independent_test_critic",
           dimensions=None, copy_risk=False):
    r={
        "test_only_signed":True, "reviewer":reviewer, "independent":True,
        "copy_risk":copy_risk, "blind":True,
        "dimensions":dimensions or {"perception":92,"causality":93,"information":91},
    }
    r["transfer_score" if transfer else "quality_score"]=score
    return r


CORE={
    "problem":"角色对突发环境只列视觉细节而没有认知因果",
    "trigger":"陌生来访者抵达且人物有警戒目标",
    "mechanism":"先由人物现有目标过滤感知，再使异常证据影响下一步行动",
    "effect":"读者随人物产生可信疑问而不预先知道谜底",
    "scope":"有限人物视角下的悬念场景",
    "counterexample":"全知叙述需要制造戏剧反讽时并不适合",
}
DRAFT="Synthetic fiction only: this is never a real copyrighted original. " * 7
SENTINEL="DRAFT_SENTINEL_NEVER_IN_SQLITE_OR_REMOTE " * 8


class TestReverseCraft(unittest.TestCase):
    def setUp(self):
        self.tmp=TemporaryDirectory()
        self.base=Path(self.tmp.name)
        self.path=self.base/"study.sqlite3"
        self.engine=ReverseCraftCoordinator(
            self.path,"pilot",create=True,scratch=self.base/"scratch")
        self.r2=FakeR2()
        self.vault=ReverseCoreVault(
            R2Config(account_id="a"*32,bucket="writerforge-private-library",
                     access_key_id="test",secret_access_key="test"),
            client=self.r2)
        self.auth=SyntheticTestAuthority()

    def tearDown(self):
        self.engine.close()
        self.tmp.cleanup()

    def open_one(self,index=1):
        return self.engine.open_unit(1,index,_hash("span-"+str(index)),
                                     _hash("context-"+str(index)))

    def attempt(self,unit,score=92):
        return self.engine.practice(unit,SENTINEL,writer="draft_model",
            report=report(score),core=CORE,
            fault="首次练习没有足够展现人物目标",
            hypothesis="作者可能用间接动作安排注意焦点而非直接告知",
            authority=self.auth)

    def finish(self,unit):
        self.assertEqual(self.attempt(unit),"PERSIST_PENDING")
        self.assertEqual(self.engine.checkpoint(unit,self.vault),"RETEST_READY")
        self.assertEqual(self.engine.retest(
            unit,DRAFT,writer="draft_model",
            report=report(93,transfer=True),authority=self.auth),
            "RETEST_PERSIST_PENDING")
        self.assertEqual(self.engine.checkpoint(unit,self.vault),"PASS")
        self.assertEqual(list((self.base/"scratch").iterdir()),[])

    def test_no_real_review_is_fail_closed_and_no_body_persists(self):
        unit=self.open_one()
        state=self.engine.practice(unit,SENTINEL,writer="draft_model",
            report=report(100),core=CORE,fault="没有人物前置动机",
            hypothesis="强调后果能够建立人物认知的方向",
            authority=None)
        self.assertEqual(state,"REVIEW_BLOCKED")
        self.assertEqual(self.engine.inspect()["units"][0]["attempts"],1)
        self.assertNotIn("DRAFT_SENTINEL",self.engine.snapshot().decode())
        self.assertEqual(list((self.base/"scratch").iterdir()),[])

    def test_bound_retry_stops_after_three_and_does_not_loop(self):
        unit=self.open_one()
        self.assertEqual([self.attempt(unit,score=60) for _ in range(3)],
                         ["RETRY","RETRY","BLOCKED"])
        with self.assertRaises(ReverseCraftError):
            self.attempt(unit)
        self.assertEqual(self.engine.conn.execute(
            "SELECT COUNT(*) FROM rc_attempts").fetchone()[0],3)

    def test_two_units_require_real_merge_gate_and_clean_restore(self):
        a=self.open_one(1)
        self.finish(a)
        b=self.open_one(2)
        self.finish(b)
        with self.assertRaisesRegex(ReverseCraftError,"merged"):
            self.open_one(3)
        self.engine.open_pair_merge(a)
        state=self.engine.merge(a,DRAFT,writer="draft_model",
            report=report(94,transfer=True),authority=self.auth,
            vault=self.vault)
        self.assertEqual(state,"MERGED_PASS")
        self.assertEqual(self.engine.open_unit(1,3,_hash("anchor-3"),
                                               _hash("ctx-3")),3)
        digest=self.engine.conn.execute(
            "SELECT remote_hash FROM rc_merges WHERE pair_start=1").fetchone()[0]
        original=self.vault.restore_verified(work=WORK,project="pilot",
                                             edition=EDITION,snapshot_sha=digest)
        self.assertNotIn(b"DRAFT_SENTINEL",original)
        restored=ReverseCraftCoordinator.restore_snapshot(
            self.base/"fresh.sqlite3","pilot",original,
            scratch=self.base/"fresh-scratch")
        try:
            self.assertEqual(restored.inspect()["merges"][0]["status"],"MERGED_PASS")
            self.assertEqual(len(restored.inspect()["units"]),2)
        finally:restored.close()

    def test_same_context_cannot_multiply_plus_three_evidence(self):
        unit=self.open_one()
        self.finish(unit)
        with self.assertRaises(ReverseCraftError):
            self.engine.checkpoint(unit,self.vault)
        key=self.engine.conn.execute("SELECT core_hash FROM rc_cores").fetchone()[0]
        self.assertEqual(self.engine.conn.execute(
            "SELECT COUNT(*) FROM rc_evidence WHERE core_hash=?",(key,)).fetchone()[0],1)
        self.assertEqual(self.engine.conn.execute(
            "SELECT tier FROM rc_cores WHERE core_hash=?",(key,)).fetchone()[0],"candidate")
        with self.assertRaises(sqlite3.IntegrityError):
            self.engine.open_unit(1,2,_hash("new-span"),_hash("context-1"))
        self.engine.conn.rollback()

    def test_wrong_edition_and_invalid_review_are_rejected(self):
        unit=self.open_one()
        self.assertEqual(self.engine.practice(unit,SENTINEL,writer="draft_model",
            report=report(reviewer="draft_model"),core=CORE,
            fault="未体现前史影响",hypothesis="文本可能限制视角",authority=self.auth),
            "REVIEW_BLOCKED")
        with self.assertRaises(ReverseCraftError):
            ReverseCraftCoordinator(self.path,"other-project")
        with self.assertRaises(ReverseCraftError):
            self.engine.open_unit(7,1,_hash("x"),_hash("y"))

    def test_r2_corrupt_read_never_promotes_state(self):
        unit=self.open_one()
        self.assertEqual(self.attempt(unit),"PERSIST_PENDING")
        self.r2.corrupt_reads=True
        with self.assertRaises(R2StorageError):
            self.engine.checkpoint(unit,self.vault)
        self.assertEqual(self.engine.inspect()["units"][0]["status"],"PERSIST_PENDING")
        self.r2.corrupt_reads=False
        self.assertEqual(self.engine.checkpoint(unit,self.vault),"RETEST_READY")
        self.assertEqual(self.r2.uploads,1)

    def test_crash_resume_and_ttl_scratch_cleanup(self):
        unit=self.open_one()
        self.assertEqual(self.attempt(unit),"PERSIST_PENDING")
        self.engine.close()
        self.engine=ReverseCraftCoordinator(self.path,"pilot",scratch=self.base/"scratch")
        self.assertEqual(self.engine.inspect()["units"][0]["status"],"PERSIST_PENDING")
        orphan=self.base/"scratch"/"rc-interrupted"
        orphan.mkdir()
        (orphan/"transient.txt").write_text(SENTINEL)
        import os
        os.utime(orphan,(time.time()-7200,time.time()-7200))
        self.assertEqual(self.engine.cleanup_stale_scratch(max_age_seconds=3600),1)
        self.assertFalse(orphan.exists())
        self.assertEqual(self.engine.checkpoint(unit,self.vault),"RETEST_READY")

    def test_review_disagreement_and_missing_dimensions_cannot_pass(self):
        unit=self.open_one()
        bad=report(100,dimensions={"perception":100,"causality":100})
        self.assertEqual(self.engine.practice(unit,SENTINEL,writer="draft_model",
            report=bad,core=CORE,fault="失误",
            hypothesis="需要区分作者与叙述者",authority=self.auth),"REVIEW_BLOCKED")
        self.assertEqual(self.engine.inspect()["units"][0]["status"],"REVIEW_BLOCKED")

    def test_snapshot_rejects_modified_hash(self):
        unit=self.open_one()
        self.finish(unit)
        sha=self.engine.inspect()["units"][0]["remote_hash"]
        key=next(k for k in self.r2.storage if k[1].endswith(sha+".json"))
        content,metadata=self.r2.storage[key]
        self.r2.storage[key]=(content+b"bad",metadata)
        with self.assertRaises(R2StorageError):
            self.vault.restore_verified(work=WORK,project="pilot",
                                        edition=EDITION,snapshot_sha=sha)


if __name__=="__main__":
    unittest.main()
