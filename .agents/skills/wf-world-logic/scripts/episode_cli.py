"""Private CLI: no source passages printed in index/check, no overwrites."""
from __future__ import annotations
import argparse
from hashlib import sha256
import json
from pathlib import Path
from worldlogic import FORMAT, initial_world, line_units, try_proposal, validate_source


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(path, data):
    target = Path(path)
    if target.exists():
        raise SystemExit("REFUSE_OVERWRITE_PRIVATE_LEDGER")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def main(argv=None):
    p = argparse.ArgumentParser(description="Private source world-logic study; SHADOW only")
    sub = p.add_subparsers(dest="command", required=True)
    init = sub.add_parser("index", help="Create PENDING, byte-exhaustive source units, not semantics")
    init.add_argument("--source", required=True)
    init.add_argument("--encoding", choices=("gb18030", "utf-8", "utf-8-sig"), required=True)
    init.add_argument("--start", type=int, required=True, help="Inclusive BYTE offset")
    init.add_argument("--end", type=int, required=True, help="Exclusive BYTE offset")
    init.add_argument("--out", required=True)
    chk = sub.add_parser("check", help="Verify source anchors and ledger references")
    chk.add_argument("--source", required=True)
    chk.add_argument("--episode", required=True)
    sim = sub.add_parser("propose", help="One atomic counterfactual; never predict downstream")
    sim.add_argument("--source", required=True)
    sim.add_argument("--episode", required=True)
    sim.add_argument("--proposal", required=True)
    args = p.parse_args(argv)
    raw = Path(args.source).read_bytes()
    if args.command == "index":
        data = {"format": FORMAT,
                "source": {"sha256": sha256(raw).hexdigest(), "encoding": args.encoding,
                           "scope": [args.start, args.end]},
                "units": line_units(raw, args.start, args.end),
                "anchors": [], "places": [], "actors": [], "routes": [],
                "rules": [], "facts": [], "events": []}
        validate_source(data, raw)
        write_json(args.out, data)
        print(json.dumps({"status": "PENDING_ALL_UNITS", "units": len(data["units"]),
                          "literary_one_to_one_verified": False}))
        return
    episode = read_json(args.episode)
    report = validate_source(episode, raw)
    if args.command == "check":
        print(json.dumps(report, ensure_ascii=False))
    else:
        result = try_proposal(initial_world(episode), read_json(args.proposal))
        print(json.dumps({"accepted": result["accepted"],
                          "reason": result.get("reason"), "future": result["future"],
                          "state": result["state"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
