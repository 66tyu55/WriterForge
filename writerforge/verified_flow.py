"""Production opt-in WriterForge writing route: published source -> context -> model.

Unlike the legacy WritingFlow (which deliberately only wraps accept/commit),
this route refuses to generate without a real PUBLISHED Xuehai snapshot,
source retrieval evidence, and an explicitly configured model endpoint.
Never claim that ChatGPT's own prose was produced by this pipeline.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from ipaddress import ip_address
from pathlib import Path
from datetime import datetime, timezone
import json
import os
import re
import urllib.request
from urllib.parse import urlsplit

from .craft_engine import CraftEngine, CraftRequest
from .db import WriterForgeDB
from .runtime import RuntimeEngine, Mode
from .writing_flow import WritingFlow
from .xuehai import XuehaiStore, Query
from .encyclopedia import FictionEncyclopedia, FacetQuery
from .writing_companion import CATEGORIES as COMPANION_CATEGORIES
from .prose_style import ProseStyleStore, rejects_verbatim_copy, format_prose_reference


MAX_PROMPT_CHARS = 10_000
MAX_GENERATED_CHARS = 100_000
MAX_MODEL_RESPONSE_BYTES = 1024 * 1024


class WritingExecutionError(RuntimeError):
    pass


@dataclass(frozen=True)
class GroundedDraftPacket:
    scene_id: str
    project_id: str
    snapshot_id: int
    evidence: tuple[dict, ...]
    craft_ids: tuple[str, ...]
    prompt: str
    prompt_sha256: str
    encyclopedia_refs: tuple[dict,...] = ()
    prose_reference_text: str | None = None
    prose_reference_sha256: str | None = None
    r2_verified_sources: tuple[dict, ...] = ()
    r2_snapshot_sha256: str | None = None

    def manifest(self) -> dict:
        return {
            "kind": "writerforge_v23_verified_draft",
            "project_id": self.project_id,
            "scene_id": self.scene_id,
            "snapshot_id": self.snapshot_id,
            "prompt_sha256": self.prompt_sha256,
            "retrieval_refs": [
                {"work_id": x["work_id"], "chapter": x["location"][0],
                 "paragraph": x["location"][1], "sentence": x["location"][2],
                 "entry_id": x["entry_id"], "function": x["function"]}
                for x in self.evidence
            ],
            "craft_ids": list(self.craft_ids),
            "encyclopedia_refs": [
                {"entity_id":e["entity_id"],"evidence_id":e["id"],
                 "work_id":e["work_id"],"category_path":e["category_path"],
                 "location":[e["chapter"],e["paragraph"],e["sentence"]]}
                for e in self.encyclopedia_refs
            ],
            "study_level": "deterministic_structural_unverified",
            "review_status": "pending_external_review",
            "accepted": False,
            "r2_source_lookup": {
                "snapshot_sha256":self.r2_snapshot_sha256,
                "references":[{
                    "work_id":x["work_id"],
                    "work_original_sha256":x["work_original_sha256"],
                    "source_unit_sha256":x["source_unit_sha256"],
                    "location":x["location"],
                    "evidence_class":x["evidence_class"]
                } for x in self.r2_verified_sources],
                "literary_method_verified":False,
            },
            "unreviewed_source_excerpts_shown_to_model": False,
            "craft_labels_shown_to_model": False,
            "prose_style": {
                "mode": "explicit_author_approved" if self.prose_reference_sha256 else "free_model",
                "reference_sha256": self.prose_reference_sha256,
                "reference_content_in_manifest": False,
                "literary_quality_verified": False,
                "model_weight_training": False,
            },
        }


class VerifiedWritingFlow(WritingFlow):
    """The only CLI writing path labelled 'trained-source grounded'."""

    def __init__(self, db: WriterForgeDB, runtime: RuntimeEngine, project_id: str):
        super().__init__(db, runtime, project_id)
        self.db = db
        self.xuehai = XuehaiStore(db, runtime)
        row = db.conn.execute(
            "SELECT status FROM snapshots WHERE id=?", (runtime.pinned_snapshot_id,),
        ).fetchone()
        if not row or row["status"] != "published":
            raise WritingExecutionError("a real published Xuehai snapshot is required")
        if not db.conn.execute("SELECT 1 FROM studied_chapters LIMIT 1").fetchone():
            raise WritingExecutionError("no original text has completed the structural study")

    def prepare(
        self, scene_id: str, goal: str, *, concerns: tuple[str, ...] = (),
        language: str = "简体中文", genre: str = "古代白话",
        reference_category: str | None = None,
        reference_name: str | None = None,
        r2_library: str | None = None,
        r2_snapshot: str | None = None,
        r2_terms: tuple[str,...] = (),
        r2_cache_dir: str | Path = "corpus/r2-readonly-cache",
    ) -> GroundedDraftPacket:
        self.runtime.require(Mode.WRITE)
        if not goal.strip() or len(goal) > 2000 or not scene_id or len(scene_id)>128:
            raise WritingExecutionError("scene_id and bounded specific writing goal required")
        if r2_library is None and (r2_snapshot is not None or r2_terms):
            raise WritingExecutionError("R2_LOOKUP_NEEDS_EXPLICIT_LIBRARY")
        r2_result=None
        if r2_library is not None:
            if not r2_snapshot:
                raise WritingExecutionError("R2_WRITING_REQUIRES_PINNED_SNAPSHOT")
            from .r2_retrieval import R2SourceGateway
            r2_result=R2SourceGateway.from_environment().search(
                library=r2_library,snapshot=r2_snapshot,
                terms=r2_terms,cache_dir=r2_cache_dir,limit=4)
            if not r2_result.matches:
                raise WritingExecutionError("R2_NO_EXACT_SOURCE_EVIDENCE_MATCH")

        # CraftEngine accepts fine-grained scene signals, but Companion
        # accepts author preference categories only. Never send Craft signal
        # identifiers into Companion's strict validation API.
        companion_aliases = {
            "character_entrance":"character", "relationship_pressure":"character",
            "decision":"character", "interiority":"character",
            "free_indirect":"voice", "scene":"plot",
            "reversal":"plot", "setup_payoff":"plot",
            "detail_utility":"description", "white_room":"description",
        }
        companion_concerns = tuple(dict.fromkeys(
            companion_aliases.get(key,key) for key in concerns
            if companion_aliases.get(key,key) in COMPANION_CATEGORIES
        ))
        frame = self.begin_draft(scene_id, concerns=companion_concerns)
        mapped = ("environment" if "description" in concerns else
                  "dialogue" if "dialogue" in concerns else None)
        def get(function):
            return self.xuehai.query(Query(
                genre=genre,culture="中国",function=function,
                project_id=self.project_id,
                max_per_work=8,max_per_cluster=3,limit=6,
            ))
        evidence = get(mapped) if mapped else get(None)
        if not evidence and mapped:
            evidence = get(None)
        if not evidence:
            raise WritingExecutionError("no source-learning evidence matches this snapshot")
        # Explicit optional encyclopedia reference request. Only reviewed
        # ORIGINAL evidence reaches the generation prompt; proposed keyword
        # candidates never become genre/classified writing instructions.
        facet_refs=[]
        if reference_category or reference_name:
            facet_result=FictionEncyclopedia(self.db).query(FacetQuery(
                category_path=reference_category,
                entity_name=reference_name,
                genre=genre, status="verified",limit=5,
            ))
            facet_refs=facet_result["items"]
        craft = CraftEngine().plan(CraftRequest(needs=concerns))
        craft_ids = tuple(t.id for t in craft.techniques)
        # Read only the last TWO accepted scenes for factual continuity.
        # This is NOT an automatic style reference: earlier drafts may be poor.
        previous = self.db.conn.execute(
            """SELECT scope_id,substr(body,-1400) AS tail FROM accepted_prose
               WHERE project_id=? ORDER BY updated_at DESC,scope_id DESC LIMIT 2""",
            (self.project_id,),
        ).fetchall()
        continuation = "\n".join(
            f"{r['scope_id']}: {r['tail']}" for r in reversed(previous)
        )
        # Only explicit author corrections are creative constraints. Do not
        # transform weak accepted-AI rhythm statistics into writing rules.
        explicit_preferences = "\n".join(frame.companion.guidance[:4])
        verified_fact_notes = "\n".join(
            f"- 已复核设定 {e['category_path']}: {e['name']} / {e['attribute']}"
            for e in facet_refs
        )
        # Persist one OPTIONAL author-approved prose sample in the existing DB.
        # Absent approval => free-model prose. No "best first chapter" guesses.
        style = ProseStyleStore(self.db, self.project_id).load()
        prose_tail = format_prose_reference(style.text) if style else ""
        # SHA-verified original source is NOT a reviewed literary technique.
        r2_context = ""
        if r2_result:
            r2_context = (
                "\nR2已验证原著出处（词面检索，非经审文学经验；禁止照搬）：\n"
                + "\n".join(
                    "- "+x["work_id"]+" 位置 "+",".join(map(str,x["location"]))+
                    "；短引 "+x["source_excerpt"][:45]
                    for x in r2_result.matches
                )
            )
        prompt = (
            f"请创作原创{language}小说正文。体裁：{genre}。\n"
            "原著学习档案里的关键词与第几章标签仅作来源审计，不是文笔范例，"
            "不要照搬原著人物、词句或设定。\n"
            f"场景：{scene_id}\n本场景的目标：{goal.strip()}\n"
            f"本场景关注：{', '.join(concerns[:4])}\n"
            f"此前已接受的正文末尾（用于事实衔接，不代表优秀文风）：\n{continuation[:2900]}\n"
            f"作者明确提出的写作偏好：\n{explicit_preferences}\n"
            f"确需使用的已复核设定：\n{verified_fact_notes}\n"
            "让人物根据已知信息、欲望和风险作出有后果的选择；"
            "情绪、动作、声音和环境只在情节需要时自然出现。"
            "不强制对话比例、转折次数、修辞配额，也不解释写作方法。"
            "不要输出大纲、自评或教学说明；只写原创正文。"
            + r2_context
            + prose_tail
        )
        if len(prompt) > MAX_PROMPT_CHARS:
            raise WritingExecutionError("draft prompt exceeds 10,000-character bound")
        return GroundedDraftPacket(
            scene_id, self.project_id, int(self.runtime.pinned_snapshot_id),
            tuple(evidence), craft_ids, prompt,
            sha256(prompt.encode("utf-8")).hexdigest(),
            tuple(facet_refs),
            style.text if style else None,
            style.sha256 if style else None,
            tuple(r2_result.matches) if r2_result else (),
            r2_result.snapshot if r2_result else None,
        )


def local_chat_completion(packet: GroundedDraftPacket, *, model: str,
                          api_base: str = "http://127.0.0.1:1234/v1",
                          timeout: int = 120, max_tokens: int = 1600) -> str:
    """OpenAI-compatible local LM Studio/Ollama endpoint; no implicit cloud use."""
    parsed = urlsplit(api_base)
    host = parsed.hostname or ""
    if parsed.scheme != "http" or parsed.username or parsed.password or not (
        host == "localhost" or (host and _is_loopback_ip(host))
    ):
        raise WritingExecutionError("model endpoint must be a local HTTP loopback address")
    if parsed.query or parsed.fragment or not 1 <= timeout <= 300:
        raise WritingExecutionError("invalid model endpoint or timeout")
    if not model or not 1 <= max_tokens <= 6000:
        raise WritingExecutionError("model and bounded max_tokens are required")
    endpoint = api_base.rstrip("/") + "/chat/completions"
    payload = json.dumps({
        "model":model,
        "messages":[{"role":"system","content":"你是原创中文小说作者；不要模仿或逐字复制参考原著。"},
                    {"role":"user","content":packet.prompt}],
        "temperature":0.8,"max_tokens":max_tokens,
        "stream":False,
    },ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        endpoint,data=payload,headers={
            "Content-Type":"application/json","Authorization":"Bearer lm-studio",
        },method="POST",
    )
    with urllib.request.urlopen(request,timeout=timeout) as response:
        chunk = response.read(MAX_MODEL_RESPONSE_BYTES + 1)
    if len(chunk) > MAX_MODEL_RESPONSE_BYTES:
        raise WritingExecutionError("model response exceeds 1 MiB")
    try:
        obj = json.loads(chunk.decode("utf-8"))
        output = obj["choices"][0]["message"]["content"]
    except (KeyError,IndexError,TypeError,ValueError) as exc:
        raise WritingExecutionError("invalid chat completion response") from exc
    if not isinstance(output,str) or not output.strip() or len(output)>MAX_GENERATED_CHARS:
        raise WritingExecutionError("missing or excessive generated prose")
    if packet.prose_reference_text and rejects_verbatim_copy(
        output, packet.prose_reference_text
    ):
        raise WritingExecutionError("model copied long prose from the approved style sample")
    return output.strip()


def _is_loopback_ip(host: str) -> bool:
    try:
        return ip_address(host).is_loopback
    except ValueError:
        return False


def save_candidate(packet: GroundedDraftPacket, body: str, model: str,
                   output_dir: str | Path) -> dict:
    """Never auto-commit or label the model text as author-written."""
    if not body.strip() or len(body)>MAX_GENERATED_CHARS:
        raise WritingExecutionError("invalid candidate prose")
    out = Path(output_dir)
    out.mkdir(parents=True,exist_ok=True)
    slug = re.sub(r"[^a-zA-Z0-9_-]+","_",packet.scene_id)[:72] or "scene"
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    folder = out / (slug+"-"+stamp)
    folder.mkdir(exist_ok=False)
    path = folder / "candidate.md"
    path.write_text(body,encoding="utf-8")
    manifest = packet.manifest()
    manifest.update(
        model=model,
        candidate_file="candidate.md",
        candidate_sha256=sha256(body.encode("utf-8")).hexdigest(),
        produced_at=stamp,
    )
    (folder/"run.json").write_text(
        json.dumps(manifest,ensure_ascii=False,indent=2),encoding="utf-8"
    )
    return {"folder":str(folder),"candidate":str(path),
            "manifest":str(folder/"run.json"),"source_refs":len(packet.evidence),
            "accepted":False}


def accept_candidate(db: WriterForgeDB, runtime: RuntimeEngine, *,
                     project_id: str, manifest_path: str | Path,
                     commit_id: str, explicitly_approved: bool) -> dict:
    """Only an explicit author approval can make a generated draft durable."""
    if not explicitly_approved:
        raise WritingExecutionError("author must explicitly approve the candidate")
    meta_path = Path(manifest_path)
    manifest = json.loads(meta_path.read_text(encoding="utf-8"))
    if manifest.get("kind")!="writerforge_v23_verified_draft":
        raise WritingExecutionError("not a WriterForge verified draft")
    if manifest.get("project_id")!=project_id or manifest.get("accepted"):
        raise WritingExecutionError("project mismatch or already accepted")
    body = (meta_path.parent / "candidate.md").read_text(encoding="utf-8")
    if sha256(body.encode("utf-8")).hexdigest()!=manifest.get("candidate_sha256"):
        raise WritingExecutionError("candidate has changed: generate a fresh trace")
    sid = manifest.get("snapshot_id")
    if sid!=runtime.pinned_snapshot_id:
        raise WritingExecutionError("snapshot changed since generation")
    row=db.conn.execute("SELECT status FROM snapshots WHERE id=?",(sid,)).fetchone()
    if not row or row["status"]!="published":
        raise WritingExecutionError("source snapshot no longer published")
    flow=WritingFlow(db,runtime,project_id)
    result=flow.accept_draft(
        commit_id,manifest["scene_id"],body,origin="assistant_generated"
    )
    # Never claim durable commit failed if an optional audit-file write fails.
    manifest["accepted"]=True
    manifest["commit_id"]=commit_id
    try:
        temp=meta_path.with_suffix(".tmp")
        temp.write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding="utf-8")
        os.replace(temp,meta_path)
    except OSError:
        pass  # Receipt is canonical; CLI retry is idempotent.
    return {"commit_id":commit_id,"replayed":result.replayed,
            "accepted":True,"origin":"assistant_generated"}
