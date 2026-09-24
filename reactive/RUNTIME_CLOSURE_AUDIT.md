# WriterForge V18 Runtime Closure & Leak Audit

## Fixed
- Per-lane pending updates prevent cross-lane state overwrite.
- Reject clears rendered pending inputs/lanes and detaches speculative alternates.
- Reactive cache has global + per-scope bounds.
- Invalidation racing an in-flight compute marks the late result stale and prevents cache insertion.
- Event batching aggregates per scope instead of retaining every raw event.
- Queue generation metadata is released when the last task for a scope leaves.
- Suspended members block their whole entangled group until pinged.
- 100 sequential commits verify the test WorkTree remains within a two-buffer node bound.

## Intentional growth
SQLite history/evidence tables are append-only durable history, not RAM leaks. They still need an archival policy for multi-million-word projects.

## Remaining end-to-end closure gap
Persistence is not yet atomic. StoryStore setters commit independently, while CommitLedger receipts live only in RAM.

Required next layer:
Finished Work -> StoryEffect[] -> validate -> BEGIN IMMEDIATE -> apply all effects + durable receipt -> COMMIT -> adopt WorkTree.

On failure: ROLLBACK -> discard WIP -> accepted tree and durable story state remain unchanged.
