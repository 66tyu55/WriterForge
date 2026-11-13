# WF world-structure inverse trial — frozen protocol (2026-11-13)

## Objective and stop rule

One attempt at the user's *actual* concern: can anonymous, parameterized observations **carry enough information to reconstruct the original world's constraints, off-screen behavior, uncertainty and direction of causality**, and can one source-derived reading habit improve reconstruction on a different novel?

If the attempt fails, STOP treating additional graph validators as progress and summarize the root cause. Do not repeat model requests or tune against this same heldout data.

## Model, privacy and cost

- Four real local open-weight inference calls: Qwen2.5-3B-Instruct Q4_K_M at the GitHub Actions fixed SHA-256 in the workflow, CPU only. Seed 20261113, temperature 0, max 920 completion tokens **per arm**; prompts/usage and full raw outputs retained separately.
- NO paid API, no model weights fine-tuning, no real original prose, source names, or identities in Git or model prompts. All real-source evidence spans, source ledger and true original files are private.
- Two *source-grounded*, strongly anonymized candidate worlds (not a complete novel): A, multiparty contested space and hidden exchanges; B, rural generations / incidental natural activity / uncertain phenomena.
- Source-grounded gold annotated and frozen in private storage **before model calls**, with 5 A checks and 6 B checks, plus negative examples. Gold SHA-256: `151e6a0e409cc61cbc0b08cd79a90caac23576d6fce73361f584a6ac04a87c79`. Not an independent human-reviewed gold standard: do not claim unbiased accuracy.

## Frozen 4 arms (no same-sample tuning)

1. `world_a / numeric_only`: unlabeled numeric parameters and pair indices; discover whether information can be recovered without an axis dictionary. These intentionally omit semantics: an abstaining decoder may be **correct**. Numeric rows here are a *negative ablation*, not calibrated literary weights.
2. `world_a / typed`: anonymized but semantically typed relational observations from the same original, with explicit direction and unknown clocks. Evaluate source-grounded mechanism reconstruction.
3. `world_b / bare`: different novel, anonymous typed facts only; model-independent baseline for this case.
4. `world_b / transfer`: the exact same second-world facts plus a source-A-derived tentative interpretation habit. Evaluate whether a learned procedure actually adds source-supported insight or just restates caution.

Crucially these arms are **not a balanced demonstration of neural training**. The A numeric vs typed arm is an information-content ablation; the B bare vs transfer arm is an in-context procedure comparison with unequal prompt lengths. No reviewer should call this "same-budget trained author uplift" just because completion caps match.

## Score in separate private context after generation

- A gold: multi-actor inability to monopolize; repeated mutual-profit exchange; concealed transfer tied to provenance risk; a minor employee independently requests tracking and a senior rejects to protect reputational trust; any resulting institution is conditional, not universal or protagonist-created.
- B gold: unexplained sensory phenomena are uncertain even if temporal co-occurrence; incidental fish/crabs retain independent actions; multi-generational household activity outside POV; a chance animal encounter need not cause mystical perception; repairs, boats and livestock still belong to wider world; separate actor belief from fact.
- **Provisional reconstruction pass:** at least 80% of source-anchored check items with zero decisive hallucinated causal edges, and correct separation of narrated time vs story time.
- **Provisional transfer evidence:** world_b transfer improves at least 1 distinct grounded item over world_b bare, with zero additional causal hallucinations. Mere repeat of the prompt or generic warnings is not uplift.
- **User's actual final pass** requires source-disjoint examples, separately adjudicated gold and actual world/character/personality swaps. Four model answers cannot establish full-book learning or a reliable accuracy rate.

Preserve raw prompts and completions including invalid JSON or failures, and freeze the first failed run. No deployment, no merge, no Xuehai/R2/Canon change.

## Experiment launch receipt

The frozen four-arm prompt file and runner are now committed on this experimental branch. This one-shot commit is intentionally the **only** trigger for actual local Qwen inference. No additional calls, automatic retries or tuning against the first results are permitted.
