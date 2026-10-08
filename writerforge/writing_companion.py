"""Writing companion that grows from accepted work without interrupting drafting.

The source-learning Xuehai and model weights remain unchanged. Only the durable
StoryCommitCoordinator writes companion evidence; all reads are bounded, cheap,
and scoped to one project. Weak acceptance signals are NEVER called author voice.
"""
from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass
from types import MappingProxyType
import hashlib
import json
from typing import Any, Mapping

from .voice import fingerprint


MAX_SAMPLE_CHARS = 8192
MAX_ACTIVE_SCOPES = 32
MAX_PREFERENCES = 64
MAX_GUIDANCE_CHARS = 240
MAX_KEY_CHARS = 80
VOICE_FIELDS = (
    "avg_sentence_chars",
    "sentence_length_std",
    "dialogue_mark_ratio",
    "exclamation_ratio",
    "question_ratio",
    "comma_per_sentence",
)
TRUSTED_ORIGINS = frozenset({"author_written", "author_edited"})
ORIGINS = TRUSTED_ORIGINS | {"accepted", "assistant_generated"}
DIRECTIONS = frozenset({"prefer", "avoid"})
# Explicit author-curated axes, never guessed from the prose or category.
WRITING_SHEET_AXES = ("plot", "creativity", "character_emotion", "language")
# Category is descriptive, not a new skill/plugin.
CATEGORIES = frozenset({
    "general", "dialogue", "description", "action", "pacing", "character",
    "plot", "voice", "world", "revision",
})


class CompanionEvidenceError(ValueError):
    pass


def validate_origin(origin: Any) -> str:
    if type(origin) is not str or origin not in ORIGINS:
        raise CompanionEvidenceError(f"invalid accepted prose origin: {origin!r}")
    return origin


def validate_preference(key: str, payload: Mapping[str, Any]) -> None:
    if type(key) is not str or not key.strip() or len(key) > MAX_KEY_CHARS:
        raise CompanionEvidenceError("preference key must be 1..80 characters")
    action = payload.get("action", "set")
    if action not in {"set", "remove"}:
        raise CompanionEvidenceError("preference action must be set or remove")
    if action == "remove":
        # A removal must not carry a replacement value accidentally.
        if any(field in payload for field in (
            "guidance", "direction", "category", "axis", "conflict_group",
            "evidence_scope", "evidence_excerpt",
        )):
            raise CompanionEvidenceError("remove preference cannot carry replacement fields")
        return
    guidance = payload.get("guidance")
    if type(guidance) is not str or not guidance.strip() or len(guidance) > MAX_GUIDANCE_CHARS:
        raise CompanionEvidenceError("guidance must be 1..240 characters")
    if payload.get("direction", "prefer") not in DIRECTIONS:
        raise CompanionEvidenceError("invalid preference direction")
    if payload.get("category", "general") not in CATEGORIES:
        raise CompanionEvidenceError("invalid preference category")
    axis = payload.get("axis")
    if axis is not None and (type(axis) is not str or axis not in WRITING_SHEET_AXES):
        raise CompanionEvidenceError("invalid writing-sheet axis")
    group = payload.get("conflict_group")
    if group is not None and (
        type(group) is not str or not group.strip() or len(group) > MAX_KEY_CHARS
    ):
        raise CompanionEvidenceError("invalid conflict group")
    scope, excerpt = payload.get("evidence_scope"), payload.get("evidence_excerpt")
    if (scope is None) != (excerpt is None):
        raise CompanionEvidenceError("evidence_scope and evidence_excerpt must be supplied together")
    if scope is not None and (
        type(scope) is not str or not scope.strip() or len(scope) > 128
        or type(excerpt) is not str or not excerpt.strip() or len(excerpt) > 128
    ):
        raise CompanionEvidenceError("invalid evidence anchor (max 128 characters)")


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _update_ema(previous: dict, current: dict, count: int, alpha: float = 0.25) -> dict:
    # Bounded exponential mean tracks a changing style. It never stores raw prose.
    if count == 0:
        return {key: round(float(current[key]), 6) for key in VOICE_FIELDS}
    return {
        key: round((1 - alpha) * float(previous[key]) + alpha * float(current[key]), 6)
        for key in VOICE_FIELDS
    }


