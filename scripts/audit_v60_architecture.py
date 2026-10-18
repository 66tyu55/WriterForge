"""V60 evidence-only architecture inventory and trace audit.

Runs locally on checked-out repository source. No model/R2/network/novel reads,
no writes to production stores, no code transformation and no promotions.
Automated probes that reproduce flaws are OBSERVATIONS, not passing remedies.
"""
from __future__ import annotations

import argparse
import ast
from collections import Counter, deque
from hashlib import sha256
import json
from pathlib import Path
import re

FORMAT = "writerforge.v60-readonly-architecture-audit.v1"
BASE_COMMIT = "3e589412acabaee95e9881923b0f3fa4cc7080c2"
OUTPUT = "v60_architecture_audit_receipt.json"

CORE = (
    "writerforge/source_study.py",
    "writerforge/xuehai.py",
    "writerforge/verified_flow.py",
    "writerforge/writing_assist.py",
    "writerforge/writing_flow.py",
    "writerforge/v31_autonomous_core.py",
    "writerforge/v35_observable_trace.py",
    "writerforge/v38_lesson_transfer_bridge.py",
    "writerforge/fact_journal.py",
    "writerforge/structural_observer.py",
    "writerforge/actual_reader.py",
    "writerforge/feedback.py",
    "writerforge/evolution.py",
    "writerforge/db.py",
    "writerforge/cli.py",
    "writerforge/scene_learning.py",
    "writerforge/corpus_foundation.py",
    "writerforge/r2_storage.py",
)

def sha(path: str) -> str:
    return sha256(Path(path).read_bytes()).hexdigest()

