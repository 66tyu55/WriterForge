# WF non-time original grounding → anonymous inverse: first real transfer FAILED (2026-11-13)

## User's correction

**"没有原著训练，也没有反推，怎么确保参数正确？"** — Correct. 12 synthetic tests and a file SHA previously were only engineering properties and never verified literary semantics. This report preserves actual source reading, its gaps, and a real local-model inverse failure. **Do not merge/promote these three Skills as trained literary understanding.**

## Source handling and split

Three **actual complete original plain-text files** from the user's own connected Drive were read in private local storage; all read as strict GB18030, never published into this public repo. A and B are separate calibration works, C is a separate previously unseen work for the transfer question. Private title/character crosswalk, full prose, exact byte quotes and gold remain private.

- A: 8,254,082 raw bytes, 45 provisional original-anchored claims; first four chapters 37 learning atoms, next 8 held out.
- B: 15,224,548 raw bytes, 46 provisional source atoms; first four chapters 36 learning atoms, next 10 held out.
- C: 5,548,542 raw bytes, 41 provisional source atoms; first two chapters 30 anonymous test-prefix atoms, next 11 source-anchored future gold atoms held private.
- **132** source-provisioned candidate observations across three works; **103 prefix + 29 heldout**, with exact private original byte-anchor checks. No independent human verification and no model-weight training.
- Source-prefix partiality, not completeness: A first four chapters 25,234 bytes, 219 nonblank lines, 34 lines containing an anchor; B 17,579 bytes, 135 nonblank lines, 31 anchored; C first two chapters 17,548 bytes, 167 nonblank lines, 29 anchored. Therefore any full-chapter one-to-one claim **fails before inverse**. These counts are evidence of *incompleteness*, not literary accuracy rates.
- A/B had **41 provisional open axis names**; among C's 30 test observations, **13** used previously unseen axis names (11 distinct new names). Vocabulary growth cannot be equated with logic understanding.
- Private local SHA of frozen semantic evaluation rubric: `90c01a28fef46c51cd9cb4239a29f824b9bccba59e80971762c9809ca7f1101e`. This is authored by the same investigator, not independent gold.

**Source-index error caught before model launch:** naive repeated chapter title detection picked the *last repeated chapter 1* of a later volume instead of C's original opening, giving impossible source offsets. Rewrote private indexing to select the first ascending first-volume 1..20 sequence, corrected several wrongly attributed chapter numbers, verified all 132 exact byte spans. The earlier mistaken selections are not evidence of comprehension and should not be hidden.

## Causal-direction source reading

A private source-anchored direction ledger captured **19 provisional** relations, with **4 whose explanation appears later in the text than the result**, plus three deliberately rejected causal arrows. Reading/display order is not event/causal chronology.

Examples in generic words:

- Scarce family treasury access predates observed differential strength although the narrator explains it *after* first showing the rivalry. Flipping that arrow would be an error.
- Eligibility age is a default institutional route; a privileged older applicant can obtain an exception. An exception does **not** mean anyone is automatically accepted.
- Competing factions and recruitment pressure operate independently of protagonist decisions.
- A child can conclude an absent director no longer cares while that adult retains a private plan and maintains protection; child's conclusion is not the world's objective fact.
- A repeatable strange effect can establish a candidate trigger, **not** an unseen object's final mechanism.

This ledger is self-annotated and provisional. It is not a signature of semantic truth.

## Real holdout model, no invented outputs

