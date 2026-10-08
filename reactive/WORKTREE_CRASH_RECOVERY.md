# WriterForge V20 — WorkTree Crash Recovery

V19 made story effects and durable receipts atomic. V20 removes the restart gap
for commits that supply a finished WorkTree.

## Commit path

Event -> Schedule -> Render -> Finished Work -> StoryEffects -> Validate ->
BEGIN IMMEDIATE -> Effects + Events + Receipt + WorkTree Checkpoint ->
COMMIT -> Adopt WorkTree.

The checkpoint is a **cache of accepted computation state**, not a replacement
for canonical story rows (prose, canon, characters, reader, promises).

- Exactly one current checkpoint is stored per project.
- It records the complete Book/Arc/Chapter/Scene/capability topology, accepted
  memoized states/fingerprints, generation markers and outstanding lane updates.
- It is written in the same SQLite transaction as its matching receipt.
- The latest receipt identifies the only checkpoint eligible for recovery.
- The checksum and WorkTree fingerprint are verified before restoration.
- Alternates, speculative buffers and in-process callbacks never persist.
- Scheduler tick/expiry/suspend state is volatile; pending lanes are reconstructed.
- Checkpointed state must be plain JSON data (str-keyed dicts, lists, strings,
  numbers, booleans, null). Non-serializable states fail **before BEGIN**.

## Restart

    from writerforge import WriterForgeDB, restore_work_root

    db = WriterForgeDB("novel.sqlite3")
    root = restore_work_root(db, "my-project")
    # The returned root has a clean two-buffer lifecycle; pending lanes survive.

The restore API refuses missing, corrupt, stale, or unsupported-schema snapshots.
Old V19 commits have no WorkTree checkpoint; they require project-driven
reconstruction. A production commit without WorkTree invalidates the previous
checkpoint because it changes accepted story state independently.

## Guardrails

- The finished candidate cannot accept newly scheduled updates. Queue arriving
  events in the event batcher until commit/reject, then apply them to the new
  current root; otherwise a later event could be lost on adoption.
- Replaying an older receipt is still a durable no-op, but cannot adopt an old
  WorkTree over a newer commit.
- Restored roots track the project ID and commit ID from which they were loaded. Committing a
  root based on a superseded head is rejected.
- A failure before COMMIT rolls back effects, journal, receipt, and checkpoint.
- An adoption exception **after** COMMIT requires restore_work_root rather than
  reverting SQLite. Recovery starts from the persisted checkpoint.

## Known limits

This is a one-row-per-project full-tree snapshot at each WorkTree commit (O(N)
serialization/write). A future version can introduce incremental or compacted
node checkpoints. JSON-native states are required. Roll-forward of queued
external events remains the caller's responsibility and is not an outbox.
Freshly constructed legacy roots do not yet carry optimistic head markers;
production restart paths should use restore_work_root.
