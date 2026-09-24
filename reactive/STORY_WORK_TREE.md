# WriterForge V17 Story Work Tree

V17 adds a Fiber-inspired computation tree for long-form fiction. It is not a DOM renderer and does not copy React's component model.

## Why

A book-level system should not recompute the whole novel when one scene changes.

Book -> Arc -> Chapter -> Scene -> capability nodes.

Each node carries its own lanes and aggregated child_lanes.

When a leaf changes:

dirty leaf -> mark own lane -> bubble child_lanes through parent path -> unrelated siblings stay clean.

## Double buffer

The accepted computation tree is current. A speculative pass uses alternate/workInProgress. Only two versions are retained and the alternate is reused across passes.

Important: the WIP tree is not accepted story state. WriterForge may render/review it repeatedly and discard it. Only after the outer Story Commit succeeds may adopt_after_commit() swap the computation tree.

## Begin phase

A node can:

1. do its own work if its lane intersects the render lanes;
2. skip its own work but descend if child_lanes contain relevant work;
3. bailout the whole subtree if neither itself nor its descendants have relevant work.

This is the tree-level form of: No Change -> No Recompute.

## Complete phase

After children finish, the parent recomputes cheap aggregate metadata:

- surviving child lanes;
- whether any descendant performed work.

No Canon/prose/database effect is committed here.

## Deliberately not in V17

- effect list / mutation list;
- transactional story commit;
- rollback of external side effects;
- keyed scene reorder reconciliation;
- wall-clock shouldYield().

Those remain separate phases so the Work Tree stays independently testable.
