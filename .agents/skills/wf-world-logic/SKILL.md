---
name: wf-world-logic
description: Evidence-based world pressure and counterfactual Skill. Models institutions, material resources, directed causal proposals, contingency, accidents and downstream costs, and refuses to force the original future.
compatibility: Python 3.10+, standard library, offline.
metadata:
  wf-skill-id: wf-world-logic
  wf-lifecycle: shadow
  wf-version: "0.1"
---

# 世界机制 Skill：必然的条件和不必然的事件共同存在

The prior world inverse PR #69 **failed**: its anonymous representations discarded everyday evidence, and a decoder reversed causation. Do NOT rebrand that failed experiment as training. This new Skill starts with a private chapter-local observation ledger and a separately executable state-transition laboratory. Neither correct byte storage nor green unit tests means it has understood a novel.

## 1:1 source contract

A private episode document has:
- source SHA256, exact bytes + strict encoding (UTF-8 or GB18030), contiguous byte scope;
- byte-exhaustive units, initially PENDING even if mechanically indexed;
- original anchors with start/end byte offsets, literal surface and independent-review state;
- all evidenced macro/micro places, actors (including disposable NPCs), routes, access, institutional rules, relationships, facts, events, material and causal costs;
- UNKNOWN/CONTESTED whenever narrator, hearsay, inference and actual observation differ.

Every claim requires original evidence anchors. An exact anchor only proves the text exists, not that the encoded actor, motive, world state, or arrow direction is correct. Review labels do not automatically grant semantic truth. Never guess hidden facts, precise weights, travel or chapter times.

Source-fitted world rules have open action tags and requirements (access, resource_min, knows, at_place, attribute_equals). These determine permission to attempt **not** success, preference or inevitability. A finite resource must pay a cost. An unknown cause stays unknown; an accident can have no established cause. An irrational act can be allowed. Never infer postconditions from a historical event in the source after changing its antecedent.

## Operations

Python scripts:
- python .agents/skills/wf-world-logic/scripts/episode_cli.py index --source PRIVATE.txt --encoding gb18030 --start START --end END --out PRIVATE_episode.json
- python .agents/skills/wf-world-logic/scripts/episode_cli.py check --source PRIVATE.txt --episode PRIVATE_episode.json
- python .agents/skills/wf-world-logic/scripts/episode_cli.py propose --source PRIVATE.txt --episode PRIVATE_episode.json --proposal PRIVATE_action.json
- python -m unittest discover -s tests -p test_wf_source_world_logic.py -v

The kernel checks source/ID references, containment cycles, directed route gate/costs, witness location and actor-specific knowledge, lying/rumour separation, action preconditions and atomic rejection. It also permits unspecified unpredictable accidents without saying they must happen; an altered action never causes historical downstream events automatically to replay. The time_ref is **opaque** and owned by the independent time Skill.

## Training and promotion gate

Read entire original works **progressively**, recording all small-scale daily-life facts and minor actors rather than chapter title keywords. Freeze a reviewed consecutive source prefix and unseen future evidence. Randomly rename world/roles; change one trait/affiliation/resource; attempt inverse of world constraints, state transitions, motives and missing information. Compare with independent original readers, count fabricated facts, reversed causes, omitted facts and premature knowledge. If the inverse fails, fix the representation or halt, NOT tailor labels/validators to the failed holdout or auto-publish guessed corrections.

No original passage, private source-name map or paid model calls in public Git. No second XuehaiStore, Canon, R2, Railway or official author. Author keeps USE/SKIP. **Status SHADOW, NOT fully trained or source-complete.**
