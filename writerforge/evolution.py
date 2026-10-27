from __future__ import annotations

from dataclasses import dataclass, field, asdict, replace
from enum import Enum
from collections import Counter, defaultdict
from hashlib import sha256
import hmac
import json
import os
import re
from typing import Iterable


class SkillStatus(str, Enum):
    ACTIVE = "active"
    NEEDS_REVALIDATION = "needs_revalidation"
    SHADOW = "shadow"
    RETIRED = "retired"


@dataclass(frozen=True)
class CapabilityContract:
    name: str
    level: int
    statement: str
    depends_on: dict[str, int] = field(default_factory=dict)
    status: SkillStatus = SkillStatus.ACTIVE
    revision: int = 1

    def __post_init__(self):
        if not 1 <= int(self.level) <= 10:
            raise ValueError("capability level must be 1..10")
        if not self.statement.strip():
            raise ValueError("capability statement is required")
        # A frozen dataclass still permits mutation of nested dicts unless
        # inputs are detached; exported snapshots are separately copied.
        object.__setattr__(self,"depends_on",dict(self.depends_on))


@dataclass(frozen=True)
class CapabilityLag:
    skill: str
    dependency: str
    required_level: int
    actual_level: int | None


@dataclass(frozen=True)
class OptionalExecutionPermit:
    """External, reviewer-signed authorization for ONE pinned optional artifact.

    This is not a model claim, a registry promotion or a host API credential.
    The signer verifies the intended contract/capsule before signing; the
    scheduler rechecks current registry state and actual bytes at dispatch.
    """

    name: str
    revision: int
    contract_sha256: str
    capsule_sha256: str
    dependency_revisions: tuple[tuple[str, int], ...]
    required_host_capabilities: tuple[str, ...]
    reviewer_id: str
    review_id: str
    signature: str

    def signing_payload(self) -> dict:
        return {
            "kind": "wf.optional-habit-execution.v1",
            "name": self.name,
            "revision": self.revision,
            "contract_sha256": self.contract_sha256,
            "capsule_sha256": self.capsule_sha256,
            "dependency_revisions": [list(pair) for pair in self.dependency_revisions],
            "required_host_capabilities": list(self.required_host_capabilities),
            "reviewer_id": self.reviewer_id,
            "review_id": self.review_id,
            "auto_promotion": False,
        }

    def fingerprint(self) -> str:
        """Queue/dispatch binding; replaying an older approval won't fit."""
        payload = {"grant": self.signing_payload(), "signature": self.signature}
        return sha256(json.dumps(
            payload, ensure_ascii=False, sort_keys=True,
            separators=(",", ":"), allow_nan=False).encode("utf-8")).hexdigest()


