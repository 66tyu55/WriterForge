"""Adversarial, no-network verification of factual V32 exam grading."""
import unittest,json
from unittest.mock import patch
from test_v32_examiner_blind import FakeStore,Model
import scripts.run_v32_examiner_blind as exam
import scripts.audit_v32_examiner_blind as audit

class ExamAuditTests(unittest.TestCase):
    def setUp(self):
        self.store=FakeStore()
        self.patches=[
            patch.object(exam,"STAGE1_SHA",self.store.sha1),
            patch.object(exam,"STAGE2_SHA",self.store.sha2),
            patch.object(audit,"STAGE2_SHA",self.store.sha2),
        ]
        for p in self.patches:p.start();self.addCleanup(p.stop)
    def test_examiner_keeps_opposing_reviewers_not_positive_average(self):
        log=[]
        for slot in range(3):
            exam.run(slot,vault=self.store,
                     models_factory=lambda role,name:Model(role,name,log))
        result=audit.read_grades(self.store)
        self.assertEqual(result["two_grader_valid_trials"],3)
        self.assertTrue(result["any_critic_criticizes_memory"])
        self.assertFalse(result["all_exams_consensus_positive"])
        self.assertFalse(result["literary_skill_promotion"])
        self.assertTrue(result["student_did_not_grade_own_answers"])
        self.assertEqual(len(result["results"]),3)
        row=result["results"][0]
        self.assertEqual(row["individual_critic_deltas"][exam.EXAMINERS[0]]["language"],4)
        self.assertEqual(row["individual_critic_deltas"][exam.EXAMINERS[1]]["language"],-4)
        self.assertEqual(row["individual_negative_dimensions"][exam.EXAMINERS[1]]["causality"],-4)
    def test_missing_one_exam_does_not_invent_model_scores(self):
        exam.run(0,vault=self.store,
                 models_factory=lambda role,name:Model(role,name,[]))
        report=audit.read_grades(self.store)
        self.assertEqual(report["two_grader_valid_trials"],1)
        self.assertEqual(report["results"][1]["status"],"NOT_SCORED")
        self.assertIsNone(report["results"][1]["grades"])
        self.assertFalse(report["all_exams_consensus_positive"])
    def test_forged_critiques_rejected_even_when_report_hash_is_fresh(self):
        exam.run(0,vault=self.store,
                 models_factory=lambda role,name:Model(role,name,[]))
        root=exam.exam_root(0)
        pointer=json.loads(self.store.objects[root+"/complete.json"])
        old=root+"/snapshots/"+pointer["sha256"]+".json"
        doc=json.loads(self.store.objects[old])
        doc["exam_protocol"]["per_grader"][1][
            "dimension_deltas_wf_memory_minus_control"]["causality"]=99
        from writerforge.r2_storage import _canonical
        from hashlib import sha256
        data=_canonical(doc);h=sha256(data).hexdigest()
        self.store.objects[root+"/snapshots/"+h+".json"]=data
        self.store.objects[root+"/complete.json"]=_canonical({
            "sha256":h,"slot":0,"session":exam.SESSION})
        with self.assertRaisesRegex(ValueError,"EXAM_CRITIC_SCORE_DIFFERENCE_FORGED"):
            audit.read_grades(self.store)

if __name__=="__main__":
    unittest.main()
