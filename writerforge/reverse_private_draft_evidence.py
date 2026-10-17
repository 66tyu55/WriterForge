"""Opt-in, client-side AES-GCM encrypted, bounded private draft evidence.

Legacy training stores only hashes. This class is for FUTURE experiments
explicitly opting into retention, never recovery of prior discarded drafts.
The source novel, original paragraphs and planner analysis are NOT saved.

Requires an INDEPENDENT 32-byte random key in
WF_PRIVATE_DRAFT_KEY_B64 (base64). Never derive it from R2 credentials and
never log it. Missing key -> fail before any persistence. Cloudflare R2
private bucket != zero-knowledge encryption; client side AES-GCM adds
protection at rest. The key must be backed up by the user; loss of key means
drafts cannot be recovered.

Retention expires after <=14 days but is NOT auto-deleted without invoking
delete_expired explicitly; expiration is enforced during reads.
"""
from __future__ import annotations
from hashlib import sha256
from datetime import datetime,timezone
from collections.abc import Mapping
import base64,json,os,re,time

from .r2_storage import _canonical

SHA=re.compile(r"[0-9a-f]{64}\Z")
MAX_TTL_DAYS=14
MAX_BLOB_BYTES=42000
PREFIX="writerforge/v1/private-draft-review-evidence"

class DraftEvidenceError(ValueError):
    pass

def _sha(data:bytes)->str:
    return sha256(data).hexdigest()

def _key(value:str)->bytes:
    if not isinstance(value,str) or len(value)>120:
        raise DraftEvidenceError("ENCRYPTION_KEY_REQUIRED")
    try:
        binary=base64.b64decode(value,validate=True)
    except (ValueError,TypeError):
        raise DraftEvidenceError("ENCRYPTION_KEY_INVALID_BASE64") from None
    if len(binary)!=32:
        raise DraftEvidenceError("ENCRYPTION_KEY_NOT_256_BITS")
    return binary

def _aes():
    try:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    except ImportError as exc:
        raise DraftEvidenceError("INSTALL_WRITERFORGE_EVIDENCE_CRYPTO_EXTRA") from exc
    return AESGCM

