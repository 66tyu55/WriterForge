# Upstream Skill Placement Map

The placement below answers one question: **if the mechanism is useful, which existing WriterForge owner should absorb it?**

Legend:
- **ADOPT** — new mechanism with clear value; schedule assimilation.
- **MERGE** — WriterForge already has the capability; strengthen that owner, do not create a new Skill.
- **WATCH** — useful idea, but not enough evidence or not urgent.
- **REJECT** — unrelated, overly rigid, duplicate, or wrong for fiction.

## Anthropic / skills

| Upstream skill | Decision | WriterForge owner | What survives |
|---|---|---|---|
| skill-creator | ADOPT | Evolution Engine | baseline-vs-candidate eval, held-out tests, qualitative review, trigger evaluation, lean iterative improvement |
| discernment-nudge | WATCH | Human review / Taste | lightweight human reflection points; never a writing-time nag |
| doc-coauthoring | WATCH | Revision / human review | staged context transfer and reader verification |
| academy-guide | REJECT | — | product-specific |
| algorithmic-art / canvas-design / brand-guidelines / frontend-design / theme-factory | REJECT | — | visual-art domain |
| docx / pdf / pptx / xlsx / web artifacts / webapp testing / slack gif / mcp builder / claude-api | REJECT | — | tooling, not novelist capability |

## Matt Pocock / skills

| Upstream skill | Decision | WriterForge owner | What survives |
|---|---|---|---|
| writing-for-agents | ADOPT | Reactive Runtime + Skill Architecture | context pointers, progressive disclosure, one source of truth, pruning/no-op detection, context-load vs cognitive-load |
| writing-fragments | MERGE | Discovery | explore before exploit; preserve promising fragments without prematurely structuring them |
| writing-beats | MERGE | Multiscale Craft / Reader State | each beat requires already-grounded reader concepts and may ground new ones |
| writing-shape | MERGE | Revision / Observed Story | ask what each paragraph newly does; cut blocks that do not earn their place |
| grill-me / grilling | ADOPT | Story Sense offline stress test | relentless branch-by-branch challenge of assumptions |
| grill-with-docs | MERGE | Story Bible / Story Sense | stress-test story decisions while writing durable decisions/glossary |
| diagnosing-bugs | MERGE | Evolution Engine | root-cause before edit; do not patch symptoms |
| research | MERGE | LEARN research support | evidence gathering before durable change |
| retro | MERGE | Experience Ledger | post-run review of what actually failed/succeeded |
| handoff / claude-handoff | MERGE | Memory Budget / Recovery | durable handoff packet instead of conversational recall |
| wayfinder | WATCH | Story Sense | navigation through large problem spaces |
| code-review / implementation / merge / TS / pre-commit / code architecture family | REJECT | — | engineering-specific |
| writing-for-agents' negative-prompt warning | ADOPT | Skill authoring policy | describe desired behavior positively; keep prohibitions only for hard guards |

## obra / superpowers

| Upstream skill | Decision | WriterForge owner | What survives |
|---|---|---|---|
| systematic-debugging | ADOPT | Evolution Engine | root-cause investigation before Skill edits |
| test-driven-development | MERGE | Evolution Curriculum | reproduce failure first, then candidate fix, then regression |
| verification-before-completion | ADOPT | Promotion Gate | no “improved” claim without fresh evidence |
| writing-skills | MERGE | Skill Birth / Skill authoring | test workflow instructions as executable behavior, not documentation prose |
| brainstorming | WATCH | Story Architecture | scale process to scope; avoid coding-style approval gates in ordinary fiction |
| subagent-driven-development | WATCH | Offline Evolution | independent proposer/reviewer pattern only for expensive upgrade work |
| dispatching-parallel-agents | WATCH | Offline Evaluation | parallel candidate evaluation where independent work is safe |
| executing-plans / git-worktrees / branch-finishing / code-review family | REJECT | — | software workflow |

## Context Engineering skills

