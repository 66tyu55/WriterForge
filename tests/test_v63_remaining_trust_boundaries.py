"""V63 intentional OPEN-boundary diagnostics, not bug-fix success.

These tests are deliberately GREEN *when the remaining trust boundary exists*.
They do NOT certify safe third-party plugin access or literary grade legitimacy.
Do not merge the results into the 9 repaired red-team cases.
"""
from __future__ import annotations
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
import hmac
import unittest

from writerforge.db import WriterForgeDB
from writerforge.runtime import RuntimeEngine
from writerforge.evolution import SkillRegistry,CapabilityContract,SkillStatus
from writerforge.experience_decision import ExperienceDecisionBridge,canonical
from writerforge.writing_flow import WritingFlow

KEY=b"synthetic-V63-diagnostic-only-key"


class RemainingTrustBoundaries(unittest.TestCase):
    def test_unreviewed_new_level_ten_can_still_be_bootstrapped(self):
        """Registration is a trusted initial declaration, NOT earned grade."""
        reg=SkillRegistry()
        # V64 converts the V63 deliberately-green OPEN-risk observation
        # into a regression: high-grade INITIAL creation now needs proof.
        with self.assertRaisesRegex(PermissionError,"BOOTSTRAP"):
            reg.register(CapabilityContract(
                "synthetic_level_ten",10,
                "not validated against any real literary evidence",
                status=SkillStatus.ACTIVE))
        self.assertEqual(reg.all(),[])

    def test_trusted_low_level_storycommit_is_not_an_authentication_boundary(self):
        with TemporaryDirectory() as t:
            db=WriterForgeDB(Path(t)/"synthetic.db")
            try:
                mode=RuntimeEngine()
                mode.enter_learn()
                sn=db.conn.execute(
                    "INSERT INTO snapshots(status,layout,note) "
                    "VALUES('published','full','synthetic')").lastrowid
                txt="synthetic only"
                sha=sha256(txt.encode("utf-8")).hexdigest()
                db.conn.execute(
                    "INSERT INTO studied_works(work_id,title,source_uri,"
                    "source_sha256,chapter_count) VALUES(?,?,?,?,?)",
                    ("syntheticw","Synthetic","test://synthetic",
                     sha256(b"synthetic-work").hexdigest(),1))
                db.conn.execute(
                    "INSERT INTO studied_chapters(work_id,chapter,"
                    "chapter_sha256,heading,source_spans,retrieval_entries,"
                    "snapshot_id) VALUES(?,?,?,?,?,?,?)",
                    ("syntheticw",1,sha,"synthetic",1,1,sn))
                db.conn.execute(
                    "INSERT INTO source_spans(work_id,chapter,paragraph,"
                    "sentence,excerpt,source_sha256,tracks_json,craft_json)"
                    " VALUES(?,?,?,?,?,?,?,?)",
                    ("syntheticw",1,1,1,txt,sha,"{}","{}"))
                db.conn.commit()
                b=ExperienceDecisionBridge(db,mode,reviewer_key=KEY)
                b.stage_candidate(
                    project_id="syntheticproj",experience_id="lesson99",
                    snapshot_id=sn,source_ref={
                        "work_id":"syntheticw","chapter":1,
                        "paragraph":1,"sentence":1,"source_sha256":sha},
                    required_tags=["knowledge_limited"],
                    forbidden_tags=["omniscient"],
                    operation_code="CHECK_KNOWLEDGE")
                approval=b.approval_payload(
                    project_id="syntheticproj",experience_id="lesson99",
                    reviewer_id="external99",review_id="review99")
                b.approve_candidate(
                    project_id="syntheticproj",experience_id="lesson99",
                    reviewer_id="external99",review_id="review99",
                    signature=hmac.new(KEY,canonical(approval).encode("utf-8"),
                                       "sha256").hexdigest())
                self.assertTrue(b.has_approved(project_id="syntheticproj"))
                mode.exit()
                mode.enter_write(sn)
                # Trusted in-process host API; it does NOT accept a decision
                # permit by default. User-authored drafts legitimately use
                # this route, but an untrusted plugin must never be handed it.
                flow=WritingFlow(db,mode,"syntheticproj")
                # V64: the same low-level assistant claim must fail.
                # Truly human-hosted editing remains an allowed separate path.
                with self.assertRaisesRegex(
                        (PermissionError,RuntimeError),"PROVENANCE"):
                    flow.accept_draft(
                        "commit99","scene99",
                        "synthetic original human/host provided text",
                        origin="assistant_generated")
                saved=flow.accept_draft(
                    "human99","scene99",
                    "synthetic original human/host provided text",
                    origin="author_written")
                self.assertTrue(saved.committed)
                self.assertEqual(db.conn.execute(
                    "SELECT COUNT(*) FROM story_ai_provenance"
                    ).fetchone()[0],0)
                self.assertEqual(db.conn.execute(
                    "SELECT COUNT(*) FROM story_commit_receipts"
                    ).fetchone()[0],1)
            finally:
                db.close()


if __name__=="__main__":
    unittest.main()