class SkillRegistry:
    """Read model and durable storage for skills; formal upgrades are gated.

    Normal callers may register an initial skill once and may LOWER trust to
    SHADOW, but cannot promote levels or reactivate via plain booleans. The
    only active-upgrade path is an independently verified, manually approved
    EvolutionEngine permit, checked AGAIN before atomic SQLite update.

    Raw SQLite write access and arbitrary Python monkeypatching are outside
    this API security boundary; this is not a privilege sandbox.
    """
    def __init__(self, db=None, scope: str="__system__", *,
                 bootstrap_verifier_key: bytes | None = None):
        self._skills: dict[str, CapabilityContract] = {}
        self.db=db
        self.scope=scope
        self._trusted_promotion_key=None
        if bootstrap_verifier_key is None:
            raw=os.environ.get("WRITERFORGE_BOOTSTRAP_VERIFY_KEY_HEX")
            if raw is not None:
                try:
                    bootstrap_verifier_key=bytes.fromhex(raw)
                except ValueError as exc:
                    raise ValueError("SKILL_BOOTSTRAP_VERIFIER_INVALID") from exc
        if bootstrap_verifier_key is not None and (
            not isinstance(bootstrap_verifier_key,bytes) or
            len(bootstrap_verifier_key)<16):
            raise ValueError("SKILL_BOOTSTRAP_VERIFIER_INVALID")
        self._bootstrap_verifier_key=bootstrap_verifier_key
        if self.db is not None:
            for row in self.db.conn.execute(
                "SELECT skill_name,level,statement,dependencies_json,status,"
                "revision FROM skill_capabilities WHERE scope=? "
                "ORDER BY skill_name LIMIT 256",(self.scope,)):
                c=CapabilityContract(
                    row["skill_name"],int(row["level"]),row["statement"],
                    json.loads(row["dependencies_json"]),
                    SkillStatus(row["status"]),int(row["revision"]))
                self._skills[c.name]=c

    @staticmethod
    def _snapshot(item: CapabilityContract) -> CapabilityContract:
        return replace(item,depends_on=dict(item.depends_on))

    @staticmethod
    def execution_contract_sha256(item: CapabilityContract) -> str:
        """Canonical identity of the FULL registry contract, not just its name."""
        if not isinstance(item, CapabilityContract):
            raise TypeError("OPTIONAL_HABIT_CONTRACT_REQUIRED")
        payload = {
            "name": item.name, "level": item.level,
            "revision": item.revision, "status": item.status.value,
            "statement": item.statement,
            "dependencies": item.depends_on,
        }
        return sha256(json.dumps(
            payload, ensure_ascii=False, sort_keys=True,
            separators=(",", ":"), allow_nan=False).encode("utf-8")).hexdigest()

    def _bind_promotion_verifier(self,key:bytes|None):
        if key is None:
            return
        if not isinstance(key,bytes) or len(key)<16:
            raise ValueError("SKILL_PROMOTION_VERIFIER_INVALID")
        if (self._trusted_promotion_key is not None and
                not hmac.compare_digest(self._trusted_promotion_key,key)):
            raise PermissionError("SKILL_PROMOTION_VERIFIER_IMMUTABLE")
        self._trusted_promotion_key=key

    def register(self, contract: CapabilityContract) -> None:
        """New unverified ACTIVE capabilities start at level 1 only.

        Legacy imports keep their historically claimed level in SHADOW,
        never call it mastered. A high ACTIVE initial declaration needs a
        reviewer-signed, explicit software bootstrap attestation.
        """
        if (contract.level>1 and contract.status==SkillStatus.ACTIVE):
            raise PermissionError("SKILL_BOOTSTRAP_ATTESTATION_REQUIRED")
        return self._register_initial(contract)

    def import_legacy_capability(self, contract: CapabilityContract, *,
                                 provenance: str):
        if not isinstance(provenance,str) or not provenance.strip():
            raise ValueError("SKILL_BOOTSTRAP_LEGACY_PROVENANCE_REQUIRED")
        self._register_initial(replace(
            contract,status=SkillStatus.SHADOW))
        return {"status":"UNVERIFIED_LEGACY_SHADOW",
                "literary_mastery_verified":False}

    @staticmethod
    def bootstrap_payload(contract: CapabilityContract, *,
                          reviewer_id: str,review_id: str):
        if (not isinstance(contract,CapabilityContract) or
            not isinstance(reviewer_id,str) or
            not isinstance(review_id,str) or
            not re.fullmatch(r"[A-Za-z0-9_-]{2,80}",reviewer_id) or
            not re.fullmatch(r"[A-Za-z0-9_-]{2,80}",review_id)):
            raise ValueError("SKILL_BOOTSTRAP_FIELDS_INVALID")
        return {"contract":"writerforge.v64-high-level-bootstrap",
                "name":contract.name,"level":contract.level,
                "status":contract.status.value,
                "statement":contract.statement,
                "dependencies":contract.depends_on,
                "revision":contract.revision,
                "reviewer_id":reviewer_id,
                "review_id":review_id,
                "literary_mastery_verified":False}

    def register_verified(self, contract: CapabilityContract, *,
                          reviewer_id:str,review_id:str,signature:str):
        if self._bootstrap_verifier_key is None:
            raise PermissionError("SKILL_BOOTSTRAP_VERIFIER_REQUIRED")
        payload=self.bootstrap_payload(contract,reviewer_id=reviewer_id,
                                       review_id=review_id)
        expected=hmac.new(
            self._bootstrap_verifier_key,
            json.dumps(payload,ensure_ascii=False,sort_keys=True,
                       separators=(",",":"),allow_nan=False).encode(),
            "sha256").hexdigest()
        if not isinstance(signature,str) or not hmac.compare_digest(
            expected,signature):
            raise PermissionError("SKILL_BOOTSTRAP_ATTESTATION_INVALID")
        self._register_initial(contract)
        return {"accepted":True,"literary_mastery_verified":False}

    def _register_initial(self, contract: CapabilityContract) -> None:
        """Create an initial capability contract exactly once.

        Registration is NOT a way to overwrite/promote an existing ID.
        New unverified high-level declarations remain a separate release
        policy risk, not evidence of WF's actual artistic ability.
        """
        if not isinstance(contract,CapabilityContract):
            raise TypeError("SKILL_REGISTRATION_SCHEMA_INVALID")
        proposed=self._snapshot(contract)
        old=self._skills.get(proposed.name)
        if old is not None:
            if old!=proposed:
                raise ValueError("SKILL_REGISTRATION_IMMUTABLE_EXISTS")
            return
        if len(self._skills)>=256:
            raise ValueError("capability registry is capped at 256 entries")
        if self.db is not None:
            conn=self.db.conn
            if conn.in_transaction:
                raise RuntimeError("SKILL_REGISTRATION_NESTED_TRANSACTION")
            try:
                conn.execute("BEGIN IMMEDIATE")
                prior=conn.execute(
                    "SELECT skill_name FROM skill_capabilities "
                    "WHERE scope=? AND skill_name=?",
                    (self.scope,proposed.name)).fetchone()
                if prior is not None:
                    raise ValueError("SKILL_REGISTRATION_CONCURRENT_EXISTS")
                conn.execute(
                    "INSERT INTO skill_capabilities("
                    "scope,skill_name,level,status,revision,statement,"
                    "dependencies_json) VALUES(?,?,?,?,?,?,?)",
                    (self.scope,proposed.name,proposed.level,
                     proposed.status.value,proposed.revision,
                     proposed.statement,
                     json.dumps(proposed.depends_on,ensure_ascii=False,
                                sort_keys=True)))
                conn.commit()
            except Exception:
                if conn.in_transaction:
                    conn.rollback()
                raise
        self._skills[proposed.name]=proposed

    def get(self,name:str)->CapabilityContract:
        return self._snapshot(self._skills[name])

    def all(self)->list[CapabilityContract]:
        return [self._snapshot(x) for x in self._skills.values()]

    def promote(self, name: str, *, new_level: int,
                statement: str, evidence_id: str) -> list[str]:
        """Closed public bypass: use EvolutionEngine.apply_upgrade instead."""
        raise PermissionError("SKILL_PROMOTION_VERIFIED_ENGINE_REQUIRED")

    def _verify_external_upgrade(self, candidate, attestation, approved):
        if not approved:
            raise PermissionError("SKILL_PROMOTION_EXPLICIT_APPROVAL_REQUIRED")
        if self._trusted_promotion_key is None:
            raise PermissionError("SKILL_PROMOTION_ATTESTATION_KEY_MISSING")
        if not isinstance(attestation,dict) or set(attestation)!={
                "reviewer_id","review_id","signature"}:
            raise PermissionError("SKILL_PROMOTION_ATTESTATION_REQUIRED")
        try:
            payload=EvolutionEngine.promotion_attestation_payload(
                candidate,reviewer_id=attestation["reviewer_id"],
                review_id=attestation["review_id"])
            signature=attestation["signature"]
            expected=hmac.new(
                self._trusted_promotion_key,
                json.dumps(payload,ensure_ascii=False,sort_keys=True,
                           separators=(",",":"),allow_nan=False).encode("utf-8"),
                "sha256").hexdigest()
        except (KeyError,TypeError,ValueError) as exc:
            raise PermissionError(
                "SKILL_PROMOTION_ATTESTATION_INVALID") from exc
        if not isinstance(signature,str) or not hmac.compare_digest(
                signature,expected):
            raise PermissionError("SKILL_PROMOTION_ATTESTATION_INVALID")
        if candidate.evidence.human_anchor_count<1:
            raise PermissionError("SKILL_PROMOTION_ANCHOR_NOT_VERIFIED")
        decision=PromotionGate().evaluate(
            candidate.evidence,requires_human_anchor=True)
        if not decision.accepted:
            raise ValueError("SKILL_PROMOTION_EVIDENCE_GATE_NOT_PASSED")
        item=self._skills[candidate.skill]
        if candidate.new_level!=item.level+1:
            raise ValueError("SKILL_PROMOTION_LEVEL_INVALID")

    def _promote_verified(self,candidate,*,attestation,approved):
        """Internal gate repeats signer validation at the storage boundary."""
        self._verify_external_upgrade(candidate,attestation,approved)
        target=self._skills[candidate.skill]
        elevated=replace(
            target,level=candidate.new_level,
            statement=candidate.capability_statement,
            revision=target.revision+1,status=SkillStatus.ACTIVE)
        new_deps={}
        for item in self._skills.values():
            if candidate.skill in item.depends_on and item.name!=target.name:
                new_deps[item.name]=replace(
                    item,status=SkillStatus.NEEDS_REVALIDATION,
                    revision=item.revision+1)
        if self.db is not None:
            conn=self.db.conn
            if conn.in_transaction:
                raise RuntimeError("SKILL_PROMOTION_NESTED_TRANSACTION")
            try:
                conn.execute("BEGIN IMMEDIATE")
                expected_rows={target.name:target}
                expected_rows.update({
                    n:self._skills[n] for n in new_deps})
                for old in expected_rows.values():
                    actual=conn.execute(
                        "SELECT level,revision,status,statement FROM "
                        "skill_capabilities WHERE scope=? AND skill_name=?",
                        (self.scope,old.name)).fetchone()
                    if (actual is None or
                        actual["level"]!=old.level or
                        actual["revision"]!=old.revision or
                        actual["status"]!=old.status.value or
                        actual["statement"]!=old.statement):
                        raise RuntimeError(
                            "SKILL_PROMOTION_STALE_REVISION")
                for modified in (elevated,*new_deps.values()):
                    before=expected_rows[modified.name]
                    changed=conn.execute(
                        "UPDATE skill_capabilities SET level=?,status=?,"
                        "revision=?,statement=?,dependencies_json=?,"
                        "updated_at=CURRENT_TIMESTAMP WHERE scope=? "
                        "AND skill_name=? AND revision=? AND level=?",
                        (modified.level,modified.status.value,
                         modified.revision,modified.statement,
                         json.dumps(modified.depends_on,ensure_ascii=False,
                                    sort_keys=True),
                         self.scope,modified.name,before.revision,before.level))
                    if changed.rowcount!=1:
                        raise RuntimeError(
                            "SKILL_PROMOTION_STALE_REVISION")
                conn.execute(
                    "INSERT INTO skill_upgrade_events("
                    "scope,skill_name,old_level,new_level,evidence_id,statement)"
                    " VALUES(?,?,?,?,?,?)",
                    (self.scope,candidate.skill,target.level,
                     elevated.level,candidate.evidence_id,
                     elevated.statement))
                conn.commit()
            except Exception:
                if conn.in_transaction:
                    conn.rollback()
                raise
        # Only now reflect the committed batch in memory. A failed audit
        # insert or stale writer leaves both the DB and registry unchanged.
        self._skills[target.name]=elevated
        self._skills.update(new_deps)
        return sorted(new_deps)

    def revalidate(self,name:str,*,passed:bool)->None:
        """A self-declared PASS cannot reactivate a shadow capability."""
        if passed:
            raise PermissionError("SKILL_REVALIDATION_EXTERNAL_PROOF_REQUIRED")
        item=self._skills[name]
        if item.status==SkillStatus.SHADOW:
            return
        new=replace(item,status=SkillStatus.SHADOW,revision=item.revision+1)
        if self.db is not None:
            conn=self.db.conn
            if conn.in_transaction:
                raise RuntimeError("SKILL_REVALIDATION_NESTED_TRANSACTION")
            try:
                conn.execute("BEGIN IMMEDIATE")
                upd=conn.execute(
                    "UPDATE skill_capabilities SET status=?,revision=?,"
                    "updated_at=CURRENT_TIMESTAMP WHERE scope=? "
                    "AND skill_name=? AND revision=? AND level=?",
                    (new.status.value,new.revision,self.scope,name,
                     item.revision,item.level))
                if upd.rowcount!=1:
                    raise RuntimeError("SKILL_REVALIDATION_STALE_REVISION")
                conn.commit()
            except Exception:
                if conn.in_transaction:
                    conn.rollback()
                raise
        self._skills[name]=new

    def _live_execution_contract(self, name: str):
        """Check SQLite anew at every permission boundary, never trust a cached row.

        Another registry/process may have revoked or changed a contract after
        this instance loaded it. On any disagreement, fail closed without
        silently resynchronizing the permission or minting a new revision.
        """
        cached = self._skills.get(name)
        if cached is None:
            return None, "OPTIONAL_HABIT_NOT_REGISTERED"
        if self.db is None:
            return cached, None
        try:
            row = self.db.conn.execute(
                "SELECT level,status,revision,statement,dependencies_json "
                "FROM skill_capabilities WHERE scope=? AND skill_name=?",
                (self.scope, name)).fetchone()
            if row is None:
                return None, "OPTIONAL_HABIT_REGISTRY_STALE"
            actual = CapabilityContract(
                name, int(row["level"]), row["statement"],
                json.loads(row["dependencies_json"]),
                SkillStatus(row["status"]), int(row["revision"]))
            if actual != cached:
                return None, "OPTIONAL_HABIT_REGISTRY_STALE"
        except Exception:
            return None, "OPTIONAL_HABIT_REGISTRY_STALE"
        return cached, None

    def optional_execution_reason(
        self, permit: OptionalExecutionPermit, *,
        verifier_key: bytes | None, capsule_bytes: bytes,
        host_capabilities: Iterable[str],
    ) -> str | None:
        """None means approved for this dispatch; otherwise a stable denial.

        Only the explicit scheduler opt-in calls this. HMAC controls permission;
        SHA controls artifact bytes, never literary truth; registry/SQLite
        control lifecycle/dependency state. No model or remote resource is used.
        """
        if not isinstance(permit, OptionalExecutionPermit):
            return "OPTIONAL_HABIT_ATTESTATION_INVALID"
        if not isinstance(verifier_key, bytes) or len(verifier_key) < 16:
            return "OPTIONAL_HABIT_AUTHORITY_UNAVAILABLE"
        sha_pattern = r"[0-9a-f]{64}"
        name_pattern = r"[A-Za-z][A-Za-z0-9_-]{0,79}"
        reviewer_pattern = r"[A-Za-z0-9_-]{2,80}"
        try:
            deps = permit.dependency_revisions
            rights = permit.required_host_capabilities
            valid = (
                isinstance(permit.name, str) and
                re.fullmatch(name_pattern, permit.name) is not None and
                type(permit.revision) is int and permit.revision >= 1 and
                isinstance(permit.contract_sha256, str) and
                re.fullmatch(sha_pattern, permit.contract_sha256) is not None and
                isinstance(permit.capsule_sha256, str) and
                re.fullmatch(sha_pattern, permit.capsule_sha256) is not None and
                type(deps) is tuple and
                all(type(pair) is tuple and len(pair) == 2 and
                    isinstance(pair[0], str) and
                    re.fullmatch(name_pattern, pair[0]) is not None and
                    type(pair[1]) is int and pair[1] >= 1 for pair in deps) and
                list(deps) == sorted(set(deps)) and
                type(rights) is tuple and len(rights) >= 1 and
                all(isinstance(cap, str) and
                    re.fullmatch(name_pattern, cap) is not None for cap in rights) and
                len(set(rights)) == len(rights) and
                isinstance(permit.reviewer_id, str) and
                re.fullmatch(reviewer_pattern, permit.reviewer_id) is not None and
                isinstance(permit.review_id, str) and
                re.fullmatch(reviewer_pattern, permit.review_id) is not None and
                isinstance(permit.signature, str) and
                re.fullmatch(sha_pattern, permit.signature) is not None
            )
            if not valid:
                return "OPTIONAL_HABIT_ATTESTATION_INVALID"
            payload = permit.signing_payload()
            expected = hmac.new(
                verifier_key,
                json.dumps(payload, ensure_ascii=False, sort_keys=True,
                           separators=(",", ":"), allow_nan=False).encode("utf-8"),
                "sha256").hexdigest()
            if not hmac.compare_digest(permit.signature, expected):
                return "OPTIONAL_HABIT_ATTESTATION_INVALID"
        except (ValueError, TypeError, KeyError):
            return "OPTIONAL_HABIT_ATTESTATION_INVALID"

        if type(capsule_bytes) is not bytes or (
                sha256(capsule_bytes).hexdigest() != permit.capsule_sha256):
            return "OPTIONAL_HABIT_CAPSULE_SHA_MISMATCH"

        # A signed digest does not license a differently named or SHADOW
        # capsule; even a valid signature can't rewrite its stage.
        try:
            def unique_pairs(pairs):
                result = {}
                for key, value in pairs:
                    if key in result:
                        raise ValueError("duplicate capsule field")
                    result[key] = value
                return result
            capsule = json.loads(capsule_bytes.decode("utf-8", "strict"),
                                 object_pairs_hook=unique_pairs)
            if (type(capsule) is not dict or
                    capsule.get("format") != "wf.habit.capsule.v1" or
                    capsule.get("id") != permit.name):
                return "OPTIONAL_HABIT_CAPSULE_ID_INVALID"
            if (type(capsule.get("revision")) is not int or
                    capsule["revision"] != permit.revision):
                return "OPTIONAL_HABIT_CAPSULE_VERSION_MISMATCH"
            if capsule.get("lifecycle") != "ACTIVE":
                return "OPTIONAL_HABIT_CAPSULE_NOT_ACTIVE"
        except (UnicodeError, ValueError, TypeError):
            return "OPTIONAL_HABIT_CAPSULE_ID_INVALID"

        item, reason = self._live_execution_contract(permit.name)
        if reason is not None:
            return reason
        if item.status != SkillStatus.ACTIVE:
            return "OPTIONAL_HABIT_NOT_ACTIVE"
        if (item.revision != permit.revision or
                self.execution_contract_sha256(item) != permit.contract_sha256):
            return "OPTIONAL_HABIT_CONTRACT_VERSION_MISMATCH"

        expected_deps = dict(permit.dependency_revisions)
        observed_deps = set()

        def validate_dependencies(contract, ancestors):
            for dep_name, min_level in sorted(contract.depends_on.items()):
                if dep_name in ancestors:
                    return "OPTIONAL_HABIT_DEPENDENCY_CYCLE"
                dep, invalid = self._live_execution_contract(dep_name)
                if invalid is not None:
                    return ("OPTIONAL_HABIT_DEPENDENCY_MISSING"
                            if invalid == "OPTIONAL_HABIT_NOT_REGISTERED"
                            else invalid)
                if dep.status != SkillStatus.ACTIVE:
                    return "OPTIONAL_HABIT_DEPENDENCY_NOT_ACTIVE"
                if dep.level < min_level:
                    return "OPTIONAL_HABIT_DEPENDENCY_LEVEL"
                if dep.revision != expected_deps.get(dep_name):
                    return "OPTIONAL_HABIT_DEPENDENCY_REVISION"
                observed_deps.add(dep_name)
                invalid = validate_dependencies(dep, ancestors | {dep_name})
                if invalid is not None:
                    return invalid
            return None

        invalid = validate_dependencies(item, {item.name})
        if invalid is not None:
            return invalid
        if set(expected_deps) != observed_deps:
            return "OPTIONAL_HABIT_DEPENDENCY_REVISION"
        try:
            granted = frozenset(host_capabilities)
        except (TypeError, ValueError):
            return "OPTIONAL_HABIT_HOST_PERMISSION_MISSING"
        if any(right not in granted for right in permit.required_host_capabilities):
            return "OPTIONAL_HABIT_HOST_PERMISSION_MISSING"
        return None

    def lagging(self)->list[CapabilityLag]:
        out=[]
        for skill in self._skills.values():
            for dep,minimum in skill.depends_on.items():
                actual=self._skills.get(dep)
                if actual is None or actual.level<minimum:
                    out.append(CapabilityLag(
                        skill.name,dep,minimum,
                        None if actual is None else actual.level))
        return out


