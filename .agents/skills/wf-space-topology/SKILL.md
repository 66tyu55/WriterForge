---
name: wf-space-topology
description: Source-evidenced fictional-space Skill for WF: reconstruct small rooms, macro territory, nesting, directed routes, restrictions and resource costs without inventing distances or clocks.
compatibility: Python 3.10+, standard library; shadow engine ../wf-world-logic/scripts.
metadata:
  wf-skill-id: wf-space-topology
  wf-lifecycle: shadow
  wf-version: "0.1"
---

# 空间 Skill：空间不是地名清单

Use the exact private original, chapter by chapter. Capture EVERY observed or mentioned space: rooms, paths, gates, farms, distant regions, unnamed sites and spatial boundaries, including incidental ones. A place mentioned in a rumour is not necessarily visited, and a place simply inside a kingdom does not prove a passage from another place. Mark UNKNOWN instead of inventing coordinates, distances or implicit travel.

Each place has anonymous id, optional parent_id, source evidence byte anchors, open source-derived kind, and unknown attributes. Each route is directed source -> target with independently evidenced travel gate, access tokens and nonnegative decimal resource costs. A -> B does not prove B -> A. Actors' current location is separate from narrative perspective; null is an honest unknown.

Time belongs entirely to the other time Skill: never infer journey elapsed, cultivation duration or era alignment from routes. The non-time engine carries only opaque time_ref.

## Workflow

1. Obtain an authorized original in **private local** storage; identify strict contiguous source byte scope and encoding (UTF-8 or GB18030).
2. Run: python .agents/skills/wf-world-logic/scripts/episode_cli.py index --source PRIVATE.txt --encoding gb18030 --start START --end END --out PRIVATE_episode.json
3. Read every line and fill PRIVATE_episode.json with anchors, minor/major places, visited vs merely reported locations, containment, directional travel and stated costs. An index with PENDING units proves NOTHING semantic.
4. Run: python .agents/skills/wf-world-logic/scripts/episode_cli.py check --source PRIVATE.txt --episode PRIVATE_episode.json
5. Test counterfactual changes of actor location and access through propose; record impossible paths, unpaid crossings and loss of visibility.
6. Blind inverse from renamed places and newly changed character traits, comparing withheld original events with an independent reader. Record missing rooms and routes as failures.

Source hash/span checks are mechanical only. Do not reuse unapproved claims in author context, publish private text/identity maps or modify R2, Xuehai, Canon, Railway or main. Stay SHADOW pending independently validated full contiguous semantic recovery.
