from __future__ import annotations
from dataclasses import dataclass
from collections import Counter

@dataclass
class EvalResult:
    name: str
    score: float
    details: dict

class EvalLab:
    @staticmethod
    def continuity_score(findings):
        blocking = sum(1 for f in findings if getattr(f, "severity", "") == "blocking")
        warnings = sum(1 for f in findings if getattr(f, "severity", "") == "warning")
        score = max(0.0, 100.0 - blocking*20.0 - warnings*5.0)
        return EvalResult("continuity", score, {"blocking": blocking, "warnings": warnings})

    @staticmethod
    def detection_metrics(expected_codes, findings):
        expected = set(expected_codes)
        got = set(getattr(f, "code", "") for f in findings)
        tp = len(expected & got)
        fp = len(got - expected)
        fn = len(expected - got)
        precision = tp / (tp + fp) if tp + fp else 1.0
        recall = tp / (tp + fn) if tp + fn else 1.0
        f1 = (2*precision*recall/(precision+recall)) if precision+recall else 0.0
        return {
            "tp":tp, "fp":fp, "fn":fn,
            "precision":round(precision,4),
            "recall":round(recall,4),
            "f1":round(f1,4),
            "expected":sorted(expected),
            "got":sorted(got)
        }

    @staticmethod
    def compare_systems(name_a, metrics_a, name_b, metrics_b):
        # Deterministic metrics only. Human literary judgment must remain separate.
        score_a = metrics_a.get("f1", 0.0)
        score_b = metrics_b.get("f1", 0.0)
        winner = "tie" if score_a == score_b else (name_a if score_a > score_b else name_b)
        return {"a":{"name":name_a,**metrics_a},"b":{"name":name_b,**metrics_b},"winner":winner}

    @staticmethod
    def human_blind_summary(ballots):
        # ballots: [{"candidate":"A","continue_reading":1..5,...}]
        by = {}
        for b in ballots:
            c = b["candidate"]
            by.setdefault(c, []).append(b)
        out = {}
        for c, rows in by.items():
            keys = [k for k in rows[0] if k != "candidate"]
            out[c] = {
                k: round(sum(float(r[k]) for r in rows)/len(rows), 3)
                for k in keys if isinstance(rows[0][k], (int,float))
            }
        return out
