# V120 — high-Star architecture review and plan-to-prose execution audit

Date: 2026-10-22. Branch: `v120-plan-prose-source-verification`.
Safe continuation of V119 (`v119-source-locked-revision-transaction`), which itself continues V118. No modification of the stable main branch and no Railway deployment. Existing source artifacts preserved.

## User problem

A model can clearly explain a story plan or revise its own explanations while its actual prose violates its intention, loses ownership/injury state, and grows worse after local edits. Its plan, explanation, and V96 exact quotations must **not** be promoted into independent evidence of an executed change.

The target is a lightweight, source-driven "streetlamp" system:
- Let the author/model choose and change the route, with no mandatory outline beat formulas.
- Before the next beat, light only demonstrably relevant unresolved earlier causal preconditions.
- After generating a candidate paragraph, inspect what was ACTUALLY written and source-anchor evidence; never infer a physical action from a planned action.
- Preserve V119's source-locked local edit rollback boundary.
- Avoid new model API calls, memory bloat, dependency lock-in, and arbitrary long prompts.

## Public high-Star comparison (GitHub API queried 2026-10-22)

| Public repository | Stars at audit | License | Fit / decision |
|---|---:|---|---|
| `mem0ai/mem0` | 67,605 | Apache-2.0 | Layered longer-term memory; **do not install** for V120. Its default memory flow uses LLMs, and memories can include agent-made statements; does not independently verify whether planned prose actions occurred. |
| `langchain-ai/langgraph` | 43,681 | MIT | Adopt idea of isolated, durable state snapshots and human-reviewed acceptance boundaries; **do not replace** WF's existing candidate checkpoint scheme. Workflow/checkpoint durability is not exactly-once external side effect execution. |
| `microsoft/graphrag` | 36,408 | MIT | Helpful graph retrieval ideas, but upstream says maintenance mode, warns indexing may be costly; **do not install** for event-identity validation. |
| `getzep/graphiti` | 32,118 | Apache-2.0 | Best conceptual fit: event/episode provenance and temporal fact validity rather than flat summaries. Full framework expects graph DB and usually LLM/embedding services; **do not install or run it** under zero-paid-call constraint. |
| `pydantic/pydantic` | 29,132 | MIT | Strict schema/type boundaries; not a solution to ambiguous Chinese action attribution by itself. Builtin validation is sufficient for the bounded V120 typed receipt. |
| `networkx/networkx` | 17,348 | see repository | Useful for graph queries, but not needed to solve source evidence validation and would introduce unnecessary graph infrastructure for V120. |

This is an **architectural comparison**, not a claim that WF imported, installed, trained on, or directly incorporated code from these repositories. The implemented code relies on WF's existing V116 events, V114 pinned MIT Novel Studio reducer and V117 cross-chapter memory, not new external provider calls.

Sources: https://github.com/mem0ai/mem0; https://github.com/langchain-ai/langgraph; https://github.com/microsoft/graphrag; https://github.com/getzep/graphiti; https://github.com/pydantic/pydantic .

## Changes implemented

1. `writerforge/v120_plan_prose_gate.py`
   - `compare_plan_to_prose(project_id,scene_id,beat,prose,cast,prior_candidate_state)`.
   - Only a narrow affirmative *state change subgoal* is compiled from a model's beat goal (resource swallow, teeth-to-palm, explicitly named palm-to-person handoff, right arm limited).
   - The model's goal and `trace.action_quote/trace.effect_quote` are **not** observational evidence. Only prose-referenced, uniquely anchored, present-tense source events from the existing V116 extractor can qualify. A new V120 source clause can also corroborate the SAME explicitly named right-arm state when V116 suppresses redundant updates; it does not create additional canon changes.
   - Validate the active actor before recognizing arm constraints. Reject wrong-character observer clauses, hypothetical/dialogue clauses, ambiguous pronoun patients, and predicate-local negations (not the unrelated "没有停步").
   - For a supported subgoal only, returns one of:
       * `OBSERVED_SOURCE_SUPPORTED`: latest valid quote-supported state matches the planned typed subgoal.
       * `CONTRADICTED`: the latest valid quote-supported state for that cell differs.
       * `UNPROVEN`: no reliable matching source observation, or the plan was ambiguous/unsupported. This is **not automatically a literary failure**.
   - All receipts carry a source hash, beat and goal hashes, brief anchors, scope, coverage, SHA-256 of receipt, no raw private prose, no claim of full scene-goal correctness or literary quality.
   - `pending_dependency_hint()` activates one short optional hint only for a **direct causal child** of a prior type-supported but unfulfilled plan, never compels a rewrite or forces the prior storyline.