def source(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")

def locate(path: str, needle: str) -> dict:
    contents = source(path)
    index = contents.find(needle)
    if index < 0:
        raise ValueError(f"V60_EVIDENCE_ANCHOR_MISSING:{path}:{needle[:70]}")
    start = contents.count("\n", 0, index) + 1
    return {"path": path, "line": start, "anchor": needle,
            "sha256": sha(path)}

def imports_from(tree: ast.AST, path: str):
    edges = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if node.level and node.module:
                head = node.module.split(".")[0]
                if node.level == 1:
                    edges.add("writerforge." + head)
            elif node.module and node.module.startswith("writerforge."):
                edges.add("writerforge." + node.module.split(".")[1])
        elif isinstance(node, ast.Import):
            for item in node.names:
                name = item.name
                if name.startswith("writerforge."):
                    edges.add("writerforge." + name.split(".")[1])
    return sorted(edges)

def package_graph(paths):
    graph = {}
    for p in sorted(paths):
        tree = ast.parse(source(p), filename=p)
        graph["writerforge." + Path(p).stem] = imports_from(tree, p)
    return graph

def reachable(graph, origin):
    visited = {origin}
    queue = deque([origin])
    while queue:
        for to in graph.get(queue.popleft(), []):
            if to in graph and to not in visited:
                visited.add(to)
                queue.append(to)
    return sorted(visited)

def finding(identifier, priority, label, implication, anchors,
            kind="OBSERVED_IMPLEMENTATION_BOUNDARY", next_action=""):
    return {
        "id": identifier, "priority": priority, "kind": kind,
        "observed": label, "impact_if_unaddressed": implication,
        "evidence": [locate(path,needle) for path,needle in anchors],
        "next_action": next_action,
        "literary_ability_improved": False,
    }

def audit():
    package_paths = sorted(str(p).replace("\\","/")
                           for p in Path("writerforge").glob("*.py"))
    tests = list(Path("tests").glob("test_*.py"))
    workflows = list(Path(".github/workflows").glob("*.yml"))
    graph = package_graph(package_paths)
    normal = reachable(graph,"writerforge.verified_flow")
    writing = reachable(graph,"writerforge.writing_assist")
    claims = []
    claims.append(finding(
        "WF60-P0-001","P0",
        "Official source-grounded writing retrieves Xuehai entries, but its "
        "prompt assembly has no explicit source-derived decision/action object.",
        "Source membership can change without changing the draft directive. "
        "A verified source reference is not proof that a literary lesson was "
        "applied or that behavior improved.",
        [("writerforge/verified_flow.py","evidence = get(mapped) if mapped else get(None)"),
         ("writerforge/verified_flow.py","craft_ids = tuple(t.id for t in craft.techniques)"),
         ("writerforge/verified_flow.py","prompt = ("),
         ("writerforge/verified_flow.py","tuple(evidence), craft_ids, prompt,")],
        kind="BEHAVIORALLY_REPRODUCED_DIAGNOSTIC",
        next_action="Introduce a gated CreativeDecision contract between "
                    "LEARN evidence and WRITE planning; keep source excerpts "
                    "out of generated prompt."))
    claims.append(finding(
        "WF60-P0-002","P0",
        "Autonomous V31 rule cards and V38 lesson-transfer checks exist as "
        "experiments, but are not explicit dependencies of inspected official "
        "VerifiedWritingFlow.prepare path.",
        "The host may demonstrate model rule-memory changes in one pilot "
        "without them becoming a reproducible independent literary decision.",
        [("writerforge/v31_autonomous_core.py","def writer_instruction("),
         ("writerforge/v38_lesson_transfer_bridge.py","def verify_lesson_transfer_claims("),
         ("writerforge/v35_observable_trace.py","if learned_lessons is not None or lesson_transfer_claims is not None:"),
         ("writerforge/verified_flow.py","def prepare(")],
        kind="STATIC_IMPORT_AND_ENTRYPOINT_FINDING",
        next_action="Do not blindly merge experimental rules. Map one frozen "
                    "lesson to an explicit prewrite select/skip decision and "
                    "postwrite evidence with zero promotion."))
    claims.append(finding(
        "WF60-P0-003","P0",
        "Generic EvolutionEngine numeric-promotion API accepts self-supplied "
        "ratings and optional human-anchor requirement.",
        "Without an independent receipt verifier upstream, caller-supplied "
        "high scores can satisfy a generic promotion decision. This does "
        "NOT demonstrate that a public production route is exploitable.",
        [("writerforge/evolution.py","class PromotionGate:"),
         ("writerforge/evolution.py","requires_human_anchor: bool = False"),
         ("writerforge/evolution.py","policy: str = \"gated_auto\"")],
        kind="BEHAVIORALLY_REPRODUCED_DIAGNOSTIC",
        next_action="Attach immutable external proof and a fixed, non-bypassable "
                    "subjective-skill approval policy; keep V49 no-promotion."))
    claims.append(finding(
        "WF60-P0-004","P0",
        "OriginalStudy's eight-track classification is explicit deterministic "
        "keyword structure, not a verified literary understanding stage.",
        "Publishing its structural snapshot alone must not grant a literary "
        "mechanism permission to guide future prose.",
        [("writerforge/source_study.py","SOURCE_SIGNALS = {"),
         ("writerforge/source_study.py","def _structural_analysis(sentence: str)"),
         ("writerforge/source_study.py","\"analysis_level\": \"deterministic_structural_unverified\""),
         ("writerforge/verified_flow.py","row[\"status\"] != \"published\"")],
        kind="IMPLEMENTATION_LIMITATION_CORRECTLY_LABELED",
        next_action="Separate locatable source units, hypotheses, corroborated "
                    "experience and approved writing policy."))
    claims.append(finding(
        "WF60-P1-005","P1",
        "Core story/learning and the temporal FactJournal are independently "
        "opened SQLite stores with separate CLI database selectors.",
        "No single atomic commit spans both stores in this inspected route. "
        "Physical separation may be desirable for privacy; missing mapping "
        "and version pinning are the architectural issue.",
        [("writerforge/cli.py","p.add_argument(\"--db\",default=\"writerforge.sqlite3\""),
         ("writerforge/cli.py","record.add_argument(\"--journal\",required=True)"),
         ("writerforge/fact_journal.py","self.db = sqlite3.connect(str(file)"),
         ("writerforge/db.py","class WriterForgeDB:")],
        kind="MULTI_LEDGER_INTERFACE_RISK",
        next_action="Define durable source/scene/entity ID mapping and a "
                    "cross-ledger transaction/compensation boundary; "
                    "do not merge entire R2 libraries into memory."))
    claims.append(finding(
        "WF60-P1-006","P1",
        "FeedbackStore counts distinct supplied reader_id values as "
        "convergent reader signals, without a verifier at this layer.",
        "Two independently typed IDs alone cannot prove two genuine "
        "readers or reliable literary criticism.",
        [("writerforge/feedback.py","def add(self, *, reader_id"),
         ("writerforge/feedback.py","COUNT(DISTINCT reader_id) AS readers"),
         ("writerforge/actual_reader.py","source_url=r.get(\"source_url\",\"\")")],
        kind="BEHAVIORALLY_REPRODUCED_DIAGNOSTIC",
        next_action="Use evidence-provenance levels and verified independent "
                    "reviewer identities before advice can promote skill."))
    claims.append(finding(
        "WF60-P1-007","P1",
        "Reader literature and source-span analysis remain intentionally "
        "provisional despite names that may imply real interpretation.",
        "Comment URL fields and model-reader notes are references or proposals, "
        "not independently authenticated reception history.",
        [("writerforge/actual_reader.py","def _load(self):"),
         ("writerforge/actual_reader.py","source_url=r.get(\"source_url\",\"\")"),
         ("writerforge/scene_learning.py","model_literary_interpretation_unreviewed")],
        kind="PROVENANCE_REVIEW_REQUIRED",
        next_action="Audit comment retrieval dates, author identity, "
                    "quotation privacy, deduplication and independence."))
    claims.append(finding(
        "WF60-P1-008","P1",
        "Official package metadata stays at version 27.0.0 while V59 "
        "refers to a development branch; one-shot CI workflows are numerous.",
        "Tests and version labels are not the same as a releasable runtime. "
        "Publishing without a verified migration path would be risky.",
        [("pyproject.toml","version = \"27.0.0\""),
         ("README.md","# WriterForge V27"),
         ("writerforge/fact_journal.py","def _initialize_global_clock(")],
        kind="RELEASE_AND_MIGRATION_BOUNDARY",
        next_action="Consolidate release matrix and migration preflight "
                    "without deleting historical one-shot workflow evidence."))

    gaps = sorted(x["id"] for x in claims)
    # Static import traversal is only evidence about direct Python imports,
    # not proof about runtime monkey-patching, dynamic strings or third-party
    # adapters, and MUST NOT be labeled exhaustive call tracing.
    graph_subset = {
        k: [v for v in graph.get(k,[]) if v in graph]
        for k in [
            "writerforge.verified_flow","writerforge.writing_assist",
            "writerforge.writing_flow","writerforge.xuehai",
            "writerforge.v31_autonomous_core",
            "writerforge.v35_observable_trace",
            "writerforge.v38_lesson_transfer_bridge",
            "writerforge.fact_journal","writerforge.structural_observer",
            "writerforge.evolution",
        ]
    }
    report = {
        "format": FORMAT, "audited_ref": "v59-global-ledger-clock-audit",
        "audited_commit": BASE_COMMIT, "source_files_changed": False,
        "model_calls": 0, "r2_network_calls": 0,
        "real_literary_training_performed": False,
        "v49_status_unchanged": "THIRD_STRIKE_FAILED",
        "result": "ARCHITECTURE_GAPS_OPEN_NO_PROMOTION",
        "inventory": {
            "top_level_python_modules": len(package_paths),
            "unittest_modules": len(tests),
            "workflow_yml_files": len(workflows),
            "core_evidence_file_sha256": {p: sha(p) for p in CORE},
        },
        "static_python_import_graph": graph_subset,
        "official_writing_reachable_modules": {
            "verified_flow_root": len(normal),
            "writing_assist_root": len(writing),
            "v31_autonomous_reached_by_verified_flow":
                "writerforge.v31_autonomous_core" in normal,
            "v38_transfer_reached_by_verified_flow":
                "writerforge.v38_lesson_transfer_bridge" in normal,
        },
        "static_analysis_limits": [
            "AST imports alone cannot establish runtime reachability for "
            "dynamic imports, injected services, monkeypatches or external "
            "host plugins.",
            "Synthetic negative diagnostics test an API's present behavior, "
            "not full production exploitability or literary quality.",
            "No connected R2 data, proprietary corpus, private model output "
            "or authenticated reader accounts are accessed.",
        ],
        "open_findings": claims,
        "open_finding_ids": gaps,
        "recommended_order": [
            "Freeze authority/provenance and experience status policy",
            "Specify one no-copy CreativeDecision input/output contract",
            "Trace actual LEARN->candidate->select/skip->draft->postcheck "
            "without model calls, using synthetic fixtures",
            "Design dual-store ID and evidence pinning adapter",
            "Prohibit subjective promotion without verified independent "
            "external approval",
            "Only after engineering closure, pre-register independent "
            "literary evaluation on new tasks",
        ],
    }
    return report

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--out",default=OUTPUT)
    args = p.parse_args()
    result=audit()
    raw=json.dumps(result,ensure_ascii=False,sort_keys=True,indent=2)+"\n"
    Path(args.out).write_text(raw,encoding="utf-8")
    print(json.dumps({
        "format":FORMAT,
        "receipt_sha256":sha256(raw.encode()).hexdigest(),
        "open_findings":len(result["open_findings"]),
        "priority_0":sum(x["priority"]=="P0"
                          for x in result["open_findings"]),
        "status":result["result"],"training_calls":0
    },ensure_ascii=False))
    # An audit can finish correctly while the architecture remains deficient.
    # Never label zero exit code as literary promotion or resolved findings.

if __name__=="__main__":
    main()
