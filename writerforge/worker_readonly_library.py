"""V67: bounded, verified, ephemeral READ-ONLY WF library access via Worker.

The Worker is NOT a SQL database. It streams only the two verified objects
needed for a single pinned library; WriterForge opens its own temporary SQLite
with mode=ro and query_only=ON. No whole-bucket sync, private-source logging,
new S3 credentials, model inference, permanent disk cache or remote writes.
"""
from __future__ import annotations

from contextlib import contextmanager
from hashlib import sha1, sha256
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request
import json
import re
import sqlite3

from .r2_worker_http import WFWorkerAPIError, WFWorkerR2Client

LIBRARY = "laocanyouji-25124"
ROOT = "writerforge/v1/libraries/" + LIBRARY + "/"
R2_FORMAT = "writerforge.r2.xuehai.v1"
SHA = re.compile(r"[0-9a-f]{64}\Z")
MAX_JSON = 128 * 1024
MAX_DB = 256 * 1024 * 1024
MAX_SOURCE = 8 * 1024 * 1024
CHUNK = 4 * 1024 * 1024
MAX_REQUESTS_PER_BLOB = 64  # 256 MiB/4 MiB, plus a separate HEAD
MAX_RESULTS = 8


class WFReadOnlyLibraryError(WFWorkerAPIError):
    pass


def require(condition, code):
    if not condition:
        raise WFReadOnlyLibraryError(code)


def key_kind(key):
    if not isinstance(key, str) or not key.startswith(ROOT):
        return None
    tail = key[len(ROOT):]
    if tail == "latest.json" or re.fullmatch(r"snapshots/[0-9a-f]{64}\.json", tail):
        return "metadata"
    if re.fullmatch(r"blobs/[0-9a-f]{64}", tail):
        return "blob"
    return None


def _integer(value, lower=0, upper=MAX_DB):
    if not isinstance(value, str) or not re.fullmatch(r"(0|[1-9][0-9]{0,11})", value):
        raise WFReadOnlyLibraryError("WF_LIBRARY_HEADER_INVALID")
    number = int(value)
    require(lower <= number <= upper, "WF_LIBRARY_SIZE_OVER_LIMIT")
    return number