Actual [GitHub Actions run #43414129666](https://github.com/66tyu55/WriterForge/actions/runs/43414129666) **SUCCESS as an execution**, not a literary pass. A pinned CPU **Qwen2.5-3B-Instruct Q4_K_M** received the same 30 anonymous C-source observations relocated into a different science-fantasy setting. Future C chapters, book title, identities and private gold were **not** in its model input. Two real calls; no retries, no paid API. All original prompts/raw engine outputs preserved in artifact `WF-NonTime-RealOriginal-SchemaVsSourceLearning-TwoArm-20261113`, artifact ID `14031262557`.

| Arm | Prompt / completion tokens | JSON | Inverse literary result |
| --- | ---: | --- | --- |
| Baseline: C observations only | 1205 / 400 | VALID | **FAIL**: put all 30 observation IDs into `constraints` without reconstructing any stated constraints; returned only a source ID for intervention and confused known observations with unknowns |
| Source learning from A/B: same C observations + six prior-work learning habits | 1466 / 496 | VALID | **FAIL**: again put all 30 IDs in `constraints`; listed already observed choices among possible futures, failed to explain altered-character consequences; counterfactual was only `C027` |

The stronger arm had **more prompt and output tokens**; even a superficial category difference would be confounded by extra context. Crucially **neither arm generated a justified causal reconstruction**. Valid JSON ≠ source understanding. No out-of-distribution transfer or literary uplift proven. Do not run the same frozen test again or revise its prompt to manufacture passing grades.

## Small source-driven correction AFTER frozen model run

The runtime core now allows explicit `any_of` groups for **source-evidenced alternate admissibility paths** (e.g. default eligibility versus exceptional patron permission), while preserving separate actual outcome and protagonist choice. It also distinguishes `REPORTED`, `CHARACTER_BELIEF`, `CHARACTER_INFERENCE`, `CHARACTER_KNOWLEDGE_LIMIT` etc, and never turns hearsay into knowledge by witnessing. These are *mechanical repair hypotheses* informed by the originals, **not** a post-hoc re-scoring of frozen model replies.

Targeted synthetic/mechanical preflight CI: [Actions #43415129655](https://github.com/66tyu55/WriterForge/actions/runs/43415129655) SUCCESS (15 source-world regressions + 7 source-disjoint preflight tests). Existing unmodified full WF CI still fails because of old missing external artifacts/historical dependency tests; targeted success does not override it.

## Stop/promotion gate

All three Skills remain SHADOW; literary transfer and 1:1 original comprehension **NOT PASSED**. The evidence has demonstrated four priorities for *source work* instead of more calculators:

1. **Coverage**: one contiguous original episode must capture material daily life, unnamed people, links, all observed actions and exclusions, not just 30 important facts. Track omissions and narrative sentence coverage explicitly.
2. **Causal identity**: require anchored directed claims, counter-examples and distinctions between presentation order, past cause, current action, contingent event, inferred mechanism, and unknown. Never backfill the exact later twist.
3. **Character cognition**: actor-by-actor belief, witnessed fact, information channel, misconception, resource cost and irrational act; autonomous off-screen events remain real but not arbitrarily invented.
4. **One true new heldout**: after sources and encoding are independently reviewed and frozen, use a **different original/world** as evaluation rather than recycle C and its known answers. Restore the original causal logic under renaming; changed personality should yield legitimate different outcomes while world constraints persist. Pass/fail must be adjudicated independently, with errors retained.

No merge to `main`, no production WF author, Canon, R2, Xuehai, Railway, or other assistant's time branch touched. **Engineering improved; source parameter correctness and literary inverse remain UNVERIFIED/FAILED.**

## Source reading after FAILED model — one contiguous chapter, every paragraph

Instead of re-calling the same failed frozen decoder, the investigator performed an additional **real original-text** reading of B's entire first chapter (5,080 raw GB18030 bytes). All **38/38 nonblank paragraphs** were checked against exact private byte spans, producing **71 separate provisionally interpreted semantic atoms**. Original paragraphs and private character/world crosswalk remain outside GitHub. Private local ledger SHA256: `b9f9a1f0ceedb9d93876af52818617ae53f5eead241aae8efcbb63b454ba68d7`.

The paragraph pass distinguished ordinary spatial facts that the earlier abstract encoding had missed (e.g. a damaged wall gives an acoustic observation channel, not necessarily knowledge of the conversation), independent incidental characters, compensation for rare literacy, the trust history behind an uncle's recruitment, economic promises rather than guaranteed wages, hidden aspirations and limited child understanding. The last paragraph foreshadows a later life course **to the reader** but does not grant it to the acting child. A sealed-future test must account for such narrator prolepsis already visible in the prefix.

**Important:** 38/38 paragraph-level coverage is NOT sentence-atomic 1:1 mapping. It does not claim every semantic relationship has been extracted or independently approved. Current stage is `SELF_PROVISIONAL`, with no retrained model and no subsequent blind inverse. The original run's failure remains unchanged.

### Complete private three-section reading, without shrinking the original to rules

An immutable further **v3.1 private revision** preserves all 38 original paragraphs verbatim next to the 71 anchored micro-annotations plus **7 open-ended reading reflections** (source text + annotations + reflections). This source study follows the author's requirement that full original and observations must coexist, rather than replacing literature with numeric parameters or `add details` slogans. Private SHA256: `51b3692744b24478bac80261b68c5132f1aee694433c595db499a86023219908`. Neither file is in GitHub/R2.

Key reflections include: cracked walls as an incomplete information channel; literacy and naming as pre-existing small-scale services; intersecting kinship, wealth, status and hope; a rural family's decision under a recruiter's wage claims; narrator's future foreshadow not becoming character knowledge; and why altering the child's desire in another world may change the plot while leaving the economic institution intact. **These are investigator interpretations, not independent truth or improved author prose.**
