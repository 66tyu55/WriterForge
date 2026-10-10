---
name: writer-forge-v23-2
description: >
  Long-form fiction runtime with Reader-First source learning, reactive lane scheduling,
  dependency-driven context loading, controlled self-evolution, story-sense routing,
  embodied scene causality, and pairwise literary taste. Designed for novels, not generic copywriting.
---

# WriterForge V23.2

WriterForge is a long-form fiction writer system. LEARN and WRITE remain mutually exclusive.

## Runtime rule

Capability library size must not determine per-turn cost.

WriterForge V23 schedules work as:

`App Shell -> Route -> Dirty Feature Chunk -> Background Worker`

Lanes:
- `SYNC`: runtime/snapshot/commit correctness
- `DRAFT`: sentence continuity
- `REACTIVE`: Xuehai/memory/craft routing caused by real deltas
- `BOUNDARY`: scene/chapter checks for dirty domains only
- `TRANSITION`: interruptible Reader/Taste/reviewer work
- `OFFLINE`: LEARN synthesis, full-book audit, evolution

Several state changes in one logical turn are batched. Newer scene/chapter generations may discard stale transition/offline work. Expired background work receives starvation protection.

Do not use old-style event object pooling. Batch event meaning; do not recycle event objects.

## LEARN / WRITE separation

- LEARN reads sources sequentially, first as a spoiler-blind reader, then studies craft/effect and publishes versioned Xuehai snapshots.
- WRITE pins one published Xuehai snapshot and never mutates Xuehai.
- Project experience, taste, reader feedback and failures remain separate from source evidence.

## Scene-time Craft

Craft remains five groups only:
- Dialogue Action
- Perception & Description
- Cognitive Motion
- Narrative Restraint
- Scene Turn & Rhythm

At scene planning or relevant dependency change, select 0-2 technique cards and freeze a Scene Craft Contract. Reuse it until a dependency actually changes.

## Embodied Scene Causality

Sound, temperature, touch, smell and bodily manifestation are consequences of environment + entity + action/contact + established embodiment. They are not separate sensory Skills or quotas.

## Literary Taste / Story Sense

Taste is pairwise and used only for hard choices between valid alternatives. Story Sense selects the dominant literary problem rather than activating every reviewer.

## Evolution

Evolution is OFFLINE. Promotion requires failure evidence, held-out/transfer/regression gates, runtime-cost checks, and human/real-reader anchoring for subjective literary capability.

## Commit discipline

Planning, simulation, routing, retrieval, review and candidate generation are discardable compute.

Only Commit Boundary mutates accepted prose, Canon, Character State, Promise State, Motif State or long-term project memory.

`Compute twice is okay. Commit twice is a bug.`


## Event Priority + Lane Root

Business events expose only four urgency levels: `DISCRETE / CONTINUOUS / DEFAULT / IDLE`. Capability execution still uses the seven WriterForge lanes.

Each logical root may track `pending / suspended / pinged / warm / expired / entangled` lanes. Missing evidence suspends work instead of forcing retries; arriving evidence pings the lane. Semantically coupled updates may be entangled so Character/Knowledge/Reader state cannot expose a half-updated logical version.

Event priority orders source events; it does not promote expensive Reader/Taste/Offline work into synchronous execution.


## Story Work Tree

Book/Arc/Chapter/Scene capability state is organized as a lazy work tree. Each node has own lanes plus aggregated child lanes. A local change bubbles only through its ancestor path; unrelated sibling subtrees can bailout.

Rendering uses a reusable current/workInProgress double buffer. Begin/complete phases are compute-only. The finished computation tree may replace current only after the outer durable Story Commit succeeds. Rejected candidates discard WIP with zero durable side effects.


## Runtime hardening

Pending story updates are lane-specific. Reject removes rendered pending state and speculative buffers. Reactive caches are bounded; invalidated in-flight results cannot re-enter cache as fresh. V18 explicitly does not claim durable persistence is transactional yet.


## Transactional Story Commit

Production WRITE mutations must be represented as StoryEffect values and committed through StoryCommitCoordinator. The coordinator validates the whole bundle, opens one SQLite transaction, writes all story state + audit events + durable commit receipt, commits, and only then adopts the matching finished WorkTree.

Direct StoryStore mutators are legacy/backward-compatible APIs, not the production accepted-story commit path.


## V20 WorkTree Restart Discipline

