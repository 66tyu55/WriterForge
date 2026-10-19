"""V71 UTF-8/BOM/legacy-Chinese decoding guard (stdlib, no model).

Never modify source bytes; never decode with errors=replace/ignore. An
unlabelled GB18030 candidate is only a PROVISIONAL technical index, not an
approved source edition or WF literary-learning input: Big5/other legacy
encodings cannot always be disambiguated purely from byte statistics.
"""
from __future__ import annotations

from pathlib import Path
import codecs
import unicodedata

SAMPLE_MAX=256*1024

class SourceEncodingError(ValueError):
    pass

def require(ok,code):
    if not ok:
        raise SourceEncodingError(code)

def decode_prefix(data: bytes, encoding: str):
    decoder=codecs.getincrementaldecoder(encoding)(errors="strict")
    # final=False permits a multibyte character to straddle sample boundary.
    return decoder.decode(data,final=False)

def safe_text_metrics(text: str):
    require(isinstance(text,str) and bool(text),
            "WF_V71_ENCODING_EMPTY_TEXT")
    disallowed=sum(
        ch not in ("\n","\r","\t","\f")
        and unicodedata.category(ch) in ("Cc","Cf","Cs")
        for ch in text)
    nulls=text.count("\x00")
    require(nulls==0 and disallowed/max(1,len(text))<=0.0005,
            "WF_V71_ENCODING_BINARY_OR_CONTROL_TEXT")
    han=sum(('\u3400'<=ch<='\u9fff') for ch in text)
    marks=sum(ch in "，。！？；：、“”‘’…—！?;" for ch in text)
    return {
       "han_ratio":han/max(1,len(text)),
       "punctuation_ratio":marks/max(1,len(text)),
       "characters_examined":len(text),
    }

def detect_decoding_for_index(path):
    """Pick strict decode for indexed *copy*. Never rewrite R2 originals."""
    source=Path(path)
    require(source.is_file(),"WF_V71_ENCODING_SOURCE_MISSING")
    with source.open("rb") as f:
        data=f.read(SAMPLE_MAX)
    require(len(data)>=1024,"WF_V71_ENCODING_SAMPLE_TOO_SHORT")
    if data.startswith(codecs.BOM_UTF8):
        text=decode_prefix(data,"utf-8-sig")
        safe_text_metrics(text)
        return {
          "encoding":"utf-8-sig",
          "decision":"UTF8_BOM_DETECTED",
          "provisional_legacy_decoding":False,
        }
    if data.startswith((codecs.BOM_UTF16_LE,codecs.BOM_UTF16_BE)):
        text=decode_prefix(data,"utf-16")
        safe_text_metrics(text)
        return {
          "encoding":"utf-16",
          "decision":"UTF16_BOM_DETECTED",
          "provisional_legacy_decoding":False,
        }
    try:
        text=decode_prefix(data,"utf-8")
    except UnicodeDecodeError:
        # Cannot assert GB18030 provenance from bytes alone; merely offer a
        # cautious candidate for a PRELIMINARY local index.
        try:
            text=decode_prefix(data,"gb18030")
        except UnicodeDecodeError:
            raise SourceEncodingError(
                "WF_V71_ENCODING_UNSUPPORTED_LEGACY_SOURCE") from None
        stats=safe_text_metrics(text)
        require(stats["characters_examined"]>=1000 and
                stats["han_ratio"]>=0.35 and
                stats["punctuation_ratio"]>=0.002,
                "WF_V71_ENCODING_LEGACY_CONFIDENCE_TOO_LOW")
        return {
          "encoding":"gb18030",
          "decision":"LIKELY_LEGACY_CHINESE_STRICT_DECODING",
          "provisional_legacy_decoding":True,
          "source_edition_human_verified":False,
        }
    safe_text_metrics(text)
    return {
       "encoding":"utf-8",
       "decision":"STRICT_UTF8_SAMPLE",
       "provisional_legacy_decoding":False,
    }
