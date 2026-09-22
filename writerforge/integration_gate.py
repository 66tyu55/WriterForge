from __future__ import annotations
from dataclasses import dataclass

@dataclass
class GateResult:
    accepted: bool
    reasons: list[str]

def evaluate_integration(*,
                         quality_before: float,
                         quality_after: float,
                         latency_before: float,
                         latency_after: float,
                         error_before: float,
                         error_after: float,
                         max_latency_regression: float = 0.20,
                         min_quality_gain: float = 0.01) -> GateResult:
    reasons = []
    quality_gain = quality_after - quality_before
    latency_reg = (latency_after-latency_before)/max(latency_before,1e-9)
    error_gain = error_before-error_after

    if quality_gain < min_quality_gain and error_gain <= 0:
        reasons.append("no measurable quality/error improvement")
    if latency_reg > max_latency_regression:
        reasons.append(f"latency regression {latency_reg:.1%} exceeds budget")
    accepted = not reasons
    if accepted:
        reasons.append("passes quality/error benefit and latency budget")
    return GateResult(accepted, reasons)
