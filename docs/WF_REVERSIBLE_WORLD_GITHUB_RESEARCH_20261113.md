# WF reversible-world Skill: GitHub solutions compared (2026-11-13)

User objective: one-to-one source-parameter inverse, not names/keyword memory. Preserve world constraints and changes outside protagonist POV, yet allow irrational decisions and accidents to disrupt trends. Do not turn the novel into a fixed quest/genre template.

All five projects below were checked in their upstream GitHub repositories; this is a **design review**, not a claim that they have been installed, trained on our novels, or validated on Chinese fantasy causality.

| Upstream | Grounded capability | Useful part | Rejected shortcut |
|---|---|---|---|
| https://github.com/getzep/graphiti | Temporal context graph, episodes, entity/edge source provenance, changing validity windows | Inspiration for keeping source-reveal order distinct from event/story chronology; never overwrite previous observed/contradictory claims | Do not install a second world-truth graph; existing WF FactJournal already has multi-clock, scoped knowledge and source IDs |
| https://github.com/zjunlp/DeepKE | Chinese named entity, relation, attribute and document-level extraction; cnSchema model supports common relationship types | Candidate generation for entity mentions after a source index, with each source byte span checked and independently reviewed | Chinese generic NER may miss fantasy inventions, unnamed NPCs, epoch descriptions and implicit world constraints; do not accept an automatic triplet as true causality |
| https://github.com/microsoft/graphrag | Entity/relationship extraction, community/global retrieval, local text-unit provenance | Studying relationships involving many minor/offscreen entities and locations; cross-chapter discovery | Co-occurrence or entity summaries are not causal proof; expensive full indexing or an extra knowledge store does not fix the inverse problem |
| https://github.com/py-why/dowhy | Explicit causal assumptions, interventions, counterfactuals and refuters | Require assumptions and falsification tests before promoting numeric influences as causal facts | Fictional narrative association values do not provide the intervention data or identification conditions for causal effect estimation |
| https://github.com/NLP2CT/TRACE | Temporal counterfactual benchmark with Modify/Insert, forward/backward hop, history/future | Implemented a sealed prefix and Modify/Insert style candidate fork to catch historical replay after an intervention | Benchmark dataset is unrelated to fictional worlds: do not claim successful transfer from an offline synthetic test |

## Accepted small implementation steps

1. Added `chronology.py`: a fact is first eligible only after its **last required evidence span** becomes available. Packed evidence cannot silently retain a wrong `telling_seq`. The source order is not the fiction's time axis.
2. Added `intervention.py`: a changed choice or introduced event forks from a pinned seen prefix. Original future facts are not copied; possible, unexplained or unknown outcomes remain possibilities, not canon.
3. Removed heldout future counts from model-facing prefix and fork. A future sample count is leakage even when original text is sealed.
4. Reused the existing reversible source codec, source index and numeric provenance gate. **No Graphiti/Neo4j, DeepKE weights, GraphRAG database or DoWhy runtime dependency was installed.**

## Real-original negative evidence retained

Two complete privately authorized original text files were source-indexed and byte-restored in an earlier run. A later independent source-revelation audit exposed **15 wrong evidence-order ranks among only 20 candidate facts**: 8/9 in one novel and 7/11 in the other. **The earlier byte-perfect PASS did not detect these errors.** Private non-destructive normalized copies and refreshed lossless bundles restored the correct mechanical source-revelation ranks; no claims of literary truth, fine-tuning or cross-world reverse inference are made. This is a failure found and corrected, not hidden.

## Adversarial test boundary

The feature-branch GitHub workflow runs synthetic-only unit tests to avoid exposing copyrighted original novels, API credentials or private Xuehai/R2 contents. At the verified 2026-11-13 checkpoint, **26/26** focused tests passed. Full WriterForge aggregate CI remains independently red in this environment due to existing external fixture and `cryptography` dependency requirements; do not mask or attribute that failure to semantic proof. This PR is a draft, experimental and isolated from production.

## Next training gate

Before training any semantic model, freeze full original text editions, chapter-order audit, evidence/character ownership, heldout books/chapters, outsider events and independent gold judgments. Compare candidate causal links against counterexamples from truly unseen material; precision, missing causal links, false certainty and missed minor actors must be scored independently of mechanical byte roundtrip. Character trait interventions are allowed to change outcomes; the accepted question is whether the **constraint structure** was correctly understood, not whether the original plot was forcibly reproduced.