@dataclass(frozen=True)
class FailureEvent:
    skill: str
    code: str
    context: str
    severity: int = 1
    genre: str = ""
    evidence_ref: str = ""


@dataclass(frozen=True)
class FailureCluster:
    skill: str
    code: str
    count: int
    examples: tuple[str, ...]
    genres: tuple[str, ...]


class FailureClusterer:
    def cluster(self, events: Iterable[FailureEvent], *, min_count: int = 3) -> list[FailureCluster]:
        groups: dict[tuple[str, str], list[FailureEvent]] = defaultdict(list)
        for event in events:
            groups[(event.skill, event.code)].append(event)
        out = []
        for (skill, code), items in groups.items():
            if len(items) < min_count:
                continue
            out.append(FailureCluster(
                skill=skill,
                code=code,
                count=len(items),
                examples=tuple(i.context for i in items[:5]),
                genres=tuple(sorted({i.genre for i in items if i.genre})),
            ))
        return sorted(out, key=lambda x: (-x.count, x.skill, x.code))


@dataclass(frozen=True)
class TrainingScenario:
    scenario_id: str
    capability: str
    split: str  # train | heldout | transfer
    relationship: str
    pressure: str
    information_pattern: str
    task: str
    success_evidence: tuple[str, ...]


class CurriculumPlanner:
    """Builds frontier-style literary exercises without writing the answer itself."""

    RELATIONSHIPS = ("mentor_student", "siblings", "partners", "rivals", "strangers", "ruler_subject")
    PRESSURES = ("betrayal", "shame", "grief", "jealousy", "duty", "survival")
    INFO = ("mutual_concealment", "one_sided_secret", "false_belief", "dramatic_irony", "shared_goal_value_conflict")

    def design(self, cluster: FailureCluster, *, count: int = 8) -> list[TrainingScenario]:
        scenarios: list[TrainingScenario] = []
        for i in range(max(3, count)):
            if i < max(1, count - 3):
                split = "train"
            elif i < count - 1:
                split = "heldout"
            else:
                split = "transfer"
            rel = self.RELATIONSHIPS[i % len(self.RELATIONSHIPS)]
            pressure = self.PRESSURES[(i + 1) % len(self.PRESSURES)]
            info = self.INFO[(i + 2) % len(self.INFO)]
            task = (
                f"Exercise {cluster.skill}/{cluster.code}: write or plan a scene where {rel} face {pressure}; "
                f"information pattern={info}. Demonstrate the capability without naming the technique or explaining the answer."
            )
            scenarios.append(TrainingScenario(
                scenario_id=f"{cluster.skill}:{cluster.code}:{i+1}",
                capability=cluster.skill,
                split=split,
                relationship=rel,
                pressure=pressure,
                information_pattern=info,
                task=task,
                success_evidence=(
                    "observable story-state or reader-effect change",
                    "no answer leakage from training examples",
                    "capability transfers across relationship/context",
                ),
            ))
        return scenarios