2. `writerforge/writing_assist.py`: the already opt-in `continuity_guard` flow invokes V120 **after** V96 accepts a source-anchored candidate turn and **before** that candidate contributes the next temporal state. Adds source-only records to the old `v96_turn_evidence.json` and optional, bounded direct-dependency cue to the next turn. No extra LLM call, no new DB or R2 write.

3. `tests/test_v120_plan_prose_gate.py`: synthetic adversarial tests for swallow vs bite/spit, actor attribution, stale inventory handoff, pronouns, dialogue, quiet scenes, source quote hashes, previously skipped unchanged-value arm corroboration, narrowed negation scope and actual WF call-site.

4. `experiments/v120_readonly_plan_prose_cold_audit.py`: reads exact historical original R2/CAS text, validates SHA, never prints the original, never generates a second scene, never modifies source, and tests that historical false success remains false.

5. `.github/workflows/v120-plan-prose-source.yml`: zero-provider whole repository regression and separate R2-CAS **read-only** frozen-source audit, no model credentials in either test job.

## Verified real-source outcomes

Codeful CI run **completed success**: https://github.com/66tyu55/WriterForge/actions/runs/39719701886
- Full suite: 1,285 tests ran, 4 skipped, zero failures.
- Sealed R2 cold audit: passed; V113 original 951 characters, SHA-256 `339b2b1cab1e4895ed73d4e8ef73ed0b51c6adb832149cd097c35b0ec9b585f7`.
- V114B original 964 characters, SHA-256 `c5146b829348ea12724290550ab8d4b4d959f2c1aaa41459c38bdeef757ad166`.
- Intended **沈砚吞下火髓果**: `CONTRADICTED` (real text leaves fruit unconsumed, at latest supported holder).
- **唐蜃吞下火髓果**: `UNPROVEN`; no false transfer of protagonist resource event to antagonist.
- **沈砚右臂受限**: `OBSERVED_SOURCE_SUPPORTED`, thanks to later explicit protagonist/arm narration and independent corroboration of an unchanged state. **唐蜃右臂受限** not falsely source-confirmed.
- Unproven historical V113 sword tassel transfer remains `UNPROVEN`, under the separate V117 continuity debt logic.
- No new second scene, no new literary model requests, no canon writes, no R2 writes, no novel text revisions, and **no proof of actual creative-writing quality improvement**.

During development, CI caught a real overbroad negation bug: **“右臂垂着，却没有停步”** wrongly failed when negation applied to an entire sentence. This was corrected to bind negation to the injury predicate, then complete CI was rerun green. Historical red runs remain visible; do not hide them.

## Important remaining gaps

- These typed checks cover **very few** Chinese state constructions: no universal co-reference, indirect discourse, metaphors, nonlocal intent, full narrative outcome, creative quality or general injury recovery support. Mark unknown rather than invent ground truth. Tests passing prove the narrow software behavior only.
- The V116 next-prose preflight still contains actor-agnostic right-arm matching for some patterns; investigate in a separate defect-scoped test rather than equating its `findings` with V120's independently anchored verdict.
- Source evidence receipts are candidate information; model prose does not become verified canon until author acceptance.
- Long-term unreconciled candidate goals should not grow forever; V120 confines direct-dependency cues to recent bounded turns. Fully durable unmet **intent** tracking remains future work.
- Optional cue insertion shares the main writing-context char cap; if approaching budget, drop optional literary cues before removing hard state/continuity checks. Needs targeted prompt-pressure regression before any actual model A/B.
- Original frozen V114B failure of the old 950-char prose validator remains an original **964-character rejected first scene**; do not claim a second segment exists or that literary quality improved.
- No dependency/package upgrade or Railway deployment was performed. Security/credential rotation after Railway's 2026-10-21 disclosure is a separate operations priority.
- Under prior constraints no paid model is called: actual same-model >1,000-character artistic A/B remains not yet tested.

## Next recommended gated step

Defect-based V121: (1) eliminate actor-agnostic arm preflight in V116 with per-character provenance tests, (2) pressure test prompt budget with optional-lamp dropping instead of hard failure, (3) only then consider explicit budgeted same-model creative A/B with independent literary assessment. Do not read many extra novels in bulk or claim that checking produces model-weight training.
