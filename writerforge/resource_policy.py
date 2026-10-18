"""V54 resource policy: no corpus on install; explicit bounded R2 transfer.

This is *not* a downloader that runs on import or writer start. Only an
operator's explicit r2-plan (metadata-only) / r2-sync --approve-download
can access remote R2. Inspect size before restore, refuse oversized jobs,
and never quietly connect to the author's private R2 for other users.
"""
from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import json
import re
import shutil

from .r2_storage import (
    R2StudyVault, R2StorageError, R2_FORMAT,
    MAX_LATEST_BYTES, MAX_MANIFEST_BYTES, MAX_TOTAL_BYTES,
    MAX_DB_BYTES, MAX_EXTRA_BYTES, _safe_library,
)

SHA = re.compile(r"[0-9a-f]{64}\Z")


class ResourcePolicyError(ValueError):
    pass


def _need(value, reason):
    if not value:
        raise ResourcePolicyError(reason)


def offline_status():
    """Never consult remote credentials, create a file, or instantiate S3."""
    return {
        "format": "writerforge.resource-policy.v1",
        "automatic_corpus_download_on_install": False,
        "automatic_corpus_download_on_import": False,
        "ordinary_skill_requires_author_private_R2": False,
        "r2_source_access_by_explicit_user_action_only": True,
        "remote_sync_permission_required": True,
        "literary_training_performed": False,
    }


def plan_r2(vault: R2StudyVault, *, library: str,
            snapshot: str | None = None, cache: str | Path = "corpus/r2-readonly-cache"):
    """Bounded *metadata* reads only; no blob download or local writes."""
    _need(isinstance(vault, R2StudyVault), "RESOURCE_PRIVATE_R2_CLIENT_REQUIRED")
    _need(vault.config.bucket == "writerforge-private-library",
          "RESOURCE_AUTHOR_PRIVATE_BUCKET_ONLY")
    library = _safe_library(library)
    if snapshot is None:
        pointer_raw = vault._get_small(vault._latest_key(library), MAX_LATEST_BYTES)
        pointer = json.loads(pointer_raw)
        _need(pointer.get("format") == R2_FORMAT and
              pointer.get("library") == library and
              pointer.get("snapshot") == pointer.get("manifest_sha256"),
              "RESOURCE_UNTRUSTED_LATEST_POINTER")
        snapshot = pointer.get("snapshot")
    _need(isinstance(snapshot, str) and SHA.fullmatch(snapshot),
          "RESOURCE_SNAPSHOT_SHA_INVALID")
    encoded = vault._get_small(vault._manifest_key(library, snapshot),
                               MAX_MANIFEST_BYTES)
    _need(sha256(encoded).hexdigest() == snapshot,
          "RESOURCE_R2_MANIFEST_HASH_MISMATCH")
    manifest = json.loads(encoded)
    files = manifest.get("files")
    _need(manifest.get("format") == R2_FORMAT and
          manifest.get("library") == library and
          isinstance(files, dict) and "study.sqlite3" in files and
          1 <= len(files) <= 14, "RESOURCE_MANIFEST_SCHEMA_INVALID")
    expected = 0
    for name, value in files.items():
        _need(isinstance(name, str) and "/" not in name and "\\" not in name
              and name not in (".", "..") and
              (name in ("study.sqlite3", "source.txt") or
               re.fullmatch(r"[a-z][a-z0-9_-]{0,47}\.(json|txt|md)", name)),
              "RESOURCE_FILE_NAME_INVALID")
        _need(isinstance(value, dict) and
              isinstance(value.get("size"), int) and
              type(value["size"]) is int and
              0 < value["size"] <= (
                  MAX_DB_BYTES if name == "study.sqlite3" else MAX_EXTRA_BYTES) and
              isinstance(value.get("sha256"), str) and
              SHA.fullmatch(value["sha256"]),
              "RESOURCE_FILE_METADATA_INVALID")
        expected += value["size"]
    _need(expected <= MAX_TOTAL_BYTES, "RESOURCE_REMOTE_BUDGET_INVALID")
    target = Path(cache).expanduser().resolve()/library/snapshot[:16]
    return {
        "format": "writerforge.r2-resource-plan.v1",
        "library": library, "snapshot_sha256": snapshot,
        "remote_source_bytes": expected,
        "remote_source_mib_approx": round(expected/(1024*1024), 2),
        "file_count": len(files),
        "target_folder": str(target),
        "cache_folder_already_exists": target.exists(),
        "requires_separate_explicit_download_approval": True,
        "contains_original_documents": "source.txt" in files,
        "download_performed": False, "model_calls": 0,
    }


def approved_sync(vault: R2StudyVault, *, library: str, snapshot: str | None,
                  cache: str | Path, approved: bool,
                  max_download_mib: int = 256):
    """Check consent and storage budget BEFORE calling existing restore()."""
    _need(approved is True, "RESOURCE_DOWNLOAD_CONSENT_REQUIRED")
    _need(type(max_download_mib) is int and 1 <= max_download_mib <= 1200,
          "RESOURCE_DOWNLOAD_BUDGET_INVALID")
    plan = plan_r2(vault, library=library, snapshot=snapshot, cache=cache)
    _need(plan["remote_source_bytes"] <= max_download_mib*1024*1024,
          "RESOURCE_EXCEEDS_USER_APPROVED_DOWNLOAD_BUDGET")
    folder = Path(cache).expanduser().resolve()
    check = folder
    while not check.exists():
        _need(check != check.parent, "RESOURCE_DESTINATION_UNAVAILABLE")
        check = check.parent
    free = shutil.disk_usage(check).free
    # R2 restore may temporarily hold the staging files beside final files.
    _need(free >= max(16*1024*1024, 2*plan["remote_source_bytes"]),
          "RESOURCE_INSUFFICIENT_DISK_SPACE")
    from .corpus_foundation import sync_r2
    outcome = sync_r2(vault, library=plan["library"],
                      snapshot=plan["snapshot_sha256"], cache=cache)
    outcome.update({
        "explicit_user_approval": True,
        "user_limit_mib": max_download_mib,
        "planned_remote_bytes": plan["remote_source_bytes"],
        "background_download": False,
    })
    return outcome