@dataclass(frozen=True)
class SkillSignature:
    diagnosis: frozenset[str]
    intervention: frozenset[str]
    failure_modes: frozenset[str]


@dataclass(frozen=True)
class SkillBirthDecision:
    create_new_skill: bool
    merge_target: str | None
    reason: str


class SkillBirthGate:
    """Prevents skill-library bloat by merging near-duplicate literary mechanisms."""

    @staticmethod
    def _jaccard(a: frozenset[str], b: frozenset[str]) -> float:
        if not a and not b:
            return 1.0
        return len(a & b) / max(1, len(a | b))

    def decide(self, candidate: SkillSignature, existing: dict[str, SkillSignature], *, merge_threshold: float = 0.65) -> SkillBirthDecision:
        best_name, best = None, -1.0
        for name, sig in existing.items():
            score = (
                self._jaccard(candidate.diagnosis, sig.diagnosis)
                + self._jaccard(candidate.intervention, sig.intervention)
                + self._jaccard(candidate.failure_modes, sig.failure_modes)
            ) / 3.0
            if score > best:
                best_name, best = name, score
        if best_name is not None and best >= merge_threshold:
            return SkillBirthDecision(False, best_name, f"overlap={best:.2f}; upgrade/merge existing skill")
        return SkillBirthDecision(True, None, f"distinct mechanism; max overlap={max(0.0,best):.2f}")


@dataclass(frozen=True)
class PromotionEvidence:
    capability_statement: str
    heldout_success: float
    transfer_success: float
    regression_success: float
    judge_stability: float
    repeated_failure_reduction: float
    runtime_regression: float
    human_anchor_count: int = 0


@dataclass(frozen=True)
class PromotionDecision:
    accepted: bool
    reasons: tuple[str, ...]


class PromotionGate:
    def evaluate(self, evidence: PromotionEvidence, *, requires_human_anchor: bool = False) -> PromotionDecision:
        reasons: list[str] = []
        if not evidence.capability_statement.strip():
            reasons.append("missing qualitative capability statement")
        if evidence.heldout_success < 0.80:
            reasons.append("held-out success below 0.80")
        if evidence.transfer_success < 0.75:
            reasons.append("transfer success below 0.75")
        if evidence.regression_success < 0.95:
            reasons.append("regression preservation below 0.95")
        if evidence.judge_stability < 0.90:
            reasons.append("pairwise judge stability below 0.90")
        if evidence.repeated_failure_reduction < 0.30:
            reasons.append("target failure did not fall enough")
        if evidence.runtime_regression > 0.20:
            reasons.append("runtime regression exceeds 20%")
        if requires_human_anchor and evidence.human_anchor_count < 1:
            reasons.append("literary/taste promotion requires at least one human or real-reader anchor")
        if not reasons:
            reasons.append("passes held-out, transfer, regression, stability, failure-reduction, and runtime gates")
        return PromotionDecision(not any(r for r in reasons if not r.startswith("passes ")), tuple(reasons))


WRITER_MATURITY_LEVELS = {
    1: "Can produce fiction text but has little long-form control.",
    2: "Maintains basic character/world/plot continuity.",
    3: "Plans and completes coherent chapters and story arcs.",
    4: "Characters act from bounded knowledge, goals, fear, beliefs, and relationships rather than plot puppetry.",
    5: "Selects scene-level literary techniques intentionally instead of rendering every scene the same way.",
    6: "Learns functional literary mechanisms from full works and real-reader evidence and transfers them to unfamiliar stories.",
    7: "Controls long-range echoes: arcs, promises, motifs, voice, memory, and cumulative meaning across long fiction.",
    8: "Has story sense: diagnoses the dominant literary problem and knows which otherwise-valid rules do not matter now.",
    9: "Finds its own literary weaknesses, designs targeted exercises, upgrades dependent skills, and proves transfer with external anchors.",
    10: "Sustains high-quality long-form fiction with independent work-specific judgment rather than fixed formulas.",
}

