"""One-book private R2 smoke test. No Google Drive login or manual ZIP.

The full 13-work archive is ALREADY in the user's R2 root. This action
extracts 星辰变 only and checks upload, ListObjects, independent fresh
download and SHA-256. It does NOT perform literary training.
"""
from __future__ import annotations

import json

from writerforge.private_single_book_transfer import PrivateSingleBookVault
from writerforge.r2_storage import R2Config


def main():
    config=R2Config.from_environment()
    if config.bucket!="writerforge-private-library":
        raise RuntimeError("refusing to write outside the known private R2 bucket")
    result=PrivateSingleBookVault(config).smoke_transfer()
    if not all((
        result["target_bucket_matches_expected"],
        result["source_archive_sha256_verified"],
        result["only_one_book_extracted"],
        result["remote_objects_present"]>=3,
        result["fresh_download_sha256_verified"],
        result["other_12_works_unchanged"],
    )):
        raise RuntimeError("private one-book upload/recovery incomplete")
    # Book TEXT, section content and cloud credentials are never printed.
    print(json.dumps(result,ensure_ascii=False,sort_keys=True))


if __name__=="__main__":
    main()
