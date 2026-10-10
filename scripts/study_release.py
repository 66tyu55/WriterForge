"""CLI for immutable, verified study assets built by the GitHub Actions runner."""
from __future__ import annotations

from pathlib import Path
import argparse
import json
import sys

from writerforge.study_storage import prepare_release, validate_bundle


def main(argv=None):
    parser=argparse.ArgumentParser(description="Package and verify durable WriterForge study snapshots")
    sub=parser.add_subparsers(dest="command",required=True)
    pack=sub.add_parser("pack")
    pack.add_argument("source_dir")
    pack.add_argument("out_dir")
    verify=sub.add_parser("verify")
    verify.add_argument("bundle")
    verify.add_argument("manifest")
    verify.add_argument("restored_dir")
    args=parser.parse_args(argv)
    if args.command=="pack":
        result=prepare_release(args.source_dir,args.out_dir)
    else:
        result=validate_bundle(args.bundle,args.manifest,args.restored_dir)
    print(json.dumps(result,ensure_ascii=False,sort_keys=True))


if __name__=="__main__":
    main()
