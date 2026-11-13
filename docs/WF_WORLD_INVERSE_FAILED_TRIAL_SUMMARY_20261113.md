# WF world-causality reverse trial — STOP / FAILED (2026-11-13)

## Actual execution, not simulated model output

Ran [Actions #43384652916](https://github.com/66tyu55/WriterForge/actions/runs/43384652916) with the SHA-pinned, CPU-local Qwen2.5-3B-Instruct Q4_K_M model. **Four actual calls, four completed responses, four valid JSON, zero paid API calls, zero retry**. The exact original prompts, raw engine replies, response usage and hashes are retained in its uploaded artifact: `WF-World-Inverse-Original-Qwen3B-Four-Anonymous-Decodes`.

The test inputs are two small, aggressively anonymized **real-original-grounded** world-state samples, not whole-book training. The real novels, names, original source text, source spans and privately frozen gold were never part of model input or public Git. The source-grounded private rubric (5 A facts, 6 B facts) was frozen before model calls; its SHA256 is `151e6a0e409cc61cbc0b08cd79a90caac23576d6fce73361f584a6ac04a87c79`. This is **the same assistant's source review, not an independent reader**; counts below are provisional item-level adjudication, NOT transferable accuracy percentages.

## Pre-registered criteria reviewed against real local-model completions

| Arm | Complete supported items | Partial | Missing/wrong | Observed errors |
|---|---:|---:|---:|---|
| A unlabeled numeric-only negative ablation | 0/5 | 0 | 5 | Inferred feudal land/power distribution from numbers with no feature axes or provenance; made up the institution |
| A open-typed anonymized observations | 1/5 | 1 | 3 | Reconstructed a minor worker suggesting identity tracking and the senior protecting trust, but lost the role of multi-party restraint/profit and reversed the original causal order of covert trading/anonymity |
| B typed observations alone | 3/6 | 2 | 1 | Identified independent animal activity and multi-generational rural labor; did not recover source details absent from the encoded parameters |
| B same observations plus tentative A-derived interpretation habit | 4/6 | 1 | 1 | Added clearer "co-occurrence is not causation" caution, but also invented observer absence and did not recover the unencoded daily-life evidence |

**Transfer failure under frozen gate**: B+habit added one provisionally supported item but also an unsupported detail; its prompt had **562 vs 492** tokens and output **303 vs 226** tokens, so this cannot prove habit-induced gain. Strict criterion required >=80% of grounded items and no newly unsupported claim. **FAIL**.

## Failure mechanism

1. **Irreversible semantic information loss occurs in the encoder.** Certain material life / incidental-world details from the original simply did not enter the anonymous packet. Byte-perfect backup and later semantic decoding cannot recover absent attributes; add-on checks cannot solve missing representation.
2. **Typed labels leak expected mechanism words but do not produce causal understanding.** The model can repeat labels such as shared exchange or anonymity while misunderstanding *why* arrangements arise and reversing the cause/effect arrow. Reconstructing a glossary is not reconstructing the world.
3. **The treatment wasn't actually training WF on original novels.** The "learned" arm was only a hand-written in-context reading habit derived from a previous case. No model weights changed, no full-book fact/state reconstruction, no locked future-event prediction.
4. **The trial isn't independent enough for a literary claim.** Two narrow source samples, model capacity limited to 3B, criterion review authored by the same assistant, no source-disjoint deep future holdouts, no meaningful changed-character/world simulations.
5. **Unlabeled numbers were only a deliberately information-destroying negative control.** This does not prove all numerical parameters are worthless; it does prove bare numbers with no axis semantics cannot reliably invert rich world states.

## Decision

**STOP this method here.** Do not re-run the fixed four prompts, adjust labels to get higher scores, buy another model call, automatically approve candidate causal edges, or merge PR #69 as literary capability. Existing Xuehai, R2, Canon and production WF remain untouched. Preserve both failed answers and raw requests.

If work resumes with user authorization, the **first mandatory step** is a tiny end-to-end, source-complete, evidence-cited, independently decoded event/state reconstruction on contiguous original chapters with unseen later original held back. Every actor, minor passerby, clock, location, belief, uncertainty, resource and incident in scope must survive encoding or carry an explicit unknown/omission receipt. Only after that genuine inverse passes can whole-book ingestion or model training be justified.

**Coding/test infrastructure: working. Literary/world inverse from parameters: NOT PASSED. No claimed accuracy or quality uplift.**
