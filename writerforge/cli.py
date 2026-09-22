from __future__ import annotations
import argparse, json
from pathlib import Path
from .db import WriterForgeDB
from .runtime import RuntimeEngine

def main():
    p = argparse.ArgumentParser(prog="writerforge")
    p.add_argument("--db", default="writerforge.sqlite")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("init")
    args = p.parse_args()
    db = WriterForgeDB(Path(args.db))
    if args.cmd == "init":
        print(json.dumps({"ok":True,"db":str(args.db)},ensure_ascii=False))
    db.close()

if __name__ == "__main__":
    main()
