"""Private Google Drive -> private Cloudflare R2, one original TXT per trusted run.

The complete TXT NEVER passes through ChatGPT storage, public GitHub, or
Actions artifacts. GitHub Actions must have its OWN Google service-account
credential, and the file owner must share with that service-account email.
This is file archiving, NOT literary model training.
"""
from __future__ import annotations

from contextlib import closing
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
import json
import os
import re

from writerforge.r2_storage import (
    R2Config, R2StorageError, _canonical, _digest,
    MAX_LATEST_BYTES, MAX_MANIFEST_BYTES,
)
from writerforge.single_work_runner import SingleWorkVault, FORMAT

WORK_ID = "fanrenxiuxian"
TITLE = "凡人修仙传"
EXACT_EXPECTED_BYTES = 15_224_548
MAX_SOURCE_BYTES = 32 * 1024 * 1024
MIN_SOURCE_BYTES = 10 * 1024 * 1024


class DriveR2InputError(R2StorageError):
    pass


def _source_reader(session, file_id: str, destination: Path) -> tuple[str, int, str]:
    if not isinstance(file_id, str) or not re.fullmatch(r"[A-Za-z0-9_-]{12,128}", file_id):
        raise DriveR2InputError("invalid private Google Drive file ID secret")
    url = "https://www.googleapis.com/drive/v3/files/" + file_id
    # Requests execute INSIDE GitHub Actions, never in the ChatGPT runtime.
    try:
        metadata_response = session.get(
            url, params={"fields": "id,name,mimeType,size,trashed"},
            timeout=60, allow_redirects=False,
        )
        if metadata_response.status_code in (401, 403):
            raise DriveR2InputError(
                "GOOGLE_DRIVE_AUTH_OR_SHARE_DENIED: service account lacks access"
            )
        if metadata_response.status_code == 404:
            raise DriveR2InputError(
                "GOOGLE_DRIVE_FILE_NOT_VISIBLE_TO_SERVICE_ACCOUNT: "
                "share this private TXT to the service account email as reader"
            )
        metadata_response.raise_for_status()
        info = metadata_response.json()
        if (info.get("trashed") or info.get("mimeType") != "text/plain"
            or TITLE not in str(info.get("name", ""))):
            raise DriveR2InputError("unexpected Drive original file identity/type")
        size = int(info.get("size", -1))
        if not MIN_SOURCE_BYTES <= size <= MAX_SOURCE_BYTES:
            raise DriveR2InputError("unexpected Drive TXT size in metadata")
        if size != EXACT_EXPECTED_BYTES:
            raise DriveR2InputError(
                "DRIVE_SOURCE_VERSION_CHANGED: size does not match owner-visible version"
            )
        with closing(session.get(
            url, params={"alt": "media"}, stream=True,
            timeout=(30, 120), allow_redirects=False,
        )) as response:
            if response.status_code in (401, 403, 404):
                raise DriveR2InputError(
                    "GOOGLE_DRIVE_DOWNLOAD_AUTH_DENIED: cannot read original bytes"
                )
            # Never allow OAuth token-bearing redirect to another host.
            if response.status_code != 200:
                raise DriveR2InputError(
                    "GOOGLE_DRIVE_MEDIA_HTTP_" + str(response.status_code)
                )
            running = sha256()
            total = 0
            with destination.open("xb") as out:
                for block in response.iter_content(chunk_size=1024 * 1024):
                    if not block:
                        continue
                    total += len(block)
                    if total > MAX_SOURCE_BYTES:
                        raise DriveR2InputError("Drive original exceeds 32 MiB")
                    running.update(block)
                    out.write(block)
        if total != size or total != EXACT_EXPECTED_BYTES:
            raise DriveR2InputError("Drive downloaded original size mismatch")
        if _digest(destination) != (running.hexdigest(), total):
            raise DriveR2InputError("Drive download checksum changed on disk")
        return running.hexdigest(), total, sha256(file_id.encode("ascii")).hexdigest()
    except DriveR2InputError:
        raise
    except Exception as exc:
        # Never report cookies, access tokens, URLs or private response bodies.
        raise DriveR2InputError("GOOGLE_DRIVE_CONNECTOR_CREDENTIALS_OR_NETWORK_ERROR") from exc


