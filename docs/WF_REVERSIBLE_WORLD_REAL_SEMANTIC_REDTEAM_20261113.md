# WF world causality Skill — real-source red-team, initial failure, admission hardening

Date: 2026-11-13. Scope: private complete original texts **in the local private evaluator only**, public repository contains ZERO original prose. This note is a diagnostic, **not a semantic or literary mastery claim**.

## What was genuinely tested

Two whole private originals, previously scanned and byte-roundtripped, were used with their source-located candidate evidence ledgers:

| Original | Input file bytes | Candidate source anchors | Candidate facts | Candidate causal edges |
|---|---:|---:|---:|---:|
| 武动乾坤 | 8,254,082 | 37 | 17 | 7 |
| 玄鉴仙族 | 18,755,689 | 21 | 11 | 2 |
| Total | 27,009,771 | 58 | 28 | 9 |

The original file and ledger versions are SHA256 pinned privately. Prior human/editor review of these particular candidates: **0**. Recorded causal effect estimates/learned numerical weights: **0**. No author-model calls or source-disjoint transfer evaluation occurred.

To discover whether the old source-matched codec actually proved causality, the private evaluator performed **four deliberately wrong perturbations against each actual source**:

1. Reverse the endpoints of an asserted directed causal link while leaving cited source anchors unchanged.
2. Replace one typed world claim with an invented, unsupported world-entity existence claim.
3. Reassign a fact's subject to a different, legitimately anchored character/item.
4. Invent an exact fictional story-time tick where the original candidate only had UNKNOWN time.

**Observed RED**: the old `codec.validate_observations` accepted all **8/8 corrupted inputs**. It correctly verified literal source bytes and anchor positions but failed to detect semantic fabrication. This is an actual test failure, NOT a success score, and it illustrates why a source match cannot be taken as causal validation. No original strings or private identifiers are published here.

## Fix introduced in this feature branch

Added `.agents/skills/reversible-world-causality/scripts/semantic_gate.py` and required the reviewed-only `intervention.prepare_reviewed_branch` for any model-facing future-change experiment.

- Model input defaults to **zero** approved facts or edges unless separate human editorial receipts are provided with exact source-bound claim SHA and external HMAC attestation.
- Reversed arrows, swapped subjects, changed fact kinds, changed source provenance or edited rationale invalidate existing review attestations.
- Model self-review, partial review, unsupported claims and unknown facts remain quarantined. HMAC confirms the receipt, not the reviewer’s reasoning or true independence; authentication/independence must be administered out of band.
- Model-facing inputs retain evidence-revelation and fictional time as separate fields; story time remains `null` when the source does not establish it.
- Sealed future source facts, source text, later-review counts, source SHA and original content offsets are not included in the model context.

The existing source codec and archive still accept unreviewed candidate records for *offline research*; that is deliberate and must **not** be confused with approved writing knowledge. This Skill must not be wired directly to the production author until attested review and independent source-disjoint transfer tests.

## Reproducible tests

Synthetic-only regression exercises the real bug classes and the new gate (including a signed record failing after edge reversal or invented claim, time preservation, and refusal to use an unreviewed choice in a model-facing fork). Focused tests: **37/37 passed** at [Actions #43380893991](https://github.com/66tyu55/WriterForge/actions/runs/43380893991), followed by chronology-field retention checks and developer docs. The full-repository workflow remains red due to independently present dependency/fixture problems; don't conflate that with these 37 passes.

## Verdict and next hard gate

**Old causal truth validation: FAIL.** **Mechanical source roundtrip: PASS.** **New semantic admission quarantine: PASS (synthetic regression).** **Real causal inverse accuracy: UNMEASURED**, because neither independent gold annotation nor a genuinely blind model prediction was obtained. Do not report a 100% causal success or a fabricated 0% skill score. With no verified human attestation, **28/28 facts and 9/9 edges are still candidates**, 0 approved for WF writing.

Future genuine test: independently review/annotate sufficient story events across space/time/actors (including one-line NPCs, off-protagonist change, economic institutions, irrational behavior and accidents); freeze a disjoint held-out original or chapter; isolate the full target from model and prompt builder; compare model inferences against adjudicated gold and count false causes, reversed arrows, overlooked actors and mistaken story-time knowledge. Compare generic baseline vs reviewed-skill within the same model/time/token budget. A failed result must be retained without training on the test answers.
