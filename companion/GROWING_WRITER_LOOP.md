# WriterForge V21 — Growing Writing Companion

> It isn't a tool the author stops to invoke. It grows at accepted-story boundaries
> and is quietly available in the next drafting context.

## The loop

    DRAFT (cheap context only)
      -> candidate / author edit / review
      -> ACCEPTED StoryEffect
      -> single SQLite transaction
           ├─ accepted prose + Canon/Character/Reader/Promise effects
           ├─ audit events + durable receipt
           ├─ incremental companion rhythm profile
           └─ explicitly stated writer preferences (if any)
      -> next scene automatically reads compact project-scoped guidance
      -> repeat

No speculative text is automatically learned. A commit replay contributes zero
observations. A failed commit contributes zero observations. Source-learning
Xuehai is still immutable during WRITE.

## Trust and provenance

Accepted prose is *weak* evidence of the story's current narrative rhythm,
not automatically the author's preference or native style. The optional
ACCEPT_PROSE origin field is:

- accepted (default): low-trust structural observation only
- assistant_generated: same low-trust status; never called "author voice"
- author_written: high-trust voice evidence
- author_edited: high-trust evidence of the author's final revision

The editor/host MUST supply origin from actual edit provenance, not from
guessing whether text "sounds human." Two **distinct currently accepted authored scenes** permit the companion to show
a tentative author rhythm fingerprint; otherwise three distinct currently
accepted scenes permit only an explicitly weak accepted-prose signal. Repeated
revisions of one scene never masquerade as independent authorship evidence.

The profile is recomputed from an EMA of six deterministic VoiceFingerprint
fields across up to 32 most recently changed **distinct scopes**, using at most
the last 8,192 characters per changed scope (not model fine-tuning). A new
revision replaces its older sample; deleting a scene retracts its sample.
It is capped-size, and *does not attempt to learn tone, intentions, literary
quality, or emotional effect from style metrics*. Those require explicit
feedback and real reader / revision evidence.

## Explicit author corrections

The host uses an ordinary durable StoryEffect, never a separate untracked
mutation:

    StoryEffect(
        EffectType.SET_AUTHOR_PREFERENCE,
        "dialogue_no_explanation",
        {"action": "set", "direction": "avoid",
         "category": "dialogue", "guidance": "对话之后不重复解释情绪"},
    )

Use the same key to update a preference. Use {"action": "remove"} with the
same key to forget it. The action, category and direction are checked before
mutating story. Maximum 64 preference slots per project, at most 240
characters each. An explicit correction carries more authority than any
weak inference from accepted prose.

## No Skill ceremony during drafting

Construct one WritingFlow(db, runtime, project_id) in the host's writing shell.
Its begin_draft(scene_id, concerns=...) method automatically supplies a bounded
companion frame, and accept_draft(...) uses the real StoryCommitCoordinator.
The lower-level WritingCompanion is also available to hosts that already own a
writing session. The writing route calls before_draft(scene_id, concerns=...)
when it assembles the next scene/paragraph context, not in response to an
author command such as "run the voice skill." The returned
CompanionDraftContext.compact_context() is at most 768 characters by default,
and the host can optionally lower that limit. When the profile version has
not changed, an SQL version probe + bounded LRU cache is used. After any
committed preference/revision change, the version automatically invalidates
that cache on the next draft.

The compact context contains *guidance*, not mandatory rewrite instructions.
It complements Canon, character facts and Scene Craft Contract, and may not
override them. No additional deep reviewer is activated solely because the
author wrote another sentence. The existing Scheduler handles those based on
dirty domains and genuine risks.

## Example

    db = WriterForgeDB("novel.sqlite3")
    runtime = RuntimeEngine()
    runtime.enter_write(1)  # normally a real published Xuehai snapshot ID
    flow = WritingFlow(db, runtime, "novel")

    # The app's usual begin-writing action (not a user-invoked Skill):
    frame = flow.begin_draft("chapter-3.scene-2", concerns=("dialogue",))
    guidance = frame.companion_guidance  # small, project-specific, stable

    # After the author accepts/edits the scene, one ordinary write boundary:
    flow.accept_draft(
        "commit-42", "chapter-3.scene-2",
        "她没有答话。窗纸被风吹得微微鼓起。",
        origin="author_edited",
    )
    # Next begin_draft observes the new profile version automatically.

## Acceptance guarantees / known limits

- No autonomous retraining of language-model weights, no self-modifying Python,
  no automatic skill creation, and no quality claim without blind reader checks.
- SQL writes share the same rollback/replay boundary as story acceptance.
- Project isolation is strict. No per-project profile is shared by default.
- Only the latest aggregate, up to 32 distinct active-scope metrics, and up to
  64 explicit preferences persist in these new tables; no raw draft is copied
  into companion memory. Revision counts can increase without increasing RAM.
- The host must mark provenance accurately and call before_draft as part of
  its normal writing route. WriterForge's repository remains a Python
  kernel, not an always-on chat agent or full prose-generation service.
- Speed benefit at this stage is bounded memory/prompt and avoiding repeated
  corpus searches, **not** a measured model-token/s writing speedup.
- eval/companion_benchmark.py measures 256 accepted scenes and 5,000 repeated
  draft-context reads. It checks the active sample cap (32) and cache reuse,
  while reporting Python/SQLite time separately from actual prose generation.
- Reader satisfaction, semantic style adaptation and subjective quality remain
  unproven until benchmarked in real writing sessions.