class WFWorkerLibraryClient(WFWorkerR2Client):
    """Uses V66's existing token, fixed HTTPS endpoint and no-redirect opener."""

    def _call(self, key, method="GET", *, offset=None, length=None, cap=MAX_JSON):
        kind = key_kind(key)
        require(kind is not None, "WF_LIBRARY_KEY_OUT_OF_SCOPE")
        require(method in ("GET", "HEAD"), "WF_LIBRARY_METHOD_FORBIDDEN")
        require((offset is None) == (length is None), "WF_LIBRARY_RANGE_INCOMPLETE")
        if offset is not None:
            require(kind == "blob" and type(offset) is int and type(length) is int and
                    0 <= offset < MAX_DB and 1 <= length <= CHUNK and
                    offset + length <= MAX_DB, "WF_LIBRARY_RANGE_UNSAFE")
        query = {"key": key}
        if offset is not None:
            query.update(offset=offset, length=length)
        url = self.endpoint + "/r2/object?" + urlencode(query)
        req = Request(url, method=method,
                      headers={"Authorization": "Bearer " + self.token,
                               "Accept": "application/octet-stream",
                               "User-Agent": "WriterForge-ReadOnly-Library/1.0"})
        try:
            with self._opener.open(req, timeout=self.timeout) as reply:
                status = reply.status
                expected = 200 if method == "HEAD" or offset is None else 206
                require(status == expected, "WF_LIBRARY_HTTP_STATUS_INVALID")
                total = _integer(reply.headers.get("X-WF-Object-Size"), 1)
                etag = reply.headers.get("ETag")
                require(isinstance(etag, str) and len(etag) >= 2,
                        "WF_LIBRARY_OBJECT_ETAG_MISSING")
                if method == "HEAD":
                    require(_integer(reply.headers.get("Content-Length"), 1) == total,
                            "WF_LIBRARY_HEAD_LENGTH_MISMATCH")
                    return total, etag, b""
                length_header = _integer(reply.headers.get("Content-Length"), 1, CHUNK)
                if offset is not None:
                    expected_range = f"bytes {offset}-{offset+length-1}/{total}"
                    require(reply.headers.get("Content-Range") == expected_range and
                            length_header == length, "WF_LIBRARY_RANGE_RESPONSE_BAD")
                else:
                    require(kind == "metadata" and total <= cap and
                            length_header == total, "WF_LIBRARY_METADATA_BOUND_FAILED")
                require(length_header <= cap, "WF_LIBRARY_RESPONSE_OVER_LIMIT")
                raw = reply.read(cap + 1)
                require(len(raw) == length_header, "WF_LIBRARY_TRUNCATED_RESPONSE")
                return total, etag, raw
        except HTTPError as exc:
            code = {
                401: "WF_LIBRARY_UNAUTHORIZED",
                403: "WF_LIBRARY_OUT_OF_SCOPE",
                404: "WF_LIBRARY_ROUTE_OR_OBJECT_MISSING",
                413: "WF_LIBRARY_REMOTE_OBJECT_TOO_LARGE",
                416: "WF_LIBRARY_REMOTE_RANGE_INVALID",
            }.get(exc.code, "WF_LIBRARY_REMOTE_HTTP_FAILED")
            raise WFReadOnlyLibraryError(code) from None
        except (URLError, OSError, TimeoutError):
            raise WFReadOnlyLibraryError("WF_LIBRARY_NETWORK_FAILED") from None

    def small_json(self, key, cap=MAX_JSON):
        kind = key_kind(key)
        require(kind is not None, "WF_LIBRARY_KEY_OUT_OF_SCOPE")
        require(kind == "metadata", "WF_LIBRARY_NOT_METADATA")
        _size, _etag, data = self._call(key, cap=cap)
        try:
            doc = json.loads(data.decode("utf-8"))
        except (UnicodeError, ValueError):
            raise WFReadOnlyLibraryError("WF_LIBRARY_METADATA_JSON_INVALID") from None
        require(isinstance(doc, dict), "WF_LIBRARY_METADATA_SCHEMA_INVALID")
        return doc, data

    def download_sha_blob(self, key, target, expected_sha, expected_size, max_size):
        require(key_kind(key) == "blob" and isinstance(expected_sha, str) and
                SHA.fullmatch(expected_sha), "WF_LIBRARY_DIGEST_INVALID")
        require(type(expected_size) is int and 1 <= expected_size <= max_size <= MAX_DB,
                "WF_LIBRARY_BLOB_SIZE_FORBIDDEN")
        total, etag, _ = self._call(key, method="HEAD")
        require(total == expected_size, "WF_LIBRARY_BLOB_SIZE_MISMATCH")
        digest = sha256()
        done = 0
        calls = 0
        target = Path(target)
        try:
            with target.open("xb") as dest:
                while done < total:
                    calls += 1
                    require(calls <= MAX_REQUESTS_PER_BLOB,
                            "WF_LIBRARY_NETWORK_BUDGET_EXCEEDED")
                    n = min(CHUNK, total - done)
                    size2, etag2, chunk = self._call(
                        key, offset=done, length=n, cap=CHUNK)
                    require(size2 == total and etag2 == etag,
                            "WF_LIBRARY_REMOTE_OBJECT_CHANGED_DURING_READ")
                    dest.write(chunk)
                    digest.update(chunk)
                    done += len(chunk)
            require(done == expected_size and digest.hexdigest() == expected_sha,
                    "WF_LIBRARY_CONTENT_SHA256_MISMATCH")
            return {"verified_bytes": done, "chunk_requests": calls}
        except BaseException:
            target.unlink(missing_ok=True)
            raise


class VerifiedStudy:
    """Read-only source locator; a hit is NOT a literary semantic judgment."""
    def __init__(self, conn, library, snapshot, work_id, counts, bytes_read):
        self.conn = conn
        self.library = library
        self.snapshot = snapshot
        self.work_id = work_id
        self.counts = counts
        self.bytes_read = bytes_read

    def locate(self, terms: tuple[str, ...], limit=6):
        require(isinstance(terms, tuple) and 1 <= len(terms) <= 4 and
                type(limit) is int and 1 <= limit <= MAX_RESULTS,
                "WF_LIBRARY_LOOKUP_BUDGET_INVALID")
        result = []
        seen = set()
        for term in terms:
            require(isinstance(term, str) and 2 <= len(term) <= 32 and
                    term == term.strip() and
                    all(ord(c) >= 32 for c in term), "WF_LIBRARY_TERM_INVALID")
            rows = self.conn.execute(
                "SELECT work_id,chapter,paragraph,sentence,excerpt,source_sha256 "
                "FROM source_spans WHERE work_id=? AND instr(excerpt,?)>0 "
                "ORDER BY chapter,paragraph,sentence LIMIT ?",
                (self.work_id, term, limit))
            for r in rows:
                where = (r["chapter"], r["paragraph"], r["sentence"])
                if where in seen:
                    continue
                seen.add(where)
                require(SHA.fullmatch(str(r["source_sha256"])),
                        "WF_LIBRARY_SPAN_SHA_INVALID")
                result.append({
                    "chapter": r["chapter"], "paragraph": r["paragraph"],
                    "sentence": r["sentence"], "excerpt": r["excerpt"][:100],
                    "source_unit_sha256": r["source_sha256"],
                    "evidence_type": "VERIFIED_SOURCE_LEXICAL_MATCH_NOT_SEMANTIC_PROOF",
                })
                if len(result) >= limit:
                    return result
        return result


