from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass
import hashlib
import json
import threading
from typing import Any, Callable, Mapping


def stable_fingerprint(payload: Any) -> str:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class ComputeResult:
    value: Any
    fingerprint: str
    cache_hit: bool
    shared_inflight: bool = False
    stale_after_compute: bool = False


@dataclass(frozen=True)
class InvalidationResult:
    changed_dependencies: tuple[str, ...]
    invalidated_keys: tuple[str, ...]


class ReactiveSkillRuntime:
    def __init__(self, *, max_cache_entries: int = 512, max_versions_per_scope: int = 2):
        if max_cache_entries < 1 or max_versions_per_scope < 1:
            raise ValueError("cache bounds must be >= 1")
        self.max_cache_entries = max_cache_entries
        self.max_versions_per_scope = max_versions_per_scope
        self._cache: OrderedDict[str, Any] = OrderedDict()
        self._key_dependencies: dict[str, set[str]] = {}
        self._dependency_index: dict[str, set[str]] = {}
        self._scope_keys: dict[tuple[str, str], list[str]] = {}
        self._key_scope: dict[str, tuple[str, str]] = {}
        self._dependency_versions: dict[str, int] = {}
        self._inflight: dict[str, threading.Event] = {}
        self._lock = threading.RLock()

    def _key(self, skill_name: str, scope: str, dependencies: Mapping[str, Any]) -> tuple[str, str]:
        fp = stable_fingerprint({"skill": skill_name, "scope": scope, "dependencies": dict(dependencies)})
        return f"{skill_name}:{scope}:{fp}", fp

    def _drop_key(self, key: str) -> None:
        self._cache.pop(key, None)
        for dep in self._key_dependencies.pop(key, set()):
            keys = self._dependency_index.get(dep)
            if keys is not None:
                keys.discard(key)
                if not keys:
                    self._dependency_index.pop(dep, None)
        scope_key = self._key_scope.pop(key, None)
        if scope_key is not None:
            keys = self._scope_keys.get(scope_key)
            if keys is not None:
                try:
                    keys.remove(key)
                except ValueError:
                    pass
                if not keys:
                    self._scope_keys.pop(scope_key, None)

    def _remember_key(self, key: str, *, skill_name: str, scope: str, dependencies: Mapping[str, Any], value: Any) -> None:
        self._cache[key] = value
        self._cache.move_to_end(key)
        dep_names = set(dependencies.keys())
        self._key_dependencies[key] = dep_names
        for dep in dep_names:
            self._dependency_index.setdefault(dep, set()).add(key)
        scope_key = (skill_name, scope)
        self._key_scope[key] = scope_key
        versions = self._scope_keys.setdefault(scope_key, [])
        if key not in versions:
            versions.append(key)

        while len(versions) > self.max_versions_per_scope:
            self._drop_key(versions[0])
            versions = self._scope_keys.get(scope_key, [])
        while len(self._cache) > self.max_cache_entries:
            self._drop_key(next(iter(self._cache)))

    def compute(self, *, skill_name: str, scope: str, dependencies: Mapping[str, Any], fn: Callable[[], Any]) -> ComputeResult:
        key, fp = self._key(skill_name, scope, dependencies)
        dep_names = tuple(sorted(dependencies.keys()))
        owner = False

        with self._lock:
            if key in self._cache:
                value = self._cache[key]
                self._cache.move_to_end(key)
                return ComputeResult(value, fp, cache_hit=True)
            if key in self._inflight:
                event = self._inflight[key]
            else:
                event = threading.Event()
                self._inflight[key] = event
                owner = True
            observed_versions = {dep: self._dependency_versions.get(dep, 0) for dep in dep_names}

        if not owner:
            event.wait()
            with self._lock:
                if key not in self._cache:
                    raise RuntimeError(f"in-flight computation became stale or failed for {skill_name}:{scope}")
                value = self._cache[key]
                self._cache.move_to_end(key)
                return ComputeResult(value, fp, cache_hit=True, shared_inflight=True)

        try:
            value = fn()
            with self._lock:
                stale = any(
                    self._dependency_versions.get(dep, 0) != observed_versions[dep]
                    for dep in dep_names
                )
                if not stale:
                    self._remember_key(
                        key, skill_name=skill_name, scope=scope,
                        dependencies=dependencies, value=value
                    )
            return ComputeResult(value, fp, cache_hit=False, stale_after_compute=stale)
        finally:
            with self._lock:
                evt = self._inflight.pop(key, None)
                if evt is not None:
                    evt.set()

    def invalidate(self, changed_dependencies) -> InvalidationResult:
        changed = tuple(sorted(set(changed_dependencies)))
        with self._lock:
            doomed: set[str] = set()
            for dep in changed:
                self._dependency_versions[dep] = self._dependency_versions.get(dep, 0) + 1
                doomed |= self._dependency_index.get(dep, set())
            for key in tuple(doomed):
                self._drop_key(key)
            return InvalidationResult(changed, tuple(sorted(doomed)))

    def clear_scope(self, skill_name: str, scope: str) -> int:
        with self._lock:
            keys = tuple(self._scope_keys.get((skill_name, scope), ()))
            for key in keys:
                self._drop_key(key)
            return len(keys)

    def clear(self) -> None:
        with self._lock:
            self._cache.clear()
            self._key_dependencies.clear()
            self._dependency_index.clear()
            self._scope_keys.clear()
            self._key_scope.clear()

    def cache_size(self) -> int:
        with self._lock:
            return len(self._cache)

    def dependency_index_size(self) -> int:
        with self._lock:
            return sum(len(keys) for keys in self._dependency_index.values())


@dataclass(frozen=True)
class CommitResult:
    commit_id: str
    committed: bool
    body_hash: str


class CommitLedger:
    """In-memory receipt ledger; durable transactional receipts are a later boundary."""

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

    def receipt_count(self) -> int:
        with self._lock:
            return len(self._commits)
