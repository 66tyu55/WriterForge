from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import hashlib
import json
from typing import Any, Mapping, Sequence

from .db import WriterForgeDB
from .runtime import RuntimeEngine, Mode
from .story import CanonPatchRequired
from .story_work_tree import StoryWorkRoot


def _json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


class EffectType(str, Enum):
    ACCEPT_PROSE = "ACCEPT_PROSE"
    SET_CHARACTER = "SET_CHARACTER"
    UPSERT_CANON = "UPSERT_CANON"
    PATCH_CANON = "PATCH_CANON"
    SET_PROMISE = "SET_PROMISE"
    SET_READER_STATE = "SET_READER_STATE"
    UPSERT_CAUSAL_EVENT = "UPSERT_CAUSAL_EVENT"
    SET_PROJECT_POSITION = "SET_PROJECT_POSITION"
    ADD_ITEM_CLAIM = "ADD_ITEM_CLAIM"
    SET_WORLD_RULE = "SET_WORLD_RULE"


@dataclass(frozen=True)
class StoryEffect:
    type: EffectType
    target: str
    payload: Mapping[str, Any]

    def canonical(self) -> dict[str, Any]:
        return {
            "type": self.type.value,
            "target": self.target,
            "payload": dict(self.payload),
        }


@dataclass(frozen=True)
class StoryCommitPlan:
    project_id: str
    commit_id: str
    effects: tuple[StoryEffect, ...]
    work_fingerprint: str | None = None

    def bundle_hash(self) -> str:
        raw = _json({
            "project_id": self.project_id,
            "commit_id": self.commit_id,
            "work_fingerprint": self.work_fingerprint,
            "effects": [effect.canonical() for effect in self.effects],
        })
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class StoryCommitResult:
    commit_id: str
    bundle_hash: str
    committed: bool
    replayed: bool
    effects_applied: int
    adopted_work_tree: bool


class StoryCommitError(RuntimeError):
    pass


class PostCommitAdoptionError(StoryCommitError):
    def __init__(self, message: str, *, commit_id: str, bundle_hash: str):
        super().__init__(message)
        self.commit_id = commit_id
        self.bundle_hash = bundle_hash
        self.durable_committed = True


_EFFECT_ORDER = {
    EffectType.UPSERT_CANON: 10,
    EffectType.PATCH_CANON: 10,
    EffectType.SET_CHARACTER: 20,
    EffectType.SET_PROMISE: 30,
    EffectType.SET_READER_STATE: 40,
    EffectType.UPSERT_CAUSAL_EVENT: 50,
    EffectType.ADD_ITEM_CLAIM: 60,
    EffectType.SET_WORLD_RULE: 70,
    EffectType.SET_PROJECT_POSITION: 80,
    EffectType.ACCEPT_PROSE: 90,
}


