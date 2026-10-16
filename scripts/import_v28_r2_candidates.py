"""One-shot R2-to-R2 backfill of previously saved V28 v4 *abstract* evidence.

NO language-model SDK, DISCOVERY secret, novel blob download, or new prompt.
This script reads the immutable A/B receipt and writes only bounded candidate
metadata under a new content-addressed key in the same PRIVATE R2 bucket.
It must never unlock the second source window.
"""
from __future__ import annotations

from hashlib import sha256
import json

from writerforge.r2_storage import R2Config, R2StudyVault, _canonical
from writerforge.reverse_ab_candidates import derive_unverified_candidates
# Freeze the *historical* role mapping so future model changes cannot make
# this immutable trial inaccessible during offline re-audit.
PINNED_ROLES = {
    "planner": "deepseek-v4-flash-0731",
    "writer": "glm-5.3",
    "critic": "deepseek-v4-flash-0731",
}

WORK = "wudongqiankun"
SOURCE_SHA = "86a2fd859b424efe0500b4b36713ea8b05d551140650904ffc2ae02eb244ed28"
RECEIPT_SHA = "a2882f770e76fee4f4cedffb219d919a1a169fd731832b3d2de24e105c6a0282"
PREFIX = "writerforge/v1/reverse-craft/wudongqiankun/cross-vendor-flash-glm53-50k-ab-v4"
TRIAL = "cross-vendor-flash-glm53-50k-ab-v4"
MAX_RECEIPT_BYTES = 32000


def import_prior_receipt(r2: R2StudyVault) -> dict:
    if r2.config.bucket != "writerforge-private-library":
        raise ValueError("only the user's pinned private R2 library is valid")
    config = {
        "source": SOURCE_SHA,
        "task": "opening-chapter-1-contiguous-window-1",
        "roles": dict(PINNED_ROLES),
        "trial": TRIAL,
    }
    key_root = f"{PREFIX}/{sha256(_canonical(config)).hexdigest()}"
    raw = r2._get_small(f"{key_root}/snapshots/{RECEIPT_SHA}.json",
                        MAX_RECEIPT_BYTES)
    if sha256(raw).hexdigest() != RECEIPT_SHA:
        raise ValueError("PRIVATE_R2_EXISTING_RECEIPT_HASH_FAILED")
    report = json.loads(raw)
    candidate = derive_unverified_candidates(report, receipt_sha256=RECEIPT_SHA)
    if candidate["work"] != WORK or candidate["edition_sha256"] != SOURCE_SHA:
        raise ValueError("PINNED_SOURCE_REPORT_MISMATCH")
    serialized = _canonical(candidate)
    candidate_hash = sha256(serialized).hexdigest()
    dest = f"{key_root}/offline-candidates/{candidate_hash}.json"
    # Hash-indexed immutable data. No latest pointer and no writing into old
    # snapshots or a user's existing original-source library.
    r2._put_small_immutable(dest, serialized, candidate_hash)
    recovered = r2._get_small(dest, 8192)
    if recovered != serialized or sha256(recovered).hexdigest() != candidate_hash:
        raise ValueError("CANDIDATE_R2_ROUNDTRIP_FAILED")
    return {
        "stage": "V28_EXISTING_RECEIPT_OFFLINE_CANDIDATE_R2_VERIFIED",
        "historical_receipt_sha256": RECEIPT_SHA,
        "candidate_sha256": candidate_hash,
        "fault_count": len(candidate["fault_candidates_unreviewed"]),
        "mechanism_count_unreviewed": len(candidate["mechanism_hypotheses_unreviewed"]),
        "model_calls": 0, "novel_blob_downloaded": False,
        "human_review_performed": False, "literary_mastery_verified": False,
        "first_window": "NOT_PASSED", "second_window": "LOCKED",
    }


def main() -> None:
    config = R2Config.from_environment()
    result = import_prior_receipt(R2StudyVault(config))
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
