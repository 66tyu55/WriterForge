---
name: wf-character-epistemics
description: Source-grounded character knowledge/belief/action Skill. Track protagonists, antagonists, neutrals, one-line minor people, what each actually knows, misunderstands and chooses, without omniscient leakage.
compatibility: Python 3.10+, standard library; shadow engine ../wf-world-logic/scripts.
metadata:
  wf-skill-id: wf-character-epistemics
  wf-lifecycle: shadow
  wf-version: "0.1"
---

# 人物 Skill：知道、听说、误信、选择是四件事

Read real source chapters in order, retaining **every** present or mentioned person, including unnamed servants, bystanders, temporary opponents, strangers and off-screen agents when evidenced. Do not reduce a crowd to one individual if the source distinguishes count or separate agency. Protagonist / villain / neutral / incidental roles are **temporary narrative functions**, never immutable essences. Source-anchored role transitions must remain observable.

Actor parameters: anonymous actor id; role_at_open; original-evidenced place or null; material resources; access rights; explicit motives/pressures; knowledge; hearsay/beliefs; relationships; choices; costs; uncertainty. Open-world dimensions are allowed, but arbitrary numeric character weights such as +0.145 without source-grounded calibration are forbidden.

- Narrator knows fact F does **not** imply actor knows F.
- Actual witness at a place may acquire F only when F is attested by evidence.
- Hearing testimony adds a claim to BELIEFS, not to KNOWS. A listener may be mistaken or deceived.
- A character can make irrational choices or refuse an available opportunity; rules permit or prevent but never pick the act.
- Off-screen NPCs continue to exist; don't invent their activities. Temporal progress belongs to the time Skill.

Implement in a private evidence ledger defined by ../wf-world-logic/SKILL.md; use the same single underlying shadow kernel, not another Canon/Character DB. Freeze original prefix before attempts to inverse a later event. Swap personalities and goals in a renamed world: the same choice need not occur, but known constraints, locations, material costs and information access must hold.

Real acceptance requires independently reviewing even minor actors, finding the earliest hallucinated fact or wrong motive, and reconstructing unseen consequences. Mechanical checks and name replacement alone are not training. SHADOW until source-complete, source-disjoint inverse passes; do not inject into WF official writer or public original-text archives.

## 2026-11-13 original-grounded reality check — FAILED literary inverse

The owner rejected numeric/unit-only skills as proof of source understanding. We privately checked 132 exact original-anchored **candidate** observations across three complete novels, but the consecutive chapters are **not semantically exhausted** and no independent human review has approved them. The first two books supplied 73 pre-future observations; a third disjoint work supplied 30 anonymized prefix observations and kept later chapters outside the model input.

The **actual** pinned Qwen2.5-3B source-disjoint two-arm run [#43414129666](https://github.com/66tyu55/WriterForge/actions/runs/43414129666) failed: neither arm reconstructed a causal argument; both listed every source observation ID under the `constraints` key and did not reason through a changed protagonist motive. The learned arm used more prompt tokens, so no gain is established.

**Do not call this a trained source Skill or an approved author context.** Preserve the raw model failures and provisional source errors. Stop this frozen test: future experiments require source-complete consecutive reading, independent cause-arrow review, and a new unseen book/scene rather than tweaking the failed prompt.

Full report: `docs/WF_20261113_NON_TIME_ORIGINAL_INVERSE_REAL_FAILURE.md`.
