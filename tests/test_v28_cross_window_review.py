"""No-network cross-source-window regression using synthetic R2-style receipts."""
import unittest
from hashlib import sha256
from test_v28_reverse_ab_candidates import synthetic_receipt
from writerforge.reverse_ab_candidates import _canonical,CandidateEvidenceError
from writerforge.reverse_cross_window_review import compare_existing_chapters


def fake_pair(v6_skill=None):
    old=synthetic_receipt()
    old["critic_prompt_original_source_prose"]=False
    old["writing_task_sha256"]="f"*64
    new=synthetic_receipt()
    new["critic_prompt_original_source_prose"]=False
    new["writing_task_sha256"]="f"*64
    new["source_unit_sha256"]="c"*64
    new["source_cursor_diagnostic"]={
        "chapter":2,"ordinal":1,"diagnostic_only_no_promotion":True,
        "earlier_first_window":"NOT_PASSED","second_curriculum_window":"LOCKED",
        "full_body_reconstructed":True,
        "chapter_headers_sequential":True,
        "source_window_sha256":"c"*64,
        "next_contiguous_sha256":new["next_unit_sha256"],
        "chapter_body_sha256":"46acf29ea47e63b0a47a18413260a689bcaf9a9f1284338a2cebc4771428956e",
    }
    if v6_skill is not None:
        for name in ("perception","causality","information","continuity","language"):
            new["comparisons"]["skill"]["dimension_review"][name]["score"]=v6_skill
        new["comparisons"]["skill"]["model_critic_score_unverified"]=v6_skill
    return old,new

def h(v):return sha256(_canonical(v)).hexdigest()

class CrossWindowTests(unittest.TestCase):
    def test_keeps_old_raw_scores_and_prevents_promotion(self):
        a,b=fake_pair(v6_skill=60)
        result=compare_existing_chapters(a,b,v5_sha=h(a),v6_sha=h(b))
        self.assertTrue(result["sharp_model_rated_skill_drop_10_or_more"])
        self.assertTrue(result["negative_model_rated_new_ab_effect"])
        self.assertFalse(result["first_window_passed"])
        self.assertFalse(result["second_window_unlocked"])
        self.assertFalse(result["core_promoted"])
        self.assertEqual(result["source_chapter_new"],2)

    def test_same_hash_or_different_task_or_fake_gate_is_refused(self):
        for mutation in [
            lambda a,b:b.update(source_unit_sha256=a["source_unit_sha256"]),
            lambda a,b:b.update(writing_task_sha256="c"*64),
            lambda a,b:b["source_cursor_diagnostic"].update(second_curriculum_window="PASSED"),
        ]:
            a,b=fake_pair()
            mutation(a,b)
            with self.assertRaises(CandidateEvidenceError):
                compare_existing_chapters(a,b,v5_sha=h(a),v6_sha=h(b))

    def test_source_not_blind_fails_closed(self):
        a,b=fake_pair()
        a["critic_prompt_original_source_prose"]=True
        with self.assertRaises(CandidateEvidenceError):
            compare_existing_chapters(a,b,v5_sha=h(a),v6_sha=h(b))

    def test_proven_negative_context_quarantine_not_global_disable(self):
        from writerforge.reverse_cross_window_review import (
            quarantine_pairs_from_verified_candidate,
        )
        from writerforge.reverse_mechanism_boundary import (
            source_paragraphs, guarded_selections,
        )
        from writerforge.reverse_ab_candidates import _canonical
        a,b=fake_pair(v6_skill=60)
        result=compare_existing_chapters(a,b,v5_sha=h(a),v6_sha=h(b))
        digest=sha256(_canonical(result)).hexdigest()
        blocked=quarantine_pairs_from_verified_candidate(
            result,candidate_sha256=digest)
        self.assertEqual(blocked[0][0],"c"*64)
        paragraphs=source_paragraphs("合成场景存在不确定的认知线索。\n"*20)
        selection={"selections":[
            {"id":"COST_VISIBLE_IN_ACTION","evidence_ids":["P0"]},
            {"id":"EMOTIONAL_TURN_WITH_EVIDENCE","evidence_ids":["P1"]},
        ]}
        picks,reason=guarded_selections(
            selection,paragraphs,source_window_sha256="c"*64,
            quarantined_pairs=blocked)
        self.assertEqual(picks,())
        self.assertEqual(reason,"QUARANTINED_PREVIOUS_NEGATIVE_CONTEXT")
        old_picks,other=guarded_selections(
            selection,paragraphs,source_window_sha256="b"*64,
            quarantined_pairs=blocked)
        self.assertEqual(len(old_picks),2)
        self.assertEqual(other,"UNVERIFIED_EXPERIMENT_CANDIDATE")
        with self.assertRaises(CandidateEvidenceError):
            quarantine_pairs_from_verified_candidate(
                result,candidate_sha256="d"*64)


if __name__=="__main__":
    unittest.main()
