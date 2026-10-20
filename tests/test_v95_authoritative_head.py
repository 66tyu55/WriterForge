"""V95 synthetic R2 atomic-authority-head contract and concurrency tests.

Client can't fake head CAS with client-side GET+PUT: fake transport's compare
and swap is storage-lock atomic, modeling R2 onlyIf semantics. Does NOT
claim that V95 route is installed on the real Cloudflare Worker.
"""
from __future__ import annotations
import threading
import unittest
from copy import deepcopy
from hashlib import sha256

from writerforge.v95_authoritative_head import (
    make_head,verify_head,verify_capabilities,commit_synthetic_head,
    HeadCommitError,canonical,digest,parse_strict,
)


def h(x):
    return sha256(x.encode("utf8")).hexdigest()


class AtomicFakeTransport:
    def __init__(self,available=True):
        self.current=None
        self.etag=None
        self.lock=threading.Lock()
        self.available=available
        self.successes=0

    def capability(self):
        if not self.available:
            raise HeadCommitError("WF95_HEAD_ROUTE_NOT_DEPLOYED")
        return True

    def read(self):
        with self.lock:
            if self.current is None:
                raise HeadCommitError("WF95_NO_CURRENT_HEAD")
            return self.etag,deepcopy(self.current)

    def atomic_update(self,head,etag):
        verify_head(head)
        with self.lock:
            if self.current is None:
                if etag is not None or head["generation"]!=1:
                    raise HeadCommitError(
                        "WF95_ATOMIC_CONFLICT_STALE_HEAD")
            elif (etag!=self.etag or
                  head["generation"]!=self.current["generation"]+1 or
                  head["previous_head_sha256"]!=
                       self.current["head_sha256"]):
                raise HeadCommitError("WF95_ATOMIC_CONFLICT_STALE_HEAD")
            self.current=deepcopy(head)
            self.etag='"'+digest(canonical(head))[:32]+'"'
            self.successes+=1
            return {
                "ok":True,
                "head_sha256":head["head_sha256"],
                "generation":head["generation"],
                "atomic_conditional_commit":True,
                "synthetic_only":True,
            }


class V95HeadTests(unittest.TestCase):
    def test_sha_and_generational_parent_are_bound(self):
        first=make_head(
            generation=1,previous_head_sha256=None,
            commit_manifest_sha256=h("manifest0"),
            writer_id="w1")
        verify_head(first)
        self.assertFalse(first["real_fact_authority_granted"])
        self.assertFalse(first["skills_promotion_allowed"])
        self.assertFalse(first["writer_literary_truth_verified"])
        self.assertEqual(verify_head(parse_strict(canonical(first))),first)
        child=make_head(
            generation=2,previous_head_sha256=first["head_sha256"],
            commit_manifest_sha256=h("manifest1"),writer_id="w2")
        self.assertEqual(child["previous_head_sha256"],
                         first["head_sha256"])
        self.assertNotEqual(first["head_sha256"],child["head_sha256"])

    def test_exact_genesis_and_stale_two_writer_race(self):
        host=AtomicFakeTransport()
        first=commit_synthetic_head(
            host,new_manifest_sha256=h("manifest0"),writer_id="writer0")
        etag,parent=host.read()
        winners=[];failures=[]
        lock=threading.Lock()
        gate=threading.Barrier(2)
        def contender(name):
            gate.wait()
            try:
                result=commit_synthetic_head(
                    host,new_manifest_sha256=h("new_"+name),
                    writer_id=name,prior_etag=etag,prior_head=parent)
                with lock:winners.append(result)
            except HeadCommitError as err:
                with lock:failures.append(str(err))
        a=threading.Thread(target=contender,args=("writer_a",))
        b=threading.Thread(target=contender,args=("writer_b",))
        a.start();b.start();a.join(timeout=5);b.join(timeout=5)
        self.assertEqual(len(winners),1)
        self.assertEqual(len(failures),1)
        self.assertIn("ATOMIC_CONFLICT_STALE_HEAD",failures[0])
        self.assertEqual(host.successes,2)
        self.assertEqual(host.current["generation"],2)
        self.assertEqual(host.current["previous_head_sha256"],
                         first["head_sha256"])

    def test_no_route_refuses_to_create_even_synthetic(self):
        host=AtomicFakeTransport(available=False)
        with self.assertRaisesRegex(HeadCommitError,
                                    "ROUTE_NOT_DEPLOYED"):
            commit_synthetic_head(
                host,new_manifest_sha256=h("first"),
                writer_id="writer0")
        self.assertEqual(host.successes,0)

    def test_no_client_side_unconditional_update(self):
        host=AtomicFakeTransport()
        result=commit_synthetic_head(
            host,new_manifest_sha256=h("first"),writer_id="writer0")
        with self.assertRaisesRegex(HeadCommitError,
                                    "ATOMIC_CONFLICT_STALE_HEAD"):
            commit_synthetic_head(
                host,new_manifest_sha256=h("clobber"),writer_id="writer0")
        with self.assertRaisesRegex(HeadCommitError,
                                    "EXPECTED_PREVIOUS_ETAG_MISSING"):
            commit_synthetic_head(
                host,new_manifest_sha256=h("new"),writer_id="writer1",
                prior_head=host.current,prior_etag=None)
        self.assertEqual(host.current["generation"],1)

    def test_cross_project_and_fake_production_flags_rejected(self):
        initial=make_head(
            generation=1,previous_head_sha256=None,
            commit_manifest_sha256=h("x"),writer_id="writer0")
        for field in ("real_fact_authority_granted",
                      "writer_literary_truth_verified",
                      "skills_promotion_allowed","original_prose_stored"):
            forged=deepcopy(initial);forged[field]=True
            with self.subTest(field=field):
                with self.assertRaisesRegex(HeadCommitError,
                                            "HASH_OR_AUTHORITY_TAMPERED"):
                    verify_head(forged)
        forged=deepcopy(initial)
        forged["project_id"]="real_work_project"
        with self.assertRaisesRegex(HeadCommitError,
                                    "AUTHORITATIVE_HEAD_INPUT_INVALID"):
            verify_head(forged)

    def test_unknown_future_versions_and_duplicate_keys_fail_closed(self):
        initial=make_head(
            generation=1,previous_head_sha256=None,
            commit_manifest_sha256=h("first"),writer_id="writer0")
        for kind in ("schema_version","generation","head_sha256"):
            forged=deepcopy(initial)
            forged[kind] = 999 if kind!="head_sha256" else "a"*64
            with self.assertRaises(HeadCommitError):
                verify_head(forged)
        with self.assertRaises(HeadCommitError):
            parse_strict(b'{"format":"first","format":"second"}')
        with self.assertRaises(HeadCommitError):
            parse_strict(b"\xffbroken")
        with self.assertRaises(HeadCommitError):
            parse_strict(b'{"error":"\xef\xbf\xbd"}')

    def test_capabilities_declared_only_for_synthetic_and_atomic_r2(self):
        good={
            "ok":True,"protocol":"wf95-authoritative-head",
            "atomic_r2_conditional_put":True,
            "real_production_facts_allowed":False,
            "synthetic_only":True,
        }
        self.assertTrue(verify_capabilities(good))
        for field,value in (
            ("real_production_facts_allowed",True),
            ("synthetic_only",False),
            ("atomic_r2_conditional_put",False),
        ):
            forged=deepcopy(good);forged[field]=value
            with self.assertRaisesRegex(HeadCommitError,
                                        "CAPABILITY_NOT_DEPLOYED"):
                verify_capabilities(forged)


if __name__=="__main__":
    unittest.main()