def observe_accepted(
    conn, project_id: str, scope_id: str, body: str, *, origin: str, changed: bool,
) -> None:
    """Refresh one accepted scene's evidence inside the durable story transaction.

    A scene counts once in the active author-voice profile, however often it
    gets revised. Replacing or deleting its accepted text replaces/retracts its
    old evidence. Keep just 32 most recently edited scopes to bound memory and
    make growth follow recent practice rather than fossilizing old mistakes.
    """
    validate_origin(origin)
    if not changed:
        return
    old = conn.execute(
        """SELECT version,accepted_revisions,authored_revisions,sampled_chars
           FROM writer_companion_profiles WHERE project_id=?""",
        (project_id,),
    ).fetchone()
    version = old["version"] if old else 0
    accepted_revisions = old["accepted_revisions"] if old else 0
    authored_revisions = old["authored_revisions"] if old else 0
    sampled_chars = old["sampled_chars"] if old else 0

    if body.strip():
        # Reading only the tail avoids scanning a full chapter on every small
        # scene edit. Raw prose never enters companion storage.
        sample = body[-MAX_SAMPLE_CHARS:]
        sampled_chars += len(sample)
        voice = fingerprint(sample).__dict__
        conn.execute(
            """INSERT INTO writer_companion_samples(
                    project_id,scope_id,origin,voice_json,sample_seq
               ) VALUES(?,?,?,?,?)
               ON CONFLICT(project_id,scope_id) DO UPDATE SET
                    origin=excluded.origin,voice_json=excluded.voice_json,
                    sample_seq=excluded.sample_seq""",
            (project_id, scope_id, origin, _json(voice), version + 1),
        )
        if origin in TRUSTED_ORIGINS:
            authored_revisions += 1
    else:
        # Deletion must not leave behind voice from prose that is no longer
        # accepted, even though the historical count of revisions remains.
        conn.execute(
            """DELETE FROM writer_companion_samples
               WHERE project_id=? AND scope_id=?""",
            (project_id, scope_id),
        )

    conn.execute(
        """DELETE FROM writer_companion_samples
           WHERE project_id=? AND scope_id NOT IN (
               SELECT scope_id FROM writer_companion_samples WHERE project_id=?
               ORDER BY sample_seq DESC,scope_id DESC LIMIT ?
           )""",
        (project_id, project_id, MAX_ACTIVE_SCOPES),
    )
    rows = conn.execute(
        """SELECT origin,voice_json FROM writer_companion_samples
           WHERE project_id=? ORDER BY sample_seq,scope_id""",
        (project_id,),
    ).fetchall()
    accepted_voice: dict = {}
    authored_voice: dict = {}
    authored_scopes = 0
    for index, row in enumerate(rows):
        metrics = json.loads(row["voice_json"])
        accepted_voice = _update_ema(accepted_voice, metrics, index)
        if row["origin"] in TRUSTED_ORIGINS:
            authored_voice = _update_ema(
                authored_voice, metrics, authored_scopes, alpha=0.30
            )
            authored_scopes += 1
    conn.execute(
        """INSERT INTO writer_companion_profiles(
               project_id,version,accepted_revisions,authored_revisions,
               accepted_scopes,authored_scopes,sampled_chars,
               accepted_voice_json,authored_voice_json
           ) VALUES(?,?,?,?,?,?,?,?,?)
           ON CONFLICT(project_id) DO UPDATE SET
             version=excluded.version,accepted_revisions=excluded.accepted_revisions,
             authored_revisions=excluded.authored_revisions,
             accepted_scopes=excluded.accepted_scopes,
             authored_scopes=excluded.authored_scopes,
             sampled_chars=excluded.sampled_chars,
             accepted_voice_json=excluded.accepted_voice_json,
             authored_voice_json=excluded.authored_voice_json,
             updated_at=CURRENT_TIMESTAMP""",
        (project_id, version + 1, accepted_revisions + 1, authored_revisions,
         len(rows), authored_scopes, sampled_chars,
         _json(accepted_voice), _json(authored_voice)),
    )


