"""Synthetic-only encrypted original prose evidence; NEVER use true novel text."""
import base64,importlib.util,unittest
from hashlib import sha256
from types import SimpleNamespace
from writerforge.reverse_private_draft_evidence import (
    PrivateDraftEvidenceVault,DraftEvidenceError,
)
from test_v28_cloud_ab import FakeModel,PLANNER,CRITIC
from writerforge.reverse_cloud_ab import CloudABTrial
from writerforge.reverse_real_training import raw_hash

KEY=base64.b64encode(b"K"*32).decode("ascii")
CRYPTO=importlib.util.find_spec("cryptography") is not None

class FakeStore:
    def __init__(self):
        self.config=SimpleNamespace(bucket="writerforge-private-library")
        self.objects={}
        self.client=SimpleNamespace(delete_object=self.delete)
    def _put_small_immutable(self,key,content,sha):
        if key in self.objects and self.objects[key]!=content:raise ValueError("overwrite")
        if sha256(content).hexdigest()!=sha:raise ValueError("invalid SHA")
        self.objects[key]=content
    def _get_small(self,key,cap):
        b=self.objects[key]
        if len(b)>cap:raise ValueError("over cap")
        return b
    def _head(self,key):
        return {"ContentLength":len(self.objects[key])} if key in self.objects else None
    def delete(self,*,Bucket,Key):
        assert Bucket=="writerforge-private-library"
        self.objects.pop(Key,None)

@unittest.skipUnless(CRYPTO,"optional evidence crypto dependency not installed")
class PrivateDraftEvidenceTests(unittest.TestCase):
    def sample(self):
        source=("合成的雨夜小径并不是任何现成小说的一部分。"+chr(10))*18
        draft_a="雨夜的人站在废桥旁边，犹豫着要不要绕路前进。"*20
        draft_b="守桥的少年听见雨声，决定先用灯检查石阶是否滑动。"*20
        return source,{"baseline":draft_a,"skill":draft_b}

    def test_private_ciphertext_not_plaintext_then_readback_then_expiry_delete(self):
        times=[1_850_000_000]
        store=FakeStore()
        vault=PrivateDraftEvidenceVault(store,encryption_key_b64=KEY,
                                       ttl_days=1,clock=lambda:times[0])
        source,drafts=self.sample()
        rec=vault.save_pair(drafts,source_unit_sha256=raw_hash(source),
                            task_sha256="a"*64)
        self.assertTrue(rec["encrypted"])
        self.assertTrue(rec["retention_needs_explicit_cleanup"])
        self.assertEqual(len(store.objects),1)
        cipher=next(iter(store.objects.values()))
        self.assertNotIn(drafts["baseline"].encode(),cipher)
        self.assertNotIn(drafts["skill"].encode(),cipher)
        decoded=vault.read_pair(rec)
        self.assertEqual(decoded["drafts"],drafts)
        self.assertFalse(decoded["human_review_performed"])
        with self.assertRaisesRegex(DraftEvidenceError,"EXPLICIT_CLEANUP"):
            vault.delete_expired(rec)
        with self.assertRaisesRegex(DraftEvidenceError,"RETENTION_WINDOW"):
            vault.delete_expired(rec,explicitly_authorized=True)
        times[0]+=86400
        with self.assertRaisesRegex(DraftEvidenceError,"EXPIRED"):
            vault.read_pair(rec)
        vault.delete_expired(rec,explicitly_authorized=True)
        self.assertEqual(store.objects,{})

    def test_wrong_key_or_receipt_not_decryptable(self):
        store=FakeStore()
        vault=PrivateDraftEvidenceVault(store,encryption_key_b64=KEY)
        src,drafts=self.sample()
        receipt=vault.save_pair(drafts,source_unit_sha256=raw_hash(src),task_sha256="a"*64)
        wrong=PrivateDraftEvidenceVault(
            store,encryption_key_b64=base64.b64encode(b"Z"*32).decode())
        with self.assertRaisesRegex(DraftEvidenceError,"DECRYPTION"):
            wrong.read_pair(receipt)
        bad={**receipt,"task_sha256":"b"*64}
        with self.assertRaises(DraftEvidenceError):
            vault.read_pair(bad)

    def test_legacy_ab_keeps_ephemeral_drafts_and_opt_in_is_only_after_critic(self):
        store=FakeStore()
        vault=PrivateDraftEvidenceVault(store,encryption_key_b64=KEY)
        src,_=self.sample()
        p=FakeModel("planner",PLANNER,"p")
        w=FakeModel("writer",{},"w")
        c=FakeModel("critic",CRITIC,"c")
        out=CloudABTrial(planner=p,writer=w,critic=c,
                         manuscript_sink=vault).run(
            src,"合成后续"*60,source_sha="a"*64,window_hash=raw_hash(src))
        self.assertTrue(out["drafts_retained"])
        self.assertTrue(out["private_encrypted_manuscript_evidence"]["encrypted"])
        self.assertNotIn("陌生的山雨",str(out))
        self.assertEqual(len(store.objects),1)
        self.assertFalse(out["core_automatically_promoted"])
        from writerforge.reverse_ab_candidates import (
            derive_unverified_candidates,_canonical,CandidateEvidenceError,
        )
        raw_digest=sha256(_canonical(out)).hexdigest()
        candidate=derive_unverified_candidates(out,receipt_sha256=raw_digest)
        self.assertTrue(candidate["future_drafts_reviewable_with_separate_key"])
        self.assertEqual(candidate["encrypted_draft_receipt_sha256"],
                         out["private_encrypted_manuscript_evidence"]["receipt_sha256"])
        self.assertFalse(candidate["promotable"])
        p2=FakeModel("planner",PLANNER,"p")
        w2=FakeModel("writer",{},"w")
        c2=FakeModel("critic",CRITIC,"c")
        original=CloudABTrial(planner=p2,writer=w2,critic=c2).run(
            src,"合成后续"*60,source_sha="a"*64,window_hash=raw_hash(src))
        self.assertFalse(original["drafts_retained"])
        self.assertIsNone(original["private_encrypted_manuscript_evidence"])

    def test_missing_or_insecure_key_fails_closed(self):
        store=FakeStore()
        with self.assertRaisesRegex(DraftEvidenceError,"KEY"):
            PrivateDraftEvidenceVault(store,encryption_key_b64="")
        with self.assertRaisesRegex(DraftEvidenceError,"256_BITS"):
            PrivateDraftEvidenceVault(store,
                 encryption_key_b64=base64.b64encode(b"short").decode())
        store.config=SimpleNamespace(bucket="public-sandbox")
        with self.assertRaisesRegex(DraftEvidenceError,"PRIVATE_BUCKET"):
            PrivateDraftEvidenceVault(store,encryption_key_b64=KEY)

if __name__=="__main__":
    unittest.main()
