---
name: observe-before-next-choice
description: Source-grounded decision habit for a writing AI. Use when continuing a story after earlier authored choices might conflict with an old outline; distinguish actual prose, beliefs, unknowns and pending plans before autonomously choosing the next action.
compatibility: Python 3.10+ for optional offline conformance script. Activation itself only requires reading text and a text-capable AI model. No network, API keys, WF database or private novel corpus required.
metadata:
  wf-habit-id: observe-before-next-choice
  wf-revision: "1"
  wf-lifecycle: shadow
---

# Observe before next choice

This is a **portable cognitive procedure**, not an author, automatic judge, training dataset, source memory or coding patch. Its source-of-truth is [capsule.json](capsule.json), a bounded, versioned habit contract. The same procedure may be used with different host models; native prompts and tool affordances can differ, but evidence/authority boundaries must not.

## Activate only when

An actual prose-writing or decision task has **earlier original text** available and an unresolved next choice. Do not activate simply because a story contains a word matching an alleged error. If source identity cannot be verified or context cannot be delivered, **skip or remain dormant**, not guess what happened.

## Procedure

1. Read the relevant previously authored **literal original prose** with its source checksum. Separate text that was actually written from old planned beats. A matching hash verifies bytes against its expected hash, **not** that a fictional event is a world fact or that any claimed causal link is true.
2. Ask which actions and consequences are on the page, which statements are characters' beliefs, which matters remain unknown, and which proposed decisions never happened. A past decision or proposed action does not guarantee the proposed outcome.
3. **Let the host's actual writing model choose** the next move, pause, deliberate repetition, intentional failure, refusal, or revision based on its literary priorities. Do **not** automatically ban repeated words/actions, force reversal, auto-edit prose or select an apparent literary winner.
4. Keep the chosen plan/new prose as an **unaccepted candidate**. Preserve original source provenance and the candidate response separately. Do not promote uncertainty to KNOWN or Canon, modify private study material, or insert reviewer findings into the author's voice.
5. If provenance, a supported host capability or a measurable benefit is absent, **stop the expensive branch** and record an appropriate failure/dormant disposition. More iteration is not automatically better.

## Evidence and falsification

The intended benefit is stronger new choices grounded in earlier, actually written decisions—not test-detector compliance. **Pre-register** comparable stories, model/budget, held-out genres, and counterexamples: meaningful deliberate repetition, lawful ellipsis, limited POV and long quiet scenes.

The habit can be falsified by paired future tasks that do not improve choices, consistently worsen prose or legal repetition, or work only on the developer host. Also measure **full** cost including discarded candidates and judgments. A single model family's numerical literary rating is not proof of progress.

## Portability boundary

This skill directory can be copied independently of WriterForge. The optional [scripts/portable.py](scripts/portable.py) validates a pinned capsule SHA and renders the **same inner semantic activation contract** as either chat messages or a plain prompt. Different host envelopes are adapters, not learned abilities.

The source excerpts come from the host's current authorized workspace; they must **never be packaged inside this skill**. Never copy user books, chat memory, internal chain-of-thought, credentials or novel Canon into this directory. JSON encoding and labeling external excerpts as data reduce confusion but **do not guarantee prompt-injection safety**. Do not execute prose or untrusted scripts.

Until independent matched tasks are tested on at least two actual host models, the state is **SHADOW / portability and literary gain unproven**.

## Offline interface

```text
python scripts/portable.py verify --capsule capsule.json
python scripts/portable.py render --capsule capsule.json --input references/synthetic_example.json --host chat
python scripts/portable.py render --capsule capsule.json --input references/synthetic_example.json --host plain
```

Outputs are structured on stdout; no provider call is made. In production, pin the SHA from a trusted release/manifest and pass it using `--sha256` to reject a changed capsule. The example is synthetic, never original source evidence.

## Stop and mutation discipline

This is **not a self-rewriting program**. A candidate modification must be separately proposed with its parent content SHA, authentic counterexamples and a fixed held-out/transfer comparison, then reviewed through the **existing** WriterForge Evolution governance. It cannot directly edit another Skill, overwrite a failing model wire, change an evaluator/threshold, or approve itself. DORMANT and QUARANTINED are valid outcomes; retirement does not erase immutable negative evidence.
