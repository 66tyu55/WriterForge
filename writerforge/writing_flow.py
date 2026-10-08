"""Normal writing-route facade: the companion rides along, not a per-step Skill call.

The host still owns text generation, author provenance and acceptance. This
facade wires its two normal boundaries (prepare -> accept) to the durable story
coordinator and companion without exposing a separate learning command.
"""
from __future__ import annotations

from dataclasses import dataclass

from .db import WriterForgeDB
from .runtime import RuntimeEngine, Mode
from .story_work_tree import StoryWorkRoot
from .story_commit import (
    StoryEffect, EffectType, StoryCommitPlan, StoryCommitCoordinator,
    StoryCommitResult,
)
from .writing_companion import (
    WritingCompanion, CompanionDraftContext, validate_origin, validate_preference,
)


@dataclass(frozen=True)
class AuthorCorrection:
    key: str
    guidance: str = ""
    category: str = "general"
    direction: str = "prefer"
    action: str = "set"
    # These refine the EXISTING author-preference record, not a new skill.
    axis: str | None = None
    conflict_group: str | None = None
    evidence_scope: str | None = None
    evidence_excerpt: str | None = None

    def as_effect(self) -> StoryEffect:
        payload = {"action": self.action}
        if self.action == "set":
            payload.update(
                guidance=self.guidance, category=self.category, direction=self.direction
            )
        for name in ("axis", "conflict_group", "evidence_scope", "evidence_excerpt"):
            value = getattr(self, name)
            if value is not None:
                payload[name] = value
        validate_preference(self.key, payload)
        return StoryEffect(EffectType.SET_AUTHOR_PREFERENCE, self.key, payload)


@dataclass(frozen=True)
class DraftFrame:
    scene_id: str
    companion: CompanionDraftContext
    companion_guidance: str


class WritingFlow:
    """One long-lived object in the writing shell, no user-facing Skill invocation.

    The actual prose generator accepts DraftFrame.companion_guidance as an
    additive context string. The rest of the prompt (Canon, Character, scene)
    remains the generator's own responsibility and always outranks weak rhythm.
    """

    def __init__(
        self, db: WriterForgeDB, runtime: RuntimeEngine, project_id: str,
    ):
        if not project_id:
            raise ValueError("project_id is required")
        runtime.require(Mode.WRITE)
        self.project_id = project_id
        self.runtime = runtime
        self.companion = WritingCompanion(db, project_id)
        self.coordinator = StoryCommitCoordinator(db, runtime)

    def begin_draft(
        self, scene_id: str, *, concerns: tuple[str, ...] = (),
    ) -> DraftFrame:
        self.runtime.require(Mode.WRITE)
        ctx = self.companion.before_draft(scene_id, concerns=concerns)
        return DraftFrame(scene_id, ctx, ctx.compact_context())

    def review_writing_sheet(self) -> dict:
        """Read-only inspection of verified and stale style evidence.

        Independent editorial review may diagnose preferences but never edit
        accepted prose. Applying a correction still requires accept_draft().
        """
        self.runtime.require(Mode.WRITE)
        return {
            "axes": self.companion.writing_sheet(),
            "evidence": self.companion.evidence_audit(),
        }

    def accept_draft(
        self,
        commit_id: str,
        scene_id: str,
        body: str,
        *,
        origin: str = "accepted",
        corrections: tuple[AuthorCorrection, ...] = (),
        finished_work_root: StoryWorkRoot | None = None,
    ) -> StoryCommitResult:
        self.runtime.require(Mode.WRITE)
        validate_origin(origin)
        if not isinstance(body, str) or not scene_id:
            raise ValueError("scene_id and prose body are required")
        effects = (
            StoryEffect(
                EffectType.ACCEPT_PROSE, scene_id,
                {"body": body, "origin": origin},
            ),
            *(correction.as_effect() for correction in corrections),
        )
        work_fingerprint = (
            finished_work_root.finished_fingerprint()
            if finished_work_root is not None else None
        )
        plan = StoryCommitPlan(
            self.project_id, commit_id, effects,
            work_fingerprint=work_fingerprint,
        )
        return self.coordinator.commit(plan, work_root=finished_work_root)
