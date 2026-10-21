"""GitHub Actions S3-compatible R2 CAS, isolated from Railway.

Only new V113 ORIGINAL WRITING experiment blobs are read/written.
No list/prefix scan, no user novels, no snapshot mutations or pointer rewrites.
SHA-256 immutable content-addressed objects, fresh independent readbacks,
S3 conditional write (IfNoneMatch="*") to refuse accidental run replays.
"""
from __future__ import annotations
from hashlib import sha256
from botocore.exceptions import ClientError
from writerforge.r2_storage import R2Config,R2StudyVault

PREFIX="writerforge/v1/experiments/v113-matched-fantasy-chase/sha256/"
MAX_OBJECT_BYTES=280000

class V113CASException(RuntimeError):
    pass

class GitHubS3CAS:
    def __init__(self,*,config=None,client=None):
        self.config=config or R2Config.from_environment()
        self.client=client or R2StudyVault(self.config).client
        self.bucket=self.config.bucket

    @staticmethod
    def _key(digest):
        if (type(digest) is not str or len(digest)!=64 or
            any(ch not in "0123456789abcdef" for ch in digest)):
            raise V113CASException("WF112_INVALID_PRIVATE_CAS_SHA")
        return PREFIX+digest[:2]+"/"+digest

    def require_writer_ready(self):
        # Existing four secrets and config were parsed; a real put+get
        # of the frozen experiment precommit proves S3 writeability.
        return True

    @staticmethod
    def _remote_error(e):
        return str(e.response.get("Error",{}).get("Code","")) if (
            isinstance(getattr(e,"response",None),dict)) else ""

    def _get_content(self,digest):
        key=self._key(digest)
        try:
            item=self.client.get_object(Bucket=self.bucket,Key=key)
            body=item["Body"]
            try:
                raw=body.read(MAX_OBJECT_BYTES+1)
            finally:
                close=getattr(body,"close",None)
                if callable(close):close()
        except ClientError:
            raise V113CASException("WF112_R2_CAS_READ_FAILED") from None
        if (type(raw) is not bytes or len(raw)>MAX_OBJECT_BYTES
            or sha256(raw).hexdigest()!=digest):
            raise V113CASException("WF112_R2_CAS_CONTENT_HASH_MISMATCH")
        return raw

    def _put_content(self,content):
        if (type(content) is not bytes or not (0<len(content)<=MAX_OBJECT_BYTES)):
            raise V113CASException("WF112_R2_OBJECT_SIZE_INVALID")
        digest=sha256(content).hexdigest()
        key=self._key(digest)
        try:
            self.client.head_object(Bucket=self.bucket,Key=key)
        except ClientError as e:
            if self._remote_error(e) not in ("404","NoSuchKey","NotFound"):
                raise V113CASException("WF112_R2_HEAD_PERMISSION_OR_NETWORK_FAILURE") from None
        else:
            if self._get_content(digest)!=content:
                raise V113CASException("WF112_EXISTING_CAS_COLLISION")
            return digest,False
        try:
            # If a parallel run races for the same content, only one can
            # claim the first write. Never overwrite an existing object.
            self.client.put_object(Bucket=self.bucket,Key=key,
                Body=content,IfNoneMatch="*",
                ContentType="application/octet-stream",
                Metadata={"sha256":digest})
            first=True
        except ClientError as e:
            if self._remote_error(e) in ("412","PreconditionFailed","409",
                                         "ConditionalRequestConflict"):
                first=False
            else:
                raise V113CASException("WF112_R2_CONDITIONAL_PUT_FAILED") from None
        if self._get_content(digest)!=content:
            raise V113CASException("WF112_R2_FRESH_CAS_READBACK_FAILED")
        return digest,first
