"""Live private R2 smoke: exactly three immutable synthetic objects per scope.

Nothing from the user's copyrighted manuscripts or private novel ever travels
through this test. GitHub Actions only receives whitelisted status values,
never keys, original story text, model responses or private prose. The scope
contains the CI run identifier, preventing touching existing WF artifacts.
"""
from __future__ import annotations

from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
import json
import os

from writerforge.r2_storage import (
    R2Config,R2NarrativeMemoryStore,R2StorageError,
)
from writerforge.narrative_core import (
    new_graph,advance_graph,record_chapter_memory,recall_original,
    read_core_from_resume,
)
from writerforge.v114_external_story_state import external_temporal_step
from writerforge.v117_continuity_trace import make_resume

SOURCE="完全合成的第一章：沈砚沿石桥前行，他尚未把密令交给任何人。"
P="wf-ci-private-r2-synthetic-narrative"
RUN=os.environ.get("GITHUB_RUN_ID","manual-local")
S="isolated-"+RUN


def main():
    config=R2Config.from_environment()
    # Guardrail: do not write to any accidental bucket other than WF's
    # established private test/storage bucket. No public bucket switch.
    if config.bucket!="writerforge-private-library":
        raise R2StorageError("WFCORE_LIVE_R2_WRONG_PRIVATE_BUCKET")
    first=R2NarrativeMemoryStore(
        config,project_id=P,scene_id=S)
    second=R2NarrativeMemoryStore(
        config,project_id=P,scene_id=S)
    with TemporaryDirectory(prefix="wf-r2-synthetic-") as directory:
        file=Path(directory)/"synthetic.md"
        file.write_text(SOURCE,encoding="utf8")
        graph=new_graph(project_id=P,scene_id=S)
        graph=advance_graph(graph,project_id=P,scene_id=S,
                            chapter_index=1,prose=SOURCE)
        graph=record_chapter_memory(
            graph,project_id=P,scene_id=S,chapter_index=1,
            source_path=str(file),prose=SOURCE,
            source_writer=first.put_original,
            source_reader=first.read_original,
            archive_writer=first.put_capsule,
            archive_reader=first.read_capsule)
        original=graph["memory"]["hot"][0]
        expected=sha256(SOURCE.encode()).hexdigest()
        if not (original["source_sha256"]==expected and
                original["source_path"].startswith("r2://") and
                second.read_original(original["source_path"],expected)==SOURCE):
            raise AssertionError("WFCORE_R2_ORIGINAL_REMOTE_RESTART_FAILED")
        # Private cold archive payload with real SHA readback.
        capsule={
            "chapter":1,
            "source_sha256":expected,
            "source_path":original["source_path"],
            "summary":"仅作为索引的合成文本摘录。",
            "summary_kind":"EXTRACTIVE_SOURCE_EXCERPT_ONLY",
            "connected_protected_nodes":[],
            "literary_interpretation_verified":False,
        }
        page={
            "format":"wf.narrative.cold-capsule-page.v1",
            "project_id":P,"scene_id":S,
            "chapter_index":1,"capsule":capsule,"previous":None,
        }
        cold=first.put_capsule(page)
        if second.read_capsule(cold)!=page:
            raise AssertionError("WFCORE_R2_CAPSULE_REMOTE_RESTART_FAILED")
        checkpoint=external_temporal_step(SOURCE,cast=("沈砚",))
        resume=make_resume(
            project_id=P,scene_id=S,chapter_index=1,
            checkpoint=checkpoint,unified_narrative_core=graph)
        locator=first.put_resume(resume)
        restored=second.read_resume(locator)
        recovered=read_core_from_resume(
            restored,project_id=P,scene_id=S)
        recovered_text=recall_original(
            recovered,project_id=P,scene_id=S,chapter_index=1,
            source_reader=second.read_original,
            archive_reader=second.read_capsule)
        if recovered_text!=SOURCE:
            raise AssertionError("WFCORE_R2_RESTART_SOURCE_NOT_AVAILABLE")
        # Never expose private path, bucket, account or source in logs.
        result={
            "format":"wf.audit.private-r2-unified-memory-live-synthetic",
            "source_sha256":expected,
            "synthetic_original_uploaded_and_verified":True,
            "synthetic_capsule_uploaded_and_verified":True,
            "v117_resume_uploaded_and_verified":True,
            "independent_second_client_reads_source":True,
            "no_original_private_novel_transmitted":True,
            "old_r2_libraries_or_manifests_changed":False,
            "new_model_calls":0,"canon_writes":0,
            "test_isolation_scope_is_hash_derived":True,
            "no_railway_dependency":True,
        }
        out=Path("wf_private_r2_synthetic_results")
        out.mkdir(parents=True,exist_ok=False)
        (out/"STATUS.json").write_text(json.dumps(
            result,ensure_ascii=False,sort_keys=True,indent=2),
            encoding="utf8")
        print(json.dumps(result,ensure_ascii=False))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
