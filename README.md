# WriterForge V23.1 — Real Original-Chinese Study, Verified Writing & Durable Storage

WriterForge is a long-form fiction system built around strict LEARN / WRITE separation, Reader-First source learning, Canon/Character/Knowledge/Promise memory, lean Craft routing, Literary Taste, Story Sense and controlled Evolution.

V16 continues the runtime optimization phase. It separates source-event urgency from capability execution lanes and adds root-level pending/suspended/pinged/warm/expired/entangled state.

## V15: SPA-style capability loading

The whole capability library no longer implies a whole-runtime load:

```text
App Shell
  -> current LEARN/WRITE route
  -> dirty feature chunks only
  -> interruptible background/review work
```

The new lane model is inspired by React's cooperative scheduling ideas:

```text
SYNC -> DRAFT -> REACTIVE -> BOUNDARY -> TRANSITION -> OFFLINE -> IDLE
```

Key behavior:
- lane priorities are bitmasks;
- same-turn events are batched by scope;
- deep scene/chapter audits require matching dirty domains;
- Reader/Taste/broad review can yield to more urgent work;
- stale transition/offline work is discarded when a newer scene/chapter generation supersedes it;
- low-priority work eventually expires and receives starvation protection;
- existing dependency cache, singleflight and idempotent Commit remain separate layers.

This fixes an earlier weakness where scene/chapter budget competition could be influenced by capability ordering instead of story relevance.

## Literary architecture remains lean

Craft still has only five groups and activates at most 0-2 groups for a scene. Evolution remains offline. Embodied Scene Resolver produces causal perceptual facts rather than sensory quotas. Ending Backtrace, Orthogonal Originality and Observed Story remain boundary/revision mechanisms rather than always-on agents.

## Core invariants

`No Change -> No Recompute`

`One Change -> Only Dependents Recompute`

`Same Request -> One Execution`

`Stale Transition -> Discard`

`Rejected Candidate -> Zero Side Effects`

`Accepted Candidate -> One Commit`

## Tests

Run:

`python -m unittest discover -s tests -q`

GitHub CI executes the full repository suite for V15 changes.


## V16: Event Priority + Root State

```text
Business Event
-> EventPriority (4 levels)
-> Event Batch
-> Dirty Domains
-> Capability Lane (7 lanes)
-> Lane Root State
-> Cost-sliced Task Queue
```

Event priority is intentionally smaller than the execution model: callers classify urgency without learning scheduler internals. Blocked work can suspend and later be pinged; related literary state can be entangled; lower-priority arrivals do not automatically throw away useful work in progress.


V16 GitHub CI regression: **107 / 107 passed**.


## V17: Story Work Tree

V17 adds a Fiber-inspired but fiction-specific work tree:

Book -> Arc -> Chapter -> Scene -> capability nodes

A dirty leaf marks its own lane and bubbles child_lanes only through ancestors. Begin work can bailout an unchanged subtree; complete work bubbles surviving lanes upward. The accepted computation tree and speculative work-in-progress tree are double-buffered and the alternate is reused.

This tree remains compute-only. It does not mutate accepted prose or Canon, and swapping current is allowed only after the existing outer Commit succeeds.

V17 GitHub CI regression: **116 / 116 passed**.


## V18

Closes compute-side lifecycle leaks: per-lane pending updates, reject cleanup, bounded caches, stale-inflight protection, aggregate event batching, queue scope cleanup, and suspended-entanglement guarding. The remaining closure gap is transactional durable StoryEffect commit.

V18 GitHub CI regression: **126 / 126 passed**.


## V19: durable commit closure

Accepted prose and its associated Character/Canon/Promise/Reader/Causality changes now have an atomic StoryEffect path. Effect bundle, story events, effect journal and durable commit receipt are committed in one SQLite transaction. WorkTree adoption is bound by finished-work fingerprint and occurs only after the durable commit succeeds.

A failed transaction rolls everything back and preserves current pending work for retry. Replaying the same commit after process interruption is idempotent from the durable receipt.

V19 GitHub CI regression: **135 / 135 passed**.


## V20: Crash-safe WorkTree Recovery

V20 writes a JSON-native accepted WorkTree checkpoint inside the same SQLite transaction as its StoryEffect receipt. After restart, `restore_work_root(db, project_id)` verifies the latest receipt, checksum, topology and finished fingerprint before restoring the tree and pending lanes. No speculative alternates survive restart.

A rootless story commit invalidates the previous checkpoint; an older receipt cannot adopt a stale tree. A failed computation discards its speculative buffer without losing pending updates, and a node from another tree is rejected before any mutation. To avoid losing late events, the WorkTree refuses `schedule_update` between finished render and commit/reject (batch late events and schedule them on the next current root). A stale recovered root is rejected at commit time.

