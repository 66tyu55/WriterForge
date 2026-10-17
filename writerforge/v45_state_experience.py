"""V45: narrow, opt-in, *state-derived* WriterForge experience policy.

V44 found (1) generic user-provided plans passed contradictory prose,
(2) unrelated quotes passed postwrite, (3) the writer prompt never changed,
(4) a caller boolean impersonated an independent reviewer.

This module learns NO literary truth. It refuses to synthesize actor facts,
and generates an execution plan ONLY from the *existing* WF character_state
and causal_events, frozen before the model is asked to write. The policy is an
unpromoted experiment sourced from the historic V38 L2 conflict.
"""
from __future__ import annotations
from dataclasses import dataclass
from hashlib import sha256
import json
import re
import sqlite3
import hmac

V38_ROLE_CONFLICT_SHA="e2ed24abc352daef678165de8bee5f7c283f5709cf3a23c9fe99b9a876aeb0db"
POLICY="V45_L2_STATE_DERIVED_HYPOTHESIS"
NEEDED=("observation","actor_decision","causal_consequence","later_reveal")


class V45ExperienceError(ValueError):
    pass


def _require(ok, reason):
    if not ok:
        raise V45ExperienceError(reason)


def _canon(value):
    return json.dumps(value,sort_keys=True,ensure_ascii=False,
                      separators=(",",":"),allow_nan=False).encode("utf-8")


def _hash(value):
    return sha256(value if isinstance(value,bytes) else _canon(value)).hexdigest()


def _note(value, a=2, b=180):
    return isinstance(value,str) and a<=len(value.strip())<=b


def _json(raw,code):
    try:
        doc=json.loads(raw)
    except (ValueError,TypeError):
        raise V45ExperienceError(code) from None
    _require(isinstance(doc,dict),code)
    return doc


def _ids(values):
    return (isinstance(values,list) and len(values)<=48
            and all(isinstance(v,str) and re.fullmatch(r"[A-Za-z0-9_-]{2,60}",v)
                    for v in values) and len(values)==len(set(values)))


@dataclass(frozen=True)
class Decision:
    state:str
    policy_sha:str|None = None
    prewrite_sha:str|None = None
    compiled_guidance:str = ""
    actor_id:str = ""
    clue_token:str = ""

    def receipt(self):
        return {
            "format":"WF.v45.execution.v1",
            "state":self.state,
            "policy_sha256":self.policy_sha,
            "prewrite_sha256":self.prewrite_sha,
            "actor_id":self.actor_id or None,
            "clue_token_sha256":sha256(self.clue_token.encode()).hexdigest()
                if self.clue_token else None,
            "clue_token":self.clue_token if self.state=="APPLIED" else None,
            "evidence_requirements":list(NEEDED) if self.state=="APPLIED" else [],
            "literary_semantics_verified":False,
            "formal_promotion":False,
        }