class PrivateDraftEvidenceVault:
    def __init__(self,store, *, encryption_key_b64:str,ttl_days:int=7,clock=None):
        if store.config.bucket!="writerforge-private-library":
            raise DraftEvidenceError("PRIVATE_BUCKET_REQUIRED")
        if type(ttl_days) is not int or not 1<=ttl_days<=MAX_TTL_DAYS:
            raise DraftEvidenceError("UNBOUNDED_DRAFT_RETENTION")
        self.store=store
        self.key=_key(encryption_key_b64)
        self.aes=_aes()
        self.ttl_days=ttl_days
        self.clock=clock or time.time

    @classmethod
    def from_environment(cls,store,*,environ=None,ttl_days=7):
        env=os.environ if environ is None else environ
        return cls(store,encryption_key_b64=env.get("WF_PRIVATE_DRAFT_KEY_B64",""),
                   ttl_days=ttl_days)

    def save_pair(self,drafts:Mapping[str,str],*,source_unit_sha256:str,
                  task_sha256:str)->dict:
        if (not isinstance(drafts,Mapping) or set(drafts)!={"baseline","skill"}
            or not isinstance(source_unit_sha256,str)
            or not SHA.fullmatch(source_unit_sha256)
            or not isinstance(task_sha256,str) or not SHA.fullmatch(task_sha256)):
            raise DraftEvidenceError("INVALID_SOURCE_TASK_DRAFT_METADATA")
        if any(not isinstance(v,str) or not 220<=len(v)<=4500 for v in drafts.values()):
            raise DraftEvidenceError("DRAFT_PAIR_OUTSIDE_BOUNDS")
        data={
            "format":"writerforge.private-original-drafts.v1",
            "source_unit_sha256":source_unit_sha256,
            "task_sha256":task_sha256,
            "drafts":{k:drafts[k] for k in ("baseline","skill")},
            "draft_sha256":{k:_sha(drafts[k].encode("utf-8"))
                            for k in ("baseline","skill")},
            "created_unix":int(self.clock()),
            "retention_days":self.ttl_days,
            "human_review_performed":False,
            "source_novel_prose_retained":False,
        }
        plaintext=_canonical(data)
        if len(plaintext)>26000:
            raise DraftEvidenceError("DRAFT_PAIR_BINARY_SIZE_EXCEEDED")
        nonce=os.urandom(12)
        aad=(source_unit_sha256+":"+task_sha256).encode("ascii")
        encrypted=self.aes(self.key).encrypt(nonce,plaintext,aad)
        envelope={
            "format":"writerforge.private-draft-aes256gcm.v1",
            "nonce_b64":base64.b64encode(nonce).decode("ascii"),
            "ciphertext_b64":base64.b64encode(encrypted).decode("ascii"),
            "aad_sha256":_sha(aad),
        }
        blob=_canonical(envelope)
        if len(blob)>MAX_BLOB_BYTES:
            raise DraftEvidenceError("ENCRYPTED_PAIR_SIZE_EXCEEDED")
        digest=_sha(blob)
        key=f"{PREFIX}/{task_sha256[:16]}/{digest}.json"
        self.store._put_small_immutable(key,blob,digest)
        fresh=self.store._get_small(key,MAX_BLOB_BYTES)
        if fresh!=blob or _sha(fresh)!=digest:
            raise DraftEvidenceError("ENCRYPTED_R2_READBACK_FAILED")
        return {
            "format":"writerforge.private-draft-receipt.v1",
            "encrypted":True,
            "receipt_sha256":digest,
            "source_unit_sha256":source_unit_sha256,
            "task_sha256":task_sha256,
            "draft_sha256":data["draft_sha256"],
            "expires_unix":data["created_unix"]+self.ttl_days*86400,
            "retention_needs_explicit_cleanup":True,
            "source_or_draft_plaintext_in_report":False,
        }

    def _key_from_receipt(self,receipt:dict)->str:
        if (not isinstance(receipt,dict) or
            receipt.get("format")!="writerforge.private-draft-receipt.v1"
            or receipt.get("encrypted") is not True):
            raise DraftEvidenceError("INVALID_ENCRYPTED_RECEIPT")
        digest=receipt.get("receipt_sha256")
        task=receipt.get("task_sha256")
        source=receipt.get("source_unit_sha256")
        if any(not isinstance(x,str) or not SHA.fullmatch(x)
               for x in (digest,task,source)):
            raise DraftEvidenceError("INVALID_RECEIPT_SHA")
        return f"{PREFIX}/{task[:16]}/{digest}.json"

    def read_pair(self,receipt:dict)->dict:
        key=self._key_from_receipt(receipt)
        if type(receipt.get("expires_unix")) is not int:
            raise DraftEvidenceError("MISSING_EXPIRATION_TIME")
        if self.clock()>=receipt["expires_unix"]:
            raise DraftEvidenceError("DRAFT_EVIDENCE_EXPIRED")
        blob=self.store._get_small(key,MAX_BLOB_BYTES)
        if _sha(blob)!=receipt["receipt_sha256"]:
            raise DraftEvidenceError("ENCRYPTED_BLOB_DIGEST_MISMATCH")
        env=json.loads(blob)
        if env.get("format")!="writerforge.private-draft-aes256gcm.v1":
            raise DraftEvidenceError("INVALID_ENCRYPTION_ENVELOPE")
        aad=(receipt["source_unit_sha256"]+":"+receipt["task_sha256"]).encode("ascii")
        if env.get("aad_sha256")!=_sha(aad):
            raise DraftEvidenceError("MISMATCHED_SOURCE_TASK_AAD")
        try:
            nonce=base64.b64decode(env["nonce_b64"],validate=True)
            ciphertext=base64.b64decode(env["ciphertext_b64"],validate=True)
            if len(nonce)!=12 or len(ciphertext)>30000:
                raise ValueError("cipher bound")
            original=self.aes(self.key).decrypt(nonce,ciphertext,aad)
            recovered=json.loads(original)
        except Exception:
            raise DraftEvidenceError("DRAFT_DECRYPTION_OR_INTEGRITY_FAILED") from None
        if (recovered.get("source_unit_sha256")!=receipt["source_unit_sha256"] or
            recovered.get("task_sha256")!=receipt["task_sha256"] or
            recovered.get("draft_sha256")!=receipt["draft_sha256"] or
            recovered.get("created_unix")+recovered.get("retention_days")*86400!=
            receipt["expires_unix"] or
            recovered.get("human_review_performed") is not False):
            raise DraftEvidenceError("DECRYPTED_RECEIPT_PROVENANCE_MISMATCH")
        return recovered

    def delete_expired(self,receipt:dict, *, explicitly_authorized:bool=False)->dict:
        """No automatic background cleanup; caller must deliberately invoke."""
        key=self._key_from_receipt(receipt)
        if explicitly_authorized is not True:
            raise DraftEvidenceError("EXPLICIT_CLEANUP_AUTHORIZATION_REQUIRED")
        if type(receipt.get("expires_unix")) is not int or self.clock()<receipt["expires_unix"]:
            raise DraftEvidenceError("RETENTION_WINDOW_NOT_YET_EXPIRED")
        self.store.client.delete_object(Bucket=self.store.config.bucket,Key=key)
        if self.store._head(key) is not None:
            raise DraftEvidenceError("PRIVATE_R2_DELETION_NOT_VERIFIED")
        return {"deleted_receipt_sha256":receipt["receipt_sha256"],
                "expired_evidence_cleaned":True}