See `reactive/WORKTREE_CRASH_RECOVERY.md` for guarantees and limitations. Run `python -m unittest discover -s tests -q` for V20 coverage.


## V21: passive growth as you write

WriterForge now has a bounded, project-local companion profile that updates **inside the normal StoryCommitCoordinator transaction** when accepted prose changes. It records deduplicated weak accepted-prose rhythm from up to 32 distinct active scenes separately from high-trust author-written/edited samples; a merely AI-generated draft never becomes evidence of the author's own voice. Explicit author corrections use SET_AUTHOR_PREFERENCE StoryEffects and can be changed or forgotten. The host uses WritingFlow.begin_draft / accept_draft on its usual writing path (or WritingCompanion.before_draft in an existing shell), so there is no extra user-facing Skill invocation. Only a compact set of relevant instructions and (when supported) a tentative voice rhythm enters the next scene.

No raw prose is copied into companion memory; replaced/deleted scenes retract their old style samples, profiles are project isolated, cache/instruction counts are bounded, and failed/duplicate commits do not grow the profile. This is deterministic evolving context, not continual model training; claims about creative quality or faster prose generation require separate user/reader evaluation. CI also executes eval/companion_benchmark.py to track SQLite/context overhead and bounded active samples; it is not an LLM speed benchmark. See companion/GROWING_WRITER_LOOP.md.


## V22 — Learn externally, keep one authority

Inspired by real novel-studio routing conflicts, the IJCNLP-AACL evidence-oriented Author Writing Sheet, and Calliope's read-only editorial practice, V22 adds **optional evidence anchors, explicit category conflict slots and a four-axis author-curated writing-sheet view** to the existing SET_AUTHOR_PREFERENCE store. A source excerpt must exist in accepted prose for the same project, and a changed/deleted source makes its anchored guidance stale; review reports this without rewriting the story. Specific scene rules rank ahead of generic guidance inside the existing budget. V21 databases are migrated additively; no duplicate memory store, lane scheduler or third-party plug-in is added.

See research/EXTERNAL_METHODS_V22.md for original sources, rejected ideas, and precise limitations. Real creativity/reader quality remains a separate evaluation question.
 

## V23 — Executable original Chinese literary study, not just an architecture

WriterForge now ingests the complete original traditional-Chinese 100-chapter 西遊記 from Project Gutenberg #23962, preserving source hashes and sequential chapter/paragraph/sentence provenance. Each original sentence receives eight separate **deterministic, UNVERIFIED** structural tracks. 100 published chapters use one full snapshot and 99 ancestry-resolved deltas, avoiding per-chapter full database copies. Original source, durable SQLite data, license, structural study report and a verifiable draft context are packaged by GitHub Actions; the underlying repo deliberately excludes the licensed release text and SQLite.

An executable command-line path is now available: fetch-xiyouji -> learn -> status -> draft-context -> draft using an explicitly running **local** OpenAI-compatible LM Studio model -> accept with explicit author confirmation. The drafted artifact records snapshot, source citations, model and checksums; a new draft is never silently accepted or mislabeled as author-written. The only external evaluator integration is the **local lit-critic REST API**. It emits a separate read-only Markdown + JSON review report with the verified current text hash. No AI review automatically modifies canon or promotes writing skills.

Memory fixes bound SQL retrieval, SQLite cache, reader/evolution/taste histories, queued events, task queue, and WorkTree snapshot sizes. CI runs real full-100-chapter downloads/ingestion, restart retrieval, a resource report and legacy regressions. Reader-first deep literature analysis, fine-tuning, real local model runs and genuine live lit-critic ratings **are not claimed yet**.

**Detailed Windows commands and setup:** [V23 real Chinese-original study, writing and review](docs/V23_REAL_ORIGINAL_STUDY_AND_REVIEW.md).


## V23.1 — Training resources are preserved automatically, not manually

The original Chinese 西遊記 training job now produces a **durable versioned GitHub Release** after successful main-branch validation, with a compact ZIP **inside GitHub**, a separate SHA256 manifest and a second CI job that downloads and validates the published database and sources. GitHub Actions Artifacts are only short-lived job-to-job transport. Run `writerforge --db writerforge.sqlite3 restore-xiyouji` on a new computer to fetch, verify and restore the learning database without saving/uploading a ZIP by hand. An existing local database is never overwritten. Publishing remains restricted to the known Gutenberg public-domain edition; private manuscripts must not be uploaded publicly. Details: [Auto-persist Xuehai studies](docs/AUTOMATED_STUDY_STORAGE.md).
