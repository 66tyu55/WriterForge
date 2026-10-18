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


class SkillRegistry:
    """Read model and durable storage for skills; formal upgrades are gated.

    Normal callers may register an initial skill once and may LOWER trust to
    SHADOW, but cannot promote levels or reactivate via plain booleans. The
    only active-upgrade path is an independently verified, manually approved
    EvolutionEngine permit, checked AGAIN before atomic SQLite update.

    Raw SQLite write access and arbitrary Python monkeypatching are outside
    this API security boundary; this is not a privilege sandbox.
    """
    def __init__(self, db=None, scope: str="__system__",
                 bootstrap_verifier_key:bytes|None=None,
                 promotion_verifier_key:bytes|None=None):
        self._skills: dict[str, CapabilityContract] = {}
        self.db=db
        self.scope=scope
        if promotion_verifier_key is None:
            raw_promotion=os.environ.get("WRITERFORGE_PROMOTION_VERIFY_KEY_HEX")
            if raw_promotion is not None:
                try:
                    promotion_verifier_key=bytes.fromhex(raw_promotion)
                except ValueError as exc:
                    raise ValueError("SKILL_PROMOTION_VERIFIER_INVALID") from exc
        if promotion_verifier_key is not None and (
            not isinstance(promotion_verifier_key,bytes)
            or len(promotion_verifier_key)<16):
            raise ValueError("SKILL_PROMOTION_VERIFIER_INVALID")
        self._trusted_promotion_key=promotion_verifier_key
        self._verified_promotions=set()
        if bootstrap_verifier_key is None:
            raw=os.environ.get("WRITERFORGE_SKILL_BOOTSTRAP_VERIFY_KEY_HEX")
            if raw is not None:
                try:
                    bootstrap_verifier_key=bytes.fromhex(raw)
                except ValueError as exc:
                    raise ValueError("SKILL_BOOTSTRAP_KEY_INVALID") from exc
        if bootstrap_verifier_key is not None and (
            not isinstance(bootstrap_verifier_key,bytes)
            or len(bootstrap_verifier_key)<16):
            raise ValueError("SKILL_BOOTSTRAP_KEY_INVALID")
        self._bootstrap_key=bootstrap_verifier_key
        self._verified_initial_grades=set()
        self._legacy_unverified=set()
        if self.db is not None:
            for row in self.db.conn.execute(
                "SELECT skill_name,level,statement,dependencies_json,status,"
                "revision FROM skill_capabilities WHERE scope=? "
                "ORDER BY skill_name LIMIT 256",(self.scope,)):
                c=CapabilityContract(
                    row["skill_name"],int(row["level"]),row["statement"],
                    json.loads(row["dependencies_json"]),
                    SkillStatus(row["status"]),int(row["revision"]))
                if c.level>1:
                    promoted=self.db.conn.execute(
                        "SELECT receipt_sha FROM skill_promotion_receipts "
                        "WHERE scope=? AND skill_name=? AND new_level=?",
                        (self.scope,c.name,c.level)).fetchone()
                    receipt=self.db.conn.execute(
                        "SELECT * FROM skill_bootstrap_receipts "
                        "WHERE scope=? AND skill_name=?",
                        (self.scope,c.name)).fetchone()
                    if promoted is not None and self._trusted_promotion_key is not None:
                        self._verify_promotion_chain(c)
                        self._verified_promotions.add(c.name)
                    elif (promoted is None and receipt is not None
                          and self._bootstrap_key is not None):
                        self._validate_bootstrap(c,{
                            "source_sha256":receipt["source_sha"],
                            "reviewer_id":receipt["reviewer_id"],
                            "review_id":receipt["review_id"],
                            "signature":receipt["signature"]},
                            receipt=receipt)
                        self._verified_initial_grades.add(c.name)
                    else:
                        # Old grades without a verifiable chain remain
                        # SHADOW in the read model; do not rewrite SQLite.
                        self._legacy_unverified.add(c.name)
                        c=replace(c,status=SkillStatus.SHADOW)
                self._skills[c.name]=c

    @staticmethod
    def _snapshot(item: CapabilityContract) -> CapabilityContract:
        return replace(item,depends_on=dict(item.depends_on))

    def bootstrap_attestation_payload(self,contract:CapabilityContract,*,
                                       source_sha256:str,reviewer_id:str,
                                       review_id:str):
        """Exact contract + source SHA + scope; provenance, not literary truth."""
        ident=re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{1,79}")
        if (not isinstance(contract,CapabilityContract)
            or not isinstance(source_sha256,str)
            or not re.fullmatch(r"[0-9a-f]{64}",source_sha256)
            or not all(isinstance(v,str) and ident.fullmatch(v)
                       for v in (reviewer_id,review_id))):
            raise ValueError("SKILL_BOOTSTRAP_FIELDS_INVALID")
        return {
            "protocol":"writerforge.v64-controlled-skill-bootstrap",
            "scope":self.scope,
            "capability":asdict(self._snapshot(contract)),
            "source_receipt_sha256":source_sha256,
            "reviewer_id":reviewer_id,"review_id":review_id,
            "permission":"BOOTSTRAP_HIGH_GRADE",
            "literary_ability_verified_by_software":False,
        }

    def _validate_bootstrap(self,contract,attestation,*,receipt=None):
        if self._bootstrap_key is None:
            raise PermissionError("SKILL_BOOTSTRAP_KEY_REQUIRED")
        fields={"source_sha256","reviewer_id","review_id","signature"}
        if not isinstance(attestation,dict) or set(attestation)!=fields:
            raise PermissionError("SKILL_BOOTSTRAP_ATTESTATION_REQUIRED")
        try:
            payload=self.bootstrap_attestation_payload(
                contract,source_sha256=attestation["source_sha256"],
                reviewer_id=attestation["reviewer_id"],
                review_id=attestation["review_id"])
            body=json.dumps(payload,ensure_ascii=False,sort_keys=True,
                            separators=(",",":"),allow_nan=False).encode("utf-8")
            expected=hmac.new(self._bootstrap_key,body,"sha256").hexdigest()
            supplied=attestation["signature"]
        except (TypeError,ValueError,KeyError) as exc:
            raise PermissionError("SKILL_BOOTSTRAP_ATTESTATION_INVALID") from exc
        if (not isinstance(supplied,str)
            or not hmac.compare_digest(expected,supplied)):
            raise PermissionError("SKILL_BOOTSTRAP_ATTESTATION_INVALID")
        contract_sha=sha256(json.dumps(
            payload["capability"],ensure_ascii=False,sort_keys=True,
            separators=(",",":"),allow_nan=False).encode("utf-8")).hexdigest()
        receipt_sha=sha256(json.dumps({
            "payload":payload,"signature":supplied},
            ensure_ascii=False,sort_keys=True,
            separators=(",",":"),allow_nan=False).encode("utf-8")).hexdigest()
        if receipt is not None and (
                receipt["contract_sha"]!=contract_sha or
                receipt["receipt_sha"]!=receipt_sha or
                (receipt["payload_json"] and
                 receipt["payload_json"]!=body.decode("utf-8"))):
            raise PermissionError("SKILL_BOOTSTRAP_RECEIPT_TAMPERED")
        return contract_sha,receipt_sha

    @staticmethod
    def _canonical_receipt(obj):
        return json.dumps(obj,ensure_ascii=False,sort_keys=True,
                          separators=(",",":"),allow_nan=False)

    @staticmethod
    def _contract_from_record(raw):
        if not isinstance(raw,dict):
            raise PermissionError("SKILL_PROMOTION_RECEIPT_TAMPERED")
        try:
            return CapabilityContract(
                name=raw["name"],level=raw["level"],
                statement=raw["statement"],depends_on=raw["depends_on"],
                status=SkillStatus(raw["status"]),revision=raw["revision"])
        except (KeyError,TypeError,ValueError) as exc:
            raise PermissionError(
                "SKILL_PROMOTION_RECEIPT_TAMPERED") from exc

    def _verify_promotion_chain(self, latest):
        """Replay at most nine signed steps; do not invent legacy history.

        Each promotion seals the WHOLE before/after capability and the
        reviewer's original approved metrics, with a prior-receipt pointer.
        A signed L1 -> L2 receipt or signed initial L4 -> L5 can restart
        without being mislabeled as an unverifiable legacy high grade.
        """
        if self._trusted_promotion_key is None:
            raise PermissionError("SKILL_PROMOTION_VERIFIER_KEY_REQUIRED")
        current=latest
        visited=set()
        for _ in range(10):
            row=self.db.conn.execute(
                "SELECT * FROM skill_promotion_receipts "
                "WHERE scope=? AND skill_name=? AND new_level=?",
                (self.scope,current.name,current.level)).fetchone()
            if row is None or row["receipt_sha"] in visited:
                raise PermissionError("SKILL_PROMOTION_LINEAGE_MISSING")
            visited.add(row["receipt_sha"])
            try:
                proof=json.loads(row["payload_json"])
                raw=self._canonical_receipt(proof).encode("utf-8")
                expected=hmac.new(
                    self._trusted_promotion_key,raw,"sha256").hexdigest()
                signature=row["signature"]
                digest=sha256(self._canonical_receipt({
                    "payload":proof,
                    "signature":signature}).encode("utf-8")).hexdigest()
                before=self._contract_from_record(proof["before"])
                after=self._contract_from_record(proof["after"])
                reviewer=proof["reviewer_id"]
                review_id=proof["review_id"]
                attested=proof["attested_request"]
                original_signature=proof["original_signature"]
                attested_signature=hmac.new(
                    self._trusted_promotion_key,
                    self._canonical_receipt(attested).encode("utf-8"),
                    "sha256").hexdigest()
            except (KeyError,TypeError,ValueError) as exc:
                raise PermissionError(
                    "SKILL_PROMOTION_RECEIPT_TAMPERED") from exc
            if (not isinstance(signature,str)
                or not hmac.compare_digest(expected,signature)
                or digest!=row["receipt_sha"]
                or not isinstance(original_signature,str)
                or not hmac.compare_digest(
                    original_signature,attested_signature)
                or row["scope"]!=self.scope
                or row["skill_name"]!=latest.name
                or row["new_level"]!=after.level
                or row["old_level"]!=before.level
                or row["reviewer_id"]!=reviewer
                or row["review_id"]!=review_id
                or proof.get("scope")!=self.scope
                or proof.get("skill_name")!=latest.name
                or attested.get("skill")!=latest.name
                or attested.get("new_level")!=after.level
                or attested.get("capability_statement")!=after.statement
                or before.level+1!=after.level
                or after!=current):
                raise PermissionError("SKILL_PROMOTION_RECEIPT_TAMPERED")
            prev=proof.get("prior_receipt_sha256")
            if prev=="BASELINE_L1":
                if before.level!=1:
                    raise PermissionError(
                        "SKILL_PROMOTION_LINEAGE_MISSING")
                return True
            bootstrap=self.db.conn.execute(
                "SELECT * FROM skill_bootstrap_receipts "
                "WHERE scope=? AND skill_name=? AND receipt_sha=?",
                (self.scope,latest.name,prev)).fetchone()
            if bootstrap is not None:
                if self._bootstrap_key is None or not bootstrap["payload_json"]:
                    raise PermissionError(
                        "SKILL_PROMOTION_BOOTSTRAP_PROOF_REQUIRED")
                try:
                    signed=json.loads(bootstrap["payload_json"])
                    old=self._contract_from_record(signed["capability"])
                except (TypeError,ValueError,KeyError) as exc:
                    raise PermissionError(
                        "SKILL_PROMOTION_BOOTSTRAP_PROOF_TAMPERED") from exc
                self._validate_bootstrap(old,{
                    "source_sha256":bootstrap["source_sha"],
                    "reviewer_id":bootstrap["reviewer_id"],
                    "review_id":bootstrap["review_id"],
                    "signature":bootstrap["signature"]},receipt=bootstrap)
                if old!=before:
                    raise PermissionError(
                        "SKILL_PROMOTION_BOOTSTRAP_STATE_MISMATCH")
                return True
            predecessor=self.db.conn.execute(
                "SELECT new_level FROM skill_promotion_receipts "
                "WHERE scope=? AND skill_name=? AND receipt_sha=?",
                (self.scope,latest.name,prev)).fetchone()
            if predecessor is None or predecessor["new_level"]!=before.level:
                raise PermissionError("SKILL_PROMOTION_LINEAGE_MISSING")
            current=before
        raise PermissionError("SKILL_PROMOTION_HISTORY_BUDGET_EXCEEDED")

    def bootstrap_verified(self,name:str)->bool:
        return name in self._verified_initial_grades

    def grade_verified(self,name:str)->bool:
        return (name in self._verified_initial_grades or
                name in self._verified_promotions)

    def _bind_promotion_verifier(self,key:bytes|None):
        if key is None:
            return
        if not isinstance(key,bytes) or len(key)<16:
            raise ValueError("SKILL_PROMOTION_VERIFIER_INVALID")
        if (self._trusted_promotion_key is not None and
                not hmac.compare_digest(self._trusted_promotion_key,key)):
            raise PermissionError("SKILL_PROMOTION_VERIFIER_IMMUTABLE")
        self._trusted_promotion_key=key
        # EvolutionEngine can receive an already-open SkillRegistry whose
        # high grades were conservatively SHADOW while the verification key
        # was unavailable. Verify legitimate durable chains after binding.
        if self.db is not None:
            for name in tuple(self._legacy_unverified):
                row=self.db.conn.execute(
                    "SELECT skill_name,level,statement,dependencies_json,"
                    "status,revision FROM skill_capabilities "
                    "WHERE scope=? AND skill_name=?",
                    (self.scope,name)).fetchone()
                if row is None:
                    continue
                matching=self.db.conn.execute(
                    "SELECT 1 FROM skill_promotion_receipts "
                    "WHERE scope=? AND skill_name=? AND new_level=?",
                    (self.scope,name,int(row["level"]))).fetchone()
                if matching is None:
                    continue
                candidate=CapabilityContract(
                    row["skill_name"],int(row["level"]),row["statement"],
                    json.loads(row["dependencies_json"]),
                    SkillStatus(row["status"]),int(row["revision"]))
                self._verify_promotion_chain(candidate)
                self._skills[name]=candidate
                self._legacy_unverified.remove(name)
                self._verified_promotions.add(name)

    def register(self, contract: CapabilityContract, *,
                 bootstrap_attestation:dict|None=None) -> None:
        """Create an initial capability contract exactly once.

        Registration is NOT a way to overwrite/promote an existing ID.
        New unverified high-level declarations remain a separate release
        policy risk, not evidence of WF's actual artistic ability.
        """
        if not isinstance(contract,CapabilityContract):
            raise TypeError("SKILL_REGISTRATION_SCHEMA_INVALID")
        proposed=self._snapshot(contract)
        bootstrap_meta=None
        if proposed.level>1:
            contract_sha,receipt_sha=self._validate_bootstrap(
                proposed,bootstrap_attestation)
            bootstrap_meta=(
                self.scope,proposed.name,contract_sha,
                bootstrap_attestation["source_sha256"],
                bootstrap_attestation["reviewer_id"],
                bootstrap_attestation["review_id"],
                bootstrap_attestation["signature"],receipt_sha,
                json.dumps(self.bootstrap_attestation_payload(
                    proposed,
                    source_sha256=bootstrap_attestation["source_sha256"],
                    reviewer_id=bootstrap_attestation["reviewer_id"],
                    review_id=bootstrap_attestation["review_id"]),
                    sort_keys=True,ensure_ascii=False,
                    separators=(",",":"),allow_nan=False))
        elif bootstrap_attestation is not None:
            raise ValueError("SKILL_BOOTSTRAP_NOT_REQUIRED_FOR_LEVEL_ONE")
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
                if bootstrap_meta is not None:
                    conn.execute(
                        "INSERT INTO skill_bootstrap_receipts("
                        "scope,skill_name,contract_sha,source_sha,"
                        "reviewer_id,review_id,signature,receipt_sha,"
                        "payload_json)"
                        " VALUES(?,?,?,?,?,?,?,?,?)",bootstrap_meta)
                conn.commit()
            except Exception:
                if conn.in_transaction:
                    conn.rollback()
                raise
        self._skills[proposed.name]=proposed
        if bootstrap_meta is not None:
            self._verified_initial_grades.add(proposed.name)

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
        if candidate.skill in self._legacy_unverified:
            raise PermissionError("SKILL_BOOTSTRAP_LEGACY_GRADE_UNVERIFIED")
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
                # Upgrade authorization is itself durable evidence.
                # The signed AFTER state, reviewer metrics and preceding
                # trust root are committed atomically with skill/events.
                prev=conn.execute(
                    "SELECT receipt_sha FROM skill_promotion_receipts "
                    "WHERE scope=? AND skill_name=? AND new_level=?",
                    (self.scope,candidate.skill,target.level)).fetchone()
                if prev is not None:
                    previous_sha=prev["receipt_sha"]
                elif target.level==1:
                    previous_sha="BASELINE_L1"
                else:
                    boot=conn.execute(
                        "SELECT receipt_sha FROM skill_bootstrap_receipts "
                        "WHERE scope=? AND skill_name=?",
                        (self.scope,candidate.skill)).fetchone()
                    if boot is None:
                        raise PermissionError(
                            "SKILL_PROMOTION_LINEAGE_MISSING")
                    previous_sha=boot["receipt_sha"]
                original_payload=EvolutionEngine.promotion_attestation_payload(
                    candidate,reviewer_id=attestation["reviewer_id"],
                    review_id=attestation["review_id"])
                proof={
                    "protocol":"writerforge.v64-signed-manual-promotion.v1",
                    "scope":self.scope,"skill_name":candidate.skill,
                    "before":asdict(target),"after":asdict(elevated),
                    "prior_receipt_sha256":previous_sha,
                    "attested_request":original_payload,
                    "original_signature":attestation["signature"],
                    "reviewer_id":attestation["reviewer_id"],
                    "review_id":attestation["review_id"],
                    "literary_quality_proven_by_software":False,
                }
                proof_text=self._canonical_receipt(proof)
                seal_sig=hmac.new(
                    self._trusted_promotion_key,
                    proof_text.encode("utf-8"),"sha256").hexdigest()
                receipt_sha=sha256(
                    self._canonical_receipt({
                        "payload":proof,"signature":seal_sig
                    }).encode("utf-8")).hexdigest()
                conn.execute(
                    "INSERT INTO skill_promotion_receipts("
                    "scope,skill_name,new_level,old_level,reviewer_id,"
                    "review_id,signature,receipt_sha,payload_json)"
                    " VALUES(?,?,?,?,?,?,?,?,?)",
                    (self.scope,candidate.skill,elevated.level,target.level,
                     attestation["reviewer_id"],attestation["review_id"],
                     seal_sig,receipt_sha,proof_text))
                conn.commit()
            except Exception:
                if conn.in_transaction:
                    conn.rollback()
                raise
        self._verified_promotions.add(candidate.skill)
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

    def lagging(self)->list[CapabilityLag]:
        out=[]
        for skill in self._skills.values():
            for dep,minimum in skill.depends_on.items():
                actual=self._skills.get(dep)
                # An unverified legacy L9/SHADOW is not a valid
                # level-5 dependency. Trust status must participate in
                # capability planning, not only the numeric label.
                if (actual is None or actual.status!=SkillStatus.ACTIVE
                    or actual.level<minimum):
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