class StateDerivedExperience:
    def __init__(self,conn:sqlite3.Connection,project:str):
        _require(isinstance(project,str) and 1<=len(project)<=90
                 and all(c.isprintable() for c in project),
                 "V45_PROJECT_INVALID")
        self.conn=conn
        self.project=project
        self.conn.execute("""CREATE TABLE IF NOT EXISTS wf_v45_strategy(
            project TEXT PRIMARY KEY, policy_sha TEXT NOT NULL,
            mode TEXT NOT NULL)""")
        self.conn.execute("""CREATE TABLE IF NOT EXISTS wf_v45_prewrite(
            project TEXT NOT NULL, scene TEXT NOT NULL,
            policy_sha TEXT NOT NULL, plan_sha TEXT NOT NULL,
            payload TEXT NOT NULL, PRIMARY KEY(project,scene))""")
        self.conn.execute("""CREATE TABLE IF NOT EXISTS wf_v45_feedback(
            project TEXT NOT NULL, scene TEXT NOT NULL,
            reviewer TEXT NOT NULL, outcome TEXT NOT NULL,
            receipt_sha TEXT NOT NULL, PRIMARY KEY(project,scene))""")
        self.conn.commit()

    def install(self,*,opt_in:bool):
        _require(opt_in is True,"V45_EXPLICIT_EXPERIMENT_OPT_IN_REQUIRED")
        record={
            "rule":POLICY,
            "source_v38_sha256":V38_ROLE_CONFLICT_SHA,
            "mechanism":"REVIEW_CLUE_KNOWLEDGE_BEFORE_NEW_SETUP",
            "literary_status":"CONTESTED_NOT_VALIDATED",
            "promotion":False,
        }
        digest=_hash(record)
        prev=self.conn.execute(
            "SELECT policy_sha FROM wf_v45_strategy WHERE project=?",
            (self.project,)).fetchone()
        if prev is not None:
            _require(prev[0]==digest,"V45_POLICY_ALREADY_INSTALLED_DIFFERENTLY")
            return digest
        with self.conn:
            self.conn.execute(
                "INSERT INTO wf_v45_strategy VALUES(?,?,'ACTIVE_EXPERIMENT')",
                (self.project,digest))
        return digest

    def choose(self,scene:str,concerns:tuple[str,...])->Decision:
        _require(_note(scene,1,128)
                 and isinstance(concerns,tuple)
                 and all(isinstance(x,str) for x in concerns),
                 "V45_SCENE_INVALID")
        policy=self.conn.execute(
            "SELECT policy_sha,mode FROM wf_v45_strategy WHERE project=?",
            (self.project,)).fetchone()
        if policy is None:
            return Decision("UNINSTALLED")
        digest,mode=policy
        _require(mode in ("ACTIVE_EXPERIMENT","PAUSED"),
                 "V45_POLICY_MODE_INVALID")
        if mode=="PAUSED":
            return Decision("ROLLED_BACK",digest)
        if "setup_payoff" not in concerns:
            return Decision("NOT_APPLICABLE",digest)
        events=self.conn.execute(
            "SELECT event_id,payload_json FROM causal_events "
            "WHERE project_id=? ORDER BY event_id LIMIT 129",(self.project,)
        ).fetchall()
        _require(len(events)<=128,"V45_STORY_EVENT_BUDGET_EXCEEDED")
        scene_events=[]
        for event in events:
            data=_json(event["payload_json"],"V45_CAUSAL_EVENT_INVALID_JSON")
            if data.get("scene_id")==scene:
                scene_events.append(data)
        if not scene_events:
            return Decision("WITHHELD_NO_STORY_STATE",digest)
        if len(scene_events)!=1:
            return Decision("WITHHELD_AMBIGUOUS_EVENTS",digest)
        clue=scene_events[0]
        if clue.get("narrative_role")=="payoff":
            return Decision("WITHHELD_ALREADY_PAYOFF",digest)
        if clue.get("review_status")=="disputed":
            return Decision("WITHHELD_DISPUTED",digest)
        required={
            "scene_id","actor_id","clue_id","clue_token","fact_id",
            "observation","choice","expected_consequence","reveal_target",
            "alternative","narrative_role","review_status"
        }
        if not required.issubset(set(clue)) or clue["narrative_role"]!="setup":
            return Decision("WITHHELD_INCOMPLETE_EVENT",digest)
        actor=clue["actor_id"];fact=clue["fact_id"]
        if not all(_note(clue[k],2,180) for k in (
            "actor_id","clue_id","clue_token","fact_id","observation","choice",
            "expected_consequence","reveal_target","alternative")):
            return Decision("WITHHELD_INCOMPLETE_EVENT",digest)
        _require(len(clue["clue_token"])>=2 and len(clue["clue_token"])<=22,
                 "V45_CLUE_TOKEN_BOUNDS_INVALID")
        row=self.conn.execute(
            "SELECT state_json FROM character_state "
            "WHERE project_id=? AND character_id=?",(self.project,actor)
        ).fetchone()
        if row is None:
            return Decision("WITHHELD_MISSING_CHARACTER_STATE",digest)
        state=_json(row[0],"V45_CHARACTER_STATE_INVALID_JSON")
        knowledge=state.get("knowledge")
        if not isinstance(knowledge,dict) or not _ids(knowledge.get("known")) or not _ids(knowledge.get("unknown")):
            return Decision("WITHHELD_UNKNOWN_KNOWLEDGE_SCHEMA",digest)
        known=set(knowledge["known"]);unknown=set(knowledge["unknown"])
        if known & unknown:
            return Decision("WITHHELD_CONTRADICTORY_FACT_IDS",digest)
        if fact in known:
            return Decision("WITHHELD_KNOWN_REVEAL_NOT_SETUP",digest)
        if fact not in unknown:
            return Decision("WITHHELD_FACT_NOT_TRACKED",digest)
        # Only machine-grounded, persisted event state. The caller supplies
        # the task and scenario ID, NEVER an ad-hoc prose causal plan.
        record={
            "actor_id":actor,
            "clue_id":clue["clue_id"],
            "clue_token":clue["clue_token"],
            "fact_id":fact,
            "known_before":sorted(known),
            "unknown_before":sorted(unknown),
            "observation":clue["observation"],
            "choice":clue["choice"],
            "expected_consequence":clue["expected_consequence"],
            "reveal_target":clue["reveal_target"],
            "alternative":clue["alternative"],
            "source_state_version":"WF.character_state+causal_events.v1",
        }
        blob=_canon(record); ph=_hash(blob)
        old=self.conn.execute(
            "SELECT plan_sha,payload,policy_sha FROM wf_v45_prewrite "
            "WHERE project=? AND scene=?",(self.project,scene)
        ).fetchone()
        if old:
            _require(old[0]==ph and old[1].encode("utf-8")==blob and old[2]==digest,
                     "V45_PREWRITE_IMMUTABLE_CONFLICT")
        else:
            count=self.conn.execute(
                "SELECT COUNT(*) FROM wf_v45_prewrite WHERE project=?",
                (self.project,)).fetchone()[0]
            _require(count<128,"V45_PREWRITE_STORAGE_BUDGET_EXCEEDED")
            with self.conn:
                self.conn.execute(
                    "INSERT INTO wf_v45_prewrite VALUES(?,?,?,?,?)",
                    (self.project,scene,digest,ph,blob.decode("utf-8")))
        guidance=(
            "本段已启用实验性线索因果核验（非已验证文学规律）。"
            f"视角人物：{actor}；现在观察到：{clue['observation']}。"
            f"目前未知的事实编号：{fact}；不能提前写成已知。"
            f"角色将选择：{clue['choice']}，可见后果：{clue['expected_consequence']}。"
            f"可能的另一解释：{clue['alternative']}。"
            f"揭示要回查线索“{clue['clue_token']}”并核对：{clue['reveal_target']}。"
            "把知识状态自然融入故事而不是逐项复述；若无法合理实现，允许放弃该手法。"
        )
        _require(len(guidance)<1250,"V45_GUIDANCE_BUDGET_EXCEEDED")
        return Decision("APPLIED",digest,ph,guidance,actor,clue["clue_token"])

    def accept_attested_feedback(self, *, receipt:dict, mac_hex:str,
                                 verifier_shared_key:bytes)->dict:
        """Authenticate receipt bytes, NOT literary truth or human independence.

        The verifier secret must come from a separate trusted reviewer boundary
        and must not be stored in the WF learning DB. If unavailable, do NOT
        accept an independent-reviews claim or modify execution policy.
        """
        _require(isinstance(receipt,dict) and set(receipt)=={
            "scene_id","policy_sha256","reviewer_id",
            "review_report_sha256","outcome"
        },"V45_FEEDBACK_RECEIPT_SCHEMA_INVALID")
        _require(receipt["outcome"] in ("HELPED","HARMED","INCONCLUSIVE"),
                 "V45_FEEDBACK_OUTCOME_INVALID")
        _require(_note(receipt["scene_id"],1,128) and
                 _note(receipt["reviewer_id"],3,80),
                 "V45_FEEDBACK_ID_INVALID")
        _require(isinstance(receipt["review_report_sha256"],str)
                 and re.fullmatch("[0-9a-f]{64}",receipt["review_report_sha256"])
                 and isinstance(verifier_shared_key,bytes)
                 and len(verifier_shared_key)>=32
                 and isinstance(mac_hex,str)
                 and re.fullmatch("[0-9a-f]{64}",mac_hex),
                 "V45_FEEDBACK_AUTHORITY_MISSING")
        expected=hmac.new(verifier_shared_key,_canon(receipt),"sha256").hexdigest()
        _require(hmac.compare_digest(expected,mac_hex),
                 "V45_FEEDBACK_SIGNATURE_REJECTED")
        policy=self.conn.execute(
            "SELECT policy_sha FROM wf_v45_strategy WHERE project=?",
            (self.project,)).fetchone()
        _require(policy is not None and policy[0]==receipt["policy_sha256"],
                 "V45_FEEDBACK_POLICY_SHA_MISMATCH")
        row=self.conn.execute(
            "SELECT plan_sha FROM wf_v45_prewrite WHERE project=? AND scene=?",
            (self.project,receipt["scene_id"])).fetchone()
        _require(row is not None,"V45_FEEDBACK_WITHOUT_LOCKED_PREWRITE")
        digest=_hash(receipt)
        prior=self.conn.execute(
            "SELECT receipt_sha FROM wf_v45_feedback WHERE project=? AND scene=?",
            (self.project,receipt["scene_id"])).fetchone()
        if prior:
            _require(prior[0]==digest,"V45_FEEDBACK_CANNOT_REWRITE_HISTORY")
        else:
            with self.conn:
                self.conn.execute(
                    "INSERT INTO wf_v45_feedback VALUES(?,?,?,?,?)",
                    (self.project,receipt["scene_id"],receipt["reviewer_id"],
                     receipt["outcome"],digest))
        harms=self.conn.execute(
            "SELECT COUNT(*) FROM wf_v45_feedback "
            "WHERE project=? AND outcome='HARMED'",(self.project,)
        ).fetchone()[0]
        if harms>=2:
            with self.conn:
                self.conn.execute(
                    "UPDATE wf_v45_strategy SET mode='PAUSED' "
                    "WHERE project=? AND mode='ACTIVE_EXPERIMENT'",
                    (self.project,))
        return {
            "receipt_sha256":digest,"feedback_integrity_authenticated":True,
            "human_or_literary_accuracy_proven":False,
            "harm_count":harms,
            "strategy_mode":self.conn.execute(
                "SELECT mode FROM wf_v45_strategy WHERE project=?",
                (self.project,)).fetchone()[0],
            "auto_promotion":False,
        }


