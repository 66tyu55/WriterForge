# WriterForge V27 — Source-grounded Faceted Literary Encyclopedia

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


## V23.2 Cloudflare R2 private corpus vault

A real Cloudflare R2 S3-compatible storage backend is now implemented behind optional boto3 support (`python -m pip install -e '.[r2]'`). It takes an **online, WAL-safe SQLite snapshot**, streams its content and optionally an original source/report into a **private, content-addressed bucket**, validates SHA-256 metadata, stores an immutable manifest, and updates a latest-pointer only after verification. The restore command verifies every object and SQLite integrity before creating an isolated version folder. Existing author databases are never overwritten. Reproducible CI learning editions use a streamed logical-study hash to avoid growing 65 MiB with every identical run. The existing public Gutenberg Release remains a separate allowed-source mirror; **private manuscripts must never go to that public location**.

Commands: `writerforge --db writerforge.sqlite3 backup-r2 --library writerforge-personal` and `writerforge --db writerforge.sqlite3 restore-r2 --library writerforge-personal`. On local learning, opt in once with `WRITERFORGE_R2_AUTO_BACKUP=1`; no-op learning will not reupload, and accepted-scene frequent backups require separate explicit opt-in. A GitHub Actions job automatically mirrors validated 100-chapter source learning to private R2 on trusted `main` builds **only after Cloudflare R2 credentials are provisioned as GitHub Secrets**. Without those account permissions this remains tested code, not a claim of a live cloud connection. Setup: [Private Cloudflare R2 storage](docs/CLOUDFLARE_R2_PRIVATE_STORAGE.md).


## V24: continue learning original Chinese works with measurable execution

The verified source catalog adds Project Gutenberg original-language **紅樓夢 (120 chapters)** and **水滸傳 (70 chapters + genuine prologue 楔子)** to earlier 西遊記 (100 chapters). Public-domain source editions are pinned to precise GITenberg Git blob checksums, and each runs a full chapter-ordered training CI job with separate SQLite and private R2 backup + restore on trusted main. Fixed bugs discovered only with real source text: CRLF headings, narrative phrases such as 第四回中 misrecognized as headings, duplicate ch45 printed header, and hard-wrapped lines mistaken for paragraphs.

Every book now emits structured stage auditing: which reading/storage/retrieval functions truly ran and which subjective skills *did not* run. **These are source indexing traces, not model parameter training or literary-quality scores.** Use `writerforge catalog`, `writerforge fetch-classic --work honglou`, `writerforge learn-classic --work honglou --source ...`, and `writerforge corpus-progress --remote-r2` (with local R2 credentials) to view verified *distinct* works toward the 50-source threshold. Neither premature global literature synthesis nor skill promotion is performed in V24. Details: [Chinese corpus and stage audit](docs/V24_CHINESE_CORPUS_AND_STAGE_AUDIT.md).


## V25 — What the author can now ask the corpus for

A learned work is not merely 50,000 disjoint sentences. V25 adds a durable, hierarchical **source-evidence encyclopedia**: `genre -> 外貌/性格/地点/设定/行为/声音/... -> specific beast/person/place/setting -> each original cited description`. The same original 妖兽 appearing dozens of times retains every separately evidenced trait or event, not one overwritten summary. Subject identity is scoped to work; category mismatches (a 野兽 claimed 妖兽, a character claimed a place, unknown-gender treated as 女性) are refused. All annotations start `proposed` and must pass explicit item-by-item human review before the actual authoring flow can retrieve them. R2 snapshots include categorized content and review status in their semantic versioning digest, and browsing is paginated (max 100 per page) rather than loading all occurrences into RAM. Use `writerforge encyclopedia-entity`, `encyclopedia-observe`, `encyclopedia-review`, `encyclopedia-find`, `encyclopedia-subjects` and `draft-context --reference-category ...` (see full commands and limitations in [V25 docs](docs/V25_FACETED_ENCYCLOPEDIA.md)). Modern copyrighted Drive novels are NOT included in the public code or Releases. Deep semantic classification is still a verified editorial step rather than magic keyword inference; the 50-distinct-book overall quality gate is unchanged.


## V26 — WriterForge now assists while the author types (no manual library search)

A real local writing studio captures editor input, pauses for 900ms, routes intent through existing CraftEngine / published Xuehai / **human-verified V25 encyclopedic evidence only**, and asks your explicitly configured local model to produce TWO distinct, optional original prose continuations. The author inserts one with a click or ignores both; the original text is never rewritten automatically. Draft autosaves locally on each change. A second mode accepts an outline and 1–6 chapter goals, plans each chapter's objective, conflict, decision, consequence and POV, then saves genuine model-generated chapter drafts plus their original-source/craft trace. Nothing is silently promoted to author style or accepted StoryCommit. There is NO separate corpus-search panel for ordinary writers.

Start after restoring a published source-learning SQLite and loading a local LM Studio model:

    python -m pip install -e .
    writerforge --db corpus/library/your-studied.sqlite3 studio --project novel --scene c1.s1 --goal "An honest character must make a hard choice" --model "your-local-model-id"

Open http://127.0.0.1:8765/ . This observes **typing inside its own editor**, not in arbitrary Word/ChatGPT/Google Docs forms. The 900ms debounce is not a model-generation time guarantee. The old source indexing is still structural rather than deep literary training. See [V26 writer studio](docs/V26_INVISIBLE_WRITING_STUDIO.md).


## V27 pilot — graded literary practice before claims of writer-level ability

The real autonomous-draft pipeline remains available, but a genuine author cannot be obtained by merely indexing tens of thousands of novel sentences. The new developer-only literary ladder starts with original-source short-unit analysis (exact quote verification, label as unverified), then requests one human-reviewed category, two categories, three-plus categories, complete paragraphs and causal scenes. **Unreviewed lexical tags cannot unlock complex composition.** Outputs, rejected analyses, source evidence, model ID, hashes and optional independent lit-critic report / one revision are persisted in the existing local SQLite. No fake literary scores, model-weight fine-tuning or automatic skill advancement. Original Chinese source CI now records which stages are really ready and uploads the blockers to private R2. Run the internal readiness inspection before any live local model practice; the author-facing UI is not forced to select shelves. Details: [V27 graded literary practice](docs/V27_STAGED_LITERARY_PRACTICE.md).
