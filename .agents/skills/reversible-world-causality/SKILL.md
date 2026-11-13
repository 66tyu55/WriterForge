---
name: reversible-world-causality
description: Source-grounded, reversible world-state and causal-structure study for WriterForge. Use for full-original time/space/actor/event mapping, anonymous parameter encoding, inverse reconstruction and falsifiable transfer tests; never promote a partial or unverified interpretation.
compatibility: Python 3.10+, standard library. Offline; source novels and private reconstruction bundles remain outside Git.
metadata:
  wf-skill-id: reversible-world-causality
  wf-lifecycle: shadow
  wf-version: "0.1"
---

# Reversible World Causality / 世界因果反推

## Goal and hard boundary

Study **how a fictional world existed before a protagonist, changes outside their field of view, and continues after unexpected or irrational actions**. No mandatory faction/auction/sect/black-market taxonomy; discover what a given world actually contains. A world may have structural pressures without any *particular* future event being inevitable. Coincidence, unreasoned action, misinformation and unresolved mysteries are legitimate observations, not defects to patch with invented causes.

**Do not equate a numeric parameter or a SHA with understanding a novel.** This Skill has two different inverse problems:

1. **Exact inverse / engineering gate**: every source byte, source-anchored observation and typed graph entry can be reconstructed with zero loss. The private `source.zlib` and `private-ledger.json` are part of this inverse; **the anonymous JSON alone cannot reconstruct a novel**, mathematically or practically. An observed 100% byte roundtrip proves only lossless storage.
2. **Causal inverse / literary gate**: from a *newly renamed and rebuilt world*, infer constraints, dependencies, disruptions and alternative outcomes seen in held-out original events. Names and word-frequency cues must not be the solution. This gate needs real sequential reading plus independent semantic review; it is **NOT yet passed**.

Fail closed on partial evidence rather than claiming that 1 proves 2.

## Relationship to existing WF

Use the existing single `XuehaiStore`, FactJournal, modern-source checks and LEARN/WRITE separation. This is **a portable offline experiment**, not a second author, independent Canon database, new R2 store or auto-installed runtime. No change to previous V26/V98/V119 systems, project canon, production Railway, R2 or main. The writer still chooses USE/SKIP. No source prose, modern novel text, or derived private named mappings enter the public repository, CI logs or prompt context by default.

## The one-to-one study unit

For each original work, process every chapter in source order and also audit prefaces, interludes, omitted headings and duplicated/renumbered chapters. Build open-typed, source-located evidence at the **smallest independently checkable claim**, retaining:

- **Space**: local spot, room, village, remote territory, unknown place; coordinates, access/cost, nested and interrupted routes only where evidenced. A named place is not merely a noun.
- **Time**: text presentation order (`telling_seq`), world-event order (`story_tick` only when independently justified), training duration, waiting, centuries, eras and past eras. Unknown clock positions stay `null`; don't assign fictional exact dates.
- **Actors**: named/unnamed, protagonist, opponent, neutral, irrelevant and one-line passersby; record observation and knowledge state separately, including off-screen actions if the text supports them. `actor.kind` is **not** a permanent protagonist/NPC essence; roles can change.
- **Relations and transitions**: environment, scarcity, institutions, trade, conflict, misunderstanding, irrational choice, accidental death, resources, costs and downstream consequences. Record consequences that did *not* happen as negative or absent evidence only when the original genuinely supports that distinction.
- **Epistemic authority**: `narrated`, `character_belief`, `rumour`, `inferred`, `unknown`, `contingent`, `unexplained`. Never quietly turn a rumor into an objective world fact.
- **Parameters**: typed open-world predicates and exact decimal strings, e.g. `"-0.0129"`, `"0.145"` **only if a calibration/derivation record actually exists**. The codec preserves such values exactly, but does not fit, invent or certify them. Every nonempty `parameters` entry MUST have a matching `parameter_traces` record with `method=source_literal` and a source anchor containing the exact decimal, or `method=exact_ratio` with two source-anchored decimal operands and exact rational equality. Values like `+0.145` without such proof are rejected, not silently stored as trained weights. Even a mathematically valid ratio is not proof of a true causal relationship.

Each `anchor` uses exact **source byte offsets** plus a private literal `surface`. Each `fact` links to anchored evidence; each `link` states epistemic authority. Keep unsupported narrative interpretations unconfirmed. Propose open kinds as needed; do not force chapters into a fixed fantasy trope catalog.

## Execution

