# Changelog

## v19.0.0 — 2026-09-24

- Added StoryEffect and StoryCommitPlan.
- Added accepted_prose, durable story_commit_receipts, and story_effect_journal tables.
- Added BEGIN IMMEDIATE all-or-nothing story transactions.
- Added persistent idempotent commit replay and commit-id collision rejection.
- Bound WorkTree adoption to finished-work fingerprint and durable commit success.
- Added rollback/retry behavior and transaction failure regression tests.
- Marked direct StoryStore mutators as legacy for production accepted-story writes.


## v18.0.0 — 2026-09-24

- Hardened WorkTree pending updates, rejection cleanup, cache bounds, event batching and task-scope cleanup.
- Prevented invalidated in-flight computations from caching stale results.
- Prevented suspended entangled lanes from partial rendering.
- Added 100-commit bounded-graph stress coverage.
- Documented the remaining durable transaction gap.


## v17.0.0 — 2026-09-24

- Added Story Work Tree with Book/Arc/Chapter/Scene/capability nodes.
- Added reusable current/workInProgress double buffering.
- Added leaf-to-root lane propagation through child_lanes.
- Added begin-work subtree bailout so unrelated story branches are skipped.
- Added complete-work bubbling of surviving child lanes and subtree activity.
- Added explicit WIP discard and adopt-after-commit boundary; rendering remains side-effect free.
- Added V17 regression tests for double-buffer reuse, local invalidation, bailout and zero-side-effect rejection.


## v16.0.0 — 2026-09-24

- Added four-level EventPriority: DISCRETE, CONTINUOUS, DEFAULT, IDLE.
- Separated source-event urgency from seven execution lanes so business code no longer chooses scheduler lanes directly.
- Same-scope batches inherit the highest source event priority; same-lane tasks use source priority only as a tiebreaker.
- Added LaneRootState with pending, suspended, pinged, warm, expired and entangled lane sets.
- Added transitive lane entanglement for logically coupled story state.
- Added root-level starvation expiration for foreground lanes while OFFLINE/IDLE remain non-expiring by default.
- Added interruption rule that preserves useful work-in-progress unless incoming work is truly more urgent.
- Added V16 regression coverage for event priority, batching, suspension/ping, entanglement, expiration and scheduler inference.


## v15.0.0 — 2026-09-24

- Added lane-scheduled runtime: SYNC, DRAFT, REACTIVE, BOUNDARY, TRANSITION, OFFLINE, IDLE.
- Added dirty-domain routing so character/causality/continuity/reader chunks load only when relevant.
- Added same-turn event batching by scope; this is semantic batching, not legacy event-object pooling.
- Added min-heap cooperative task queue, cost slices, transition yielding, stale-generation discard, dedupe, and starvation protection.
- Changed default chapter boundary routing so Reader/Promise/Memory work is not crowded out by unrelated structural audits.
- Preserved existing ReactiveSkillRuntime singleflight/cache and CommitLedger idempotence as separate responsibilities.
- Added V15 lane scheduler regression tests and GitHub CI for the complete suite.

## v14.0.0 — 2026-09-22

- Added Embodied Scene Resolver: causal perceptual affordances derived from world state, entity properties, action/contact, and character-specific embodiment.
- Kept sound, temperature, touch, and emotion manifestation inside the existing Perception & Description capability rather than creating sensory micro-skills.
- Added POV attention filtering with no five-sense quotas and semantic cues rather than pre-written prose.
- Emotion no longer maps to stock body-language reactions unless a character-specific tendency has already been established.
- Added dependency fingerprinting so unchanged embodied scene state can be reused by the reactive runtime.

## v13.0.0 — 2026-09-22

- Added Ending Backtrace.
- Added Orthogonal Originality.
- Added Observed Story Auditor.
- Added temporal_reordering as an internal Scene Turn & Rhythm technique card.
- Full regression: 72/72 tests passed.

## v12.0.0 — 2026-09-22

- Added reactive skill runtime with dependency fingerprints, selective invalidation, single-flight execution, and commit-once semantics.
- Added Evolution Engine, Literary Taste Engine and Story Sense routing.
