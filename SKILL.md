---
name: writer-forge-v27
description: >
  Long-form fiction runtime with Reader-First source learning, reactive lane scheduling,
  dependency-driven context loading, controlled self-evolution, story-sense routing,
  embodied scene causality, and pairwise literary taste. Designed for novels, not generic copywriting.
---

# WriterForge V27

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


## V24 — Chinese original source admission + execution evidence

Approved Chinese historical literary originals (not translations) can be downloaded via fetch-classic, verified against their exact GITenberg Git blob source, and studied in isolated SQLite with learn-classic. For Honglou, strict 120 chapters; Shuihu uses original 70 chapters plus real 楔子. Never mark partial or ambiguous chapter boundaries as completed. Track and audit which craft/Reader-First/evaluation skills ACTUALLY executed, and label pure keyword eight-track evidence as deterministic and unverified. Only post-verified GitHub main CI backs up each work to the private R2 bucket and restores to test provenance. Corpus progress counts 50 *distinct completed works*, NOT 50 chapters or many source spans. No global literary assessment/automatic evolution promotion until the 50-source gate has been met. See docs/V24_CHINESE_CORPUS_AND_STAGE_AUDIT.md.


## V25 — Faceted original-novel encyclopedia

Actual purpose: from an original source, preserve entities, typed characteristics, and ALL their source-backed occurrences under hierarchical shelves (`外貌/妖兽/虎形`, `性格/人物/...`, `地点/独特地点/...`, `设定/玄幻/榜单`, `设定/玄幻/雷劫`), NOT replace thousands of observations with one general paragraph. A work-specific subject card has kind, genre, subtype and where relevant verified gender; every evidence row retains exact source chapter/paragraph/sentence and its unmodified original quote/hash. Raw keywords are PROPOSALS and **cannot** be used as verified semantic categories or rewriting prompts. A human confirms each specific annotation; no misfiled beast into place, ordinary 野兽 as 妖兽, or unknown-gender person as 女性. Use `encyclopedia-*` CLI; new `--reference-category` and `--reference-name` can enter actual verified draft context and manifests. Modern copyrighted private Drive files must never be put in public repo or GitHub Releases. The 50-distinct-works global analysis remains deferred. See docs/V25_FACETED_ENCYCLOPEDIA.md.


## V26 runtime contract: invisible assistance, not manual retrieval

When user is composing in our WriterForge Studio, browser input/debounce is the REAL trigger; do not pretend this Python Skill can monitor arbitrary third-party editors. New InvisibleWritingAssist infers tentative writing direction internally from author prose, obtains published Xuehai scene context and V25 strictly human-verified encyclopedic facts, routes to CraftEngine with existing trigger names, invokes a locally configured model, and returns exactly two different original prose options. Suggestions must never mutate the manuscript until the author explicitly chooses one; an author's choice is only a bounded weak signal, not a verified style upgrade. AutonomousWriting receives a real outline and per-chapter objectives, plans goals/conflict/decision/outcomes, invokes the same source-grounded writer and local model, saves each actual draft with provenance and never auto-accepts AI prose. No 50-work global literary assessment or unapproved copyrighted source upload is authorized. See docs/V26_INVISIBLE_WRITING_STUDIO.md.


## V27 trained-source literary curriculum: fail closed before creativity claims

For autonomous writing capability refinement use the existing Xuehai + V25 Human-Verified category evidence and the literary ladder rather than expecting source chunk statistics to imply literary mastery. Work from exact source spans -> 12-65-character original short units -> one verified category -> two distinct semantic roots -> three+ distinct roots -> paragraph -> causal scene, increasing complexity only when the source gates are satisfied. Model category annotations remain UNVERIFIED proposed hypotheses until independently checked. The real local LLM produces candidate text; optionally the existing lit-critic produces an independent editorial report on paragraphs/scenes, followed by no more than ONE logged revision. Critics and author feedback are NOT automatically treated as permanent Skill promotions or proof of artistic gain. Store every accepted and rejected practice attempt in the EXISTING SQLite and private R2 backups, not a competing learning store. Stop after 400 trials/project until archived. No 50-book global literary evaluation yet. Details in docs/V27_STAGED_LITERARY_PRACTICE.md.
