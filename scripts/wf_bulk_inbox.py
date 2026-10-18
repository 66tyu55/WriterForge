#!/usr/bin/env python3
"""V68 offline inbox catalog utility: only metadata. No R2 credentials.

Examples:
  python scripts/wf_bulk_inbox.py preview-local --root D:\Novels --batch 20261018
  rclone lsjson wf-r2:writerforge-private-library/writerforge/v1/inbox/20261018 --recursive > r2-list.json
  python scripts/wf_bulk_inbox.py import-rclone-list --listing r2-list.json --batch 20261018 --db catalog.sqlite3
  python scripts/wf_bulk_inbox.py stats --db catalog.sqlite3

Don't provide filenames, private source snippets or access keys to GPT.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from collections import Counter
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/"writerforge"/"bulk_inbox.py"
spec=importlib.util.spec_from_file_location("wf_bulk_inbox_standalone",SOURCE)
mod=importlib.util.module_from_spec(spec)
sys.modules[spec.name]=mod
spec.loader.exec_module(mod)

def main(argv=None):
    arg=argparse.ArgumentParser(prog="wf_bulk_inbox")
    sub=arg.add_subparsers(dest="action",required=True)
    local=sub.add_parser("preview-local",help="metadata-only count of existing category folders")
    local.add_argument("--root",required=True)
    local.add_argument("--batch",required=True)
    scan=sub.add_parser("import-rclone-list",help="ingest R2 lsjson metadata, no R2 access")
    scan.add_argument("--listing",required=True)
    scan.add_argument("--batch",required=True)
    scan.add_argument("--db",required=True)
    st=sub.add_parser("stats",help="summarize local derived catalogue")
    st.add_argument("--db",required=True)
    a=arg.parse_args(argv)
    if a.action=="preview-local":
        items=mod.local_inventory(a.root,a.batch)
        status=Counter(i["status"] for i in items)
        categories=Counter(i["category"] for i in items)
        result={"format":"wf.inbox.local-preview.v68",
                "objects":len(items),"categories":dict(sorted(categories.items())),
                "statuses":dict(sorted(status.items())),
                "upload_performed":False,"original_files_renamed":False,
                "model_calls":0,"sql_created":False}
    else:
        catalog=mod.BulkCatalog(a.db)
        try:
            if a.action=="import-rclone-list":
                data=Path(a.listing).read_bytes()
                if len(data)>32*1024*1024:
                    raise mod.BulkCorpusError("BULK_LISTING_METADATA_TOO_LARGE")
                records=json.loads(data.decode("utf-8-sig"))
                if not isinstance(records,list) or len(records)>100000:
                    raise mod.BulkCorpusError("BULK_LISTING_SCHEMA_INVALID")
                prepared=[]
                for entry in records:
                    if not isinstance(entry,dict):
                        raise mod.BulkCorpusError("BULK_LISTING_OBJECT_BAD")
                    if entry.get("IsDir") is True:
                        continue
                    if "key" in entry:
                        prepared.append({"key":entry["key"],
                            "size":entry["size"],"etag":entry.get("etag")})
                    else:
                        path=entry.get("Path")
                        if not isinstance(path,str):
                            raise mod.BulkCorpusError("BULK_RCLONE_PATH_MISSING")
                        prepared.append({"key":mod.INBOX+a.batch+"/"+path,
                            "size":entry.get("Size"),"etag":None})
                changed=catalog.register(prepared)
                result={"format":"wf.inbox.import-report.v68",
                        "changed":changed,"summary":catalog.summary(),
                        "source_files_read":False,"r2_requests":0}
            else:
                result={"format":"wf.inbox.catalog-stats.v68",
                        "summary":catalog.summary()}
        finally:
            catalog.close()
    print(json.dumps(result,ensure_ascii=False,sort_keys=True))
    return 0

if __name__=="__main__":
    try:
        raise SystemExit(main())
    except (mod.BulkCorpusError,ValueError,OSError) as exc:
        # Do not print original object keys, raw text or credential-bearing URLs.
        code=str(exc)
        if not code.startswith("BULK_"):
            code="BULK_IMPORT_FAILED"
        print(json.dumps({"status":"ERROR","code":code}),file=sys.stderr)
        raise SystemExit(1)
