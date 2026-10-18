"""V63 whole-WriterForge source audit (structured metadata, no prose/network).

This inventory does not certify execution safety. Calls resolved through
dynamic imports, plugins, monkeypatching, raw SQLite and external processes
cannot be conclusively enumerated by AST. Separate structural/test results
from still open architecture/authority boundaries.
"""
from __future__ import annotations
import ast
from collections import Counter
from hashlib import sha256
from pathlib import Path
import json
import re

FILENAME="v63_full_architecture_receipt.json"
CALLS={
 "promote","_promote_verified","register","revalidate",
 "apply_upgrade","accept_candidate","accept_draft",
 "commit","prepare","local_chat_completion","decide",
 "report_postwrite","revoke_candidate","read_decision",
 "validate_live_decision","backup","restore","read",
}
CORE_FILES=(
 "writerforge/evolution.py",
 "writerforge/experience_decision.py",
 "writerforge/db.py","writerforge/story_commit.py",
 "writerforge/writing_flow.py",
 "writerforge/verified_flow.py",
 "writerforge/cli.py","writerforge/runtime.py",
 "writerforge/r2_storage.py","writerforge/feedback.py",
 "writerforge/actual_reader.py",
 "writerforge/source_study.py",
 "writerforge/v31_autonomous_core.py",
 "writerforge/v38_lesson_transfer_bridge.py",
)
OUTPUT_TRUST="STRUCTURAL_REVIEW_REQUIRES_HUMAN_AND_FURTHER_TESTS"


def sha(path):
    return sha256(Path(path).read_bytes()).hexdigest()


def calls():
    findings=[]
    all_paths=[]
    for group in ("writerforge","scripts","tests"):
        all_paths += list(Path(group).rglob("*.py"))
    for p in sorted(all_paths):
        tree=ast.parse(p.read_text(encoding="utf-8"),filename=str(p))
        for n in ast.walk(tree):
            if not isinstance(n,ast.Call) or not isinstance(n.func,ast.Attribute):
                continue
            if n.func.attr not in CALLS:
                continue
            receiver=ast.unparse(n.func.value)[:70]
            findings.append({
                "path":p.as_posix(),"line":n.lineno,
                "method":n.func.attr,"receiver":receiver,
                "production":p.as_posix().startswith("writerforge/"),
            })
    return all_paths,findings


def anchor(path,txt):
    raw=Path(path).read_text(encoding="utf-8")
    i=raw.find(txt)
    if i<0:
        raise AssertionError("ARCHITECTURE_ANCHOR_NOT_FOUND:"+path+":"+txt)
    return {"path":path,"line":raw.count("\n",0,i)+1,
            "sha256":sha(path)}


def issue(name,kind,details,anchors):
    return {"id":name,"state":"OPEN","kind":kind,
            "reason":details,
            "anchors":[anchor(a,b) for a,b in anchors]}