def store_private_original(vault: SingleWorkVault, source: Path,
                           *, drive_id_digest: str) -> dict:
    if vault.work_id != WORK_ID or vault.config.bucket != "writerforge-private-library":
        raise DriveR2InputError("wrong work or private R2 destination")
    if (not source.is_file() or source.stat().st_size != EXACT_EXPECTED_BYTES
        or not re.fullmatch(r"[a-f0-9]{64}", drive_id_digest)):
        raise DriveR2InputError("original file size or private source provenance invalid")
    digest, total = _digest(source)
    latest = vault._latest_key(WORK_ID)
    # Existing independent snapshots may be verified, never overwritten as if new.
    old = vault.verify_existing_single_work()
    if old is not None:
        if old["utf8_sha256"] != digest or old["utf8_bytes"] != total:
            raise DriveR2InputError("existing R2 book differs: do not overwrite")
        return {**old, "source_drive_sha256_verified": True, "new_private_archive": False}

    key = vault._blob_key(WORK_ID, digest)
    uploaded = vault._upload_blob(WORK_ID, source, digest, total)
    manifest = {
        "format": FORMAT, "book_id": WORK_ID, "title": TITLE,
        "status": "archived_unreviewed",
        "source_provider": "private_drive_service_account",
        "private_drive_id_sha256": drive_id_digest,
        "file": {"key": key, "sha256": digest, "bytes": total},
        "semantic_training_performed": False,
    }
    data = _canonical(manifest)
    manifest_sha = sha256(data).hexdigest()
    vault._put_small_immutable(vault._manifest_key(WORK_ID, manifest_sha),
                               data, manifest_sha)
    pointer = _canonical({
        "format": FORMAT, "book_id": WORK_ID,
        "snapshot": manifest_sha, "manifest_sha256": manifest_sha,
    })
    if vault._head(latest) is not None:
        raise DriveR2InputError("R2 latest changed concurrently; do not overwrite")
    vault.client.put_object(
        Bucket=vault.config.bucket, Key=latest,
        Body=pointer, ContentType="application/json",
    )
    if vault._get_small(latest, MAX_LATEST_BYTES) != pointer:
        raise DriveR2InputError("new R2 latest pointer readback failed")
    restored = vault.verify_existing_single_work()
    if restored is None or restored["utf8_sha256"] != digest:
        raise DriveR2InputError("new R2 fresh download failed")
    return {
        **restored, "source_drive_sha256_verified": True,
        "new_private_archive": bool(uploaded),
        "source_origin": "private_google_drive_service_account",
        "already_archived": False,
        "uploaded_new_blob": bool(uploaded),
        "r2_fresh_download_verified": True,
    }


def main() -> None:
    credentials_json = os.environ.get("WRITERFORGE_GDRIVE_SERVICE_ACCOUNT_JSON")
    file_id = os.environ.get("WRITERFORGE_FANREN_DRIVE_FILE_ID")
    if not credentials_json or not file_id:
        missing = [
            key for key, value in (
                ("WRITERFORGE_GDRIVE_SERVICE_ACCOUNT_JSON", credentials_json),
                ("WRITERFORGE_FANREN_DRIVE_FILE_ID", file_id),
            ) if not value
        ]
        raise DriveR2InputError("GITHUB_ACTIONS_MISSING_GOOGLE_AUTH_INPUT: " +
                                ",".join(missing))
    try:
        from google.oauth2 import service_account
        from google.auth.transport.requests import AuthorizedSession
    except ImportError as exc:
        raise DriveR2InputError("missing google-auth runtime package") from exc
    try:
        info = json.loads(credentials_json)
        account_email = info["client_email"]
        if not re.fullmatch(r"[^@\s]+@[^@\s]+\.iam\.gserviceaccount\.com",
                            account_email):
            raise ValueError("not a Google service account")
        credentials = service_account.Credentials.from_service_account_info(
            info, scopes=["https://www.googleapis.com/auth/drive.readonly"],
        )
    except (ValueError, KeyError, TypeError) as exc:
        raise DriveR2InputError("invalid service-account JSON in GitHub secret") from exc
    config = R2Config.from_environment()
    if config.bucket != "writerforge-private-library":
        raise DriveR2InputError("not the expected private R2 bucket")
    with TemporaryDirectory(prefix="writerforge-drive-to-r2-") as tmp:
        source = Path(tmp) / "privately-downloaded-original.txt"
        session = AuthorizedSession(credentials)
        digest, total, drive_id_digest = _source_reader(session, file_id, source)
        vault = SingleWorkVault(config, work_id=WORK_ID)
        result = store_private_original(vault, source,
                                        drive_id_digest=drive_id_digest)
        if result["utf8_sha256"] != digest or result["utf8_bytes"] != total:
            raise DriveR2InputError("R2 differs from direct private Drive input")
        # Metadata only: no user original, ID, account name or token appears in logs.
        report = {
            "work_id": WORK_ID, "source_bytes": total,
            "source_sha256": digest, "new_upload": result["uploaded_new_blob"],
            "fresh_r2_download": result["fresh_download_sha256_verified"],
            "private_prefix": result["target_prefix"],
            "r2_snapshot": result["snapshot"],
            "source_transferred_directly_by_github_actions": True,
            "model_training_performed": False,
        }
        print(json.dumps(report, ensure_ascii=False, indent=2))
        if path := os.getenv("GITHUB_STEP_SUMMARY"):
            with open(path, "a", encoding="utf-8") as f:
                f.write("## 凡人修仙传 私有 Google Drive → R2\n")
                f.write(f"Bytes: {total}; SHA256: {digest}\n")
                f.write(f"New upload: {result['uploaded_new_blob']}\n")
                f.write(f"Fresh R2 download verified: {result['fresh_download_sha256_verified']}\n")
                f.write(f"R2 prefix: {result['target_prefix']}\n")
                f.write("Structural/literary training: not performed\n")


if __name__ == "__main__":
    main()
