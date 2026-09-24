# WriterForge V16 Lane Root + Event Priority

V16 separates **source event urgency** from **execution lanes**.

```text
Business Event
   -> EventPriority
   -> same-turn EventBatch
   -> Dirty Domains
   -> Capability Lane
   -> Lane Root State
   -> Task Queue
```

## Four event priorities

Business code sees only four priorities:

- `DISCRETE` — direct user/canonical decisions that should react immediately.
- `CONTINUOUS` — repeated foreground activity such as accepted sentence/stream deltas.
- `DEFAULT` — ordinary scene/chapter/craft/review events.
- `IDLE` — background learning/evolution/maintenance.

These map thinly to `SYNC / DRAFT / REACTIVE / IDLE` for ordering and tracing. They do **not** promote every expensive capability spawned by an event into an urgent lane.

## Seven execution lanes remain

`SYNC -> DRAFT -> REACTIVE -> BOUNDARY -> TRANSITION -> OFFLINE -> IDLE`

Execution lane still belongs to the capability. This prevents a discrete user edit from accidentally turning a full Reader Board or book audit into synchronous foreground work.

## Lane Root State

Each logical root may track:

- `pending`
- `suspended`
- `pinged`
- `warm`
- `expired`
- `entangled`

This is more expressive than a heap alone.

### Suspended / pinged

A task waiting on Xuehai, files, reader evidence, or another dependency becomes suspended. When the dependency arrives, the lane is pinged and can re-enter scheduling without rebuilding the whole request.

### Warm

A suspended lane that has already explored all currently available work is marked warm. It should not be repeatedly recomputed while evidence is still missing.

### Expiration

Urgent foreground lanes receive logical-tick expiration. `OFFLINE` and `IDLE` do not expire by default. Expiration is a starvation safeguard, not a quality score.

### Entanglement

Semantically coupled state updates may be entangled:

```text
character knowledge
<-> dialogue intent
<-> reader knowledge
```

If one logical version is committed, the coupled lanes should render from the same version. Entanglement is transitive.

## Interruption rule

Do not discard useful work merely because another task appeared.

A work-in-progress lane continues unless the next runnable lane is truly more urgent or the WIP is blocked. This reduces expensive literary recomputation.

## Event batching, not event pooling

WriterForge batches *meaning*:

```text
character changed
+ promise changed
+ reader question changed
= one scope batch
```

It does not recycle event objects.

## Responsibility boundaries

- EventPriority: source urgency.
- DirtyDomain: what changed.
- Capability Lane: where work belongs.
- LaneRootState: aggregate runnable/blocked/coupled state.
- LaneTaskQueue: concrete cost-sliced execution.
- ReactiveSkillRuntime: fingerprint cache + singleflight.
- CommitLedger: idempotent side effects.

Do not collapse these layers.
