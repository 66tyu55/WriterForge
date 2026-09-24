# WriterForge V19 — Transactional Story Runtime

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