| Upstream skill | Decision | WriterForge owner | What survives |
|---|---|---|---|
| context-compression | ADOPT | Memory Budget + Recovery | anchored incremental summaries, artifact trail, probe-based compression tests, optimize tokens-per-task |
| context-degradation | ADOPT | Reactive Runtime | detect stale/conflicting/distracting context before adding more context |
| context-optimization | MERGE | Reactive Runtime | pruning, caching, routing, selective loading |
| long-horizon-prompting | ADOPT | Long-form Runtime | phase-aware long-horizon context discipline |
| memory-systems | MERGE | Memory architecture | distinguish scratch/current/episodic/semantic memory and retrieval responsibility |
| filesystem-context | MERGE | Experience Archive | durable file-backed history instead of prompt stuffing |
| latent-briefing | WATCH | Scene/Chapter Context Pack | compact situation brief before expensive generation |
| bdi-mental-states | ADOPT | Character Engine | beliefs/desires/intentions as separate decision state; keep fact != belief |
| advanced-evaluation | ADOPT | Literary Taste + Evolution | pairwise judge design, bias controls, repeated judgment |
| evaluation | MERGE | Eval Lab | evaluation sets, failure categories, regression |
| self-improvement-loops | ADOPT | Evolution Engine | optimization ladder; fix at lowest adequate rung; hidden evaluator; raw-trace archive; two-split acceptance |
| harness-engineering | MERGE | Evolution governance | locked/editable/append-only surfaces and rollback |
| multi-agent-patterns | WATCH | Offline Evolution | proposer-verifier separation |
| book-sft-pipeline example | WATCH | LEARN | useful packaging ideas only; never replace Reader-First sequential learning |
| hosted-agents / tool-design / project-development / generic examples | WATCH | tooling | only if runtime implementation later needs them |

## leonxlnx / taste-skill

| Upstream skill | Decision | WriterForge owner | What survives |
|---|---|---|---|
| taste-skill / gpt-tasteskill | MERGE | Literary Taste | read-the-room first; choose aesthetic intervention from context; critique before output |
| taste-skill-v1 | WATCH | Taste history | compare evolution, not runtime |
| brandkit / brutalist / minimalist / soft / redesign / stitch / image/UI skills | REJECT | — | visual design domain |

The useful lesson is **selection discipline**, not web-design rules or aesthetic checklists.

## wordflowlab / novel-writer-skills

| Upstream skill | Decision | WriterForge owner | What survives |
|---|---|---|---|
| story-consistency-monitor | MERGE | Validators / Canon / Knowledge / Timeline | contradiction classes and intentional-exception support |
| forgotten-elements-reminder | ADOPT | Promise/Payoff + Reader Memory | dormancy detection for characters, promises, motifs, plotlines |
| pre-write-checklist | REJECT-AS-IMPLEMENTED / MERGE-IDEA | Reactive Context Pack | do not reread nine files every write; replace with fingerprinted selective loading |
| requirement-detector | MERGE | Router | infer which existing capability is needed |
| setting-detector | MERGE | Genre/World router | route only relevant setting knowledge |
| style-detector | MERGE | Project Taste | detect project-specific style state, not global imitation |
| dialogue-techniques | MERGE | Dialogue Action | keep functional dialogue mechanisms only |
| scene-structure | MERGE | Scene Craft | keep scene turn / reaction-dilemma-decision mechanisms |
| fantasy / mystery / romance | WATCH | Genre Profiles | harvest genre-specific reader promises; do not hard-code formulas |
| workflow-guide / getting-started | REJECT | — | wrapper documentation, no new capability |

## Placement summary

```text
LEARN
  <- research
  <- optional book-pipeline packaging ideas

Character Engine
  <- BDI mental states

Story Engine / Story Sense
  <- grill / assumption stress test
  <- scene structure
  <- dormancy signal

Craft Engine
  <- dialogue techniques
  <- beat grounding
  <- paragraph contribution tests

Reader / Literary Taste
  <- read-the-room selection
  <- advanced pairwise evaluation

Memory / Reactive Runtime
  <- context pointers
  <- context degradation
  <- anchored compression
  <- handoff / recovery

Evolution Engine
  <- skill-creator
  <- systematic debugging
  <- TDD-style failure reproduction
  <- verification-before-promotion
  <- self-improvement optimization ladder

Research-only / Rejected
  <- UI, slides, docs, spreadsheets, code workflow, product-specific skills
```

## Important non-adoptions

Three popular patterns are explicitly **not** copied into WriterForge:

1. “Always read every file before writing.” WriterForge uses dependency fingerprints and selective context loading.
2. “Every warning must block generation.” Fiction needs intentional contradiction, unreliable narration, discovery, and ambiguity.
3. “Popularity means quality.” Popularity is used only to prioritize inspection. Literary evidence still comes from original works, reader data, and project outcomes.