class StoryCommitCoordinator:
    """
    Durable story commit boundary.

    All effects + audit journal + idempotence receipt are written in one SQLite
    transaction. WorkTree adoption happens only after SQLite COMMIT succeeds.
    """

    def __init__(self, db: WriterForgeDB, runtime: RuntimeEngine):
        self.db = db
        self.runtime = runtime

    def commit(
        self,
        plan: StoryCommitPlan,
        *,
        work_root: StoryWorkRoot | None = None,
    ) -> StoryCommitResult:
        self.runtime.require(Mode.WRITE)
        if not plan.project_id or not plan.commit_id:
            raise StoryCommitError("project_id and commit_id are required")
        if not plan.effects:
            raise StoryCommitError("commit plan requires at least one effect")
        if work_root is not None:
            if work_root.finished_work is None:
                raise StoryCommitError("work_root has no finished work")
            actual_fp = work_root.finished_fingerprint()
            if plan.work_fingerprint != actual_fp:
                raise StoryCommitError("commit plan work_fingerprint does not match finished WorkTree")

        bundle_hash = plan.bundle_hash()
        conn = self.db.conn
        if conn.in_transaction:
            raise StoryCommitError("nested story transaction is not allowed")

        try:
            conn.execute("BEGIN IMMEDIATE")
            prior = conn.execute(
                """SELECT bundle_hash,work_fingerprint
                   FROM story_commit_receipts
                   WHERE project_id=? AND commit_id=?""",
                (plan.project_id, plan.commit_id),
            ).fetchone()

            if prior is not None:
                if prior["bundle_hash"] != bundle_hash:
                    raise StoryCommitError(
                        f"commit_id {plan.commit_id!r} already used for a different effect bundle"
                    )
                conn.commit()
                adopted = self._adopt_after_durable_commit(work_root, plan, bundle_hash)
                return StoryCommitResult(
                    plan.commit_id, bundle_hash,
                    committed=False, replayed=True,
                    effects_applied=0, adopted_work_tree=adopted,
                )

            ordered = self._validate_and_order(conn, plan)
            effects_json = _json([effect.canonical() for effect in ordered])

            # Receipt is inserted before journal rows because the journal FK is
            # deferred; all rows remain invisible until the transaction commits.
            conn.execute(
                """INSERT INTO story_commit_receipts(
                       project_id,commit_id,bundle_hash,effects_json,work_fingerprint
                   ) VALUES(?,?,?,?,?)""",
                (
                    plan.project_id,
                    plan.commit_id,
                    bundle_hash,
                    effects_json,
                    plan.work_fingerprint,
                ),
            )

            for ordinal, effect in enumerate(ordered):
                self._apply_effect(conn, plan.project_id, effect)
                conn.execute(
                    """INSERT INTO story_effect_journal(
                           project_id,commit_id,ordinal,effect_type,target,payload_json
                       ) VALUES(?,?,?,?,?,?)""",
                    (
                        plan.project_id,
                        plan.commit_id,
                        ordinal,
                        effect.type.value,
                        effect.target,
                        _json(dict(effect.payload)),
                    ),
                )

            conn.commit()
        except Exception:
            if conn.in_transaction:
                conn.rollback()
            if work_root is not None and work_root.finished_work is not None:
                # Drop speculative tree but preserve current pending updates for retry.
                work_root.discard_finished(drop_rendered_updates=False)
            raise

        adopted = self._adopt_after_durable_commit(work_root, plan, bundle_hash)
        return StoryCommitResult(
            plan.commit_id,
            bundle_hash,
            committed=True,
            replayed=False,
            effects_applied=len(plan.effects),
            adopted_work_tree=adopted,
        )

    def _adopt_after_durable_commit(
        self,
        work_root: StoryWorkRoot | None,
        plan: StoryCommitPlan,
        bundle_hash: str,
    ) -> bool:
        if work_root is None:
            return False
        try:
            work_root.adopt_after_commit()
            return True
        except Exception as exc:
            raise PostCommitAdoptionError(
                "durable story commit succeeded but WorkTree adoption failed; rebuild WorkTree from durable state",
                commit_id=plan.commit_id,
                bundle_hash=bundle_hash,
            ) from exc

    def _validate_and_order(self, conn, plan: StoryCommitPlan) -> tuple[StoryEffect, ...]:
        seen: set[tuple[str, str]] = set()
        effects = tuple(plan.effects)
        for effect in effects:
            _json(effect.canonical())  # fail before any business mutation if payload is not JSON-safe
            identity = self._identity(effect)
            if identity in seen:
                raise StoryCommitError(
                    f"duplicate effect target in one commit: {identity[0]}:{identity[1]}"
                )
            seen.add(identity)
            self._validate_effect(conn, plan.project_id, effect)
        return tuple(sorted(effects, key=lambda e: (_EFFECT_ORDER[e.type], e.type.value, e.target)))

    @staticmethod
    def _identity(effect: StoryEffect) -> tuple[str, str]:
        family = {
            EffectType.UPSERT_CANON: "canon",
            EffectType.PATCH_CANON: "canon",
            EffectType.SET_READER_STATE: "reader",
            EffectType.SET_PROJECT_POSITION: "project_position",
        }.get(effect.type, effect.type.value)
        target = "singleton" if effect.type in {EffectType.SET_READER_STATE, EffectType.SET_PROJECT_POSITION} else effect.target
        return family, target

    def _validate_effect(self, conn, project_id: str, effect: StoryEffect) -> None:
        p = effect.payload
        if effect.type == EffectType.ACCEPT_PROSE:
            if not effect.target or not isinstance(p.get("body"), str):
                raise StoryCommitError("ACCEPT_PROSE requires target scope and string body")
        elif effect.type == EffectType.SET_CHARACTER:
            if not effect.target or not isinstance(p.get("state"), dict):
                raise StoryCommitError("SET_CHARACTER requires target and state object")
        elif effect.type == EffectType.UPSERT_CANON:
            if not effect.target or not isinstance(p.get("statement"), str):
                raise StoryCommitError("UPSERT_CANON requires target and statement")
            old = conn.execute(
                "SELECT statement,status FROM canon WHERE project_id=? AND canon_id=?",
                (project_id, effect.target),
            ).fetchone()
            if old and old["status"] == "immutable" and old["statement"] != p["statement"]:
                raise CanonPatchRequired(f"Immutable canon {effect.target} requires PATCH_CANON")
        elif effect.type == EffectType.PATCH_CANON:
            if not isinstance(p.get("statement"), str) or not p.get("reason"):
                raise StoryCommitError("PATCH_CANON requires statement and reason")
            row = conn.execute(
                "SELECT 1 FROM canon WHERE project_id=? AND canon_id=?",
                (project_id, effect.target),
            ).fetchone()
            if row is None:
                raise StoryCommitError(f"cannot patch missing canon {effect.target}")
        elif effect.type == EffectType.SET_PROMISE:
            if not isinstance(p.get("payload"), dict):
                raise StoryCommitError("SET_PROMISE requires payload object")
        elif effect.type == EffectType.SET_READER_STATE:
            if not isinstance(p.get("state"), dict):
                raise StoryCommitError("SET_READER_STATE requires state object")
        elif effect.type == EffectType.UPSERT_CAUSAL_EVENT:
            if not isinstance(p.get("payload"), dict):
                raise StoryCommitError("UPSERT_CAUSAL_EVENT requires payload object")
        elif effect.type == EffectType.SET_PROJECT_POSITION:
            if not isinstance(p.get("chapter"), int):
                raise StoryCommitError("SET_PROJECT_POSITION requires integer chapter")
        elif effect.type == EffectType.ADD_ITEM_CLAIM:
            if not isinstance(p.get("time_index"), int):
                raise StoryCommitError("ADD_ITEM_CLAIM requires integer time_index")
        elif effect.type == EffectType.SET_WORLD_RULE:
            if "expected_value" not in p:
                raise StoryCommitError("SET_WORLD_RULE requires expected_value")

    @staticmethod
    def _story_event(conn, project_id: str, event_type: str, path: str, old: Any, new: Any) -> None:
        conn.execute(
            """INSERT INTO story_events(project_id,event_type,path,old_json,new_json)
               VALUES(?,?,?,?,?)""",
            (project_id, event_type, path, _json(old), _json(new)),
        )

    def _apply_effect(self, conn, project_id: str, effect: StoryEffect) -> None:
        p = effect.payload
        if effect.type == EffectType.ACCEPT_PROSE:
            old = conn.execute(
                "SELECT body_hash,revision FROM accepted_prose WHERE project_id=? AND scope_id=?",
                (project_id, effect.target),
            ).fetchone()
            body = p["body"]
            body_hash = hashlib.sha256(body.encode("utf-8")).hexdigest()
            conn.execute(
                """INSERT INTO accepted_prose(project_id,scope_id,body,body_hash,revision)
                   VALUES(?,?,?,?,1)
                   ON CONFLICT(project_id,scope_id) DO UPDATE SET
                     body=excluded.body,
                     body_hash=excluded.body_hash,
                     revision=accepted_prose.revision+1,
                     updated_at=CURRENT_TIMESTAMP""",
                (project_id, effect.target, body, body_hash),
            )
            self._story_event(
                conn, project_id, "prose_accepted", f"prose.{effect.target}",
                dict(old) if old else None, {"body_hash": body_hash},
            )
        elif effect.type == EffectType.SET_CHARACTER:
            row = conn.execute(
                "SELECT state_json FROM character_state WHERE project_id=? AND character_id=?",
                (project_id, effect.target),
            ).fetchone()
            old = json.loads(row["state_json"]) if row else None
            state = p["state"]
            conn.execute(
                """INSERT INTO character_state(project_id,character_id,state_json)
                   VALUES(?,?,?)
                   ON CONFLICT(project_id,character_id) DO UPDATE SET
                     state_json=excluded.state_json,updated_at=CURRENT_TIMESTAMP""",
                (project_id, effect.target, _json(state)),
            )
            self._story_event(conn, project_id, "character_changed", f"character.{effect.target}", old, state)
        elif effect.type == EffectType.UPSERT_CANON:
            old = conn.execute(
                "SELECT statement,status FROM canon WHERE project_id=? AND canon_id=?",
                (project_id, effect.target),
            ).fetchone()
            statement = p["statement"]
            status = p.get("status", "immutable")
            conn.execute(
                """INSERT INTO canon(project_id,canon_id,type,statement,status,established_at)
                   VALUES(?,?,?,?,?,?)
                   ON CONFLICT(project_id,canon_id) DO UPDATE SET
                     type=excluded.type,statement=excluded.statement,
                     status=excluded.status,established_at=excluded.established_at""",
                (
                    project_id, effect.target, p.get("type", "fact"),
                    statement, status, p.get("established_at", ""),
                ),
            )
            self._story_event(
                conn, project_id, "canon_changed", f"canon.{effect.target}",
                dict(old) if old else None, {"statement": statement, "status": status},
            )
        elif effect.type == EffectType.PATCH_CANON:
            old = conn.execute(
                "SELECT statement FROM canon WHERE project_id=? AND canon_id=?",
                (project_id, effect.target),
            ).fetchone()
            conn.execute(
                """INSERT INTO canon_patches(project_id,canon_id,old_statement,new_statement,reason)
                   VALUES(?,?,?,?,?)""",
                (project_id, effect.target, old["statement"], p["statement"], p["reason"]),
            )
            conn.execute(
                "UPDATE canon SET statement=? WHERE project_id=? AND canon_id=?",
                (p["statement"], project_id, effect.target),
            )
            self._story_event(
                conn, project_id, "canon_patched", f"canon.{effect.target}",
                old["statement"], p["statement"],
            )
        elif effect.type == EffectType.SET_PROMISE:
            row = conn.execute(
                "SELECT payload_json,status FROM promises WHERE project_id=? AND promise_id=?",
                (project_id, effect.target),
            ).fetchone()
            old = {"payload": json.loads(row["payload_json"]), "status": row["status"]} if row else None
            payload = p["payload"]
            status = p.get("status", "open")
            conn.execute(
                """INSERT INTO promises(project_id,promise_id,payload_json,status)
                   VALUES(?,?,?,?)
                   ON CONFLICT(project_id,promise_id) DO UPDATE SET
                     payload_json=excluded.payload_json,status=excluded.status""",
                (project_id, effect.target, _json(payload), status),
            )
            self._story_event(conn, project_id, "promise_changed", f"promise.{effect.target}", old, {"payload": payload, "status": status})
        elif effect.type == EffectType.SET_READER_STATE:
            row = conn.execute(
                "SELECT payload_json FROM reader_state WHERE project_id=?",
                (project_id,),
            ).fetchone()
            old = json.loads(row["payload_json"]) if row else None
            state = p["state"]
            conn.execute(
                """INSERT INTO reader_state(project_id,payload_json) VALUES(?,?)
                   ON CONFLICT(project_id) DO UPDATE SET payload_json=excluded.payload_json""",
                (project_id, _json(state)),
            )
            self._story_event(conn, project_id, "reader_changed", "reader", old, state)
        elif effect.type == EffectType.UPSERT_CAUSAL_EVENT:
            row = conn.execute(
                "SELECT payload_json FROM causal_events WHERE project_id=? AND event_id=?",
                (project_id, effect.target),
            ).fetchone()
            old = json.loads(row["payload_json"]) if row else None
            payload = p["payload"]
            conn.execute(
                """INSERT INTO causal_events(project_id,event_id,payload_json)
                   VALUES(?,?,?)
                   ON CONFLICT(project_id,event_id) DO UPDATE SET payload_json=excluded.payload_json""",
                (project_id, effect.target, _json(payload)),
            )
            self._story_event(conn, project_id, "causal_changed", f"causal.{effect.target}", old, payload)
        elif effect.type == EffectType.SET_PROJECT_POSITION:
            row = conn.execute(
                "SELECT current_chapter,current_scene FROM project_meta WHERE project_id=?",
                (project_id,),
            ).fetchone()
            old = dict(row) if row else None
            chapter = p["chapter"]
            scene = p.get("scene", "")
            conn.execute(
                """INSERT INTO project_meta(project_id,current_chapter,current_scene)
                   VALUES(?,?,?)
                   ON CONFLICT(project_id) DO UPDATE SET
                     current_chapter=excluded.current_chapter,current_scene=excluded.current_scene""",
                (project_id, chapter, scene),
            )
            self._story_event(conn, project_id, "position_changed", "project.position", old, {"chapter": chapter, "scene": scene})
        elif effect.type == EffectType.ADD_ITEM_CLAIM:
            conn.execute(
                """INSERT INTO item_claims(project_id,item_id,time_index,holder,location,ref)
                   VALUES(?,?,?,?,?,?)""",
                (
                    project_id, effect.target, p["time_index"],
                    p.get("holder"), p.get("location"), p.get("ref", ""),
                ),
            )
            self._story_event(conn, project_id, "item_claim_added", f"item.{effect.target}", None, dict(p))
        elif effect.type == EffectType.SET_WORLD_RULE:
            old = conn.execute(
                "SELECT expected_value,statement FROM world_rules WHERE project_id=? AND rule_key=?",
                (project_id, effect.target),
            ).fetchone()
            conn.execute(
                """INSERT INTO world_rules(project_id,rule_key,expected_value,statement)
                   VALUES(?,?,?,?)
                   ON CONFLICT(project_id,rule_key) DO UPDATE SET
                     expected_value=excluded.expected_value,statement=excluded.statement""",
                (project_id, effect.target, str(p["expected_value"]), p.get("statement", "")),
            )
            self._story_event(conn, project_id, "world_rule_changed", f"world.{effect.target}", dict(old) if old else None, dict(p))
        else:
            raise StoryCommitError(f"unsupported effect type: {effect.type}")