def audit():
    files,sites=calls()
    by_kind=Counter(site["method"] for site in sites)
    production=[s for s in sites if s["production"]]
    pkg=list(Path("writerforge").rglob("*.py"))
    tests=list(Path("tests").glob("test_*.py"))
    flows=list(Path(".github/workflows").glob("*.yml"))
    scripts=list(Path("scripts").glob("*.py"))
    dbtext=Path("writerforge/db.py").read_text(encoding="utf-8")
    schema_tables=sorted(set(re.findall(
        r"CREATE TABLE IF NOT EXISTS ([a-zA-Z0-9_]+)",dbtext)))
    refs=list(Path("references/experience").glob("*.json"))
    for p in refs:
        doc=json.loads(p.read_text(encoding="utf-8"))
        if doc.get("novel_excerpt") or doc.get("status")=="VERIFIED":
            raise AssertionError("PRIVATE_SOURCE_POINTER_MISCLASSIFIED")
    unresolved=[
        issue(
            "WF63-RISK-ROOT-BOOTSTRAP","capability bootstrap",
            "A trusted Python host can register a NEW capability at high "
            "ACTIVE level without independent literary validation. This "
            "is a baseline-import policy boundary, not a duplicate-promotion "
            "path. Registry does block same-name overwrite and direct "
            "promotion, but this creation route remains separate.",
            [("writerforge/evolution.py","def register(self, contract: CapabilityContract)"),
             ("writerforge/evolution.py","proposed=self._snapshot(contract)")]),
        issue(
            "WF63-RISK-NATIVE-SQLITE","raw database write boundary",
            "A process with raw SQLite write privileges can modify skill "
            "levels/approval records outside checked APIs. A local Python "
            "library is not a sandbox or externally witnessed ledger.",
            [("writerforge/db.py","CREATE TABLE IF NOT EXISTS skill_capabilities"),
             ("writerforge/db.py","CREATE TABLE IF NOT EXISTS experience_approvals")]),
        issue(
            "WF63-RISK-RAW-STORY-COMMIT","direct story effect route",
            "Low-level WritingFlow/StoryCommitCoordinator accepts effects "
            "for legitimate human/host writing. Only the official "
            "VerifiedWritingFlow/accept_candidate AI route currently "
            "binds an experience decision; a hostile in-process plugin "
            "must not be assumed unprivileged.",
            [("writerforge/writing_flow.py","def accept_draft("),
             ("writerforge/story_commit.py","class StoryCommitCoordinator:"),
             ("writerforge/verified_flow.py","def accept_candidate(")]),
        issue(
            "WF63-RISK-MODEL-INFLIGHT","inflight generation cancellation",
            "Transactions block stale acceptance after revocation, but "
            "cannot revoke a completed model prompt already handed "
            "to a running external model; cancellation is unverified.",
            [("writerforge/verified_flow.py","def local_chat_completion("),
             ("writerforge/verified_flow.py","def accept_candidate(")]),
        issue(
            "WF63-RISK-EXTERNAL-IDENTITIES","reviewer provenance",
            "HMAC proves the configured key holder signed an instruction; "
            "it does not establish that a human literary reviewer is "
            "independent, that the work is licensed, or that a mechanism "
            "was understood.",
            [("writerforge/experience_decision.py","def _check_signature("),
             ("writerforge/evolution.py","def _require_attestation(")]),
        issue(
            "WF63-RISK-LOCALE-TWO-DBS","cross-ledger saga",
            "WriterForgeDB and FactJournal use independent SQLite "
            "connections; no global distributed transaction is proven. "
            "Relational identity/version adapter and failure compensation "
            "remain in design stage.",
            [("writerforge/db.py","class WriterForgeDB:"),
             ("writerforge/fact_journal.py","class FactJournal:")]),
        issue(
            "WF63-RISK-READER-SOURCE","reader criticism identity",
            "Reader feedback counted by distinct supplied IDs and external "
            "URL metadata is not externally identity-authenticated.",
            [("writerforge/feedback.py","COUNT(DISTINCT reader_id)"),
             ("writerforge/actual_reader.py",'source_url=r.get("source_url","")')]),
        issue(
            "WF63-RISK-RELEASE","release management and scale",
            "Development heads V57-V63 remain stacked draft branches, "
            "while pyproject still reports v27; bulk SQLite disk growth, "
            "migration preflight and workflow load are not independently "
            "certified by small adversarial tests.",
            [("pyproject.toml",'version = "27.0.0"'),
             ("writerforge/db.py","PRAGMA cache_size=-8192")]),
    ]
    result={
        "format":"writerforge.v63-full-architecture-code-audit.v1",
        "source_ref":"v63-skill-authority-and-concurrency",
        "unit_of_work":"synthetic structural/security code review",
        "model_calls":0,"r2_network_calls":0,
        "literary_training_performed":False,
        "literary_promotion_performed":False,
        "old_v49_status":"THIRD_STRIKE_FAILED",
        "source_tree":{
            "package_modules":len(pkg),"script_modules":len(scripts),
            "unit_test_files":len(tests),
            "workflow_yml_files":len(flows),
            "existing_schema_table_count":len(schema_tables),
            "schema_tables":schema_tables,
            "v31_v38_reference_file_count":len(refs),
            "core_sha256":{p:sha(p) for p in CORE_FILES}
        },
        "static_callsite_summary":dict(sorted(by_kind.items())),
        "production_authority_and_story_calls":[
            s for s in production
            if s["method"] in {
                "promote","_promote_verified","register","revalidate",
                "apply_upgrade","accept_draft","commit",
                "revoke_candidate","decide","accept_candidate"
            }],
        "all_direct_promote_calls":[s for s in sites
                                    if s["method"]=="promote"],
        "evidence_strength":"AST-only; not dynamic call proof",
        "confirmed_engineering_controls":[
            "V63 independent skill-registration-immutability and "
            "read-only capability snapshots",
            "V63 signed manual skill promotion with transactional CAS",
            "V63 two SQLite-writer race lock at experience decision",
            "V63 STORY commit policy recheck inside BEGIN IMMEDIATE",
            "V62 adverse feedback and signed tombstone remain preserved",
            "V49 literary capability failure remains not overturned"
        ],
        "unresolved_findings":unresolved,
        "open_findings_count":len(unresolved),
        "report_status":OUTPUT_TRUST,
        "limits":[
            "Static parser does not infer runtime plugins, dynamically "
            "loaded code, authorial correctness or trustworthiness of R2.",
            "No credentials, original novels, literary ratings, private "
            "R2 files or generated fiction are emitted.",
            "New capability registration is permitted for trusted setup "
            "for backward compatibility; this does not validate a level.",
        ],
    }
    return result


def main():
    result=audit()
    raw=json.dumps(result,sort_keys=True,indent=2,ensure_ascii=False)+"\n"
    Path(FILENAME).write_text(raw,encoding="utf-8")
    print(json.dumps({
        "format":result["format"],
        "report_sha256":sha256(raw.encode("utf-8")).hexdigest(),
        "source_files":result["source_tree"]["package_modules"],
        "call_sites":len(result["production_authority_and_story_calls"]),
        "open_risks":result["open_findings_count"],
        "status":result["report_status"],
        "literary_promotion":False,
    },ensure_ascii=False))


if __name__=="__main__":
    main()
