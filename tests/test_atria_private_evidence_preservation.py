"""Offline security tests for the expiring, privately sealed Atria originals.

No GitHub requests, model calls, Railway access, R2 credentials or source files.
Never store sealed original prose in public fixtures.
"""
from __future__ import annotations

import hashlib
import io
import json
import unittest
import zipfile
from unittest.mock import patch

from scripts import preserve_atria_artifacts_r2 as archive


class Response:
    def __init__(self, *, meta=None, blob=b"", code=200):
        self.meta=meta
        self.blob=blob
        self.status_code=code
        self.closed=False

    def raise_for_status(self):
        if self.status_code!=200:
            raise RuntimeError("HTTP failure")

    def json(self):
        return self.meta

    def iter_content(self, size):
        for pos in range(0,len(self.blob),size):
            yield self.blob[pos:pos+size]

    def close(self):
        self.closed=True


class Session:
    def __init__(self, meta, data):
        self.responses=[Response(meta=meta),Response(blob=data)]
        self.urls=[]

    def get(self,url,*,headers=None,timeout=None,stream=False):
        assert url.startswith(
            "https://api.github.com/repos/66tyu55/WriterForge/actions/artifacts/")
        assert headers["Authorization"]=="Bearer synthetic"
        assert timeout
        self.urls.append(url)
        return self.responses.pop(0)


class MemoryObject:
    def __init__(self,blob):
        self.blob=blob
        self.pos=0

    def read(self,count=-1):
        if count<0:
            count=len(self.blob)-self.pos
        part=self.blob[self.pos:self.pos+count]
        self.pos+=len(part)
        return part

    def close(self):
        return None


class FakeS3:
    def __init__(self):
        self.objects={}
        self.writes=0
        self.corrupt=False

    def get_object(self,*,Bucket,Key):
        if Key not in self.objects:
            from botocore.exceptions import ClientError
            raise ClientError({"Error":{"Code":"NoSuchKey"}},
                              "GetObject")
        blob=self.objects[Key]
        if self.corrupt:
            blob+=b"tampered"
        return {"Body":MemoryObject(blob)}

    def put_object(self,*,Bucket,Key,Body,ContentType,IfNoneMatch):
        assert Bucket=="writerforge-private-library"
        assert IfNoneMatch=="*"
        assert ContentType in ("application/zip","application/json")
        if Key in self.objects:
            from botocore.exceptions import ClientError
            raise ClientError({"Error":{"Code":"PreconditionFailed"}},
                              "PutObject")
        self.objects[Key]=Body
        self.writes+=1


def synthetic_zip(contents=b"only-fictional-data"):
    output=io.BytesIO()
    with zipfile.ZipFile(output,"w",zipfile.ZIP_DEFLATED) as writer:
        writer.writestr("synthetic.txt",contents)
    return output.getvalue()


