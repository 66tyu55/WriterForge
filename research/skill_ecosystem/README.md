# Skill Ecosystem Inbox

This folder is the upstream intake layer for public Agent Skills that may strengthen WriterForge.

It is deliberately **outside the production runtime**. A popular Skill is not automatically installed into WriterForge. The intake process is:

```text
discover
-> pin exact upstream revision
-> read the relevant SKILL.md
-> classify ADOPT / MERGE / WATCH / REJECT
-> choose one WriterForge owner
-> extract mechanism, not branding or surface prompt style
-> add tests
-> promote through WriterForge's normal Evolution gate
```

## Rules

1. Popularity is discovery evidence, not literary evidence.
2. Prefer mechanisms over copied prompt text.
3. One mechanism gets one durable owner.
4. If WriterForge already owns the capability, MERGE instead of creating a sibling Skill.
5. Raw upstream material never becomes Xuehai source evidence.
6. External skills do not run during ordinary fiction writing unless assimilated into an existing runtime owner.
7. Large upstream repositories are referenced by pinned Git tree/commit rather than vendored wholesale.
8. License is recorded before any source text is redistributed.

## Current intake

Six high-signal repositories were indexed in this pass: 122 SKILL.md files total.

See:
- `SOURCES.json` — pinned upstream revisions and licenses
- `UPSTREAM_SKILL_MAP.md` — placement and disposition
- `../../integration/HOT_SKILL_ASSIMILATION.md` — mechanisms selected for WriterForge
