# WriterForge V15 — Lane-Scheduled Novelist Runtime

WriterForge is a long-form fiction system built around strict LEARN / WRITE separation, Reader-First source learning, Canon/Character/Knowledge/Promise memory, lean Craft routing, Literary Taste, Story Sense and controlled Evolution.

V15 focuses on **runtime loading speed and scheduling**, not adding more literary Skills.

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
