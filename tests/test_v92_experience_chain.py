"""V92 synthetic cold restores and migration-chain hostile fixtures.

These tests never contact R2 or any model provider. They build fifteen
Chinese V80 experience CAS documents, intentionally break the source chain,
and verify that a V92 manifest can only reference full verified V91 data.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
from unittest.mock import patch
import unittest

from writerforge.v91_experience_migration import (
    canonical, strict_roundtrip, restore_v91_experience,
)
from writerforge import v92_experience_chain as chain


def sha(raw):
    return sha256(raw).hexdigest()


class SyntheticChain:
    def __init__(self):
        self.raw={}
        self.old={}
        prev=None
        for n in range(1,16):
            candidate={
                "format":"wf.learn.experience.v80",
                "source_sha256":"a"*64,
                "source_key_sha256":"b"*64,
                "chapter":n,
                "analysis_sha256":sha(f"analysis-{n}".encode()),
                "previous_experience_sha256":prev,
                "model":"deepseek-flash",
                "reflection":{
                    "observed_weakness":f"第{n}章人物的实际知识还需独立确认。",
                    "next_strategy":f"第{n}章以后先查明人物知道什么，不能用结局倒推原因。",
                    "open_question":f"第{n}章出现的承诺是否会得到真实兑现？",
                    "confidence_limit":"这些只是模型的候选想法，不是已通过的文学判断。"
                },
                "applied_to_next_chapter_prompts":bool(n%2),
                "literary_quality_independently_verified":False,
            }
            raw=canonical(candidate)
            pointer=sha(raw)
            self.raw[pointer]=raw
            self.old[n]=pointer
            prev=pointer
        self.head=prev
        self.migrated15=canonical(strict_roundtrip(
            self.raw[self.head],self.head))
        self.migrated15_sha=sha(self.migrated15)
        self.saved_patches={}

    def patch(self):
        return [
            patch.object(chain,"ORIGINAL_V80_HEAD",self.head),
            patch.object(chain,"V91_CH15_CAS",self.migrated15_sha),
            patch.object(chain,"SOURCE_SHA","a"*64),
            patch.object(chain,"SOURCE_KEY_SHA","b"*64),
            patch.object(chain,"V91_CH15_MANIFEST","c"*64),
        ]

    def build(self):
        with self.patch()[0],self.patch()[1],self.patch()[2],self.patch()[3],self.patch()[4]:
            # Old and new JSON blobs have different SHA addresses.
            rows,objects=chain.walk_v80_chain(
                self.read,head=self.head,required_source_sha="a"*64,
                required_source_key_sha="b"*64)
            for data in objects.values():
                self.raw[sha(data)]=data
            manifest=chain.make_manifest(rows)
            proof=chain.verify_manifest(
                canonical(manifest),self.read,head=self.head,
                source_sha="a"*64,key_sha="b"*64)
        return rows,objects,manifest,proof

    def read(self,key):
        return self.raw[key]


class V92ChainTests(unittest.TestCase):
    def setUp(self):
        self.c=SyntheticChain()

    def test_fifteen_chapter_old_to_new_full_chinese_roundtrip(self):
        rows,objects,manifest,proof=self.c.build()
        self.assertEqual([r["chapter"] for r in rows],list(range(1,16)))
        self.assertEqual(proof["verified_chapters"],15)
        self.assertEqual(proof["verified_v91_experiences"],15)
        self.assertTrue(rows[0]["v80_chapter1_mixed_pilot_not_strict_pass_a"])
        self.assertFalse(rows[-1]["v80_chapter1_mixed_pilot_not_strict_pass_a"])
        for ch in range(1,16):
            restored=restore_v91_experience(objects[ch])
            self.assertIn(f"第{ch}章",restored["reflection"]["next_strategy"])
            self.assertEqual(restored["original_v80_cas_sha256"],self.c.old[ch])
            self.assertFalse(restored["eligible_for_WF_WRITE"])
        self.assertFalse(manifest["complete_lifelong_brain_verified"])
        self.assertFalse(manifest["fact_journal_sqlite_graph_included"])
        text=canonical(manifest).decode("utf8")
        self.assertNotIn("这些只是模型的候选想法",text)
        self.assertNotIn("先查明人物知道什么",text)

    def test_missing_or_corrupted_old_cas_refuses_no_skip(self):
        self.c.raw.pop(self.c.old[7])
        with patch.object(chain,"V91_CH15_CAS",self.c.migrated15_sha):
            with self.assertRaisesRegex(chain.V92ChainError,
                                        "REMOTE_EXPERIENCE_MISSING"):
                chain.walk_v80_chain(self.c.read,head=self.c.head,
                    required_source_sha="a"*64,required_source_key_sha="b"*64)
        self.c=SyntheticChain()
        self.c.raw[self.c.old[8]]=b"garbled-not-same-hash"
        with self.assertRaisesRegex(chain.V92ChainError,
                                    "CONTENT_ADDRESS_MISMATCH"):
            chain.walk_v80_chain(self.c.read,head=self.c.head,
                 required_source_sha="a"*64,required_source_key_sha="b"*64)

    def test_wrong_source_identity_fails(self):
        with self.assertRaisesRegex(chain.V92ChainError,"OTHER_BOOK"):
            chain.walk_v80_chain(self.c.read,head=self.c.head,
                                 required_source_sha="f"*64,
                                 required_source_key_sha="b"*64)

    def test_genesis_and_version_cannot_be_fabricated(self):
        raw=self.c.raw[self.c.old[1]]
        obj=__import__("json").loads(raw)
        obj["previous_experience_sha256"]="0"*64
        changed=canonical(obj)
        bad_pointer=sha(changed)
        self.c.raw[bad_pointer]=changed
        # Modify chapter2 predecessor to make the altered genesis reachable.
        old2=__import__("json").loads(self.c.raw[self.c.old[2]])
        old2["previous_experience_sha256"]=bad_pointer
        changed2=canonical(old2)
        p2=sha(changed2)
        self.c.raw[p2]=changed2
        # Full fifteen-work chain from this changed head is not reachable:
        # original chapter3 still points to original chapter2, not new p2.
        with self.assertRaisesRegex(chain.V92ChainError,
                                    "WRONG_GENESIS_OR_BROKEN_LINK"):
            with patch.object(chain,"V91_CH15_CAS",self.c.migrated15_sha):
                # Directly validate genesis precondition on a verified doc.
                migrated=strict_roundtrip(changed,bad_pointer)
                chain._check_exact_predecessor(migrated,1,None)

    def test_forged_manifest_metadata_rejected_even_if_hashes_exist(self):
        rows,objects,manifest,proof=self.c.build()
        with self.c.patch()[0],self.c.patch()[1],self.c.patch()[2],self.c.patch()[3],self.c.patch()[4]:
            changed=deepcopy(manifest)
            changed["chapters"][3]["reflection_sha256"]["next_strategy"]="0"*64
            with self.assertRaisesRegex(chain.V92ChainError,
                                        "SOURCE_LINEAGE_OR_POLICY_CHANGED"):
                chain.verify_manifest(canonical(changed),self.c.read,
                    head=self.c.head,source_sha="a"*64,key_sha="b"*64)
            changed=deepcopy(manifest)
            changed["chapter_count"]=16
            with self.assertRaisesRegex(chain.V92ChainError,
                                        "SOURCE_LINEAGE_OR_POLICY_CHANGED"):
                chain.verify_manifest(canonical(changed),self.c.read,
                    head=self.c.head,source_sha="a"*64,key_sha="b"*64)

    def test_cold_read_of_missing_migrated_object_fails(self):
        rows,objects,manifest,proof=self.c.build()
        lost=rows[5]["v91_experience_cas_sha256"]
        self.c.raw.pop(lost)
        with self.c.patch()[0],self.c.patch()[1],self.c.patch()[2],self.c.patch()[3],self.c.patch()[4]:
            with self.assertRaises((KeyError,chain.V92ChainError)):
                chain.verify_manifest(canonical(manifest),self.c.read,
                    head=self.c.head,source_sha="a"*64,key_sha="b"*64)

    def test_chain_remains_candidate_never_auto_uses_in_write(self):
        _,_,manifest,_=self.c.build()
        self.assertFalse(manifest["literary_quality_independently_verified"])
        self.assertFalse(manifest["write_skill_promotion_permitted"])
        self.assertFalse(manifest["model_retraining_performed"])
        self.assertTrue(manifest["chapter1_pilot_historical_exception_preserved"])

if __name__=="__main__":
    unittest.main()
