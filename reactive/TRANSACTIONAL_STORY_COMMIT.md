# WriterForge V19–V20 Transactional Story Commit

Production WRITE commit path:

Event -> Schedule -> Reconcile -> Finished Work -> StoryEffect[] -> Validate -> SQLite BEGIN IMMEDIATE -> Effects + Story Events + Durable Receipt -> COMMIT -> adopt WorkTree current.

## Guarantees

- No StoryEffect is durable before the transaction commits.
- A failure rolls back every effect and the durable receipt.
- A repeated commit_id with the same bundle is a no-op replay.
- A repeated commit_id with a different bundle is rejected.
- Effect journal + receipt survive process restart.
- WorkTree adoption is bound to a finished-work fingerprint.
- WorkTree is adopted only after durable COMMIT.
- Failed durable commit discards speculative buffers but preserves current pending inputs for retry.

## Crash boundary

SQLite and RAM cannot participate in a literal single ACID transaction. The durable side is the source of truth.

If the process dies after SQLite COMMIT but before WorkTree adoption, the durable receipt exists. On retry the same bundle is recognized as a replay; if a matching finished WorkTree exists it may be adopted. After process restart, WorkTree must be reconstructed from durable project state.

## Legacy StoryStore

Direct StoryStore setters remain for backward compatibility and focused tests, but production accepted-story mutation should route through StoryCommitCoordinator.


## Closure verdict

The production WRITE commit loop is closed for in-process execution:
speculative compute -> finished WorkTree -> fingerprint-bound StoryEffect bundle -> atomic durable transaction -> durable receipt -> WorkTree adoption.

V20 closes the restart gap for commits carrying finished WorkTree: a checksum-protected, head-bound WorkTree checkpoint is persisted in the same transaction as the receipt. `restore_work_root` rehydrates the latest accepted computation tree with its pending lane updates. Rootless commits and older V19 receipts have no eligible checkpoint and require application-level reconstruction. See `reactive/WORKTREE_CRASH_RECOVERY.md`.