1. Copy an authorized original to local private storage (Google Drive novel folder is an eligible user-owned input). Record source edition, byte SHA256, strict codec, chapter audit and unresolved gaps. Be especially careful about GB18030 vs UTF-8 and author notes before the first chapter.
2. Extract source spans and candidates in temporal reading order; keep exact source offsets. **Independent readers must review any semantic claim**; text containment alone does not make the claim true. Preserve omissions as unfinished coverage, not as nonexistent world events.
3. First build a byte-exhaustive, non-semantic index using:
   `python .agents/skills/reversible-world-causality/scripts/source_index.py scan --source PRIVATE_ORIGINAL.txt --out PRIVATE_LINE_INDEX`
   This records every preface, blank line, chapter-heading candidate and body line without publishing any text. Verify with `source_index.py verify --source PRIVATE_ORIGINAL.txt --index PRIVATE_LINE_INDEX`. A candidate heading is not a verified chapter; manually inspect out-of-order and missing chapter numbers. The index is a precondition, **not** a world model.
4. Create a **private** `observations.json` (format below). Store this next to the local source, never in Git.
5. Run:
   `python .agents/skills/reversible-world-causality/scripts/codec.py pack --source PRIVATE_ORIGINAL.txt --observations PRIVATE_OBSERVATIONS.json --out PRIVATE_BUNDLE_DIR`
6. Run:
   `python .agents/skills/reversible-world-causality/scripts/codec.py verify --bundle PRIVATE_BUNDLE_DIR`
7. To prove original-byte reconstruction (private, explicit opt-in only):
   `python .agents/skills/reversible-world-causality/scripts/codec.py recover --bundle PRIVATE_BUNDLE_DIR --out PRIVATE_RESTORED.txt --allow-private-original-output`
8. **Do not train model weights or promote literary skill automatically.** Once evidence coverage is actually complete, freeze a new held-out original and test hidden-event reconstruction and genuinely different world/characters. Preserve all errors and counterexamples.

Input schema (private; `source_sha256` refers to actual raw novel bytes):

```json
{
  "format": "wf.world-observations.v1",
  "source_sha256": "64 lowercase hex characters",
  "anchors": [
    {"id": "A001", "kind": "actor", "start": 0, "end": 6, "surface": "exact span from private source"}
  ],
  "facts": [
    {
      "id": "F001", "kind": "resource_constraint",
      "subject_ids": ["A001"], "evidence_ids": ["A001"],
      "telling_seq": 1, "story_tick": null, "time_axis": null,
      "epistemic": "narrated", "parameters": {}, "parameter_traces": {}
    }
  ],
  "links": []
}
```

Here `kind` and `parameters` are open extensible **ASCII codes**, not genre-dependent name lists. An evidence anchor can overlap another anchor. Some facts have no actor, but every fact needs at least one source anchor. The synthetic sample is a **shape**, not a truthful analysis of any novel.

## Hard gates and falsification

- Source bytes/UTF-8-or-GB18030 codec, every physical source line, chunk coverage, hashes, each anchor's exact location, full private-to-anonymous inverse and recovery MUST be **100%** before a bundle is admitted to the *mechanical* stage. Tampering and source mismatches must fail.
- **Semantic coverage is separately measured**: every chapter and claimed object/actor/time/space/event must be reviewed; the codec deliberately reports `NOT_ESTABLISHED` until that is actually done. No claiming whole-book causal comprehension from source-byte coverage.
- **Training test protocol**: first freeze (a) source chapter sets, (b) held-out later events, (c) new-world substitutions and character-trait perturbations, (d) scoring rubric and model-call budget. Measure exact entity/time/space/state/epistemic recovery, missing links and invented causal edges, false certainty, and whether random/irrational events remain possible. Train and evaluate on **disjoint material**.
- **Name replacement metamorphic test**: replacing names and decorative lore must preserve *abstract observed relations*; role/trait/resource interventions need **not** preserve the original event sequence. Force WF to state what changed and why.
- **Negative tests**: unsupported causes, premature knowledge, reversed story time, forged passage offsets, invented `+0.145` weights, omitted minor actors, vanished downstream costs, or silently backfilled explanations must fail or be labeled UNKNOWN.
- If accuracy fails, keep FAIL evidence, stop promotion and locate the earliest wrong observation. Do **not** patch the held-out book into the rules or report same-set regression as new blind performance.

## Meaning of initial results

The code only enforces reversible *storage and graph transport*. It does not extract full novel semantics, auto-annotate characters, or fine-tune an LM. Real-source pack/verify and small evidence probes are engineering first steps. **A successful lossless archive is never evidence that a model can reconstruct the novel's world logic.** Keep this Skill in SHADOW until independent, preregistered cross-world tests show semantic accuracy and useful literary improvement.
