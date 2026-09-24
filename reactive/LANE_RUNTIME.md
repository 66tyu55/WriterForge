# WriterForge V15 Lane Runtime

V15 borrows scheduling ideas from React's cooperative scheduler and lane model, but does **not** copy Fiber or old SyntheticEvent pooling.

## Goal

A large capability library should behave like an optimized SPA:

```text
App Shell -> Route -> Lazy Feature Chunk -> Background Worker
```

WriterForge mapping:

```text
SYNC        runtime/snapshot/commit correctness
DRAFT       sentence-level continuity and accepted-text bookkeeping
REACTIVE    Xuehai, memory, craft routing caused by real deltas
BOUNDARY    scene/chapter structural checks
TRANSITION  reader/taste/reviewer work that may be interrupted
OFFLINE     LEARN synthesis, full-book audit, evolution
IDLE        opportunistic maintenance
```

## Algorithms

### Lane bitmask

Lanes are powers of two. Selecting the highest-priority pending lane is a lowest-set-bit operation:

`lane = lanes & -lanes`

This gives constant-time route-class selection without sorting the whole capability library.

### Dirty-domain routing

A boundary is not evidence that every deep reviewer should run.

```text
character dirty  -> character_audit
causality dirty  -> causality_audit
continuity dirty -> deep_continuity
reader dirty     -> reader review
```

The scheduler intersects each capability's dependency domain with the current dirty-domain mask. Unrelated chunks are not loaded.

### Event batching

Several state updates in one logical turn are coalesced by scope:

```text
character changed
+ promise changed
+ scene location changed
        ↓
one batched event
        ↓
one dirty-domain union
        ↓
one scheduling pass
```

This is batching, **not event-object pooling**.

### Cooperative cost slices

The queue spends a bounded cost budget and yields when the next non-expired task would exceed the slice. Urgent lanes run before transition/offline work.

### Transition interruption

Reader simulation, Taste comparison and broad reviewer work are transition-like. When a newer generation of the same scene/chapter arrives before old transition work runs, stale low-priority work is discarded instead of completing useless analysis.

SYNC/DRAFT correctness work is never silently discarded by generation changes.

### Starvation protection

Low-priority work carries an expiration window. Once expired, one task may exceed the nominal slice so it cannot remain deferred forever.

### Dedupe and singleflight separation

- Lane queue dedupe prevents the same `scope + capability + fingerprint + generation` from being queued twice.
- `ReactiveSkillRuntime` singleflight still owns concurrent identical computation.
- `CommitLedger` still owns idempotent side effects.

Do not merge these responsibilities.

## What V15 deliberately does not copy

- Fiber tree rendering.
- DOM event semantics.
- Legacy SyntheticEvent object pooling.
- React-specific expiration constants.
- UI frame-time assumptions.

WriterForge uses literary cost units and scene/chapter generations instead of browser frames.