def apply_preference(conn, project_id: str, key: str, payload: Mapping[str, Any]) -> None:
    """One authoritative explicit preference store; no parallel rule engines.

    Source anchoring and group conflict checks run in the SAME transaction as
    accepted story mutations. The source body is never copied into preference
    storage: only the accepted revision hash and a short excerpt hash.
    """
    validate_preference(key, payload)
    action = payload.get("action", "set")
    if action == "remove":
        deleted = conn.execute(
            "DELETE FROM writer_companion_preferences WHERE project_id=? AND preference_key=?",
            (project_id, key),
        ).rowcount
        if not deleted:
            return
    else:
        guidance = " ".join(payload["guidance"].split())
        direction = payload.get("direction", "prefer")
        category = payload.get("category", "general")
        axis = payload.get("axis")
        group = payload.get("conflict_group")
        group = group.strip() if group is not None else None
        evidence_scope = payload.get("evidence_scope")
        evidence_body_hash = evidence_excerpt_hash = None

        if evidence_scope is not None:
            source = conn.execute(
                """SELECT body,body_hash FROM accepted_prose
                   WHERE project_id=? AND scope_id=?""",
                (project_id, evidence_scope),
            ).fetchone()
            excerpt = payload["evidence_excerpt"]
            if source is None or excerpt not in source["body"]:
                raise CompanionEvidenceError(
                    "evidence excerpt is not in the current accepted project prose"
                )
            evidence_body_hash = source["body_hash"]
            evidence_excerpt_hash = hashlib.sha256(
                excerpt.encode("utf-8")
            ).hexdigest()

        if group is not None:
            collision = conn.execute(
                """SELECT preference_key FROM writer_companion_preferences
                   WHERE project_id=? AND category=? AND conflict_group=?
                         AND preference_key<>? LIMIT 1""",
                (project_id, category, group, key),
            ).fetchone()
            if collision is not None:
                raise CompanionEvidenceError(
                    "preference group conflict with "
                    f"{collision['preference_key']!r}; update/remove the existing rule explicitly"
                )
        current = conn.execute(
            """SELECT guidance,direction,category,axis,conflict_group,
                      evidence_scope,evidence_body_hash,evidence_excerpt_hash
               FROM writer_companion_preferences
               WHERE project_id=? AND preference_key=?""",
            (project_id, key),
        ).fetchone()
        proposed = (
            guidance, direction, category, axis, group,
            evidence_scope, evidence_body_hash, evidence_excerpt_hash,
        )
        if current and tuple(current) == proposed:
            return
        if current is None:
            row = conn.execute(
                "SELECT COUNT(*) AS n FROM writer_companion_preferences WHERE project_id=?",
                (project_id,),
            ).fetchone()
            if row["n"] >= MAX_PREFERENCES:
                raise CompanionEvidenceError(
                    "companion preference capacity reached; explicitly remove or replace an old rule"
                )
        conn.execute(
            """INSERT INTO writer_companion_preferences(
                 project_id,preference_key,guidance,direction,category,
                 axis,conflict_group,evidence_scope,evidence_body_hash,evidence_excerpt_hash
               ) VALUES(?,?,?,?,?,?,?,?,?,?)
               ON CONFLICT(project_id,preference_key) DO UPDATE SET
                 guidance=excluded.guidance,direction=excluded.direction,
                 category=excluded.category,axis=excluded.axis,
                 conflict_group=excluded.conflict_group,
                 evidence_scope=excluded.evidence_scope,
                 evidence_body_hash=excluded.evidence_body_hash,
                 evidence_excerpt_hash=excluded.evidence_excerpt_hash,
                 updated_at=CURRENT_TIMESTAMP""",
            (project_id, key, *proposed),
        )
    # Existing V21 profile version remains the sole invalidation clock.
    conn.execute(
        """INSERT INTO writer_companion_profiles(project_id,version)
           VALUES(?,1)
           ON CONFLICT(project_id) DO UPDATE SET
             version=version+1,updated_at=CURRENT_TIMESTAMP""",
        (project_id,),
    )


