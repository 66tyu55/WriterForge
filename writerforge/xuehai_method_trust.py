"""Externally rooted Xuehai method attestation verification (0.BN).

A signature proves only possession of an *already trusted* review key, not
independent human quality or copyright by itself. No private key generation,
no auto-approval, no new memory owner. Pending classic/modern research cards
remain blocked until external authorities are configured and sign the exact
card and source scope. The trusted keys are NEVER read from SQLite / cards.
"""
from __future__ import annotations
from hashlib import sha256
import json
import os
import re

KEY_NAMES = (
    "WRITERFORGE_XUEHAI_RIGHTS_REVIEW_PUBKEY_HEX",
    "WRITERFORGE_XUEHAI_CRAFT_REVIEW_PUBKEY_HEX",
)
CONTRACT = "writerforge.xuehai.two-external-review-signatures.v1"
SCOPE = "ISOLATED_WRITE_PILOT_ONLY"
_SHA = re.compile(r"[0-9a-f]{64}\Z")
_SIGNATURE = re.compile(r"[0-9a-f]{128}\Z")
ROLES = ("RIGHTS", "CRAFT")


def _canonical(data:dict)->bytes:
    return json.dumps(
        data,sort_keys=True,ensure_ascii=False,
        separators=(",",":"),allow_nan=False,
    ).encode("utf8")


def signed_payload_bytes(payload:dict, role:str)->bytes:
    if role not in ROLES or not isinstance(payload,dict):
        raise ValueError("XUEHAI_SIGNED_PAYLOAD_ROLE_OR_TYPE_INVALID")
    return ("writerforge.xuehai." + role + ".v1\0").encode("ascii")+_canonical(payload)


def trusted_public_keys(*, require:bool)->tuple[bytes,bytes]|None:
    raw=tuple(os.environ.get(k,"") for k in KEY_NAMES)
    if not all(raw):
        if require:
            raise ValueError("XUEHAI_EXTERNAL_TRUST_ROOTS_REQUIRED")
        return None
    try:
        result=tuple(bytes.fromhex(s) for s in raw)
    except ValueError as exc:
        raise ValueError("XUEHAI_EXTERNAL_TRUST_ROOT_FORMAT_INVALID") from exc
    if any(len(x)!=32 for x in result):
        raise ValueError("XUEHAI_EXTERNAL_TRUST_ROOT_FORMAT_INVALID")
    if result[0] == result[1]:
        raise ValueError("XUEHAI_EXTERNAL_TRUST_ROOTS_NOT_DISTINCT")
    return result


def public_key_fingerprints(keys:tuple[bytes,bytes])->tuple[str,str]:
    return tuple(sha256(x).hexdigest() for x in keys)


def verify_external_signatures(payload:dict,
                               rights_signature_hex:str,
                               craft_signature_hex:str,
                               keys:tuple[bytes,bytes]) -> str:
    from cryptography.exceptions import InvalidSignature
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
    if any(type(x) is not str or not _SIGNATURE.fullmatch(x)
           for x in (rights_signature_hex,craft_signature_hex)):
        raise ValueError("XUEHAI_EXTERNAL_REVIEW_SIGNATURE_FORMAT_INVALID")
    for key,role,sig in zip(keys,ROLES,
                             (rights_signature_hex,craft_signature_hex)):
        try:
            Ed25519PublicKey.from_public_bytes(key).verify(
                bytes.fromhex(sig),signed_payload_bytes(payload,role))
        except (ValueError,InvalidSignature) as exc:
            raise ValueError("XUEHAI_EXTERNAL_REVIEW_SIGNATURE_INVALID") from exc
    return sha256(_canonical({
        "payload":payload,
        "rights_signature_hex":rights_signature_hex,
        "craft_signature_hex":craft_signature_hex,
    })).hexdigest()


def validate_challenge(payload:dict,card:dict,keys:tuple[bytes,bytes])->None:
    # Cardinality is frozen. Reusing a signature from a different work,
    # edition, source, card revision, source locator or keys is impossible.
    expected={
        "contract":CONTRACT,
        "entry_id":card["entry_id"],
        "card_sha256":card["card_sha256"],
        "snapshot_id":card["snapshot_id"],
        "work_id":card["work_id"],
        "source_uri":card["source_uri"],
        "source_sha256":card["source_sha256"],
        "source_unit_sha256":card["source_unit_sha256"],
        "source_locator":card["source_locator"],
        "source_edition":card["source_edition"],
        "source_kind":card["source_kind"],
        "rights_status":"RIGHTS_VERIFIED",
        "review_status":"PILOT_APPROVED",
        "value_status":"UNPROVEN_PILOT",
        "use_scope":SCOPE,
        "rights_key_sha256":public_key_fingerprints(keys)[0],
        "craft_key_sha256":public_key_fingerprints(keys)[1],
    }
    if type(payload) is not dict or set(payload) != set(expected)|{
        "rights_basis_uri","rights_evidence_sha256","craft_review_sha256",
    } or any(payload.get(k)!=v for k,v in expected.items()):
        raise ValueError("XUEHAI_EXTERNAL_REVIEW_SOURCE_OR_CARD_SCOPE_MISMATCH")
    for key in ("rights_evidence_sha256","craft_review_sha256"):
        if type(payload[key]) is not str or not _SHA.fullmatch(payload[key]):
            raise ValueError("XUEHAI_EXTERNAL_REVIEW_EVIDENCE_SHA_INVALID")
    # A signature authenticates who approved WHICH external legal basis.
    # These URLs are references for a human rights reviewer; no automatic
    # inference of licenses based on the hostname is made here.
    uri=payload["rights_basis_uri"]
    if (type(uri) is not str or len(uri)>350 or
        not uri.startswith("https://") or
        any(ch in uri for ch in "\r\n\x00")):
        raise ValueError("XUEHAI_EXTERNAL_REVIEW_RIGHTS_BASIS_INVALID")
