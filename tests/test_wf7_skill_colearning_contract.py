"""Synthetic interface checks only: these do NOT measure literary accuracy."""
import copy
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"experiments"))
import wf7_colearning_contract as lab

def sha(c):
    return c*64

def blank(active=lab.SEVEN):
    return lab.make_empty("synthetic-case-1",sha("a"),sha("b"),
                          ["E01","E02","E03"],["V01","V02"],active)

def record(owner,id,dimension,value,revision=1,evidence=None):
    return {"id":id,"owner":owner,"event_id":"V01",
            "evidence_ids":evidence or ["E01"],"dimension":dimension,
            "value":value,"epistemic":"PROVISIONAL","revision":revision}

def hint(from_owner,to_owner,id="H01"):
    return {"id":id,"from_owner":from_owner,"to_owner":to_owner,
            "event_id":"V01","evidence_ids":["E01"],
            "hypothesis":"该人物当时可能不知道外部时间已过去。",
            "status":"PROVISIONAL"}

class CoLearningIsolationTests(unittest.TestCase):
    def test_four_and_seven_own_distinct_parameter_namespaces(self):
        for active in (lab.FOUR,lab.SEVEN):
            s=blank(active)
            self.assertTrue(lab.validate(s))
            self.assertEqual(len(s["stores"]),len(active))
            self.assertFalse(lab.public_summary(s)["skills_have_trained_their_parameters"])

    def test_owner_cannot_write_another_skills_parameters(self):
        s=blank()
        with self.assertRaisesRegex(lab.ContractError,"NOT_YOUR_PARAMETER"):
            lab.owned_update(s,lab.TIME,record(lab.BODY,"injury","wound","healing"))
        self.assertEqual(s["stores"][lab.BODY],[])

    def test_peer_hint_does_not_modify_any_owner_parameters(self):
        s=lab.owned_update(blank(),lab.TIME,
             record(lab.TIME,"T01","training_duration","3h"))
        original=copy.deepcopy(s["stores"])
        t=lab.send_peer_hint(s,hint(lab.TIME,lab.CHARACTER))
        self.assertEqual(t["stores"],original)
        self.assertEqual(lab.split_after_collaboration(t),original)
        view=lab.collaborative_view(t)
        self.assertEqual(len(view["peer_suggestions_by_owner"][lab.CHARACTER]),1)
        self.assertTrue(lab.assert_lossless_disconnect(s,t)["independent_parameters_unchanged"])
        self.assertEqual(lab.assert_lossless_disconnect(s,t)["holdout_transfer_accuracy"],
                         "NOT_MEASURED")

    def test_revision_appends_and_does_not_erase_history(self):
        s=lab.owned_update(blank(),lab.TIME,
             record(lab.TIME,"T01","time_span","UNKNOWN",1))
        t=lab.owned_update(s,lab.TIME,
             record(lab.TIME,"T01","time_span","3h",2,["E02"]))
        self.assertEqual([x["revision"] for x in t["stores"][lab.TIME]],[1,2])
        self.assertEqual(s["stores"][lab.TIME][0]["value"],"UNKNOWN")
        with self.assertRaisesRegex(lab.ContractError,"VERSION_MUST_APPEND"):
            lab.owned_update(t,lab.TIME,record(lab.TIME,"T01","time_span","4h",2))

    def test_cross_domain_conflicting_interpretations_remain_separate(self):
        s=blank()
        s=lab.owned_update(s,lab.BODY,
             record(lab.BODY,"B01","visible_pallor","PALE"))
        s=lab.owned_update(s,lab.EMOTION,
             record(lab.EMOTION,"M01","fear","UNKNOWN"))
        s=lab.send_peer_hint(s,hint(lab.BODY,lab.EMOTION))
        split=lab.split_after_collaboration(s)
        self.assertEqual(split[lab.BODY][0]["value"],"PALE")
        self.assertEqual(split[lab.EMOTION][0]["value"],"UNKNOWN")
        self.assertEqual(split[lab.TIME],[])

    def test_sender_cannot_claim_peer_message_is_approved_truth(self):
        s=blank();h=hint(lab.SPACE,lab.TIME)
        h["status"]="SOURCE_REVIEWED"
        with self.assertRaisesRegex(lab.ContractError,"PEER_HINT_CANNOT_BE_APPROVED_FACT"):
            lab.send_peer_hint(s,h)

    def test_unbacked_evidence_or_future_claim_rejected(self):
        s=blank()
        with self.assertRaisesRegex(lab.ContractError,"PARAMETER_WITHOUT_SOURCE"):
            lab.owned_update(s,lab.TIME,record(lab.TIME,"T01","elapsed","300y",1,["FUTURE"]))
        with self.assertRaisesRegex(lab.ContractError,"PEER_SIGNAL_WITHOUT_SOURCE"):
            h=hint(lab.SPACE,lab.TIME);h["evidence_ids"]=["SEALED_HOLDOUT_E01"]
            lab.send_peer_hint(s,h)

    def test_comparing_4_and_7_must_keep_distinct_trial_snapshots(self):
        four=blank(lab.FOUR);seven=blank(lab.SEVEN)
        self.assertEqual(len(four["stores"]),4)
        self.assertEqual(len(seven["stores"]),7)
        self.assertNotIn(lab.EMOTION,four["stores"])
        self.assertIn(lab.EMOTION,seven["stores"])
        with self.assertRaisesRegex(lab.ContractError,"UNKNOWN_SKILL"):
            lab.owned_update(four,lab.ATMOSPHERE,
                             record(lab.ATMOSPHERE,"P01","tone","UNEASY"))

    def test_mixed_source_edit_or_evidence_edition_must_not_compare(self):
        s=blank()
        t=blank()
        t["source_sha256"]=sha("c")
        self.assertFalse(lab.assert_lossless_disconnect(s,s)["changed_owner_records"])
        with self.assertRaisesRegex(lab.ContractError,"DIFFERENT_STUDY_CANNOT_COMPARE"):
            lab.assert_lossless_disconnect(s,t)

    def test_synthetic_mechanical_pass_is_not_a_literary_gain_claim(self):
        s=lab.owned_update(blank(),lab.ATMOSPHERE,
             record(lab.ATMOSPHERE,"F01","scene_atmosphere","OPPRESSIVE"))
        report=lab.public_summary(s)
        self.assertEqual(report["accuracy"],"NOT_MEASURED")
        self.assertEqual(report["literary_improvement"],"NOT_MEASURED")
        self.assertFalse(report["skills_have_trained_their_parameters"])

if __name__=="__main__":
    unittest.main()
