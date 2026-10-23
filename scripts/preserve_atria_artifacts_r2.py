"""One-time *private evidence* preservation, NOT a narrative-memory owner.

Copies exactly nine sealed Atria GitHub Actions artifacts, not raw private
novels, from the authenticated GitHub archive endpoint to existing private R2.
Every immutable ZIP is checked against its original GitHub SHA256 and freshly
read back. No model calls, source texts in logs, overwrite, main or deployment.
"""
from __future__ import annotations

import hashlib
import io
import json
import os
from pathlib import Path
import zipfile

import boto3
from botocore.exceptions import ClientError

from writerforge.r2_storage import R2Config, R2StorageError

REPO = "66tyu55/WriterForge"
PREFIX = "writerforge/v1/private-evidence/atria-seven-genres-20261023"
MAX_DOWNLOAD = 128 * 1024
MAX_ZIP_EXPANDED = 2 * 1024 * 1024
INVENTORY = json.loads(r'''[{"run_id":39937669584,"artifact_id":12494018600,"name":"WF-Atria-Genre-fight-Originals-Receipts","zip_digest":"sha256:9fe190c2d68d2cb1499fde8ba5c9d52ac3ecb7838d1059e0b0f0832f3a148711","expires_at":"2026-11-06T10:20:07Z"},{"run_id":39937669584,"artifact_id":12494019580,"name":"WF-Atria-Genre-psychology-Originals-Receipts","zip_digest":"sha256:1aba0dc4af228e10725054ca45da760a52677bedf505d0496d935576f1a541eb","expires_at":"2026-11-06T10:26:40Z"},{"run_id":39939718654,"artifact_id":12494624315,"name":"WF-Atria-Recovery-climax-Same-6000-Originals","zip_digest":"sha256:f32db178f7b411cb92af6b8099c2cbb46b5417828b9d74b6f28c0b05236378ff","expires_at":"2026-11-06T10:35:26Z"},{"run_id":39937669584,"artifact_id":12494915629,"name":"WF-Atria-Genre-plot-Originals-Receipts","zip_digest":"sha256:963805cc2e18c25503c9c1eb4cd5acea6a52e3c6bf48aa2c849f3f3df72ea13e","expires_at":"2026-11-06T10:17:08Z"},{"run_id":39937669584,"artifact_id":12495025747,"name":"WF-Atria-Genre-climax-Originals-Receipts","zip_digest":"sha256:b250acb6b763ba0e68cd6cd88eb0b296380e7e25e40631207e8067d72d15a763","expires_at":"2026-11-06T10:17:01Z"},{"run_id":39937669584,"artifact_id":12495051315,"name":"WF-Atria-Genre-scheme-Originals-Receipts","zip_digest":"sha256:6f5f3d977e991315571c2246b7f8028a5aa54389e67d9906be149dbc81a1189c","expires_at":"2026-11-06T10:20:02Z"},{"run_id":39937669584,"artifact_id":12495241389,"name":"WF-Atria-Genre-humor-Originals-Receipts","zip_digest":"sha256:4a21391969ee438c9ad24b1806969b084946a86e281f5af4e9568f6b9234d600","expires_at":"2026-11-06T10:24:29Z"},{"run_id":39939718654,"artifact_id":12495387815,"name":"WF-Atria-Recovery-psychology-Same-6000-Originals","zip_digest":"sha256:87be384e71202ce835d9b4f31d21b8304fb73d83af2fa337e6df8c491ff32af6","expires_at":"2026-11-06T10:35:32Z"},{"run_id":39937669584,"artifact_id":12495460453,"name":"WF-Atria-Genre-horror-Originals-Receipts","zip_digest":"sha256:688692fb1c950689886a9a1eaa605e27263db7109926328b716f185b8ec9493e","expires_at":"2026-11-06T10:22:47Z"}]''')


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical(data) -> bytes:
    return json.dumps(data, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("utf8")


def artifact_bytes(item, token, *, session=None):
    """Read only the pre-registered GitHub artifact, fail on changed identity."""
    if session is None:
        import requests
        session=requests
    source = f"https://api.github.com/repos/{REPO}/actions/artifacts/{item['artifact_id']}"
    header = {"Authorization": "Bearer "+token,
              "Accept": "application/vnd.github+json",
              "X-GitHub-Api-Version": "2022-11-28"}
    meta_request = session.get(source, headers=header, timeout=(10, 40))
    meta_request.raise_for_status()
    metadata = meta_request.json()
    if not (metadata.get("id")==item["artifact_id"] and
            metadata.get("name")==item["name"] and
            metadata.get("digest")==item["zip_digest"] and
            metadata.get("expired") is False and
            (metadata.get("workflow_run") or {}).get("id")==item["run_id"] and
            type(metadata.get("size_in_bytes")) is int and
            0<metadata["size_in_bytes"]<=MAX_DOWNLOAD):
        raise RuntimeError("WF_ATRIA_ARTIFACT_IDENTITY_OR_RETENTION_MISMATCH")
    dl=session.get(source+"/zip", headers=header, stream=True,
                   timeout=(10, 50))
    dl.raise_for_status()
    output=bytearray()
    try:
        for chunk in dl.iter_content(16384):
            output.extend(chunk)
            if len(output)>MAX_DOWNLOAD:
                raise RuntimeError("WF_ATRIA_ARTIFACT_ZIP_EXCEEDS_LIMIT")
    finally:
        dl.close()
    archive=bytes(output)
    if digest(archive)!=item["zip_digest"].split(":",1)[1]:
        raise RuntimeError("WF_ATRIA_GITHUB_ZIP_SHA256_MISMATCH")
    if not zipfile.is_zipfile(io.BytesIO(archive)):
        raise RuntimeError("WF_ATRIA_ZIP_FORMAT_INVALID")
    with zipfile.ZipFile(io.BytesIO(archive)) as z:
        files=z.infolist()
        if not files or len(files)>35 or any(
                row.file_size>MAX_ZIP_EXPANDED for row in files) or sum(
                row.file_size for row in files)>MAX_ZIP_EXPANDED or (
                z.testzip() is not None):
            raise RuntimeError("WF_ATRIA_ZIP_INTEGRITY_OR_SIZE_INVALID")
    return archive


def _get_private_object(s3, bucket, key):
    try:
        body=s3.get_object(Bucket=bucket,Key=key)["Body"]
    except ClientError as error:
        code=str(error.response.get("Error",{}).get("Code",""))
        if code in ("404","NoSuchKey","NotFound"):
            return None
        raise
    try:
        raw=body.read(MAX_DOWNLOAD+1)
    finally:
        body.close()
    if len(raw)>MAX_DOWNLOAD:
        raise RuntimeError("WF_ATRIA_R2_READ_EXCEEDS_LIMIT")
    return raw


def preserve_immutable(s3, bucket, key, raw, *, content_type):
    """Never replace a different stored object, including during a race."""
    expected=digest(raw)
    old=_get_private_object(s3,bucket,key)
    if old is None:
        try:
            s3.put_object(Bucket=bucket, Key=key, Body=raw,
                          ContentType=content_type, IfNoneMatch="*")
        except ClientError as error:
            code=str(error.response.get("Error",{}).get("Code",""))
            if code not in ("PreconditionFailed","412"):
                raise
    elif digest(old)!=expected:
        raise RuntimeError("WF_ATRIA_R2_KEY_COLLIDES_WITH_OTHER_BYTES")
    fresh=_get_private_object(s3,bucket,key)
    if fresh is None or digest(fresh)!=expected or fresh!=raw:
        raise RuntimeError("WF_ATRIA_R2_REMOTE_FRESH_GET_MISMATCH")
    return expected


def main():
    if os.environ.get("GITHUB_REF_NAME") != "refactor-unified-scene-delivery-audit":
        raise RuntimeError("WF_ATRIA_EVIDENCE_ARCHIVE_WRONG_BRANCH")
    token=os.environ.get("GITHUB_TOKEN")
    if not token:
        raise RuntimeError("WF_ATRIA_MISSING_GITHUB_ACTIONS_READ_TOKEN")
    if not (len(INVENTORY)==9 and
            sorted(set(a["run_id"] for a in INVENTORY))==
                [39937669584,39939718654] and
            len(set(a["artifact_id"] for a in INVENTORY))==9):
        raise RuntimeError("WF_ATRIA_INVENTORY_UNEXPECTED")
    config=R2Config.from_environment()
    if config.bucket!="writerforge-private-library":
        raise R2StorageError("WF_ATRIA_WRONG_PRIVATE_R2_BUCKET")
    s3=boto3.client(
        "s3",endpoint_url=config.endpoint,
        aws_access_key_id=config.access_key_id,
        aws_secret_access_key=config.secret_access_key,
        region_name="auto")
    receipts=[]
    for item in INVENTORY:
        archive=artifact_bytes(item,token)
        h=digest(archive)
        key=f"{PREFIX}/artifacts/{item['artifact_id']}-{h}.zip"
        preserve_immutable(s3,config.bucket,key,archive,
                           content_type="application/zip")
        receipts.append({
            **item,"preserved_zip_sha256":h,
            "preserved_zip_size":len(archive),
            "private_r2_key":key,
            "fresh_remote_get_verified":True,
        })
    manifest={
        "format":"wf.evidence.atria-seven-genre-preservation.v1",
        "source_repo":REPO,"purpose":"sealed original Atria failures only",
        "genre_count":7,"artifact_count":9,"original_pairs":7,
        "initial_run":39937669584,"recovery_run":39939718654,
        "original_source_unmodified":True,
        "cross_genre_token_budget_not_equal":True,
        "no_model_calls":True,"canon_writes":0,"production_deployed":False,
        "artifacts":receipts,
    }
    data=canonical(manifest)
    manifest_hash=digest(data)
    if len(data)>MAX_DOWNLOAD:
        raise RuntimeError("WF_ATRIA_MANIFEST_TOO_LARGE")
    preserve_immutable(
        s3,config.bucket,f"{PREFIX}/manifests/{manifest_hash}.json",data,
        content_type="application/json")
    Path("wf_atria_private_evidence_status").mkdir(exist_ok=True)
    summary={
        "source_run_ids":[39937669584,39939718654],
        "preserved_original_github_artifacts":9,
        "private_r2_fresh_get_success":9,
        "immutable_manifest_sha256":manifest_hash,
        "source_copies_logged_or_published":False,
        "new_model_calls":0,"canon_writes":0,
        "main_or_railway_changed":False,
    }
    Path("wf_atria_private_evidence_status/STATUS.json").write_text(
        json.dumps(summary,ensure_ascii=False,indent=2),encoding="utf8")
    print(json.dumps(summary,ensure_ascii=False,sort_keys=True))


if __name__=="__main__":
    main()
