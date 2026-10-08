# WriterForge V22 — External evidence practices without a second skill system

This is a focused integration into existing V21 writer_companion_preferences
and StoryCommitCoordinator, NOT another rule store or new scheduling lane.

## Verified sources and decisions (2026-10-08)

1. novel-studio user rules runtime:
   https://github.com/Xiaoyangy/novel-studio/blob/main/docs/user-rules-runtime.md
   It consolidated overlapping long-term directives after real routing
   conflicts. Adopt: one writer-preference authority; explicit same-category
   conflict slots. Reject: a second directives or coordination pipeline.

2. Whose Story Is It? (IJCNLP-AACL 2025):
   https://aclanthology.org/2025.ijcnlp-long.82/
   It studies an evidence-informed Author Writing Sheet across plot,
   creativity, character/emotion and language. Adopt: optional, human-curated
   axis and verified source anchor on an existing author correction.
   Reject: pretending basic sentence statistics prove an author's creative
   preferences; no automatic style/persona generation from weak signals.

3. Calliope / writing-skills:
   https://github.com/Calliope-Editor/writing-skills
   It makes editorial diagnosis separate from writing or rewriting prose.
   Adopt: read-only writing sheet and stale-evidence audit.
   Reject: installing redundant reviewer agents or automatically accepting
   their findings as permanent writing rules.

This uses techniques/ideas, not transplanted third-party code.

## Runtime behavior

- The only writable author-preference path remains SET_AUTHOR_PREFERENCE inside
  accepted StoryCommit transactions. Explicit corrections still work without
  evidence and can be replaced/deleted by key.
- Optional evidence_scope + evidence_excerpt must match the CURRENT accepted
  prose for the same project. The preference table saves only a body hash and
  excerpt hash, not another copy of the novel. After that source changes, the
  linked guidance becomes stale and is excluded from future draft contexts.
- The evidence-linked rule is not automatically rewritten or re-anchored:
  evidence_audit reports it as stale until author review.
- Optional conflict_group identifies the explicit rule slot. Two different keys
  cannot occupy the same category+group slot in one project. Reject the whole
  transaction and request that the author modify/remove the existing rule.
  Unlabeled semantic contradictions remain beyond deterministic detection.
- Optional axis is one of plot, creativity, character_emotion and language.
  The four-axis writing_sheet is a READ-ONLY view over already verified
  preferences, with no new database or classifier.
- WritingFlow.review_writing_sheet() is diagnostic only. It does not change
  text, story state, or author rules.
- Relevant per-scene preferences appear before generic preferences inside
  the original V21 max-guidance and prompt budgets. No new priority scheduler.

## Example: same-bundle evidence

    flow.accept_draft(
        "commit-42", "scene-2",
        "风吹得窗纸轻响。她缓缓收剑。",
        origin="author_edited",
        corrections=(
            AuthorCorrection(
                "emotion_action", "以动作承载情绪",
                category="description", axis="character_emotion",
                conflict_group="emotion_expression",
                evidence_scope="scene-2", evidence_excerpt="缓缓收剑",
            ),
        ),
    )

Accepted prose is applied BEFORE a supported preference inside the same SQLite
transaction. Missing evidence rolls everything back, including receipts,
companion observations and WorkTree checkpoints. A V21 database is upgraded
with additive, idempotent columns. No extra skill or plugin is required.

## Deliberate limitations

- Verification proves that an excerpt exists, NOT that it establishes the
  proposed literary technique as effective.
- The writer alone explicitly labels style axes and conflicts; an LLM cannot
  silently promote its own draft/reviewer suggestion into author preference.
- No automatic review/rewrite cycle is introduced.
- Benchmarking genuine author satisfaction and reader experience requires
  later blind human evaluation, not just passing Python tests.
