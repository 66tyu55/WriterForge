from __future__ import annotations
from dataclasses import dataclass
import math, re

SENTENCE_END = re.compile(r"[。！？!?]+")
DIALOGUE_MARKS = ("“","”","「","」","『","』","\"")

@dataclass
class VoiceFingerprint:
    avg_sentence_chars: float
    sentence_length_std: float
    dialogue_mark_ratio: float
    exclamation_ratio: float
    question_ratio: float
    comma_per_sentence: float

def _std(vals, mean):
    if not vals:
        return 0.0
    return math.sqrt(sum((v-mean)**2 for v in vals)/len(vals))

def fingerprint(text: str) -> VoiceFingerprint:
    text = text or ""
    raw = [s.strip() for s in SENTENCE_END.split(text) if s.strip()]
    if not raw:
        raw = [text.strip()] if text.strip() else []
    lengths = [len(s) for s in raw]
    avg = sum(lengths)/len(lengths) if lengths else 0.0
    std = _std(lengths, avg)
    n = max(1, len(raw))
    dialogue = sum(text.count(m) for m in DIALOGUE_MARKS)
    return VoiceFingerprint(
        avg_sentence_chars=avg,
        sentence_length_std=std,
        dialogue_mark_ratio=dialogue/max(1,len(text)),
        exclamation_ratio=(text.count("！")+text.count("!"))/n,
        question_ratio=(text.count("？")+text.count("?"))/n,
        comma_per_sentence=(text.count("，")+text.count(","))/n,
    )

def distance(a: VoiceFingerprint, b: VoiceFingerprint) -> float:
    # Normalized, intentionally simple and deterministic.
    terms = [
        abs(a.avg_sentence_chars-b.avg_sentence_chars)/max(8.0,a.avg_sentence_chars,b.avg_sentence_chars),
        abs(a.sentence_length_std-b.sentence_length_std)/max(8.0,a.sentence_length_std,b.sentence_length_std),
        abs(a.dialogue_mark_ratio-b.dialogue_mark_ratio)*10,
        abs(a.exclamation_ratio-b.exclamation_ratio),
        abs(a.question_ratio-b.question_ratio),
        abs(a.comma_per_sentence-b.comma_per_sentence)/max(1.0,a.comma_per_sentence,b.comma_per_sentence),
    ]
    return sum(terms)/len(terms)

def audit(baseline_text: str, candidate_text: str, threshold: float = 0.34) -> dict:
    base = fingerprint(baseline_text)
    cand = fingerprint(candidate_text)
    d = distance(base,cand)
    return {
        "distance": round(d,4),
        "drift": d > threshold,
        "baseline": base.__dict__,
        "candidate": cand.__dict__,
        # Important: warning, not automatic rewrite.
        "action": "review_only" if d > threshold else "keep"
    }
