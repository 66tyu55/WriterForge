"""WF V78: independent byte/charset plausibility review of a FROZEN B00 source.

This is part of WriterForge's own admission pipeline, not external
classification, a model-generated answer, or proof of a canonical literary
edition. It reads a whole <=8MiB TXT within the WF Railway process, verifies
the exact existing B00 source SHA-256, and evaluates strict round-trips under
UTF-8, GB18030, GBK, Big5 and CP950. No errors=ignore/replace permitted.

Successful "TECHNICAL..." means valid reversible text representation only,
not authorial text/genre completeness, human-confirmed encoding or learning
eligibility. If two genuinely different plausible decodings remain, returns
AMBIGUOUS without choosing a winner.
"""
from __future__ import annotations

from collections import Counter
from hashlib import sha256
from pathlib import Path
import codecs
import json
import re
import unicodedata

MAX_BYTES = 8*1024*1024
CODECS = ("utf-8-sig","utf-8","gb18030","gbk","big5","cp950")
SHA = re.compile(r"^[a-f0-9]{64}$")
# Common simplified/traditional shared lexical function chars, not title keywords.
COMMON_HAN = frozenset(
    "的一是不了人在有我他她你们我这那来去说看听会对上个中和为之以所而其"
    "天地人时日月年无可道能出入从事后前手心头身很把被给让与却但就都还也"
)
CHINESE_PUNCT = frozenset("，。！？；：、“”‘’《》〈〉（）【】…—")
MOJIBAKE = ("锟斤拷","ï»¿","Ã","Â","�")


class WFCharsetReviewError(ValueError):
    pass


def need(flag, code):
    if not flag:raise WFCharsetReviewError(code)


def sha256_bytes(data):
    return sha256(data).hexdigest()


def _stats(decoded):
    need(decoded, "WF_CHARSET_DECODED_EMPTY")
    n=len(decoded)
    han=sum(("\u3400"<=ch<="\u9fff") for ch in decoded)
    common=sum(ch in COMMON_HAN for ch in decoded)
    punctuation=sum(ch in CHINESE_PUNCT for ch in decoded)
    bad=sum(
      ch not in ("\t","\n","\r","\f") and
      unicodedata.category(ch) in ("Cc","Cs","Cf","Cn")
      for ch in decoded)
    replacement=decoded.count("\ufffd")
    rare=sum(
      "\u3400"<=ch<="\u4dbf" or
      "\uf900"<=ch<="\ufaff" or
      "\ue000"<=ch<="\uf8ff"
      for ch in decoded)
    mojibake=sum(decoded.count(tag) for tag in MOJIBAKE)
    # Deliberately coarse and auditable, not an LLM 'understanding' score.
    return {
        "characters":n,
        "han_per_1000":round(1000*han/n,2),
        "common_han_per_1000":round(1000*common/n,2),
        "punct_per_1000":round(1000*punctuation/n,2),
        "controls_or_unassigned":bad,
        "replacement_chars":replacement,
        "rare_cjk_characters":rare,
        "common_mojibake_markers":mojibake,
        "decoded_text_sha256":sha256_bytes(decoded.encode("utf-8")),
    }


def _plausible(st):
    # A well-formed source may still be short ASCII, English, written in an
    # unusual dialect, or have unusual punctuation. Refuse to infer a correct
    # original or complete book from these heuristic thresholds.
    return (
        st["characters"]>=1000 and
        st["controls_or_unassigned"]==0 and
        st["replacement_chars"]==0 and
        st["han_per_1000"]>=350 and
        st["common_han_per_1000"]>=18 and
        st["punct_per_1000"]>=2 and
        st["common_mojibake_markers"]==0
    )


def byte_charset_audit(source_path,*,expected_source_sha256,expected_size,
                       expected_key_sha256=None):
    source=Path(source_path)
    need(source.is_file() and type(expected_size) is int and
         1024<=expected_size<=MAX_BYTES and
         source.stat().st_size==expected_size,
         "WF_CHARSET_SOURCE_NOT_BOUNDED")
    need(isinstance(expected_source_sha256,str) and
         SHA.fullmatch(expected_source_sha256),
         "WF_CHARSET_EXPECTED_SHA_INVALID")
    if expected_key_sha256 is not None:
        need(isinstance(expected_key_sha256,str) and
             SHA.fullmatch(expected_key_sha256),
             "WF_CHARSET_B00_KEY_BINDING_INVALID")
    raw=source.read_bytes()
    need(len(raw)==expected_size and
         sha256_bytes(raw)==expected_source_sha256,
         "WF_CHARSET_SOURCE_SHA_MISMATCH")
    attempts={}
    successes=[]
    for codec in CODECS:
        try:
            decoded=raw.decode(codec,"strict")
            reversible=decoded.encode(codec,"strict")==raw
        except (UnicodeDecodeError,UnicodeEncodeError,LookupError):
            attempts[codec]={
              "strict_full_decode":False,
              "byte_roundtrip":False,
              "technically_plausible":False,
            }
            continue
        st=_stats(decoded)
        outcome={
          "strict_full_decode":True,
          "byte_roundtrip":reversible,
          "technically_plausible":reversible and _plausible(st),
          **st,
        }
        attempts[codec]=outcome
        if outcome["technically_plausible"]:
            successes.append((codec,st["decoded_text_sha256"]))
    families={}
    for codec,digest in successes:
        families.setdefault(digest,[]).append(codec)
    # GB18030 and GBK are not separate readings if they yield exact same
    # decoded bytes. Likewise Big5 and CP950 with identical source text.
    conflicting_readings=len(families)>1
    if not families:
        code="WF_CHARSET_NO_STRICT_PLAUSIBLE_DECODING"
    elif conflicting_readings:
        code="WF_CHARSET_AMBIGUOUS_MULTIPLE_PLAUSIBLE_READINGS"
    else:
        code="WF_CHARSET_ONE_REVERSIBLE_TEXT_READING"
    return {
      "status":code,
      "format":"writerforge.wf-charset-audit.v78",
      "source_sha256":expected_source_sha256,
      "source_key_sha256":expected_key_sha256,
      "source_bytes":expected_size,
      "codecs_tested":list(CODECS),
      "results":attempts,
      "plausible_distinct_decoded_texts":len(families),
      "unique_reading_codec_aliases":list(next(iter(families.values())))
          if len(families)==1 else [],
      "source_encoding_human_confirmed":False,
      "source_edition_human_confirmed":False,
      "deepseek_model_called":False,
      "human_reading_quality_assessed":False,
      "literary_genre_inferred":False,
      "chapter_authorship_verified":False,
      "original_source_bytes_modified":False,
      "original_source_text_exposed_in_result":False,
      "does_not_auto_unlock_frozen_B00_training_gate":True,
      "competing_charset_possibilities_remain_without_external_metadata":
          conflicting_readings,
    }