@dataclass(frozen=True)
class CompanionDraftContext:
    project_id: str
    scene_id: str
    profile_version: int
    accepted_revisions: int
    authored_revisions: int
    voice_origin: str
    voice_metrics: Mapping[str, float]
    guidance: tuple[str, ...]
    fingerprint: str

    def compact_context(self, max_chars: int = 768) -> str:
        """Bounded structured guidance; never quote/retrieve raw draft passages."""
        if max_chars < 80:
            raise ValueError("max_chars must be >= 80")
        lines = []
        if self.voice_origin == "author":
            lines.append(
                "已验证作者写作节奏（仅供参考，不可强迫每句相同）："
                f"平均句长约{self.voice_metrics['avg_sentence_chars']:.1f}字"
                f"，每句逗号约{self.voice_metrics['comma_per_sentence']:.1f}个。"
            )
        elif self.voice_origin == "accepted":
            lines.append(
                "已接受稿件的节奏（弱信号，并非作者本人风格）："
                f"平均句长约{self.voice_metrics['avg_sentence_chars']:.1f}字"
                f"，每句逗号约{self.voice_metrics['comma_per_sentence']:.1f}个；"
                "仅用于保持作品连续性，不可机械模仿。"
            )
        if self.guidance:
            lines.extend(self.guidance)
        # Never truncate a rule mid-sentence: it may invert an exception,
        # negation or conditional in the author's explicit correction.
        selected: list[str] = []
        used = 0
        for line in lines:
            extra = len(line) + (1 if selected else 0)
            if used + extra <= max_chars:
                selected.append(line)
                used += extra
        return "\n".join(selected)


