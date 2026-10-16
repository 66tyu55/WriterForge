"""Synthetic 15 MB fixture: no private novel text and no real Drive/R2 keys."""
from __future__ import annotations
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import json
import os
import unittest

from writerforge.r2_storage import R2Config, R2StorageError, _digest
from writerforge.single_work_runner import SingleWorkVault
from scripts.drive_fanren_to_private_r2 import (
    DriveR2InputError, EXACT_EXPECTED_BYTES, _source_reader,
    store_private_original, main,
)


class Missing(Exception):
    response={"Error":{"Code":"404"}}


class MemoryS3:
    def __init__(self):
        self.data={}
        self.uploads=0
    def head_object(self,*,Bucket,Key):
        value=self.data.get((Bucket,Key))
        if value is None:
            raise Missing()
        contents, metadata=value
        return {"ContentLength":len(contents),"Metadata":metadata}
    def upload_file(self,path,bucket,key,ExtraArgs=None,Config=None):
        self.uploads+=1
        self.data[(bucket,key)]=(Path(path).read_bytes(),
                               (ExtraArgs or {}).get("Metadata",{}))
    def put_object(self,*,Bucket,Key,Body,ContentType=None,Metadata=None):
        self.data[(Bucket,Key)]=(bytes(Body),dict(Metadata or {}))
    def get_object(self,*,Bucket,Key):
        return {"Body":BytesIO(self.data[(Bucket,Key)][0])}
    def download_file(self,bucket,key,path):
        Path(path).write_bytes(self.data[(bucket,key)][0])
    def list_objects_v2(self,*,Bucket,Prefix,MaxKeys):
        matches=[
            {"Key":key,"Size":len(data)}
            for (bucket,key),(data,meta) in sorted(self.data.items())
            if bucket==Bucket and key.startswith(Prefix)
        ]
        return {"Contents":matches[:MaxKeys],"IsTruncated":len(matches)>MaxKeys}


class FakeResponse:
    def __init__(self,status,*,json_data=None,body=None):
        self.status_code=status
        self.data=json_data
        self.body=body
    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError("HTTP error")
    def json(self):
        return self.data
    def iter_content(self,chunk_size):
        for at in range(0,len(self.body or b""),chunk_size):
            yield self.body[at:at+chunk_size]
    def close(self):pass


class DriveSession:
    def __init__(self,body,*,metadata_status=200,media_status=200):
        self.body=body
        self.metadata_status=metadata_status
        self.media_status=media_status
    def get(self,url,*,params=None,**kwargs):
        if params.get("alt")=="media":
            return FakeResponse(self.media_status,body=self.body)
        return FakeResponse(
            self.metadata_status,
            json_data={"id":"drive-id","name":"《凡人修仙传》（校对版全本+番外）.txt",
                       "mimeType":"text/plain","size":str(len(self.body)),
                       "trashed":False},
        )


class DriveR2TransferTests(unittest.TestCase):
    def setUp(self):
        self.temp=TemporaryDirectory()
        self.folder=Path(self.temp.name)
        self.text=b"G"*EXACT_EXPECTED_BYTES
        self.vault=SingleWorkVault(
            R2Config(account_id="a"*32,bucket="writerforge-private-library",
                     access_key_id="test",secret_access_key="test"),
            work_id="fanrenxiuxian",client=MemoryS3(),
        )
        self.file_id="a" * 33

    def tearDown(self):
        self.temp.cleanup()

    def test_authenticated_download_and_new_r2_upload_fresh_download(self):
        target=self.folder/"source.txt"
        sha,size,drive_sha=_source_reader(DriveSession(self.text),self.file_id,target)
        self.assertEqual(size,EXACT_EXPECTED_BYTES)
        self.assertEqual(_digest(target),(sha,size))
        first=store_private_original(self.vault,target,drive_id_digest=drive_sha)
        self.assertTrue(first["new_private_archive"])
        self.assertTrue(first["uploaded_new_blob"])
        self.assertTrue(first["fresh_download_sha256_verified"])
        self.assertEqual(first["source_origin"],"private_google_drive_service_account")
        self.assertEqual(self.vault.client.uploads,1)
        self.assertEqual(len(self.vault.client.data),3)
        second=store_private_original(self.vault,target,drive_id_digest=drive_sha)
        self.assertTrue(second["already_archived"])
        self.assertFalse(second["uploaded_new_blob"])
        self.assertEqual(self.vault.client.uploads,1)

    def test_denied_drive_metadata_is_specific_failure(self):
        with self.assertRaisesRegex(DriveR2InputError,"AUTH_OR_SHARE_DENIED"):
            _source_reader(DriveSession(self.text,metadata_status=403),
                           self.file_id,self.folder/"not-written.txt")

    def test_missing_drive_reader_share_is_specific_failure(self):
        with self.assertRaisesRegex(DriveR2InputError,"FILE_NOT_VISIBLE_TO_SERVICE_ACCOUNT"):
            _source_reader(DriveSession(self.text,metadata_status=404),
                           self.file_id,self.folder/"not-written.txt")

    def test_metadata_size_change_cannot_archive_different_edition(self):
        with self.assertRaisesRegex(DriveR2InputError,"DRIVE_SOURCE_VERSION_CHANGED"):
            _source_reader(DriveSession(b"test"),self.file_id,
                           self.folder/"wrong-original.txt")
        self.assertEqual(self.vault.client.uploads,0)

    def test_corrupted_r2_blob_will_fail_fresh_verify(self):
        path=self.folder/"source.txt"
        path.write_bytes(self.text)
        import hashlib
        sha=hashlib.sha256(self.file_id.encode()).hexdigest()
        store_private_original(self.vault,path,drive_id_digest=sha)
        blobs=[key for (bucket,key) in self.vault.client.data
               if "/blobs/" in key]
        key=blobs[0]
        body,meta=self.vault.client.data[(self.vault.config.bucket,key)]
        self.vault.client.data[(self.vault.config.bucket,key)]=(b"x"+body[1:],meta)
        with self.assertRaisesRegex(R2StorageError,"fresh download SHA256"):
            store_private_original(self.vault,path,drive_id_digest=sha)

    def test_missing_service_account_secrets_fail_before_network_or_upload(self):
        with patch.dict(os.environ,{},clear=True):
            with self.assertRaisesRegex(DriveR2InputError,"GITHUB_ACTIONS_MISSING_GOOGLE_AUTH_INPUT"):
                main()


if __name__=="__main__":
    unittest.main()