@dataclass(frozen=True)
class UpgradeCandidate:
    skill: str
    new_level: int
    capability_statement: str
    evidence_id: str
    evidence: PromotionEvidence
    requires_human_anchor: bool = False


class EvolutionEngine:
    """Controlled literary self-improvement. It may propose; production promotion requires an explicit gate and approval."""

    def __init__(self, *, registry: SkillRegistry | None = None, db=None,
                 scope: str = "__system__",
                 promotion_verifier_key: bytes | None = None):
        self.registry = registry or SkillRegistry(db=db, scope=scope)
        self.db = db
        self.scope = scope
        if promotion_verifier_key is None:
            key_hex=os.environ.get("WRITERFORGE_PROMOTION_VERIFY_KEY_HEX")
            if key_hex is not None:
                try:
                    promotion_verifier_key=bytes.fromhex(key_hex)
                except ValueError as exc:
                    raise ValueError("PROMOTION_VERIFIER_KEY_INVALID") from exc
        if promotion_verifier_key is not None and (
                not isinstance(promotion_verifier_key,bytes) or
                len(promotion_verifier_key)<16):
            raise ValueError("PROMOTION_VERIFIER_KEY_INVALID")
        self._promotion_verifier_key=promotion_verifier_key
        # Bind the same protected verifier to the registry write boundary.
        self.registry._bind_promotion_verifier(promotion_verifier_key)
        self.failures: list[FailureEvent] = []
        self.clusterer = FailureClusterer()
        self.curriculum = CurriculumPlanner()
        self.promotion_gate = PromotionGate()

    def record_failure(self, event: FailureEvent) -> None:
        if self.db is None:
            self.failures.append(event)
            del self.failures[:-256]
        if self.db is not None:
            self.db.conn.execute(
                """INSERT INTO evolution_failures(scope, skill_name, code, context, severity, genre, evidence_ref)
                   VALUES(?,?,?,?,?,?,?)""",
                (self.scope, event.skill, event.code, event.context, event.severity, event.genre, event.evidence_ref),
            )
            self.db.conn.commit()

    def failure_clusters(self, *, min_count: int = 3) -> list[FailureCluster]:
        if self.db is not None:
            rows = self.db.conn.execute(
                """SELECT skill_name,code,context,severity,genre,evidence_ref
                   FROM evolution_failures WHERE scope=?
                   ORDER BY id DESC LIMIT 2000""", (self.scope,),
            ).fetchall()
            events = [FailureEvent(
                r["skill_name"], r["code"], r["context"],
                int(r["severity"]), r["genre"] or "", r["evidence_ref"] or "",
            ) for r in rows]
        else:
            events = self.failures
        return self.clusterer.cluster(events, min_count=min_count)

    def design_curriculum_for(self, *, skill: str, code: str, count: int = 8, min_count: int = 3) -> list[TrainingScenario]:
        for cluster in self.failure_clusters(min_count=min_count):
            if cluster.skill == skill and cluster.code == code:
                return self.curriculum.design(cluster, count=count)
        return []

    def evaluate_upgrade(self, candidate: UpgradeCandidate) -> PromotionDecision:
        current = self.registry.get(candidate.skill)
        if candidate.new_level != current.level + 1:
            return PromotionDecision(False, ("upgrade must advance exactly one capability level",))
        return self.promotion_gate.evaluate(candidate.evidence, requires_human_anchor=candidate.requires_human_anchor)

    @staticmethod
    def promotion_attestation_payload(candidate: UpgradeCandidate, *,
                                      reviewer_id: str, review_id: str):
        """Credentialed external permit binds exact metrics and level.

        A signature authenticates an authority, NOT literary truth.
        """
        id_regex=re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{1,79}")
        if not all(isinstance(x,str) and id_regex.fullmatch(x)
                   for x in (reviewer_id,review_id,candidate.evidence_id)):
            raise ValueError("PROMOTION_ATTESTATION_REFERENCE_INVALID")
        return {
            "contract":"writerforge.v61-human-controlled-promotion",
            "skill":candidate.skill,
            "new_level":candidate.new_level,
            "capability_statement":candidate.capability_statement,
            "evidence_id":candidate.evidence_id,
            "evidence":asdict(candidate.evidence),
            "reviewer_id":reviewer_id,
            "review_id":review_id,
            "human_anchor_required":True,
            "literary_quality_proven_by_software":False,
        }

    def _require_attestation(self, candidate, attestation):
        if self._promotion_verifier_key is None:
            raise PermissionError("PROMOTION_ATTESTATION_KEY_REQUIRED")
        if (not isinstance(attestation,dict) or
            set(attestation)!={"reviewer_id","review_id","signature"}):
            raise PermissionError("PROMOTION_ATTESTATION_REQUIRED")
        payload=self.promotion_attestation_payload(
            candidate,reviewer_id=attestation["reviewer_id"],
            review_id=attestation["review_id"])
        raw=json.dumps(payload,ensure_ascii=False,sort_keys=True,
                       separators=(",",":"),allow_nan=False).encode("utf-8")
        expected=hmac.new(
            self._promotion_verifier_key,raw,"sha256").hexdigest()
        received=attestation["signature"]
        if not isinstance(received,str) or not hmac.compare_digest(
                received,expected):
            raise PermissionError("PROMOTION_ATTESTATION_INVALID")
        if candidate.evidence.human_anchor_count<1:
            raise PermissionError("PROMOTION_ATTESTATION_HUMAN_ANCHOR_MISSING")

    def apply_upgrade(self, candidate: UpgradeCandidate, *,
                      policy: str = "gated_auto", approved: bool = False,
                      attestation: dict | None = None) -> list[str]:
        """No self-reviewed scores can autonomously promote a formal skill.

        Shadow proposals are non-mutating. Active promotion needs an
        out-of-band signed permit and explicit manual authorization.
        """
        decision=self.evaluate_upgrade(candidate)
        if not decision.accepted:
            raise ValueError(
                "promotion gate failed: " + "; ".join(decision.reasons))
        if policy=="shadow_only":
            return []
        if policy not in {"gated_auto","manual"}:
            raise ValueError("policy must be gated_auto, manual, or shadow_only")
        self._require_attestation(candidate,attestation)
        if policy!="manual":
            raise PermissionError("PROMOTION_MANUAL_REQUIRED")
        if not approved:
            raise PermissionError("PROMOTION_EXPLICIT_APPROVAL_REQUIRED")
        return self.registry._promote_verified(
            candidate,attestation=attestation,approved=approved)


@dataclass(frozen=True)
class ObservedScene:
    """What an accepted scene actually did, independent of what the plan claimed it would do."""
    scene_id: str
    planned_function: str = ""
    observed_function: str = ""
    character_choice: str = ""
    state_delta_keys: tuple[str, ...] = ()
    reader_effects: tuple[str, ...] = ()


@dataclass(frozen=True)
class StoryDrift:
    scene_id: str
    planned_function: str
    observed_function: str


@dataclass(frozen=True)
class ObservedStoryReport:
    drifts: tuple[StoryDrift, ...]
    functionless_scene_ids: tuple[str, ...]
    persistent_unplanned_functions: tuple[str, ...]
    observed_spine: tuple[str, ...]
    rule: str = "Treat accepted prose as evidence of the story that exists; compare it with the plan without automatically forcing either one to win."