def verify_afterdraft(story:str,receipt:dict,quotes:dict)->dict:
    """Stronger *lexical consistency*, not certified literary causality."""
    _require(isinstance(story,str) and 80<=len(story)<=20000,
             "V45_DRAFT_BOUNDS_INVALID")
    _require(isinstance(receipt,dict) and receipt.get("state")=="APPLIED",
             "V45_CLAIM_HAS_NO_APPLIED_EXPERIENCE")
    _require(isinstance(quotes,dict) and set(quotes)==set(NEEDED),
             "V45_POSTWRITE_FOUR_ANCHORS_REQUIRED")
    actor=receipt["actor_id"];clue=receipt["clue_token"]
    _require(isinstance(actor,str) and isinstance(clue,str),
             "V45_POSTWRITE_ANCHOR_IDENTITY_INVALID")
    positions=[]
    for key in NEEDED:
        quote=quotes[key]
        _require(isinstance(quote,str) and 8<=len(quote)<=100
                 and story.count(quote)==1,
                 "V45_QUOTE_NOT_EXACT_UNIQUE")
        positions.append((story.index(quote),story.index(quote)+len(quote)))
    _require(all(positions[i][1]<positions[i+1][0] for i in range(3)),
             "V45_FOUR_ANCHORS_NOT_STRICTLY_ORDERED")
    _require(clue in quotes["observation"] and clue in quotes["later_reveal"],
             "V45_CLUE_IDENTITY_NOT_CONNECTED")
    _require(actor in quotes["actor_decision"],
             "V45_ACTOR_DECISION_NOT_GROUNDED")
    # A disconnected set of real ordered sentences cannot pass merely
    # because they exist. Further literary semantic verification is still
    # explicitly unperformed.
    return {
        "format":"WF.v45.afterdraft.v1",
        "story_sha256":sha256(story.encode()).hexdigest(),
        "frozen_prewrite_sha256":receipt["prewrite_sha256"],
        "roles":{kind:{"offset":pos[0],
                       "quote_sha256":sha256(quotes[kind].encode()).hexdigest()}
                 for kind,pos in zip(NEEDED,positions)},
        "identity_and_order_consistent":True,
        "causal_semantics_verified":False,
        "literary_improvement_verified":False,
        "formal_promotion":False,
    }