@contextmanager
def open_verified_study(client: WFWorkerLibraryClient, library=LIBRARY):
    """Restores only ONE verified study database and source to Railway temp disk.

    No DB bytes or source excerpts leave this function except explicitly bounded
    read-only locate() results chosen by WF's own search call.
    """
    require(isinstance(client, WFWorkerLibraryClient) and library == LIBRARY,
            "WF_LIBRARY_UNAPPROVED_LIBRARY")
    pointer, _ = client.small_json(ROOT + "latest.json", cap=4096)
    snap = pointer.get("snapshot")
    require(pointer.get("format") == R2_FORMAT and pointer.get("library") == library
            and isinstance(snap, str) and SHA.fullmatch(snap) and
            pointer.get("manifest_sha256") == snap,
            "WF_LIBRARY_LATEST_POINTER_INVALID")
    manifest, manifest_raw = client.small_json(ROOT + "snapshots/" + snap + ".json")
    require(sha256(manifest_raw).hexdigest() == snap, "WF_LIBRARY_MANIFEST_SHA_INVALID")
    files = manifest.get("files")
    require(manifest.get("format") == R2_FORMAT and
            manifest.get("library") == library and
            isinstance(files, dict) and
            "study.sqlite3" in files and "source.txt" in files and
            len(files) <= 14, "WF_LIBRARY_MANIFEST_SCHEMA_INVALID")
    entries = {}
    for name, limit in (("study.sqlite3", MAX_DB), ("source.txt", MAX_SOURCE)):
        info = files[name]
        require(isinstance(info, dict), "WF_LIBRARY_FILE_ENTRY_INVALID")
        sha, size = info.get("sha256"), info.get("size")
        require(isinstance(sha, str) and SHA.fullmatch(sha) and
                type(size) is int and 1 <= size <= limit,
                "WF_LIBRARY_FILE_METADATA_INVALID")
        entries[name] = (sha, size)
    with TemporaryDirectory(prefix="wf-readonly-library-") as tmp:
        root = Path(tmp)
        fetched = []
        for name, (digest, size) in entries.items():
            fetched.append(client.download_sha_blob(
                ROOT + "blobs/" + digest, root / name, digest, size,
                MAX_SOURCE if name == "source.txt" else MAX_DB))
        # Independently prove catalogued edition, not merely R2 byte integrity.
        from .classics_catalog import get_book
        book = get_book("laocanyouji")
        source = (root / "source.txt").read_bytes()  # <=8MiB bound
        git = sha1(f"blob {len(source)}\0".encode("ascii") + source).hexdigest()
        require(git == book.git_blob_sha1, "WF_LIBRARY_CATALOG_EDITION_MISMATCH")
        decoded = sha256(source.decode("utf-8-sig").encode("utf-8")).hexdigest()
        dbpath = root / "study.sqlite3"
        conn = sqlite3.connect("file:" + quote(str(dbpath), safe="/") + "?mode=ro",
                               uri=True, cached_statements=32)
        conn.row_factory = sqlite3.Row
        try:
            conn.execute("PRAGMA query_only=ON")
            require(conn.execute("PRAGMA quick_check").fetchone()[0] == "ok",
                    "WF_LIBRARY_SQLITE_CORRUPTED")
            studied = conn.execute(
                "SELECT work_id,source_sha256,chapter_count FROM studied_works").fetchall()
            require(len(studied) == 1 and studied[0]["work_id"] == book.work_id and
                    studied[0]["source_sha256"] == decoded and
                    studied[0]["chapter_count"] == book.expected_chapters,
                    "WF_LIBRARY_STUDY_AND_ORIGINAL_DISAGREE")
            published = conn.execute(
                "SELECT COUNT(*) FROM studied_chapters c JOIN snapshots s "
                "ON c.snapshot_id=s.id WHERE s.status='published'").fetchone()[0]
            counts = {
                "studied_chapters": conn.execute(
                    "SELECT COUNT(*) FROM studied_chapters").fetchone()[0],
                "studied_units": conn.execute(
                    "SELECT COUNT(*) FROM source_spans").fetchone()[0],
                "retrieval_entries": conn.execute(
                    "SELECT COUNT(*) FROM xuehai_entries").fetchone()[0],
            }
            require(published >= 1 and counts == manifest.get("stats"),
                    "WF_LIBRARY_STUDY_STATS_MISMATCH")
            yield VerifiedStudy(conn, library, snap, book.work_id, counts,
                                sum(i["verified_bytes"] for i in fetched))
        finally:
            conn.close()