class ObservedStoryAuditor:
    """A reverse-outline pass for WriterForge's own accepted fiction."""

    def analyze(self, scenes: Iterable[ObservedScene], *, emergence_threshold: int = 2) -> ObservedStoryReport:
        items = list(scenes)
        drifts: list[StoryDrift] = []
        functionless: list[str] = []
        unplanned_counts: Counter[str] = Counter()
        spine: list[str] = []

        for scene in items:
            observed = scene.observed_function.strip()
            planned = scene.planned_function.strip()
            if observed:
                spine.append(observed)
            if planned and observed and planned != observed:
                drifts.append(StoryDrift(scene.scene_id, planned, observed))
                unplanned_counts[observed] += 1
            elif not planned and observed:
                unplanned_counts[observed] += 1

            if not observed and not scene.character_choice.strip() and not scene.state_delta_keys and not scene.reader_effects:
                functionless.append(scene.scene_id)

        persistent = tuple(sorted(k for k, v in unplanned_counts.items() if v >= max(2, emergence_threshold)))
        return ObservedStoryReport(tuple(drifts), tuple(functionless), persistent, tuple(spine))

# 0.AZ: ONE offline continuation/stop decision for a portable cognitive habit.
# This reuses the Evolution owner. It does not add a second SkillRegistry,
# modify a manuscript, store model memories, or grant automatic promotions.
# Live DeepSeek/GLM-5.3 source: Actions 40354436598. The fourth attempted
# request returned Discovery HTTP 429; the GLM habit response does not exist.
@dataclass(frozen=True)
class HabitTrialEvidence:
    habit_id: str
    current_status: SkillStatus
    verified_source_receipts: bool
    expected_pairs: int
    completed_pairs: int
    attempted_model_calls: int
    completed_model_responses: int
    provider_failure_code: str | None
    independent_literary_review: bool
    confirmed_literary_benefit: bool
    independently_confirmed_contamination: bool
    repeated_no_benefit_evidence: bool


@dataclass(frozen=True)
class HabitTrialDisposition:
    disposition: str
    registry_status: SkillStatus
    literary_conclusion: str
    reason: str
    habit_falsified: bool = False
    habit_promoted: bool = False
    new_provider_calls_authorized: int = 0
    requires_external_restart_approval: bool = True


def assess_habit_trial_continuation(evidence: HabitTrialEvidence
                                   ) -> HabitTrialDisposition:
    """Pure OFFLINE recommendation, no registry/Canon/model mutation.

    Unmatched A/B arms after an API outage cannot establish bad literature,
    poor cross-host portability, or skill contamination. Keeping the owner
    in SHADOW and pausing is a valid evolutionary choice. External human
    approval and actual new evidence are required to resume or promote.
    The return value alone cannot change SQLite SkillStatus.
    """
    if (type(evidence) is not HabitTrialEvidence or
        type(evidence.habit_id) is not str or
        re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*",
                     evidence.habit_id) is None or
        type(evidence.current_status) is not SkillStatus or
        any(type(n) is not int or n < 0 or n > 256 for n in
            (evidence.expected_pairs,evidence.completed_pairs,
             evidence.attempted_model_calls,evidence.completed_model_responses)) or
        evidence.expected_pairs < 1 or
        evidence.completed_pairs > evidence.expected_pairs or
        evidence.completed_model_responses > evidence.attempted_model_calls or
        evidence.completed_pairs * 2 > evidence.completed_model_responses or
        any(type(b) is not bool for b in (
            evidence.verified_source_receipts,
            evidence.independent_literary_review,
            evidence.confirmed_literary_benefit,
            evidence.independently_confirmed_contamination,
            evidence.repeated_no_benefit_evidence)) or
        (evidence.provider_failure_code is not None and
         (type(evidence.provider_failure_code) is not str or
          re.fullmatch(r"[A-Z0-9_:\.-]{5,165}",
                       evidence.provider_failure_code) is None))):
        raise ValueError("WF_HABIT_TRIAL_EVIDENCE_INVALID")

    def decision(disposition,conclusion,reason):
        return HabitTrialDisposition(
            disposition=disposition,
            registry_status=evidence.current_status,
            literary_conclusion=conclusion,
            reason=reason)

    if not evidence.verified_source_receipts:
        return decision(
            "REFUSE_UNVERIFIED_EVIDENCE","NOT_TESTED_INCOMPLETE",
            "Original provider wire or source-receipt identity unavailable; "
            "do not infer a Skill improvement or call the model.")
    if evidence.current_status is SkillStatus.RETIRED:
        return decision(
            "STOP_RETIRED","NOT_ESTABLISHED",
            "Retired capability is not resurrected by a newer model or "
            "a historical scoring claim.")
    if evidence.independently_confirmed_contamination:
        return decision(
            "REVIEW_QUARANTINE_LINEAGE","NOT_ESTABLISHED",
            "Independent contamination finding: do not auto-retire, but "
            "require manual lineage review before any promotion.")
    if evidence.provider_failure_code is not None:
        # A provider's backpressure/overload is not a falsifier for the
        # author's cognitive decision. An attempted request may have been
        # billed even if its text was not returned; never silently retry.
        if (evidence.provider_failure_code.endswith("_HTTP_429") or
            evidence.provider_failure_code.endswith("_HTTP_503") or
            "RATE_LIMIT" in evidence.provider_failure_code):
            return decision(
                "DORMANT_HOST_RESOURCE","NOT_TESTED_INCOMPLETE",
                "Host rate-limit/capacity prevented matched counterfactual; "
                "preserve original wires and resume only by a new authorized "
                "experiment, never automatic retry.")
        return decision(
            "DORMANT_PROVIDER_FAILURE","NOT_TESTED_INCOMPLETE",
            "Unresolved host delivery/parse error does not prove the "
            "habit helped or failed.")
    if evidence.completed_pairs != evidence.expected_pairs:
        return decision(
            "DORMANT_UNMATCHED_ARMS","NOT_TESTED_INCOMPLETE",
            "At least one planned matched control/habit pair has no actual "
            "complete response; no cross-host quality verdict.")
    if not evidence.independent_literary_review:
        return decision(
            "SHADOW_NEEDS_READER_EVIDENCE","NOT_ESTABLISHED",
            "Both arms completed but literary comparison has no independent "
            "reader evidence. Model preference is not promotion authority.")
    if evidence.repeated_no_benefit_evidence:
        return decision(
            "DORMANT_NO_PROVEN_VALUE","NOT_ESTABLISHED",
            "Repeated independent trials found inadequate gain relative to "
            "cost; keep source evidence and stop speculative iteration.")
    if evidence.confirmed_literary_benefit:
        return decision(
            "REVIEW_MANUAL_PROMOTION_ONLY","REVIEWABLE_NOT_PROVEN_BY_ENGINE",
            "Independent positive evidence warrants a separate existing "
            "Evolution promotion and regression gate, not self-approval.")
    return decision(
        "SHADOW_UNRESOLVED_LITERARY_COMPARISON","NOT_ESTABLISHED",
        "Reader evidence was mixed/insufficient; keep both hypotheses in "
        "SHADOW rather than inventing a winner.")


# WF 0.BA/P1 -- OFFLINE portable-habit candidate ecology.
#
# This pool is intentionally NOT a second SkillRegistry, runnable plugin, model
# grader or sovereign upgrade mechanism. It stages immutable proposal BYTES,
# binds separate reviewer evidence and traces compromised descendants. The
# stored 0.AY v1 root is never rewritten. All scores are observations from a
# specified frozen suite and NEVER certify literary improvement or promotion.


@dataclass(frozen=True)
class HabitCandidateProposal:
    proposal_id: str
    proposer_skill: str
    target_skill: str
    parent_sha256: str
    candidate_sha256: str
    evidence_sha256: str
    changed_fields: tuple[str, ...]
    status: str = "SHADOW"


