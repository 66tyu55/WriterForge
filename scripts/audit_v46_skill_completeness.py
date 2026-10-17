"""V46 read-only WriterForge SKILL readiness gate.

Reports engineering evidence separately from literary training claims. Do NOT
repair historical evidence, modify databases, call paid models or infer quality
from pytest success. A missing proof is NOT a proof of inability.
"""
from __future__ import annotations

import inspect
import json
import re
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")

def _check_links(markdown: str):
    candidates = re.findall(r"\]\(([^)#]+)(?:#[^)]*)?\)", markdown)
    relative = [u for u in candidates
                if not u.startswith(("http://","https://","mailto:","#"))]
    return sorted({u for u in relative if not (ROOT / u).is_file()})

def assess() -> dict:
    skill = _read("SKILL.md")
    manifest = json.loads(_read("manifest.json"))
    pyproject = tomllib.loads(_read("pyproject.toml"))
    from writerforge.runtime import RuntimeEngine, Mode
    from writerforge.source_study import OriginalStudy, _structural_analysis
    from writerforge.reader_learning import ReaderLearningSession
    from writerforge.scene_learning import SceneLiteraryStudy
    from writerforge.verified_flow import VerifiedWritingFlow
    from writerforge.v45_state_experience import StateDerivedExperience

    header=re.match(r"\A---\n(.*?)\n---\n",skill,re.S)
    name=re.search(r"(?m)^name:\s*(.+)$",header.group(1)) if header else None
    actual_entry=pyproject.get("project",{}).get("scripts",{}).get("writerforge")
    cli=_read("writerforge/cli.py")
    main_version=pyproject.get("project",{}).get("version")
    declared=manifest.get("version")
    entry_ok=(bool(header) and bool(name) and
              actual_entry=="writerforge.cli:main" and
              declared==main_version==(ROOT / "VERSION").read_text(encoding="utf-8").strip())
    link_errors=_check_links(skill)
    mode_source=inspect.getsource(RuntimeEngine)
    source_source=inspect.getsource(_structural_analysis)
    reader_source=inspect.getsource(ReaderLearningSession)
    scene_signature=inspect.signature(SceneLiteraryStudy.run)
    writing_source=inspect.getsource(VerifiedWritingFlow.prepare)
    strategy_source=inspect.getsource(StateDerivedExperience.choose)

    # Fact checks about executable code. These do NOT verify literary semantics.
    has_mode_guard=("enter_learn" in mode_source and
                    "enter_write" in mode_source and
                    "RuntimeErrorState" in mode_source)
    deterministic_only="deterministic_structural_unverified" in source_source
    reader_is_record_only=("def record_first_read" in reader_source and
                            "def attach_craft_analysis" in reader_source and
                            "reaction: ReaderReaction" in reader_source)
    scene_requires_model="model_call" in scene_signature.parameters
    # Explicitly identify missing DIRECT linkage, not a universal proof that
    # no other code path can ever perform literary learning.
    no_direct_scene_analysis_link=("analysis_json" not in writing_source
                                   and "SceneLiteraryStudy" not in writing_source)
    v45_state_links=("character_state" in strategy_source and
                     "causal_events" in strategy_source)
    cli_has_v45=("v45-experience" in cli or "v45_experience" in cli)
    observed = {
        "skill_frontmatter_name":name.group(1).strip() if name else None,
        "manifest_version":declared,
        "packaging_version":main_version,
        "current_stable_skill_generation":"V27-main" if main_version=="27.0.0" else "V50-engineering-release-candidate",
        "last_experimental_generation_examined":"V45",
        "missing_local_skill_document_links":link_errors,
        "console_entry_point":actual_entry,
        "separate_learn_write_modes_implemented":has_mode_guard,
        "source_analysis_is_lexical_unverified":deterministic_only,
        "reader_learning_records_caller_reactions":reader_is_record_only,
        "scene_semantic_analysis_requires_model_callback":scene_requires_model,
        "production_prepare_does_not_directly_read_scene_analysis_json":no_direct_scene_analysis_link,
        "v45_compiles_character_and_event_state":v45_state_links,
        "v45_exposed_via_standard_cli":cli_has_v45,
        "installed_as_active_chat_skill_in_this_chat":"NOT_VERIFIABLE_FROM_REPOSITORY_CI",
    }
    gates = {
        "G01_skill_package_entry":"PASS" if entry_ok and not link_errors else "FAIL",
        "G02_learn_write_mode_isolation":"PASS" if has_mode_guard else "UNVERIFIED",
        "G03_chapter_structural_study":"IMPLEMENTED_STRUCTURAL_ONLY" if deterministic_only else "UNVERIFIED",
        "G04_reader_first_actual_semantic_learning":"NOT_PROVEN" if scene_requires_model else "UNVERIFIED",
        "G05_automatic_literary_experience_induction":"NOT_PROVEN",
        "G06_learned_experience_automatically_consumed_in_production":"NOT_PROVEN" if no_direct_scene_analysis_link else "REQUIRES_END_TO_END_PROOF",
        "G07_V45_experimental_state_controls_write":"IMPLEMENTED_OPT_IN_ONLY" if v45_state_links else "UNVERIFIED",
        "G08_real_host_triggered_skill_loading":"NOT_VERIFIABLE_IN_GITHUB_CI",
        "G09_unseen_full_story_ablation":"NOT_PERFORMED",
        "G10_independent_literary_quality_gain":"NOT_PERFORMED",
        "G11_v45_experiment_entrypoint_in_standard_CLI":"EXPOSED" if cli_has_v45 else "NOT_EXPOSED",
        "G12_stable_instruction_experiment_alignment":"EXPERIMENT_NOT_IN_STABLE_INSTRUCTIONS",
    }
    return {
        "format":"writerforge.v46-skill-completeness-audit.v1",
        "scope":"v45-draft-branch-runtime-and-stable-v27-skill-entry",
        "observations":observed,"gates":gates,
        "skill_complete":False,
        "can_claim_literary_skill_learned":False,
        "model_calls":0,
        "note":(
            "Passing unit tests demonstrates software invariants only. "
            "No actual ChatGPT plugin installation, independent literary reader, "
            "model-authored manuscript, or automatic learned-skill promotion "
            "is inferred from repository source inspection."
        ),
    }

def main():
    result=assess()
    p=ROOT / "v46_skill_completeness_audit.json"
    p.write_text(json.dumps(result,ensure_ascii=False,sort_keys=True,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({
        "report":str(p.name),
        "skill_complete":result["skill_complete"],
        "passing_package_entry":result["gates"]["G01_skill_package_entry"],
        "direct_experience_link":result["gates"]["G06_learned_experience_automatically_consumed_in_production"],
        "full_literary_ab":result["gates"]["G09_unseen_full_story_ablation"],
        "model_calls":0,
    },ensure_ascii=False,sort_keys=True))
    return result

if __name__=="__main__":
    main()
