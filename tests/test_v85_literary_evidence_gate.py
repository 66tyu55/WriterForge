"""V85: synthetic FactJournal adversarial evidence regression, no paid calls."""
from __future__ import annotations
import unittest
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory

from writerforge.fact_journal import FactJournal
from writerforge.v85_literary_evidence_gate import (
    LiteraryEvidenceGate, LiteraryEvidenceError, canonical,
)

def h(s):
    return sha256(s.encode("utf8")).hexdigest()

U1="暮色压住旧桥，少年看见守桥人悄悄熄灭了灯，却没有告诉同行的妹妹。"
U2="桥外远远传来钟声，少年收起渡河的木牌，决定今晚先等待，不贸然走近。"
WINDOWS=(U1,U2)
SOURCE=h("synthetic-source")
BODY=h(U1+U2)
SEAL=h("synthetic-seal")

def mark(unit,phrase):
    text=WINDOWS[unit-1]
    offset=text.index(phrase)
    return {"unit":unit,"start":offset,"end":offset+len(phrase),
            "quote":phrase}

def claim():
    return {
        "claim_id":"test01","source_sha256":SOURCE,"chapter":3,
        "kind":"CAUSAL","actor_id":"hero","fact_id":"bridge_light",
        "story_tick":3,"claimed_knowledge_state":"KNOWN",
        "observation":mark(1,"守桥人悄悄熄灭了灯"),
        "consequence":mark(2,"少年收起渡河的木牌"),
        "hypothesis":"少年可能因看见桥边异常而改变今晚过桥的决定。",
        "alternative":"少年也可能只是因为夜色和钟声而选择等待。",
        "falsifier":"如果后续证据表明木牌早已失效，这个解释应修正。",
        "uncertainty":"这是一条还没有独立验证的因果解释假说。",
    }

class V85LiteraryEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.tmp=TemporaryDirectory()
        self.path=Path(self.tmp.name)/"synthetic.sqlite3"
        self.db=FactJournal(self.path)
        for scene,num in (("chapter01",1),("chapter03",3)):
            self.db.register_scene(story_id="novelA",scene_id=scene,
                                   chapter_index=num)
            self.db.bind_subject(scene_id=scene,scope="ACTOR",
                                 subject_id="hero",canonical_id="heroA")
        self.db.append({
            "event_id":"seen-bridge","scene_id":"chapter01",
            "actor_id":"hero","fact_id":"bridge_light","tick":2,
            "state":"KNOWN","role":"OBSERVE",
            "evidence_sha256":h("synthetic-evidence")})
        self.db.append_temporal_claim({
            "claim_id":"knowledge01","scene_id":"chapter01",
            "subject_scope":"ACTOR","subject_id":"hero",
            "fact_id":"bridge_light","story_from":2,"story_until":None,
            "knowledge_state":"KNOWN","evidence_event_id":"seen-bridge",
            "supersedes_id":None})
        self.seq=self.db.ledger_head()
        self.gate=LiteraryEvidenceGate(
            self.db,story_id="novelA",scene_id="chapter03",
            source_sha256=SOURCE,ledger_seq=self.seq)

    def tearDown(self):
        self.db.close()
        self.tmp.cleanup()

    def audit(self,docs,frontier=2):
        return self.gate.audit(
            docs,source_windows=WINDOWS,chapter=3,
            chapter_body_sha256=BODY,first_read_seal_sha256=SEAL,
            read_frontier=frontier)

    def test_machine_anchors_and_knowledge_are_not_literary_verdict(self):
        out=self.audit([claim()])
        self.assertEqual(out["claims_count"],1)
        self.assertEqual(out["claims"][0]["actor_knowledge_state_as_of_snapshot"],"KNOWN")
        self.assertFalse(out["eligible_to_direct_writing"])
        self.assertFalse(out["skill_promotion_approved"])
        serialized=canonical(out).decode("utf8")
        for phrase in ("守桥人悄悄熄灭了灯","少年收起渡河的木牌"):
            self.assertNotIn(phrase,serialized)

    def test_forged_and_future_quotes_rejected(self):
        data=claim()
        data["observation"]["quote"]="守桥人悄悄打开了门"
        with self.assertRaisesRegex(LiteraryEvidenceError,"ANCHOR_NOT_EXACT"):
            self.audit([data])
        data=claim()
        data["observation"]["unit"]=3
        with self.assertRaisesRegex(LiteraryEvidenceError,"ANCHOR_FUTURE"):
            self.audit([data])
        with self.assertRaisesRegex(LiteraryEvidenceError,"FRONTIER_NOT_SEALED"):
            self.audit([claim()],frontier=1)

    def test_known_fact_cannot_be_claimed_from_unknown_record(self):
        data=claim()
        data["fact_id"]="missing_fact"
        with self.assertRaisesRegex(LiteraryEvidenceError,"KNOWLEDGE_CONTRADICTS"):
            self.audit([data])
        data["claimed_knowledge_state"]="UNRECORDED"
        out=self.audit([data])
        self.assertEqual(out["claims"][0]["context_status"],"UNRESOLVED_OR_ABSTAIN")

    def test_duplicate_claim_and_missing_falsifier(self):
        with self.assertRaisesRegex(LiteraryEvidenceError,"REPEATED"):
            self.audit([claim(),claim()])
        data=claim()
        data["falsifier"]=""
        with self.assertRaisesRegex(LiteraryEvidenceError,"FALSIFIER_UNBOUNDED"):
            self.audit([data])

    def test_restart_preserves_bound_knowledge(self):
        self.db.close()
        self.db=FactJournal(self.path)
        self.gate=LiteraryEvidenceGate(
            self.db,story_id="novelA",scene_id="chapter03",
            source_sha256=SOURCE,ledger_seq=self.seq)
        self.assertEqual(self.audit([claim()])["claims_count"],1)

if __name__=="__main__":
    unittest.main()