@dataclass(frozen=True)
class HabitCompetitionEvidence:
    candidate_sha256: str
    evaluator_id: str
    holdout_suite_sha256: str
    matched_pairs: int
    observed_success: int
    regression_cases: int
    cost_units: int
    independent_reader_count: int
    signature: str

    def signing_payload(self) -> dict:
        return {
            "kind": "wf.portable-habit-offline-competition.v1",
            "candidate_sha256": self.candidate_sha256,
            "evaluator_id": self.evaluator_id,
            "holdout_suite_sha256": self.holdout_suite_sha256,
            "matched_pairs": self.matched_pairs,
            "observed_success": self.observed_success,
            "regression_cases": self.regression_cases,
            "cost_units": self.cost_units,
            "independent_reader_count": self.independent_reader_count,
            "literary_success_unproven": True,
            "auto_promotion": False,
        }


@dataclass(frozen=True)
class HabitQuarantineAttestation:
    ancestor_sha256: str
    evidence_sha256: str
    reason_code: str
    reviewer_id: str
    signature: str

    def signing_payload(self) -> dict:
        return {
            "kind": "wf.portable-habit-lineage-quarantine.v1",
            "ancestor_sha256": self.ancestor_sha256,
            "evidence_sha256": self.evidence_sha256,
            "reason_code": self.reason_code,
            "reviewer_id": self.reviewer_id,
        }


