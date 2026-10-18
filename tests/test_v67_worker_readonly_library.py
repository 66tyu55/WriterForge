"""Offline fail-closed tests for V67 Worker->temporary SQLite bridge.

Fake HTTP is NOT reported as a real Cloudflare test; these only establish
protocol contracts, bounded transfers, SHA failure detection and no writes.
"""
from __future__ import annotations

from hashlib import sha1, sha256
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlsplit
import json
import sqlite3
import unittest

from writerforge.worker_readonly_library import (
    ROOT, LIBRARY, R2_FORMAT, WFWorkerLibraryClient,
    WFReadOnlyLibraryError, open_verified_study,
)


class FakeReply:
    def __init__(self, status, headers, data=b""):
        self.status = status
        self.headers = headers
        self.body = BytesIO(data)

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.body.close()

    def read(self, n):
        return self.body.read(n)


class FakeWorker:
    def __init__(self, objects):
        self.objects = dict(objects)
        self.methods = []
        self.corrupt_range = False
        self.missing_route = False

    def open(self, request, timeout=None):
        parsed = urlsplit(request.full_url)
        query = parse_qs(parsed.query)
        method = request.get_method()
        self.methods.append(method)
        if self.missing_route:
            raise HTTPError(request.full_url, 404, "no", {}, BytesIO(b""))
        assert parsed.scheme == "https" and parsed.path == "/r2/object"
        assert (request.get_header("Authorization") or "").startswith("Bearer ")
        key = query["key"][0]
        if key not in self.objects:
            raise HTTPError(request.full_url, 404, "missing", {}, BytesIO(b""))
        raw = self.objects[key]
        h = {
            "ETag": '"test-content"',
            "X-WF-Object-Size": str(len(raw)),
            "Content-Length": str(len(raw)),
        }
        if method == "HEAD":
            return FakeReply(200, h)
        if "offset" in query:
            start = int(query["offset"][0])
            size = int(query["length"][0])
            h["Content-Range"] = f"bytes {start}-{start+size-1}/{len(raw)}"
            h["Content-Length"] = str(size)
            body = raw[start:start+size]
            if self.corrupt_range and start == 0:
                body = bytes([body[0] ^ 1]) + body[1:]
            return FakeReply(206, h, body)
        return FakeReply(200, h, raw)


def study_database(output):
    c = sqlite3.connect(output)
    try:
        c.executescript("""
            CREATE TABLE snapshots(id INTEGER PRIMARY KEY, status TEXT);
            CREATE TABLE studied_works(work_id TEXT, source_sha256 TEXT,
                                      chapter_count INTEGER);
            CREATE TABLE studied_chapters(chapter INTEGER, snapshot_id INTEGER);
            CREATE TABLE source_spans(work_id TEXT, chapter INTEGER,
               paragraph INTEGER, sentence INTEGER, excerpt TEXT,
               source_sha256 TEXT);
            CREATE TABLE xuehai_entries(id INTEGER);
        """)
        c.execute("INSERT INTO snapshots VALUES(1,'published')")
        c.execute("INSERT INTO studied_chapters VALUES(1,1)")
        c.execute("INSERT INTO source_spans VALUES(?,?,?,?,?,?)",
                  ("sample-work", 1, 3, 2, "此处有聲音，但不能据此证明紧张",
                   sha256("此处有聲音，但不能据此证明紧张".encode()).hexdigest()))
        c.commit()
    finally:
        c.close()


class ReadOnlyBridgeTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        root = Path(self.temp.name)
        db = root / "study.sqlite3"
        study_database(db)
        self.source = b"single pinned synthetic source\n"
        self.git_sha = sha1(
            f"blob {len(self.source)}\0".encode() + self.source).hexdigest()
        self.original_sha = sha256(self.source).hexdigest()
        with sqlite3.connect(db) as c:
            c.execute("INSERT INTO studied_works VALUES(?,?,?)",
                      ("sample-work", self.original_sha, 1))
            c.commit()
        db_raw = db.read_bytes()
        db_hash = sha256(db_raw).hexdigest()
        source_hash = sha256(self.source).hexdigest()
        manifest = {
            "format": R2_FORMAT, "library": LIBRARY,
            "stats": {"studied_chapters": 1, "studied_units": 1,
                      "retrieval_entries": 0},
            "files": {
                "study.sqlite3": {"sha256": db_hash, "size": len(db_raw)},
                "source.txt": {"sha256": source_hash,
                               "size": len(self.source)},
            },
        }
        encoded = json.dumps(manifest, ensure_ascii=False, sort_keys=True,
                             separators=(",", ":")).encode()
        snapshot = sha256(encoded).hexdigest()
        pointer = json.dumps({
            "format": R2_FORMAT, "library": LIBRARY,
            "snapshot": snapshot, "manifest_sha256": snapshot,
        }).encode()
        self.snapshot = snapshot
        self.objects = {
            ROOT + "latest.json": pointer,
            ROOT + "snapshots/" + snapshot + ".json": encoded,
            ROOT + "blobs/" + db_hash: db_raw,
            ROOT + "blobs/" + source_hash: self.source,
        }
        self.worker = FakeWorker(self.objects)
        self.client = WFWorkerLibraryClient(
            endpoint="https://wf-r2-api.3227482831.workers.dev",
            token="synthetic-test-token-longer-than-24")
        self.client._opener = self.worker
        self.catalog = SimpleNamespace(
            work_id="sample-work", git_blob_sha1=self.git_sha,
            expected_chapters=1,
        )
        self.patcher = patch("writerforge.classics_catalog.get_book",
                             return_value=self.catalog)
        self.patcher.start()

    def tearDown(self):
        self.patcher.stop()
        self.temp.cleanup()

    def test_full_single_book_verification_and_lexical_locator(self):
        with open_verified_study(self.client) as book:
            self.assertEqual(book.snapshot, self.snapshot)
            self.assertEqual(book.counts["studied_units"], 1)
            self.assertGreater(book.bytes_read, 0)
            hits = book.locate(("聲音",), 4)
            self.assertEqual(len(hits), 1)
            self.assertEqual((hits[0]["chapter"], hits[0]["paragraph"],
                              hits[0]["sentence"]), (1, 3, 2))
            self.assertIn("NOT_SEMANTIC_PROOF", hits[0]["evidence_type"])
            self.assertEqual(book.locate(("无法检索到的词",)), [])
            with self.assertRaises(sqlite3.OperationalError):
                book.conn.execute("CREATE TABLE forbidden(x INTEGER)")
        self.assertTrue(set(self.worker.methods) <= {"HEAD", "GET"})

    def test_db_corruption_refused_and_partial_file_deleted(self):
        self.worker.corrupt_range = True
        with self.assertRaisesRegex(WFReadOnlyLibraryError,
                                     "CONTENT_SHA256_MISMATCH"):
            with open_verified_study(self.client):
                pass

    def test_snapshot_manifest_tamper_refused(self):
        key = ROOT + "snapshots/" + self.snapshot + ".json"
        self.worker.objects[key] += b" "
        with self.assertRaisesRegex(WFReadOnlyLibraryError,
                                     "MANIFEST_SHA_INVALID"):
            with open_verified_study(self.client):
                pass

    def test_wrong_catalog_edition_refused(self):
        self.catalog.git_blob_sha1 = "0" * 40
        with self.assertRaisesRegex(WFReadOnlyLibraryError,
                                     "CATALOG_EDITION_MISMATCH"):
            with open_verified_study(self.client):
                pass

    def test_remote_route_not_installed_is_not_success(self):
        self.worker.missing_route = True
        with self.assertRaisesRegex(WFReadOnlyLibraryError,
                                     "ROUTE_OR_OBJECT_MISSING"):
            with open_verified_study(self.client):
                pass

    def test_scope_and_bounded_search(self):
        with self.assertRaisesRegex(WFReadOnlyLibraryError, "KEY_OUT_OF_SCOPE"):
            self.client.small_json(
                "writerforge/v1/libraries/another-book/latest.json")
        with open_verified_study(self.client) as book:
            for bad in [(), ("a",), ("%\n",), tuple(["word"] * 5)]:
                with self.subTest(bad=bad), self.assertRaises(WFReadOnlyLibraryError):
                    book.locate(bad)
        self.assertNotIn("PUT", self.worker.methods)
        self.assertNotIn("DELETE", self.worker.methods)


if __name__ == "__main__":
    unittest.main()