class WritingCompanion:
    """Lightweight app-shell companion, not an opt-in tool per sentence.

    Host calls before_draft automatically as part of its writing route.
    A version probe is the only SQL on a cache hit. A profile refresh costs
    at most 1 profile read + <=64 bounded preference rows, never entire corpus.
    """

    def __init__(self, db, project_id: str, *, max_cached_contexts: int = 32):
        if not project_id or max_cached_contexts < 1:
            raise ValueError("project_id and positive max_cached_contexts are required")
        self.db = db
        self.project_id = project_id
        self.max_cached_contexts = max_cached_contexts
        self._cache: OrderedDict[tuple, CompanionDraftContext] = OrderedDict()
        self._version = -1
        self._profile: dict | None = None
        self._preferences: tuple[dict, ...] = ()
        self._stale_preferences: tuple[dict, ...] = ()
        self.cache_hits = 0
        self.profile_loads = 0

    def before_draft(
        self, scene_id: str, *, concerns: tuple[str, ...] = (),
        max_guidance: int = 4,
    ) -> CompanionDraftContext:
        if not scene_id:
            raise ValueError("scene_id is required")
        if not 0 <= max_guidance <= 8:
            raise ValueError("max_guidance must be 0..8")
        concerns = tuple(sorted(set(concerns)))
        if any(topic not in CATEGORIES for topic in concerns):
            raise ValueError("unknown concern category")
        row = self.db.conn.execute(
            "SELECT version FROM writer_companion_profiles WHERE project_id=?",
            (self.project_id,),
        ).fetchone()
        version = row["version"] if row else 0
        if version != self._version:
            self._reload_profile()
            self._version = version
            self._cache.clear()

        key = (scene_id, concerns, max_guidance, version)
        if key in self._cache:
            self.cache_hits += 1
            self._cache.move_to_end(key)
            return self._cache[key]

        profile = self._profile or {}
        trusted = profile.get("authored_revisions", 0)
        accepted = profile.get("accepted_revisions", 0)
        authored_scopes = profile.get("authored_scopes", 0)
        accepted_scopes = profile.get("accepted_scopes", 0)
        if authored_scopes >= 2:
            voice_origin = "author"
            voice = profile.get("authored_voice", {})
        elif accepted_scopes >= 3:
            voice_origin = "accepted"
            voice = profile.get("accepted_voice", {})
        else:
            voice_origin = "insufficient"
            voice = {}

        applicable = [
            item for item in self._preferences
            if item["category"] == "general" or item["category"] in concerns
        ]
        # Current-scene specificity precedes generic preferences, within one
        # canonical priority list. Neither creates a second memory system.
        applicable.sort(key=lambda p: (p["category"] == "general", p["preference_key"]))
        instructions = tuple(
            ("遵守：" if item["direction"] == "prefer" else "避免：") + item["guidance"]
            for item in applicable[:max_guidance]
        )
        fp_payload = {
            "project_id": self.project_id, "version": version,
            "voice_origin": voice_origin, "voice": voice,
            "guidance": instructions,
        }
        checksum = hashlib.sha256(_json(fp_payload).encode("utf-8")).hexdigest()
        context = CompanionDraftContext(
            project_id=self.project_id,
            scene_id=scene_id,
            profile_version=version,
            accepted_revisions=accepted,
            authored_revisions=trusted,
            voice_origin=voice_origin,
            voice_metrics=MappingProxyType(dict(voice)),
            guidance=instructions,
            fingerprint=checksum,
        )
        self._cache[key] = context
        if len(self._cache) > self.max_cached_contexts:
            self._cache.popitem(last=False)
        return context

    def _reload_profile(self) -> None:
        self.profile_loads += 1
        row = self.db.conn.execute(
            """SELECT version,accepted_revisions,authored_revisions,
                      accepted_scopes,authored_scopes,accepted_voice_json,authored_voice_json
               FROM writer_companion_profiles WHERE project_id=?""",
            (self.project_id,),
        ).fetchone()
        self._profile = None if row is None else {
            "accepted_revisions": row["accepted_revisions"],
            "authored_revisions": row["authored_revisions"],
            "accepted_scopes": row["accepted_scopes"],
            "authored_scopes": row["authored_scopes"],
            "accepted_voice": json.loads(row["accepted_voice_json"]),
            "authored_voice": json.loads(row["authored_voice_json"]),
        }
        prefs = self.db.conn.execute(
            """SELECT p.preference_key,p.guidance,p.direction,p.category,
                      p.axis,p.conflict_group,p.evidence_scope,p.evidence_body_hash,
                      a.body_hash AS current_evidence_hash
               FROM writer_companion_preferences AS p
               LEFT JOIN accepted_prose AS a
                 ON p.evidence_scope=a.scope_id AND a.project_id=p.project_id
               WHERE p.project_id=?
               ORDER BY p.preference_key LIMIT ?""",
            (self.project_id, MAX_PREFERENCES),
        ).fetchall()
        # Evidence-linked insights become inert after source revision/deletion.
        # Bare author corrections remain valid and may be explicitly removed.
        self._preferences = tuple(dict(p) for p in prefs
            if p["evidence_scope"] is None
            or p["evidence_body_hash"] == p["current_evidence_hash"])
        self._stale_preferences = tuple(dict(p) for p in prefs
            if p["evidence_scope"] is not None
            and p["evidence_body_hash"] != p["current_evidence_hash"])

    def writing_sheet(self) -> dict[str, tuple[dict, ...]]:
        """Read-only, author-curated four-axis view over EXISTING rules.

        No model-generated personality inference and no duplicate persistence.
        Only currently supported evidence is included; edits retract stale
        source-dependent guidance on the next version check.
        """
        self.before_draft("__writing_sheet__", max_guidance=0)
        groups: dict[str, list[dict]] = {axis: [] for axis in WRITING_SHEET_AXES}
        for pref in self._preferences:
            axis = pref["axis"]
            if axis in groups:
                groups[axis].append({
                    "key": pref["preference_key"],
                    "guidance": pref["guidance"],
                    "direction": pref["direction"],
                    "evidence_scope": pref["evidence_scope"],
                })
        return {axis: tuple(items) for axis, items in groups.items()}

    def evidence_audit(self) -> tuple[dict, ...]:
        """Diagnosis only; never rewrites prose or silently repairs rules."""
        self.before_draft("__evidence_audit__", max_guidance=0)
        current = tuple({
            "key": p["preference_key"],
            "status": "explicit" if p["evidence_scope"] is None else "verified",
            "scope": p["evidence_scope"],
        } for p in self._preferences)
        stale = tuple({
            "key": p["preference_key"], "status": "stale",
            "scope": p["evidence_scope"],
        } for p in self._stale_preferences)
        return tuple(sorted(current + stale, key=lambda row: row["key"]))

    @property
    def cached_context_count(self) -> int:
        return len(self._cache)
