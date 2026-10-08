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
guessing whether text "sounds human." Two authored observations permit the
companion to show a tentative author rhythm fingerprint; otherwise three
accepted changes permit only an explicitly weak accepted-prose signal.

The profile is an EMA of six deterministic VoiceFingerprint fields on the
last 8,192 characters of each changed accepted scope (not model fine-tuning).
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

Construct one WritingCompanion(db, project_id) in the host's writing shell.
The writing route automatically calls before_draft(scene_id, concerns=...)
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
    companion = WritingCompanion(db, "novel")

    # Automatically inside the host's before-draft path:
    ctx = companion.before_draft("chapter-3.scene-2", concerns=("dialogue",))
    guidance = ctx.compact_context()  # small, project-specific, stable

    # On an accepted author-edited scene:
    coordinator.commit(StoryCommitPlan(
        "novel", "commit-42",
        (StoryEffect(EffectType.ACCEPT_PROSE, "chapter-3.scene-2",
            {"body": "她没有答话。窗纸被风吹得微微鼓起。",
             "origin": "author_edited"}),),
    ))
    # Next before_draft sees profile_version+1 with no manual learning command.

## Acceptance guarantees / known limits

- No autonomous retraining of language-model weights, no self-modifying Python,
  no automatic skill creation, and no quality claim without blind reader checks.
- SQL writes share the same rollback/replay boundary as story acceptance.
- Project isolation is strict. No per-project profile is shared by default.
- Only the latest aggregate and <=64 explicit preferences persist in these new
  tables; unbounded raw text is not copied into companion memory.
- The host must mark provenance accurately and call before_draft as part of
  its normal writing route. WriterForge's repository remains a Python
  kernel, not an always-on chat agent or full prose-generation service.
- Speed benefit at this stage is bounded memory/prompt and avoiding repeated
  corpus searches, **not** a measured model-token/s writing speedup.
- Reader satisfaction, semantic style adaptation and subjective quality remain
  unproven until benchmarked in real writing sessions.