class PortableHabitCandidatePool:
    """Bounded, in-memory, OFFLINE proposal graph with separate signed reviews.

    A proposal from skill A to skill B never writes skill B, an evaluator, the
    registry, author prose or the producer's heldout scoring procedure. The
    holder of the independent review key is outside the proposer and model
    contract. This is a functional governance prototype, not a sandbox or a
    durable cross-host audit/approval mechanism.
    """

    MAX_ROOTS = 16
    MAX_CANDIDATES = 128
    MAX_CAPSULE_BYTES = 12_000
    _HEX = re.compile(r"[0-9a-f]{64}\Z")
    _IDENT = re.compile(r"[a-z0-9]+(?:[-_][a-z0-9]+)*\Z")
    _PROTECTED = frozenset({
        "id", "format", "authority", "transfer", "provenance", "stopping",
    })
    _MUTABLE = frozenset({"purpose", "trigger", "procedure", "falsifiers"})
    _ALLOWED_KEYS = _PROTECTED | _MUTABLE | {"revision", "lifecycle"}

    @staticmethod
    def _canonical(obj) -> bytes:
        return json.dumps(obj, ensure_ascii=False, sort_keys=True,
                          separators=(",", ":"), allow_nan=False).encode("utf-8")

    @classmethod
    def _hash_valid(cls, value) -> bool:
        return type(value) is str and cls._HEX.fullmatch(value) is not None

    @classmethod
    def _identity_valid(cls, value) -> bool:
        return (type(value) is str and 2 <= len(value) <= 80 and
                cls._IDENT.fullmatch(value) is not None)

    @classmethod
    def _decode(cls, raw: bytes) -> dict:
        if type(raw) is not bytes or not 2 <= len(raw) <= cls.MAX_CAPSULE_BYTES:
            raise ValueError("HABIT_CANDIDATE_BYTES_INVALID")
        def reject_duplicates(pairs):
            obj = {}
            for name, item in pairs:
                if name in obj:
                    raise ValueError("HABIT_CANDIDATE_DUPLICATE_JSON_FIELD")
                obj[name] = item
            return obj
        try:
            obj = json.loads(raw.decode("utf-8", "strict"),
                             object_pairs_hook=reject_duplicates)
        except (ValueError, UnicodeError) as e:
            raise ValueError("HABIT_CANDIDATE_JSON_INVALID") from e
        if (type(obj) is not dict or set(obj) != cls._ALLOWED_KEYS or
                obj["format"] != "wf.habit.capsule.v1" or
                not cls._identity_valid(obj["id"]) or
                type(obj["revision"]) is not int or obj["revision"] < 1 or
                obj["lifecycle"] not in ("SHADOW", "ACTIVE") or
                type(obj["procedure"]) is not list or
                type(obj["falsifiers"]) is not list or
                len(obj["procedure"]) != 4 or len(obj["falsifiers"]) != 4 or
                any(type(x) is not str or not 35 <= len(x) <= 450
                    for x in obj["procedure"] + obj["falsifiers"]) or
                type(obj["purpose"]) is not str or
                type(obj["trigger"]) is not str):
            raise ValueError("HABIT_CANDIDATE_CAPSULE_SCHEMA_INVALID")
        return obj

    def __init__(
        self, *, pinned_roots: dict[str, bytes],
        reviewer_verifier_key: bytes,
        frozen_heldout_sha256: str,
    ):
        if (not isinstance(reviewer_verifier_key, bytes) or
                len(reviewer_verifier_key) < 16):
            raise ValueError("HABIT_ECOLOGY_EXTERNAL_VERIFIER_REQUIRED")
        if not self._hash_valid(frozen_heldout_sha256):
            raise ValueError("HABIT_ECOLOGY_HELDOUT_PIN_REQUIRED")
        if (type(pinned_roots) is not dict or
                not 1 <= len(pinned_roots) <= self.MAX_ROOTS):
            raise ValueError("HABIT_ECOLOGY_BOUNDED_ROOT_REQUIRED")
        self._roots: dict[str, bytes] = {}
        self._root_capsules: dict[str, dict] = {}
        for digest, raw in pinned_roots.items():
            if (not self._hash_valid(digest) or type(raw) is not bytes or
                    sha256(raw).hexdigest() != digest):
                raise ValueError("HABIT_ECOLOGY_ROOT_BYTES_SHA_MISMATCH")
            capsule = self._decode(raw)
            if capsule["lifecycle"] != "SHADOW":
                raise ValueError("HABIT_ECOLOGY_ROOT_MUST_NOT_BE_ACTIVE")
            self._roots[digest] = raw
            self._root_capsules[digest] = capsule
        self._reviewer_key = reviewer_verifier_key
        self._heldout_sha = frozen_heldout_sha256
        self._proposals: dict[str, HabitCandidateProposal] = {}
        self._candidate_bytes: dict[str, bytes] = {}
        self._candidate_capsules: dict[str, dict] = {}
        self._proposal_ids: set[str] = set()
        self._children: dict[str, set[str]] = defaultdict(set)
        self._evidence: dict[str, HabitCompetitionEvidence] = {}
        self._quarantined: set[str] = set()

    @property
    def has_execution_authority(self) -> bool:
        """This staging pool must never grant ACTIVE registry permissions."""
        return False

    def _known(self, digest: str) -> bool:
        return digest in self._roots or digest in self._candidate_bytes

    def status(self, digest: str) -> str:
        if not self._known(digest):
            raise KeyError("HABIT_ECOLOGY_UNKNOWN_SHA")
        return ("REVIEW_QUARANTINE_LINEAGE" if digest in self._quarantined
                else "SHADOW")

    def propose(
        self, *, proposer_skill: str, target_skill: str,
        parent_sha256: str, candidate_bytes: bytes,
        evidence_sha256: str, proposal_id: str,
    ) -> HabitCandidateProposal:
        if (not all(self._identity_valid(x)
                    for x in (proposer_skill, target_skill, proposal_id)) or
                proposer_skill == target_skill or
                not self._hash_valid(evidence_sha256)):
            raise ValueError("HABIT_ECOLOGY_PROPOSAL_IDENTITY_INVALID")
        if (not self._known(parent_sha256) or
                parent_sha256 not in self._roots and
                parent_sha256 not in self._candidate_bytes):
            raise ValueError("HABIT_ECOLOGY_UNTRUSTED_PARENT")
        if parent_sha256 in self._quarantined:
            raise PermissionError("HABIT_ECOLOGY_QUARANTINED_PARENT")
        if len(self._proposals) >= self.MAX_CANDIDATES:
            raise OverflowError("HABIT_ECOLOGY_MAX_CANDIDATES")
        if proposal_id in self._proposal_ids:
            raise ValueError("HABIT_ECOLOGY_PROPOSAL_ID_ALREADY_EXISTS")

        parent_doc = (self._root_capsules[parent_sha256]
                      if parent_sha256 in self._roots
                      else self._candidate_capsules[parent_sha256])
        candidate = self._decode(candidate_bytes)
        if candidate["id"] != parent_doc["id"] or target_skill != candidate["id"]:
            raise ValueError("HABIT_ECOLOGY_TARGET_MISMATCH")
        if (candidate["revision"] != parent_doc["revision"] + 1 or
                candidate["lifecycle"] != "SHADOW"):
            raise ValueError("HABIT_ECOLOGY_CANDIDATE_REVISION_OR_STAGE_INVALID")
        if any(candidate[key] != parent_doc[key] for key in self._PROTECTED):
            raise ValueError("HABIT_ECOLOGY_PROTECTED_CONTRACT_MUTATION")
        changed = tuple(sorted(
            name for name in self._MUTABLE if candidate[name] != parent_doc[name]))
        if not changed:
            raise ValueError("HABIT_ECOLOGY_NO_BEHAVIORAL_CHANGE")
        digest = sha256(candidate_bytes).hexdigest()
        if digest == parent_sha256 or digest in self._roots:
            raise ValueError("HABIT_ECOLOGY_IDENTITY_REUSE")
        if digest in self._candidate_bytes:
            raise ValueError("HABIT_ECOLOGY_DUPLICATE_CANDIDATE")

        proposal = HabitCandidateProposal(
            proposal_id=proposal_id, proposer_skill=proposer_skill,
            target_skill=target_skill, parent_sha256=parent_sha256,
            candidate_sha256=digest, evidence_sha256=evidence_sha256,
            changed_fields=changed)
        self._candidate_bytes[digest] = candidate_bytes
        self._candidate_capsules[digest] = candidate
        self._proposals[digest] = proposal
        self._proposal_ids.add(proposal_id)
        self._children[parent_sha256].add(digest)
        return proposal

    def export_candidate(self, candidate_sha256: str) -> dict:
        if candidate_sha256 not in self._candidate_bytes:
            raise KeyError("HABIT_ECOLOGY_NOT_A_CANDIDATE")
        p = self._proposals[candidate_sha256]
        return {
            "format": "wf.portable-habit-untrusted-proposal.v1",
            "proposal_id": p.proposal_id,
            "target_skill": p.target_skill,
            "proposer_skill": p.proposer_skill,
            "capsule_utf8": self._candidate_bytes[candidate_sha256].decode("utf-8"),
            "capsule_sha256": candidate_sha256,
            "parent_sha256": p.parent_sha256,
            "evidence_sha256": p.evidence_sha256,
            "changed_fields": list(p.changed_fields),
            "lifecycle": self.status(candidate_sha256),
            "cross_host_quality_proven": False,
            "auto_execute": False,
            "auto_promote": False,
        }

    def _verify_reviewer_signature(self, doc, signature: str) -> None:
        try:
            expected = hmac.new(
                self._reviewer_key, self._canonical(doc.signing_payload()),
                "sha256").hexdigest()
        except (TypeError, ValueError, AttributeError) as exc:
            raise PermissionError("HABIT_ECOLOGY_REVIEW_ATTESTATION_INVALID") from exc
        if not (self._hash_valid(signature) and
                hmac.compare_digest(signature, expected)):
            raise PermissionError("HABIT_ECOLOGY_REVIEW_ATTESTATION_INVALID")

    def record_competition(self, result: HabitCompetitionEvidence) -> None:
        if not isinstance(result, HabitCompetitionEvidence):
            raise TypeError("HABIT_ECOLOGY_COMPETITION_SCHEMA_INVALID")
        self._verify_reviewer_signature(result, result.signature)
        p = self._proposals.get(result.candidate_sha256)
        if p is None:
            raise ValueError("HABIT_ECOLOGY_COMPETITION_UNKNOWN_CANDIDATE")
        if p.candidate_sha256 in self._quarantined:
            raise PermissionError("HABIT_ECOLOGY_COMPETITION_QUARANTINED")
        if (not self._identity_valid(result.evaluator_id) or
                result.evaluator_id == p.proposer_skill):
            raise PermissionError("HABIT_ECOLOGY_PROPOSER_CANNOT_EVALUATE")
        if result.holdout_suite_sha256 != self._heldout_sha:
            raise ValueError("HABIT_ECOLOGY_HELDOUT_DRIFT")
        if (type(result.matched_pairs) is not int or
                not 1 <= result.matched_pairs <= 64 or
                any(type(n) is not int or n < 0 for n in
                    (result.observed_success, result.regression_cases,
                     result.cost_units, result.independent_reader_count)) or
                result.observed_success > result.matched_pairs or
                result.regression_cases > result.matched_pairs or
                result.independent_reader_count > 64):
            raise ValueError("HABIT_ECOLOGY_COMPETITION_COUNTERS_INVALID")
        if result.candidate_sha256 in self._evidence:
            raise ValueError("HABIT_ECOLOGY_DUPLICATE_FROZEN_COMPARISON")
        self._evidence[result.candidate_sha256] = result

    def compare_candidates(self, target_skill: str) -> dict:
        scored = [(p, self._evidence[sha]) for sha,p in self._proposals.items()
                  if p.target_skill == target_skill and
                  sha in self._evidence and sha not in self._quarantined]
        baseline = {
            "target_skill": target_skill,
            "status": "INSUFFICIENT_COMPARABLE_CANDIDATES",
            "provisional_leader_sha256": None,
            "dormant_review_candidates": [],
            "frozen_heldout_sha256": self._heldout_sha,
            "automatic_promotion": False,
            "independent_literary_improvement_proven": False,
            "new_provider_calls": 0,
        }
        if len(scored) < 2:
            return baseline
        if len({result.matched_pairs for _,result in scored}) != 1:
            return dict(baseline, status="INCOMPARABLE_MATCHED_PAIR_COUNTS")
        scored.sort(key=lambda pe: (
            -pe[1].observed_success, pe[1].regression_cases,
            pe[1].cost_units, pe[0].candidate_sha256))
        winner, measured = scored[0]
        ties = [p for p,r in scored if (
            r.observed_success == measured.observed_success and
            r.regression_cases == measured.regression_cases and
            r.cost_units == measured.cost_units)]
        if len(ties) > 1:
            return dict(baseline, status="NO_CLEAR_PROVISIONAL_LEADER")
        return dict(
            baseline,
            status="PROVISIONAL_SYNTHETIC_EVIDENCE_ONLY",
            provisional_leader_sha256=winner.candidate_sha256,
            dormant_review_candidates=[
                p.candidate_sha256 for p,e in scored[1:]
                if e.regression_cases > measured.regression_cases or
                e.observed_success < measured.observed_success],
        )

    def quarantine_lineage(
        self, attestation: HabitQuarantineAttestation,
    ) -> tuple[str, ...]:
        if not isinstance(attestation, HabitQuarantineAttestation):
            raise TypeError("HABIT_ECOLOGY_QUARANTINE_SCHEMA_INVALID")
        self._verify_reviewer_signature(attestation, attestation.signature)
        if (not self._hash_valid(attestation.evidence_sha256) or
                not self._identity_valid(attestation.reviewer_id) or
                attestation.reason_code != "VERIFIED_CANDIDATE_CONTAMINATION"):
            raise ValueError("HABIT_ECOLOGY_QUARANTINE_REASON_INVALID")
        if not self._known(attestation.ancestor_sha256):
            raise ValueError("HABIT_ECOLOGY_UNKNOWN_QUARANTINE_ANCESTOR")
        # Traverse only digest-linked descendants, never unrelated siblings.
        stack = [attestation.ancestor_sha256]
        affected = set()
        while stack:
            cur = stack.pop()
            if cur not in affected:
                affected.add(cur)
                stack.extend(self._children.get(cur, ()))
        self._quarantined.update(affected)
        # Quarantining the root here does not mutate its immutable bytes, the
        # SkillRegistry or any actual runtime permission.
        return tuple(sorted(affected))