class AtriaEvidencePreservation(unittest.TestCase):
    def test_inventory_fixed_and_contains_all_original_categories(self):
        self.assertEqual(len(archive.INVENTORY),9)
        self.assertEqual({x["run_id"] for x in archive.INVENTORY},
                         {39937669584,39939718654})
        self.assertEqual(len({x["artifact_id"] for x in archive.INVENTORY}),9)
        for label in ("plot","climax","fight","scheme","horror",
                      "humor","psychology"):
            self.assertTrue(any(label in x["name"].lower()
                                for x in archive.INVENTORY))
        self.assertEqual(archive.PREFIX,
                         "writerforge/v1/private-evidence/atria-seven-genres-20261023")

    def test_github_metadata_and_zip_checksum_both_required(self):
        data=synthetic_zip()
        row=dict(archive.INVENTORY[0])
        row["zip_digest"]="sha256:"+archive.digest(data)
        meta={"id":row["artifact_id"],"name":row["name"],
              "digest":row["zip_digest"],"expired":False,
              "workflow_run":{"id":row["run_id"]},
              "size_in_bytes":len(data)}
        self.assertEqual(
            archive.artifact_bytes(row,"synthetic",
                                   session=Session(meta,data)),data)
        forged=dict(meta,digest="sha256:"+"f"*64)
        with self.assertRaisesRegex(RuntimeError,"IDENTITY"):
            archive.artifact_bytes(row,"synthetic",
                                   session=Session(forged,data))
        malformed=dict(meta,workflow_run={"id":42})
        with self.assertRaisesRegex(RuntimeError,"IDENTITY"):
            archive.artifact_bytes(row,"synthetic",
                                   session=Session(malformed,data))
        with self.assertRaisesRegex(RuntimeError,"ZIP_SHA256_MISMATCH"):
            archive.artifact_bytes(
                row,"synthetic",session=Session(meta,data+b"bad"))
        badzip=b"not actually a ZIP file"
        changed=dict(row,zip_digest="sha256:"+archive.digest(badzip))
        changedmeta=dict(meta,digest=changed["zip_digest"])
        with self.assertRaisesRegex(RuntimeError,"ZIP_FORMAT_INVALID"):
            archive.artifact_bytes(
                changed,"synthetic",session=Session(changedmeta,badzip))

    def test_bounded_http_transfer_refuses_oversize_and_closes_response(self):
        source=synthetic_zip()
        row=dict(archive.INVENTORY[0],
                 zip_digest="sha256:"+archive.digest(source))
        meta={"id":row["artifact_id"],"name":row["name"],
              "digest":row["zip_digest"],"expired":False,
              "workflow_run":{"id":row["run_id"]},
              "size_in_bytes":len(source)}
        fake=Session(meta,source+b"0"*(archive.MAX_DOWNLOAD+1))
        with self.assertRaisesRegex(RuntimeError,"ZIP_EXCEEDS_LIMIT"):
            archive.artifact_bytes(row,"synthetic",session=fake)
        # The received body must be closed even when size limit fails.
        self.assertTrue(fake.urls)
        too_big=dict(meta,size_in_bytes=archive.MAX_DOWNLOAD+1)
        with self.assertRaisesRegex(RuntimeError,"IDENTITY"):
            archive.artifact_bytes(row,"synthetic",
                                   session=Session(too_big,source))

    def test_immutable_conditional_upload_and_fresh_remote_get(self):
        client=FakeS3()
        raw=synthetic_zip()
        bucket="writerforge-private-library"
        k=archive.PREFIX+"/artifacts/test-"+archive.digest(raw)+".zip"
        a=archive.preserve_immutable(
            client,bucket,k,raw,content_type="application/zip")
        self.assertEqual(a,archive.digest(raw))
        self.assertEqual(client.writes,1)
        again=archive.preserve_immutable(
            client,bucket,k,raw,content_type="application/zip")
        self.assertEqual(a,again)
        self.assertEqual(client.writes,1)
        with self.assertRaisesRegex(RuntimeError,"COLLIDES"):
            archive.preserve_immutable(
                client,bucket,k,b"different",content_type="application/zip")
        client.corrupt=True
        with self.assertRaisesRegex(RuntimeError,"COLLIDES"):
            archive.preserve_immutable(
                client,bucket,k,raw,content_type="application/zip")

    def test_lost_write_and_after_get_mismatch_cannot_claim_saved(self):
        client=FakeS3()
        source=synthetic_zip()
        key="wf-new-test"
        client.corrupt=True
        with self.assertRaisesRegex(RuntimeError,"FRESH_GET_MISMATCH"):
            archive.preserve_immutable(
                client,"writerforge-private-library",key,
                source,content_type="application/zip")
        # Failed verification must not be recorded as verified.
        self.assertIn(key,client.objects)
        self.assertNotEqual(client.objects[key]+b"tampered",source)


if __name__=="__main__":
    unittest.main()
