---
name: writer-forge-v16
description: >
  Long-form fiction runtime with Reader-First source learning, reactive lane scheduling,
  dependency-driven context loading, controlled self-evolution, story-sense routing,
  embodied scene causality, and pairwise literary taste. Designed for novels, not generic copywriting.
---

# WriterForge V16

WriterForge is a long-form fiction writer system. LEARN and WRITE remain mutually exclusive.

## Runtime rule

Capability library size must not determine per-turn cost.

WriterForge V16 schedules work as:

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
