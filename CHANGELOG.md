# Changelog

## v22.0.0 — 2026-10-08

- Borrowed externally verified ideas from novel-studio, Author Writing Sheet research and Calliope without copying source or adding redundant skills.
- Extended the existing author preference store with optional current-prose evidence anchors, four human-curated writing-sheet axes and explicitly named conflict groups.
- Stale accepted-prose anchors no longer reach future draft prompts; audits are read-only, and explicit author guidance remains compatible.
- Added atomic evidence checks after prose acceptance, whole-transaction rollback on failed evidence/group collisions and additive V21-to-V22 schema migration.
- Preserved single-path preference priority, bounded prompts, original WorkTree and LEARN/WRITE isolation.
- Added regression tests for source revisions, conflict resolution, old databases, project isolation and no-write review.


## v21.0.0 — 2026-10-08

- Added project-local WritingCompanion with bounded accepted rhythm and stronger author-edited voice provenance; new scene revisions replace their old samples.
- Automatically updates companion evidence in the accepted StoryEffect SQLite transaction; replay and rejection do not learn.
- Added explicit versioned SET_AUTHOR_PREFERENCE actions to remember, revise, or delete writer corrections.
- Added bounded 32-scene active sample ledger, 64 per-project preference slots, limited prompt assembly, and version-aware LRU read cache.
- Added WritingFlow host facade so the companion can ride the normal begin_draft / accept_draft cycle without a user-triggered Skill.
- Preserved LEARN/WRITE Xuehai separation; no model-weight fine-tuning or speculative prose learning.
- Added restart/rollback/provenance/cache/isolation tests, safety tests for immutable metrics and whole-rule truncation, and a concise host-wiring protocol.
- Added a GitHub Actions micro-benchmark for bounded samples, context reuse and SQLite cost.


## v20.0.0 — 2026-10-08

- Added one durable WorkTree checkpoint per project, in the accepted StoryEffect transaction.
- Added checksum/fingerprint/receipt-bound rehydration after process restart.
- Preserved Book/Chapter/Scene topology, accepted memoized state, and outstanding per-lane pending work.
- Rejected non-JSON-safe tree state before a durable transaction and stale checkpoint restoration.
- Blocked post-render updates from being silently lost during WorkTree adoption.
- Prevented foreign-node scheduling from dirtying another tree and cleaned up speculative buffers on render exceptions.
- Prevented stale WorkTree replay and stale restored-head commits.
- Added V20 restart, replay, rollback, corruption and lifecycle regression tests.


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