Only a finished, fingerprint-bound WorkTree may be committed alongside StoryEffects. The coordinator checkpoints that accepted tree atomically with the SQLite receipt. Call `restore_work_root(db, project_id)` on restart; do not treat a previous WIP or stale receipt as accepted state. Rehydration restores pending lanes and topology but intentionally drops speculative alternates and volatile scheduler clocks. Non-JSON-native computation states are rejected before commit. After rendering is finished, hold new events in the batch queue until commit/reject, then schedule them on current. Commits without WorkTree invalidate checkpoints and require project-driven rebuild.


## V21 Growing Writing Companion — passive by default

The companion is NOT a separate Skill to invoke when the writer wants a voice check. On every changed accepted prose commit, StoryCommitCoordinator accumulates a small, durable project-local rhythm observation in the same transaction; unchanged and rejected candidates add nothing. Only explicit author_written/author_edited provenance counts as author voice, while default/assistant_generated acceptance counts only as weak story-rhythm evidence. Author corrections are SET_AUTHOR_PREFERENCE StoryEffects, versioned and removable. The writing shell constructs WritingFlow once and automatically supplies companion guidance via begin_draft(scene_id, concerns=...), then calls accept_draft at its ordinary acceptance boundary. Revisions of the same scene replace rather than multiply the active voice sample; deleted scenes retract it. There are at most 32 distinct active-scene samples and 64 explicit preferences. It caps guidance, avoids raw prose re-ingestion, and caches across unchanged revisions. This is a growing, bounded context system, NOT training model weights or self-generating new capabilities. See companion/GROWING_WRITER_LOOP.md.


## V22 evidence and preference conflict discipline

A single SET_AUTHOR_PREFERENCE table remains the sole authority for explicit writer preferences. AuthorCorrection optionally carries evidence_scope + evidence_excerpt (verified against same-project accepted prose, stored only as hashes), axis (plot / creativity / character_emotion / language), and conflict_group (unique per project+category). Supported guidance is suppressed if its source is rewritten; stale rules are **reviewed, not automatically repaired**. Explicit same-slot conflicts reject the whole transaction, never silently choose a winner. WritingFlow.review_writing_sheet() is read-only diagnosis; the original StoryCommitCoordinator is still the only persistence route. Do not confuse stylistic suggestions with canon/plot mutations, and do not infer a writing sheet axis from statistics without explicit author confirmation. See research/EXTERNAL_METHODS_V22.md.


## V23 Original Chinese Study + Verifiable Writing (operational route)

Production novel research must go through the V23 executable CLI and real published Xuehai snapshots: fetch-xiyouji -> learn -> status -> draft-context / draft via a real local model -> author-accepted StoryCommit. A mere ChatGPT-authored prose sample is NEVER labeled a WriterForge generated test. Source study includes 100 original Chinese 西遊記 chapters, sequentially ingested with SHA256 and eight deterministic structural tracks; it does NOT invent first-read emotional responses or fine-tune model weights. Each snapshot after root is delta-only, with bounded SQL candidate retrieval. The sole independent reviewer is local lit-critic REST; require its real running local endpoint, export read-only Markdown/JSON with source hashes, and never auto-modify canon or train on unverified criticism. Enforce the queue, checkpoint, source-unit, response, and cache caps documented in docs/V23_REAL_ORIGINAL_STUDY_AND_REVIEW.md.


## V23.1 Xuehai remote persistence

Persistent corpus training is NOT a chat attachment workflow. Approved public-domain source studies are published automatically on verified main CI to source-hash + schema-versioned GitHub Releases with SHA256 manifests; automatic restore verifies all files, SQLite integrity and chapter/source metadata. Existing local novels and DBs are NEVER overwritten, and ephemeral Actions Artifacts are not long-term storage. No private/third-party copyrighted manuscripts may be published to the public release route. Use the new restore-xiyouji CLI to load the checked library. Details in docs/AUTOMATED_STUDY_STORAGE.md.


## V23.2 private R2 study persistence

Do not treat ZIP chat attachments or short-lived GitHub Actions artifacts as durable personal study storage. After explicit private R2 authorization, `backup-r2` uses a consistent SQLite online backup, versioned SHA256 objects, immutable manifests, and a verified latest pointer; `restore-r2` refuses corrupt/oversized data and never overwrites local author DBs. Local training can opt into automatic R2 backup with WRITERFORGE_R2_AUTO_BACKUP=1. Repeated unchanged original-learning editions are deduplicated using a streamed semantic checksum, while changed excerpts produce a new snapshot. The R2 publish job is enabled only on trusted main builds with complete configured credentials. Never upload private manuscripts to the existing public GitHub Releases channel. See docs/CLOUDFLARE_R2_PRIVATE_STORAGE.md.
