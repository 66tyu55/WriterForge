# Changelog

## v14.0.0 — 2026-09-22

- Added Embodied Scene Resolver: causal perceptual affordances derived from world state, entity properties, action/contact, and character-specific embodiment.
- Kept sound, temperature, touch, and emotion manifestation inside the existing Perception & Description capability rather than creating sensory micro-skills.
- Added POV attention filtering with no five-sense quotas and semantic cues rather than pre-written prose.
- Emotion no longer maps to stock body-language reactions unless a character-specific tendency has already been established.
- Added dependency fingerprinting so unchanged embodied scene state can be reused by the reactive runtime.

## v13.0.0 — 2026-09-22

- Added Ending Backtrace: endings are checked backward against established setups, protagonist choice, the central dramatic question, expansion, over-explanation, and irreversible change.
- Added Orthogonal Originality: detects default-cluster/cosmetic-swap story elements while protecting required narrative function.
- Added Observed Story Auditor: reverse-outlines accepted WriterForge prose to compare the story that actually exists against the plan, surfacing persistent emergence and functionless scenes.
- Added `temporal_reordering` as an internal Scene Turn & Rhythm technique card; no new Craft group or always-on agent.
- Kept all new mechanisms inside Story Sense, Taste, Evolution, and the existing five Craft groups.
- Full regression: 72/72 tests passed.

## v12.0.0 — 2026-09-22

- Added reactive skill runtime with dependency fingerprints, selective invalidation, single-flight execution, and commit-once semantics.
- Added Evolution Engine for failure clustering, curriculum generation, held-out/transfer validation, skill birth gates, and promotion gates.
- Added Literary Taste Engine with pairwise comparison and order-swap stability checks.
- Added Story Sense routing and capability dependency/revalidation support.
- Preserved V11 Craft Engine while extending technique cards without multiplying top-level craft domains.
