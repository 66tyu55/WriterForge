#!/usr/bin/env python3
"""WF reversible world evidence codec (shadow, offline, standard library only).

The byte archive and private observations are lossless. A causal interpretation
is NOT proved by a byte checksum. Never commit a produced bundle or novel text.
"""
from __future__ import annotations

import argparse
from decimal import Decimal, InvalidOperation
from hashlib import sha256
import json
from pathlib import Path
import re
import zlib

FORMAT = "wf.reversible-world.v1"
OBS_FORMAT = "wf.world-observations.v1"
MAX_BYTES = 64 * 1024 * 1024
CHUNK = 65536
IDENT = re.compile(r"^[A-Z][0-9]{3,8}$")
CODE = re.compile(r"^[a-z][a-z0-9_]*(?:[.][a-z0-9_]+)*$")
SHA = re.compile(r"^[a-f0-9]{64}$")
EPISTEMIC = {"narrated", "character_belief", "rumour", "inferred",
             "unknown", "contingent", "unexplained"}


class ReversibleError(ValueError):
    pass


def require(ok, code):
    if not ok:
        raise ReversibleError(code)


def canonical(obj):
    return json.dumps(obj, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def hash_bytes(value):
    return sha256(value).hexdigest()


def decode_source(raw):
    for encoding in ("utf-8-sig", "gb18030"):
        try:
            text = raw.decode(encoding, errors="strict")
            require(text.encode(encoding) == raw, "SOURCE_CODEC_NOT_BYTE_REVERSIBLE")
            return encoding
        except UnicodeError:
            continue
    raise ReversibleError("UNSUPPORTED_SOURCE_ENCODING")


def validate_observations(obs, raw, encoding):
    require(isinstance(obs, dict) and set(obs) ==
            {"format", "source_sha256", "anchors", "facts", "links"},
            "OBS_SCHEMA_INVALID")
    require(obs["format"] == OBS_FORMAT, "OBS_FORMAT_INVALID")
    require(obs["source_sha256"] == hash_bytes(raw), "SOURCE_SHA_MISMATCH")
    anchors, facts, links = obs["anchors"], obs["facts"], obs["links"]
    require(all(isinstance(x, list) for x in (anchors, facts, links)),
            "OBS_LISTS_REQUIRED")
    require(len(anchors) <= 50000 and len(facts) <= 50000 and len(links) <= 100000,
            "OBS_COUNT_CAP")
    all_anchors, all_facts = set(), set()
    for item in anchors:
        require(isinstance(item, dict) and set(item) ==
                {"id", "kind", "start", "end", "surface"},
                "ANCHOR_SCHEMA")
        aid, kind = item["id"], item["kind"]
        require(isinstance(aid, str) and IDENT.fullmatch(aid) and aid not in all_anchors,
                "ANCHOR_ID_INVALID")
        require(isinstance(kind, str) and CODE.fullmatch(kind), "ANCHOR_KIND_INVALID")
        start, end, surface = item["start"], item["end"], item["surface"]
        require(type(start) is int and type(end) is int and
                0 <= start < end <= len(raw), "ANCHOR_BOUNDS")
        require(isinstance(surface, str) and 0 < len(surface) <= 500,
                "ANCHOR_SURFACE_INVALID")
        try:
            matched = raw[start:end].decode(encoding, errors="strict")
        except UnicodeError as exc:
            raise ReversibleError("ANCHOR_CUTS_CHARACTER") from exc
        require(matched == surface, "ANCHOR_NOT_IN_ORIGINAL")
        all_anchors.add(aid)
    for fact in facts:
        require(isinstance(fact, dict) and set(fact) ==
                {"id", "kind", "subject_ids", "evidence_ids", "telling_seq",
                 "story_tick", "time_axis", "epistemic", "parameters"},
                "FACT_SCHEMA")
        fid = fact["id"]
        require(isinstance(fid, str) and IDENT.fullmatch(fid) and fid not in all_facts,
                "FACT_ID_INVALID")
        require(isinstance(fact["kind"], str) and CODE.fullmatch(fact["kind"]),
                "FACT_KIND_INVALID")
        require(isinstance(fact["subject_ids"], list) and
                isinstance(fact["evidence_ids"], list) and
                all(isinstance(a, str) and a in all_anchors
                    for a in fact["subject_ids"] + fact["evidence_ids"]) and
                len(fact["evidence_ids"]) > 0, "FACT_EVIDENCE_MISSING")
        require(type(fact["telling_seq"]) is int and fact["telling_seq"] >= 0,
                "FACT_NARRATIVE_TIME_INVALID")
        tick, axis = fact["story_tick"], fact["time_axis"]
        require(tick is None or type(tick) is int, "FACT_STORY_TIME_INVALID")
        require(axis is None or (isinstance(axis, str) and CODE.fullmatch(axis)),
                "FACT_TIME_AXIS_INVALID")
        require(tick is None or axis is not None, "FACT_TIME_AXIS_REQUIRED")
        require(fact["epistemic"] in EPISTEMIC, "FACT_EPISTEMIC_INVALID")
        params = fact["parameters"]
        require(isinstance(params, dict) and len(params) <= 24, "PARAMETER_SHAPE")
        for k, v in params.items():
            require(isinstance(k, str) and CODE.fullmatch(k), "PARAMETER_NAME")
            require(isinstance(v, str) and len(v) <= 64,
                    "PARAMETER_MUST_BE_EXACT_DECIMAL_TEXT")
            try:
                num = Decimal(v)
            except InvalidOperation as exc:
                raise ReversibleError("PARAMETER_NOT_DECIMAL") from exc
            require(num.is_finite() and format(num, "f") == v,
                    "PARAMETER_NOT_CANONICAL_OR_FINITE")
        all_facts.add(fid)
    for link in links:
        require(isinstance(link, dict) and set(link) ==
                {"source", "target", "kind", "epistemic", "evidence_ids"},
                "LINK_SCHEMA")
        require(link["source"] in all_facts and link["target"] in all_facts,
                "LINK_UNKNOWN_FACT")
        require(isinstance(link["kind"], str) and CODE.fullmatch(link["kind"]),
                "LINK_KIND_INVALID")
        require(link["epistemic"] in EPISTEMIC, "LINK_EPISTEMIC_INVALID")
        require(isinstance(link["evidence_ids"], list) and
                all(isinstance(a, str) and a in all_anchors for a in link["evidence_ids"]),
                "LINK_EVIDENCE_INVALID")
        if link["kind"] == "precedes":
            source = next(f for f in facts if f["id"] == link["source"])
            target = next(f for f in facts if f["id"] == link["target"])
            if (source["time_axis"] is not None and
                source["time_axis"] == target["time_axis"] and
                source["story_tick"] is not None and
                target["story_tick"] is not None):
                require(source["story_tick"] <= target["story_tick"],
                        "EXPLICIT_CHRONOLOGY_CONTRADICTION")
    return True


def projection(obs):
    """No names, dialogue, descriptions, or hashes of short name strings."""
    return {
        "format": FORMAT + ".anonymous",
        "anchors": [{"id": a["id"], "kind": a["kind"],
                     "start": a["start"], "end": a["end"]}
                    for a in obs["anchors"]],
        "facts": obs["facts"],
        "links": obs["links"],
        "source_sha256": obs["source_sha256"],
        "semantic_truth_independently_verified": False,
        "causal_inference_from_params_alone_proven": False,
        "unannotated_events_cannot_be_assumed_absent": True,
    }


def checked_source(path):
    path = Path(path)
    require(path.is_file() and 0 < path.stat().st_size <= MAX_BYTES,
            "SOURCE_SIZE_OR_MISSING")
    raw = path.read_bytes()
    return raw, decode_source(raw)


def chunk_index(raw):
    return [{"start": i, "end": min(i + CHUNK, len(raw)),
             "sha256": hash_bytes(raw[i:i + CHUNK])}
            for i in range(0, len(raw), CHUNK)]


def pack(source_path, observations_path, output_dir):
    raw, encoding = checked_source(source_path)
    obs = json.loads(Path(observations_path).read_text(encoding="utf-8"))
    validate_observations(obs, raw, encoding)
    public = projection(obs)
    private_bytes, public_bytes = canonical(obs), canonical(public)
    packed = zlib.compress(raw, level=9)
    out = Path(output_dir)
    require(not out.exists(), "OUTPUT_EXISTS_NO_OVERWRITE")
    out.mkdir(parents=True)
    (out / "source.zlib").write_bytes(packed)
    (out / "private-ledger.json").write_bytes(private_bytes)
    (out / "anonymous.json").write_bytes(public_bytes)
    manifest = {
        "format": FORMAT, "source_sha256": hash_bytes(raw),
        "source_bytes": len(raw), "encoding": encoding,
        "packed_sha256": hash_bytes(packed),
        "private_ledger_sha256": hash_bytes(private_bytes),
        "anonymous_sha256": hash_bytes(public_bytes),
        "chunks": chunk_index(raw), "source_coverage_bytes": len(raw),
        "semantic_extraction_complete": False,
        "semantic_truth_independently_verified": False,
        "source_verbatim_in_private_archive": True,
    }
    (out / "manifest.json").write_bytes(canonical(manifest))
    return verify(out)


def verify(bundle_dir):
    directory = Path(bundle_dir)
    manifest = json.loads((directory / "manifest.json").read_text("utf-8"))
    require(manifest["format"] == FORMAT, "MANIFEST_FORMAT")
    packed = (directory / "source.zlib").read_bytes()
    require(hash_bytes(packed) == manifest["packed_sha256"], "PACKED_HASH")
    require(manifest["source_bytes"] <= MAX_BYTES, "SOURCE_TOO_LARGE")
    dec = zlib.decompressobj()
    raw = dec.decompress(packed, MAX_BYTES + 1)
    raw += dec.flush()
    require(dec.eof and not dec.unused_data and len(raw) <= MAX_BYTES,
            "SOURCE_DECOMPRESSION_INVALID")
    require(len(raw) == manifest["source_bytes"] and
            hash_bytes(raw) == manifest["source_sha256"], "SOURCE_ROUNDTRIP_MISMATCH")
    require(manifest["encoding"] == decode_source(raw), "ENCODING_MISMATCH")
    require(chunk_index(raw) == manifest["chunks"] and
            manifest["source_coverage_bytes"] == len(raw), "CHUNK_COVERAGE_MISMATCH")
    private_bytes = (directory / "private-ledger.json").read_bytes()
    public_bytes = (directory / "anonymous.json").read_bytes()
    require(hash_bytes(private_bytes) == manifest["private_ledger_sha256"],
            "PRIVATE_LEDGER_HASH")
    require(hash_bytes(public_bytes) == manifest["anonymous_sha256"],
            "ANONYMOUS_HASH")
    obs = json.loads(private_bytes)
    validate_observations(obs, raw, manifest["encoding"])
    require(canonical(projection(obs)) == public_bytes,
            "ANONYMOUS_INVERSE_MISMATCH")
    return {
        "source_byte_roundtrip": "PASS", "anchor_inverse": "PASS",
        "graph_projection_inverse": "PASS",
        "source_bytes": len(raw), "chunks": len(manifest["chunks"]),
        "anchors": len(obs["anchors"]), "facts": len(obs["facts"]),
        "links": len(obs["links"]),
        "semantic_truth": "NOT_INDEPENDENTLY_TESTED",
        "full_book_semantic_coverage": "NOT_ESTABLISHED",
        "model_weight_training": "NOT_PERFORMED",
    }


def recover(bundle_dir, dest, *, allow_private_original=False):
    require(allow_private_original, "PRIVATE_ORIGINAL_RECOVERY_REQUIRES_OPT_IN")
    verify(bundle_dir)
    p = Path(bundle_dir) / "source.zlib"
    raw = zlib.decompress(p.read_bytes())
    dest = Path(dest)
    require(not dest.exists(), "RECOVERY_TARGET_EXISTS")
    dest.write_bytes(raw)
    return {"recovered_bytes": len(raw), "sha256": hash_bytes(raw)}


def main():
    ap = argparse.ArgumentParser(description="WF reversible-world evidence codec")
    sub = ap.add_subparsers(dest="action", required=True)
    p = sub.add_parser("pack")
    p.add_argument("--source", required=True)
    p.add_argument("--observations", required=True)
    p.add_argument("--out", required=True)
    v = sub.add_parser("verify")
    v.add_argument("--bundle", required=True)
    r = sub.add_parser("recover")
    r.add_argument("--bundle", required=True)
    r.add_argument("--out", required=True)
    r.add_argument("--allow-private-original-output", action="store_true")
    a = ap.parse_args()
    try:
        if a.action == "pack":
            result = pack(a.source, a.observations, a.out)
        elif a.action == "verify":
            result = verify(a.bundle)
        else:
            result = recover(a.bundle, a.out,
                             allow_private_original=a.allow_private_original_output)
    except (ValueError, KeyError, OSError, zlib.error, json.JSONDecodeError) as exc:
        ap.exit(2, "FAIL: " + str(exc) + "\n")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
