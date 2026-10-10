# Changelog

## v23.2.0 — 2026-10-10

- Cloudflare R2 private object storage support (optional boto3 dependency), with S3-compatible endpoint, bucket-scoped keys and explicit environment-only credentials.
- WAL-safe online SQLite backup, immutable content-addressed blobs, SHA256-verified manifests, small latest pointer and integrity-checked restoration without overwriting any existing database.
- Added `backup-r2` and `restore-r2` CLI commands, plus opt-in R2 sync after successful `learn` / accepted drafts (`WRITERFORGE_R2_AUTO_BACKUP=1`).
- Added network-independent mocked-S3 regression coverage for repeated backups, remote tampering, WAL commits, old version restore, unsafe paths and no-clobber safety.
- R2 actual bucket and credentials require account-owner authorization; no secret or personal corpus is stored in GitHub source or Releases.


## v23.1.0 — 2026-10-10

- Replaced manual/expiring GitHub Actions-only corpus delivery with automated, versioned GitHub Releases for the approved original-Chinese 西遊記 dataset.
- Main-branch-only publishing job gets minimum needed release-write token; PR source code has no release publishing rights.
- Added content-addressed source tag, compressed study archive, independent per-file SHA256 manifest and independent remote-download/SQLite integrity validation.
- Added Python standard-library restore-xiyouji command that automatically retrieves the latest matching verified Release, with no CLI token required for a public repository and no overwriting existing author databases.
- Added bounded archive extraction and path traversal protection, idempotent verified local cache, synthetic 100-chapter packaging/corruption tests and human-readable operating guide.
- Reserved private R2/S3 style object storage for future licensed/private multi-novel corpora rather than unintentionally publishing author data.


## v23.0.0 — 2026-10-10

- Added a real and resumable source-learning CLI for original Chinese 西遊記 (Gutenberg #23962), with sequential 100-chapter study and independently verified SHA256 provenance; no fabricated real-reader reactions.
- Added eight separate source-span structural tracks, literature-unverified labels, and a downloadable GitHub Actions original-corpus + SQLite + grounded-context artifact.
- Replaced quadratic child snapshot copying with legacy-safe delta ancestry and bounded SQL candidate retrieval; reduced SQLite page cache and kept temporary query data on disk.
- Added verified source-grounded writing context and actual loopback LM Studio / OpenAI-compatible generation, plus candidate manifests and explicitly confirmed author commits.
- Integrated exactly one external reviewer: lit-critic local REST, creating read-only Markdown/JSON reports only for verified new sessions; live provider credentials remain external.
- Restored project TasteMemory/SkillRegistry/EvolutionEngine data from durable SQLite and bounded fallback state, reader trajectories, review feedback, event batches, task queue, and WorkTree JSON.
- Added 100-chapter full source CI job, Windows operation instructions and safety regressions. Model fine-tuning, expert literary understanding and human review have NOT been performed.


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
