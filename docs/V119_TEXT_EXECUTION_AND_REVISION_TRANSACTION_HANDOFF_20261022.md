# V119 — prose execution is not self-reported reasoning (2026-10-22)

## Scope / status

The model's statement of intention or self-assessment is NOT evidence that it wrote that intention into the story. V96 exact action/effect quotes are source-anchored, but do NOT independently prove the semantic relationship. V114/V116/V117 recover a narrow subset of source events and temporal state; V118 lamps are optional writing cues, not model-weight training, autonomous literary judgment, or prose validation.

V119 adds an **opt-in, zero-model, host-enforced local edit transaction**. No change to legacy \`single\` or to V118 continuity guard. No Railway deployment, canon/database/R2 writes, user source mutation, model retry or new provider calls.

- \`writerforge/v119_revision_transaction.py\`:
  - \`preview_revision()\`: require original prose SHA-256, project/scene ID, exact targeted slice and offset; apply *only* a replacement fragment, never a model-controlled whole-document rewrite.
  - \`inspect_whole_rewrite()\`: reject a full replacement proposal if one character outside its announced edit span differs.
  - At most 1,800 Unicode codepoints per selection/replacement, at most 20,000 total characters, 12 unique existing source quotes allowed as explicit immutable anchors (outside edit span).
  - Optional V116 deterministic previous-state preflight on **both** source and candidate, and block display of any candidate introducing newly flagged warning codes. Note V116 is a *narrow lexical checker* and may overflag ambiguous actor assignment; errors cannot be used to claim universal semantic truth.
  - Return an in-memory candidate preview and a source/proposed-text/hash/coverage receipt; never mark author acceptance, prose-quality approval or plan-goal fulfillment. No raw manuscript inside receipts.
  - Reject stale source hashes and target span mismatch, no silent rebase, no model retries.
- \`writerforge/writing_assist.py\`: \`AutonomousWriting.preview_local_revision()\` exposes the candidate-only behavior to WF without changing existing write paths.
- \`tests/test_v119_revision_transaction.py\`: adversarial and positive tests for corruption beyond edit span, no source drift, pin immutability/duplication, excessive edits, "right arm" and "fruit teeth" newly flagged V116 warnings, revising away a baseline warning, zero model calls.
- \`.github/workflows/v119-revision-transaction.yml\`: no model secrets, complete regression suite.

## Verification

GitHub Actions **success**: https://github.com/66tyu55/WriterForge/actions/runs/39717152761 , 1,261 tests executed, 4 skipped, zero failures. Previous V118 baseline had 1,248 tests run; new +13.

Cold private-source audit was performed **locally only** against exact preserved original texts from earlier GitHub Actions artifacts (not published in a test fixture, not passed to a model, not rewritten):
- V113 951-character sword-tassel source SHA-256: \`339b2b1cab1e4895ed73d4e8ef73ed0b51c6adb832149cd097c35b0ec9b585f7\`.
- V114B 964-character original *rejected first scene* SHA-256: \`c5146b829348ea12724290550ab8d4b4d959f2c1aaa41459c38bdeef757ad166\`.
- For both, synthetic replacement only in a fixed target slice preserved prefix/suffix byte-for-byte as Python strings; attempts to alter a character outside scope were rejected. No literary or causal improvement is claimed by these tests.

## What is **not** solved

1. A model's natural-language plan \`beat.goal\` or explanatory prose is still not reliably proven to have occurred in the actual generated text. V96 quote existence alone is not enough.
2. Existing V116 Chinese event templates cover only some physical movements, possessions, consumption, injury, and continuity constraints, and are subject to false positives/negatives in ambiguous prose or actor attribution.
3. Pinned exact quotes protect literal text, not all implied causality or downstream consequences.
4. These tests do not compare artistic quality, coherence of a real newly generated ~1,000-character scene, or consistency across real rewriting sessions.
5. The module is opt-in through a Python writing facade; no new GUI or production deployment, and no successful model-based revision A/B is being claimed.

## V120 prerequisite before paid tests

Implement a small typed **plan-to-prose observation gate** rather than request a second model's self-evaluation: for each intended beat, store typed intended state postconditions; after prose generation independently derive source-anchored candidate events and compare intention vs observed results. Three explicit states: \`OBSERVED_SOURCE_SUPPORTED\`, \`UNPROVEN\`, \`CONTRADICTED\`. Do not auto-complete intended goals from the plan or infer a character's motivations as truth. Preserve ambiguities and negative tests, including mistaken actor assignment (an injured protagonist should not force an unrelated enemy's arm to be considered injured).

Combine with V119: edits may only be proposed as source-locked local patches; run old/new state preflight, retain the old version on failure, require author approval before any canon writes. Creative cues remain optional V118 lamps; do not force templates/turns where no lamp is needed. Compare full-text before-and-after to check for unintended state drift. Test unchanged V113/V114B source in a *read-only* scenario first, then independently assess same-model 1,000-char generated scenes only after finite-budget user authorization.

The immediate objective is an **external execution and verification loop**, not access to a model's true hidden chain of thought.
