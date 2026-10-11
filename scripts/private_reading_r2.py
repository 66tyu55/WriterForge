"""Explicit private R2 archiving commands; no secrets in CLI arguments."""
from __future__ import annotations
from pathlib import Path
from tempfile import TemporaryDirectory
import argparse
import json
from writerforge.r2_storage import R2Config
from writerforge.private_reading_storage import PrivateReadingVault, audit_private_reading

def main():
    p=argparse.ArgumentParser()
    p.add_argument("action",choices=("audit","backup-verify","inventory"))
    p.add_argument("--db",type=Path)
    p.add_argument("--restore-root",type=Path)
    args=p.parse_args()
    if args.action=="audit":
        if not args.db: p.error("--db required")
        print(json.dumps(audit_private_reading(args.db),ensure_ascii=False))
        return
    vault=PrivateReadingVault(R2Config.from_environment())
    if args.action=="inventory":
        print(json.dumps(vault.inventory(),ensure_ascii=False))
        return
    if not args.db: p.error("--db required")
    source=audit_private_reading(args.db)
    upload=vault.backup(database=args.db)
    inventory=vault.inventory()
    if not all((inventory["has_latest"],inventory["has_snapshot"],inventory["has_blob"])):
        raise RuntimeError("R2 inventory missing required objects")
    if args.restore_root:
        args.restore_root.mkdir(parents=True,exist_ok=True)
        restored=vault.restore(destination=args.restore_root,snapshot=upload["snapshot"])
    else:
        with TemporaryDirectory(prefix="wf-r2-live-verify-") as root:
            restored=vault.restore(destination=root,snapshot=upload["snapshot"])
    if restored["stats"]!=source:
        raise RuntimeError("restored private reading differs from original audit")
    print(json.dumps({"backup":upload,"inventory":inventory,
        "restored":{k:v for k,v in restored.items() if k!="path"}},ensure_ascii=False))

if __name__=="__main__":main()
