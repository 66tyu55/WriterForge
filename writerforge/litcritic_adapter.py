"""ONE external evaluator: read-only lit-critic local REST integration.

All findings and session metadata are exported to local JSON/Markdown files,
with a SHA-256 of the exact reviewed manuscript. WriterForge never auto-accepts
a review, changes Canon, or promotes a skill from automated critic output.
"""
from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from urllib.parse import urlencode, urlsplit
from ipaddress import ip_address
import json
import os
import urllib.request


class CriticIntegrationError(RuntimeError):
    pass


class LitCriticAdapter:
    def __init__(self, *, base_url: str = "http://127.0.0.1:8000/api",
                 timeout: int = 180):
        parsed = urlsplit(base_url)
        host = parsed.hostname or ""
        try:
            loopback = host == "localhost" or ip_address(host).is_loopback
        except ValueError:
            loopback = host == "localhost"
        if parsed.scheme != "http" or not loopback or parsed.username or parsed.password:
            raise CriticIntegrationError("lit-critic API must be a local HTTP endpoint")
        if parsed.query or parsed.fragment or not 1 <= timeout <= 300:
            raise CriticIntegrationError("invalid critic address or timeout")
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def _request(self, path: str, *, post: dict | None = None) -> dict:
        url = self.base_url + path
        data = (json.dumps(post,ensure_ascii=False).encode("utf-8")
                if post is not None else None)
        req = urllib.request.Request(
            url, data=data, headers={"Content-Type":"application/json"},
            method="POST" if post is not None else "GET",
        )
        with urllib.request.urlopen(req,timeout=self.timeout) as resp:
            payload = resp.read(2_000_001)
        if len(payload)>2_000_000:
            raise CriticIntegrationError("critic API response exceeded 2 MB")
        try:
            obj=json.loads(payload.decode("utf-8"))
            if not isinstance(obj,dict):
                raise TypeError("expected object")
            return obj
        except (ValueError,TypeError) as exc:
            raise CriticIntegrationError("invalid critic API response") from exc

    def review(self, *, project_path: str | Path, scene_path: str | Path,
               output_dir: str | Path, mode: str = "quick") -> dict:
        if mode not in {"quick","deep"}:
            raise CriticIntegrationError("mode must be quick or deep")
        project = Path(project_path).resolve()
        scene = Path(scene_path).resolve()
        if not project.is_dir() or not scene.is_file() or not scene.is_relative_to(project):
            raise CriticIntegrationError("scene must be an existing file inside project_path")
        if not all((project / doc).is_file() for doc in ("CANON.md","STYLE.md")):
            raise CriticIntegrationError("lit-critic project requires CANON.md and STYLE.md")
        source_bytes=scene.read_bytes()
        if len(source_bytes)>2_000_000:
            raise CriticIntegrationError("review scene is too large")
        content_hash=sha256(source_bytes).hexdigest()
        query="?"+urlencode({"project_path":str(project)})
        old=self._request("/sessions"+query)
        known={row.get("id") for row in old.get("sessions",[]) if isinstance(row,dict)}
        run=self._request("/analyze",post={
            "project_path":str(project),"scene_paths":[str(scene)],"mode":mode,
        })
        if run.get("status") not in {"success","completed"}:
            raise CriticIntegrationError("critic did not confirm successful analysis")
        latest=self._request("/sessions"+query)
        new_sessions=[
            row for row in latest.get("sessions",[])
            if isinstance(row,dict) and row.get("id") not in known
            and str(scene) in (
                row.get("scene_paths") or
                ([row.get("scene_path")] if row.get("scene_path") else [])
            )
        ]
        if len(new_sessions)!=1:
            raise CriticIntegrationError(
                "could not uniquely identify new review session; no report will be fabricated"
            )
        sid=new_sessions[0]["id"]
        if not isinstance(sid,int) or sid<1:
            raise CriticIntegrationError("invalid critic session id")
        details=self._request(f"/sessions/{sid}"+query)
        items=details.get("findings")
        if not isinstance(items,list) or len(items)>300:
            raise CriticIntegrationError("invalid or excessive findings")
        # Bounded report: keep evidence and proposed options but never
        # automatically turn the critic's opinion into a writing directive.
        findings=[
            {
                "number":item.get("number"),"severity":item.get("severity"),
                "lens":item.get("lens"),"scene_path":item.get("scene_path"),
                "line_start":item.get("line_start"),
                "line_end":item.get("line_end"),
                "evidence":str(item.get("evidence",""))[:800],
                "impact":str(item.get("impact",""))[:1000],
                "options":[str(x)[:300] for x in item.get("options",[])[:5]],
                "status":item.get("status","pending"),
            }
            for item in items if isinstance(item,dict)
        ]
        if len(findings)!=len(items):
            raise CriticIntegrationError("malformed critic findings")
        data={
            "provider":"lit-critic","session_id":sid,"mode":mode,
            "scene":str(scene),"scene_sha256":content_hash,
            "project":str(project),
            "generated_at":datetime.now(timezone.utc).isoformat(),
            "verified_with_live_provider":True,
            "findings":findings,
            "assessment_policy":"read_only_author_decides",
            "author_decisions":[],
        }
        directory=Path(output_dir)
        directory.mkdir(parents=True,exist_ok=True)
        base=f"litcritic_{sid}_{content_hash[:12]}"
        path_json=directory/(base+".json")
        path_md=directory/(base+".md")
        lines=[
            f"# lit-critic 独立审稿 · 会话 {sid}","",
            f"- 原稿：{scene.name}","- 状态：仅供作者判断，不自动修稿",
            f"- SHA256：{content_hash}",f"- 审稿模式：{mode}",
            f"- 问题条数：{len(findings)}","",
        ]
        for idx,item in enumerate(findings,1):
            lines.extend([
                f"## {idx}. {item['lens']} · {item['severity']}",
                f"位置：{item['scene_path']} 第 {item['line_start']}–{item['line_end']} 行",
                f"证据：{item['evidence']}",
                f"读者影响：{item['impact']}",
                "可选修改方向："+("; ".join(item["options"]) or "无"),
                "作者结论：待决定","",
            ])
        # JSON is an immutable record of the evaluator's original feedback.
        # No automatic edits to the scene or database.
        self._atomic(path_json,json.dumps(data,ensure_ascii=False,indent=2))
        self._atomic(path_md,"\n".join(lines))
        return {"json":str(path_json),"markdown":str(path_md),
                "session_id":sid,"count":len(findings),"read_only":True}

    @staticmethod
    def _atomic(path: Path, content: str) -> None:
        temp=path.with_suffix(path.suffix+".partial")
        try:
            temp.write_text(content,encoding="utf-8")
            os.replace(temp,path)
        finally:
            temp.unlink(missing_ok=True)
