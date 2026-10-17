"""Immutable snapshot formatting for a bounded self-study pilot."""
from __future__ import annotations
from hashlib import sha256
import json

def canonical(value):
    return json.dumps(value,sort_keys=True,ensure_ascii=False,
                      separators=(",",":")).encode("utf-8")

def fingerprint(value):
    return sha256(canonical(value)).hexdigest()

def verify(snapshot,expected):
    return isinstance(snapshot,dict) and fingerprint(snapshot)==expected
