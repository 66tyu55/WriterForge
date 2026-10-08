"""Writing companion that grows from accepted work without interrupting drafting.

The source-learning Xuehai and model weights remain unchanged. Only the durable
StoryCommitCoordinator writes companion evidence; all reads are bounded, cheap,
and scoped to one project. Weak acceptance signals are NEVER called author voice.
"""
from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass
import hashlib
import json
from typing import Any, Mapping

from .voice import fingerprint


MAX_SAMPLE_CHARS = 8192
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
        if any(field in payload for field in ("guidance", "direction", "category")):
            raise CompanionEvidenceError("remove preference cannot carry guidance")
        return
    guidance = payload.get("guidance")
    if type(guidance) is not str or not guidance.strip() or len(guidance) > MAX_GUIDANCE_CHARS:
        raise CompanionEvidenceError("guidance must be 1..240 characters")
    if payload.get("direction", "prefer") not in DIRECTIONS:
        raise CompanionEvidenceError("invalid preference direction")
    if payload.get("category", "general") not in CATEGORIES:
        raise CompanionEvidenceError("invalid preference category")


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
    conn, project_id: str, body: str, *, origin: str, changed: bool,
) -> None:
    """Run INSIDE the receipt/story transaction; only genuinely changed text grows."""
    validate_origin(origin)
    if not changed or not body.strip():
        return
    # Reading only the tail avoids full-book style analysis on every tiny edit.
    sample = body[-MAX_SAMPLE_CHARS:]
    voice = fingerprint(sample).__dict__
    old = conn.execute(
        """SELECT version,accepted_revisions,authored_revisions,accepted_chars,
                  accepted_voice_json,authored_voice_json
           FROM writer_companion_profiles WHERE project_id=?""",
        (project_id,),
    ).fetchone()
    if old is None:
        count = trusted = accepted_chars = version = 0
        accepted_voice, authored_voice = {}, {}
    else:
        count = old["accepted_revisions"]
        trusted = old["authored_revisions"]
        accepted_chars = old["accepted_chars"]
        version = old["version"]
        accepted_voice = json.loads(old["accepted_voice_json"])
        authored_voice = json.loads(old["authored_voice_json"])
    accepted_voice = _update_ema(accepted_voice, voice, count)
    count += 1
    if origin in TRUSTED_ORIGINS:
        authored_voice = _update_ema(authored_voice, voice, trusted, alpha=0.30)
        trusted += 1
    conn.execute(
        """INSERT INTO writer_companion_profiles(
               project_id,version,accepted_revisions,authored_revisions,
               accepted_chars,accepted_voice_json,authored_voice_json
           ) VALUES(?,?,?,?,?,?,?)
           ON CONFLICT(project_id) DO UPDATE SET
             version=excluded.version,accepted_revisions=excluded.accepted_revisions,
             authored_revisions=excluded.authored_revisions,
             accepted_chars=excluded.accepted_chars,
             accepted_voice_json=excluded.accepted_voice_json,
             authored_voice_json=excluded.authored_voice_json,
             updated_at=CURRENT_TIMESTAMP""",
        (project_id, version + 1, count, trusted, accepted_chars + len(sample),
         _json(accepted_voice), _json(authored_voice)),
    )


def apply_preference(conn, project_id: str, key: str, payload: Mapping[str, Any]) -> None:
    """Only caller-explicit feedback; NEVER derived semantically from AI drafts."""
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
        current = conn.execute(
            """SELECT guidance,direction,category FROM writer_companion_preferences
               WHERE project_id=? AND preference_key=?""", (project_id, key),
        ).fetchone()
        guidance = payload["guidance"].strip()
        direction = payload.get("direction", "prefer")
        category = payload.get("category", "general")
        if current and (current["guidance"], current["direction"], current["category"]) == (
            guidance, direction, category,
        ):
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
                 project_id,preference_key,guidance,direction,category
               ) VALUES(?,?,?,?,?)
               ON CONFLICT(project_id,preference_key) DO UPDATE SET
                 guidance=excluded.guidance,direction=excluded.direction,
                 category=excluded.category,updated_at=CURRENT_TIMESTAMP""",
            (project_id, key, guidance, direction, category),
        )
    # Preference-only commits should still create a versioned project profile.
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
            lines.append("已接受稿件的节奏仅是弱观察，不等同于作者个人风格。")
        if self.guidance:
            lines.extend(self.guidance)
        return "\n".join(lines)[:max_chars]


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
        if trusted >= 2:
            voice_origin = "author"
            voice = profile.get("authored_voice", {})
        elif accepted >= 3:
            voice_origin = "accepted"
            voice = profile.get("accepted_voice", {})
        else:
            voice_origin = "insufficient"
            voice = {}

        applicable = [
            item for item in self._preferences
            if item["category"] == "general" or item["category"] in concerns
        ]
        applicable.sort(key=lambda p: (p["category"] != "general", p["preference_key"]))
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
            voice_metrics=voice,
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
                      accepted_voice_json,authored_voice_json
               FROM writer_companion_profiles WHERE project_id=?""",
            (self.project_id,),
        ).fetchone()
        self._profile = None if row is None else {
            "accepted_revisions": row["accepted_revisions"],
            "authored_revisions": row["authored_revisions"],
            "accepted_voice": json.loads(row["accepted_voice_json"]),
            "authored_voice": json.loads(row["authored_voice_json"]),
        }
        prefs = self.db.conn.execute(
            """SELECT preference_key,guidance,direction,category
               FROM writer_companion_preferences WHERE project_id=?
               ORDER BY preference_key LIMIT ?""", (self.project_id, MAX_PREFERENCES),
        ).fetchall()
        self._preferences = tuple(dict(p) for p in prefs)

    @property
    def cached_context_count(self) -> int:
        return len(self._cache)
