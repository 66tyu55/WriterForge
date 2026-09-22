from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import threading
from typing import Any, Callable, Mapping


def stable_fingerprint(payload: Any) -> str:
    """Return a stable SHA-256 fingerprint for JSON-compatible data."""
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class ComputeResult:
    value: Any
    fingerprint: str
    cache_hit: bool
    shared_inflight: bool = False


@dataclass(frozen=True)
class InvalidationResult:
    changed_dependencies: tuple[str, ...]
    invalidated_keys: tuple[str, ...]


class ReactiveSkillRuntime:
    """
    React-like runtime for expensive literary skills.

    Rules:
    - pure compute may run again;
    - unchanged dependency fingerprints reuse cached results;
    - dependency changes invalidate only affected computations;
    - concurrent identical requests use one in-flight computation.
    """

    def __init__(self):
        self._cache: dict[str, Any] = {}
        self._key_dependencies: dict[str, set[str]] = {}
        self._dependency_index: dict[str, set[str]] = {}
        self._inflight: dict[str, threading.Event] = {}
        self._lock = threading.RLock()

    def _key(self, skill_name: str, scope: str, dependencies: Mapping[str, Any]) -> tuple[str, str]:
        fp = stable_fingerprint({
            "skill": skill_name,
            "scope": scope,
            "dependencies": dict(dependencies),
        })
        return f"{skill_name}:{scope}:{fp}", fp

    def compute(
        self,
        *,
        skill_name: str,
        scope: str,
        dependencies: Mapping[str, Any],
        fn: Callable[[], Any],
    ) -> ComputeResult:
        key, fp = self._key(skill_name, scope, dependencies)
        owner = False
        event: threading.Event

        with self._lock:
            if key in self._cache:
                return ComputeResult(self._cache[key], fp, cache_hit=True)
            if key in self._inflight:
                event = self._inflight[key]
            else:
                event = threading.Event()
                self._inflight[key] = event
                owner = True

        if not owner:
            event.wait()
            with self._lock:
                if key not in self._cache:
                    raise RuntimeError(f"in-flight computation failed for {skill_name}:{scope}")
                return ComputeResult(self._cache[key], fp, cache_hit=True, shared_inflight=True)

        try:
            value = fn()
            with self._lock:
                self._cache[key] = value
                dep_names = set(dependencies.keys())
                self._key_dependencies[key] = dep_names
                for dep in dep_names:
                    self._dependency_index.setdefault(dep, set()).add(key)
            return ComputeResult(value, fp, cache_hit=False)
        finally:
            with self._lock:
                evt = self._inflight.pop(key, None)
                if evt is not None:
                    evt.set()

    def invalidate(self, changed_dependencies: set[str] | tuple[str, ...] | list[str]) -> InvalidationResult:
        changed = tuple(sorted(set(changed_dependencies)))
        with self._lock:
            doomed: set[str] = set()
            for dep in changed:
                doomed |= self._dependency_index.get(dep, set())
            for key in doomed:
                self._cache.pop(key, None)
                for dep in self._key_dependencies.pop(key, set()):
                    keys = self._dependency_index.get(dep)
                    if keys is not None:
                        keys.discard(key)
                        if not keys:
                            self._dependency_index.pop(dep, None)
            return InvalidationResult(changed, tuple(sorted(doomed)))

    def cache_size(self) -> int:
        with self._lock:
            return len(self._cache)


@dataclass(frozen=True)
class CommitResult:
    commit_id: str
    committed: bool
    body_hash: str


class CommitLedger:
    """Idempotent commit boundary: compute twice is okay; commit twice is a bug."""

    def __init__(self):
        self._commits: dict[str, str] = {}
        self._lock = threading.RLock()

    def commit_once(self, commit_id: str, body: str, effect: Callable[[], None]) -> CommitResult:
        body_hash = hashlib.sha256(body.encode("utf-8")).hexdigest()
        with self._lock:
            previous = self._commits.get(commit_id)
            if previous is not None:
                if previous != body_hash:
                    raise ValueError(f"commit_id {commit_id!r} already used for different content")
                return CommitResult(commit_id, committed=False, body_hash=body_hash)
            effect()
            self._commits[commit_id] = body_hash
            return CommitResult(commit_id, committed=True, body_hash=body_hash)
