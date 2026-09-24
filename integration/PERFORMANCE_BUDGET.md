# Performance Budget — V15 Lane Runtime

WriterForge optimizes **active work**, not library size. A capability may exist without being loaded for the current route.

## SPA model

```text
Resident shell
  runtime_guard + snapshot_guard

WRITE route
  current scene/character/reader/canon pointers

Lazy chunks
  only dirty literary domains

Background workers
  LEARN synthesis / full-book audit / evolution
```

## Lane budgets

### Ordinary sentence
- allowed lanes: SYNC + DRAFT + REACTIVE
- default cost <= 8
- active literary domains: usually 0-1
- BOUNDARY / TRANSITION / OFFLINE = 0

### Paragraph boundary
- SYNC + DRAFT + REACTIVE
- default cost <= 12
- Voice Guard only when VOICE is dirty

### Scene boundary
- may include BOUNDARY
- default cost <= 24
- deep continuity, causality and character audits are **dirty-domain routed**, not all-on

### Chapter boundary
- default context is Reader/Promise/Memory oriented
- structural audits load only when their domains were dirtied
- TRANSITION reviewers may defer if urgent boundary work consumes the slice
- broad Reviewer Board is never entitled to budget merely because a chapter ended

### Offline / LEARN / Rewrite / Evolution
- OFFLINE lane only
- default cost <= 60
- never blocks ordinary WRITE

## Runtime rules

- lane bitmask chooses route class cheaply
- same-turn events batch before scheduling
- dependency fingerprint unchanged -> cache hit
- same request queued twice -> dedupe
- same computation concurrent -> singleflight
- newer scene/chapter generation may invalidate stale TRANSITION/OFFLINE work
- expired background work receives starvation protection
- rejected candidate -> zero side effects
- accepted commit -> idempotent once

## Degradation priority

Correctness / Commit
> Draft continuity
> Relevant reactive context
> Dirty structural domain
> Reader simulation
> Targeted Craft/Taste
> Broad review
> Offline evolution

The runtime must never spend a chapter's budget on unrelated audits simply because their names sort earlier.
