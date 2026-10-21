"""V113 same task, same model, strict ACTUAL Unicode length benchmark.

Offline only: never sends a DeepSeek request, never accesses user's R2 books.
Original author raw prose is not truncated/repaired to meet word counts.
"""
from __future__ import annotations
from io import BytesIO
from hashlib import sha256
import unittest
from botocore.exceptions import ClientError

from experiments import v113_equal_length_three_arm as new
from experiments import v112_three_arm_github_runner as old
from experiments.v113_github_r2_cas import GitHubS3CAS,PREFIX,V113CASException

class FakePrivateR2:
    def __init__(self):
        self.files={}
        self.count=0
    def head_object(self,*,Bucket,Key):
        if Key not in self.files:
            raise ClientError({"Error":{"Code":"404"}},"HeadObject")
        return {}
    def get_object(self,*,Bucket,Key):
        if Key not in self.files:
            raise ClientError({"Error":{"Code":"NoSuchKey"}},"GetObject")
        return {"Body":BytesIO(self.files[Key])}
    def put_object(self,*,Bucket,Key,Body,IfNoneMatch,ContentType,Metadata):
        assert IfNoneMatch=="*" and Key not in self.files
        assert Metadata["sha256"]==sha256(Body).hexdigest()
        self.files[Key]=Body
        self.count+=1

class EqualLengthThreeArm(unittest.TestCase):
    def test_fixed_question_provider_and_independent_experiment_identity(self):
        self.assertEqual(new.TASK,old.TASK)
        self.assertEqual(new.TASK,"给我一个追逐打斗的玄幻1000字")
        self.assertEqual(new.MODEL,"deepseek-flash")
        self.assertEqual(new.MODEL,old.MODEL)
        self.assertEqual(new.MAX_CALLS,old.MAX_CALLS)
        self.assertEqual(new.MAX_CALLS,4)
        self.assertEqual(new.PROSE_TOKENS,old.PROSE_TOKENS)
        self.assertEqual(new.PROSE_TOKENS,2600)
        self.assertEqual(new.WF_PLAN_TOKENS,650)
        self.assertEqual(new.ARMS,old.ARMS)
        self.assertNotEqual(new.EXAM,old.EXAM)
        self.assertEqual(new.EXAM,
                         "WF-V113-STRICT-900-1100-CHASE-3WAY-20261021")
        self.assertTrue(new.freeze(new.skill_original()[0])[
            "V112_real_model_responses_never_replayed"])
        self.assertEqual(new.freeze(new.skill_original()[0])["source_branch"],
                         "v113-equal-length-chase-causal-blind")

    def test_same_strict_length_contract_without_story_answer(self):
        shared=new.common_prose_instruction()
        self.assertIn("950至1030字符",shared)
        self.assertIn("最终必须在900至1100字符",shared)
        self.assertIn("不能为了凑字数重复一句话",shared)
        self.assertEqual(new.bare_system(),shared)
        skill,_=new.skill_original()
        self.assertIn(skill,new.peer_system(skill))
        self.assertNotIn(skill,shared)
        self.assertNotIn(skill,new.bare_system())
        self.assertEqual(new.user_question(),old.user_question())
        self.assertNotIn("他在巷中左转",shared)
        self.assertNotIn("你要用某种具体招式",shared)

    def test_actual_length_symmetric_hard_gate(self):
        good={
            "WF_SINGLE":"追"*970,
            "GITHUB_STORYTELLER":"逃"*1020,
            "BARE_DEEPSEEK":"斗"*995,
        }
        v=new.length_fairness_by_arm(good)
        self.assertTrue(v["eligible_for_equal_length_literary_review"])
        self.assertTrue(v["each_arm_in_900_1100"])
        self.assertEqual(v["largest_smallest_relative_gap"],50/1020)
        self.assertFalse(v["not_evidence_of_literary_superiority"] is False)
        self.assertEqual(new.length_fairness_by_arm({
            **good,"WF_SINGLE":"追"*1400,
        })["eligible_for_equal_length_literary_review"],False)
        self.assertFalse(new.length_fairness_by_arm({
            **good,"WF_SINGLE":"追"*900,
            "GITHUB_STORYTELLER":"逃"*1100,
        })["eligible_for_equal_length_literary_review"])
        self.assertFalse(new.length_fairness_by_arm({
            k:v for k,v in good.items() if k!="WF_SINGLE",
        })["eligible_for_equal_length_literary_review"])

    def test_original_prose_never_cropped_even_when_overlong(self):
        t="灵"*1432
        observed=new.prose_observation({"prose":t})
        self.assertEqual(observed["status"],"LENGTH_OFF_TARGET")
        self.assertEqual(observed["actual_codepoints"],1432)
        self.assertEqual(observed["raw_prose"],t)
        self.assertEqual(observed["body_sha256"],
                         sha256(t.encode("utf8")).hexdigest())
        self.assertEqual(new.prose_observation({"prose":"战"*1000})[
            "status"],"LENGTH_WITHIN_TARGET")
        self.assertEqual(new.prose_observation({"prose":"追"*1000,
                                                "rewrite":"test"})["status"],
                         "PROSE_JSON_SCHEMA_FAILED")

    def test_private_new_CAS_prefix_can_never_overlap_v112_history(self):
        self.assertIn("v113-",PREFIX)
        self.assertNotIn("v112-",PREFIX)
        s3=FakePrivateR2()
        cfg=type("Cfg",(),{"bucket":"synthetic-v113-only"})()
        cas=GitHubS3CAS(config=cfg,client=s3)
        raw=b"v113 synthetic CAS marker; no story or secret"
        ptr,fresh=cas._put_content(raw)
        self.assertTrue(fresh)
        self.assertEqual(cas._get_content(ptr),raw)
        ptr2,again=cas._put_content(raw)
        self.assertEqual(ptr2,ptr)
        self.assertFalse(again)
        self.assertEqual(s3.count,1)

    def test_frozen_skill_same_byte_pinned_SHA_and_no_old_user_novels(self):
        skill,_=new.skill_original()
        self.assertEqual(new.PEER_GIT_BLOB,old.PEER_GIT_BLOB)
        self.assertEqual(new.PEER_ORIGIN_COMMIT,old.PEER_ORIGIN_COMMIT)
        frozen=new.freeze(skill)
        self.assertTrue(frozen["WF_neutral_fixture_not_15_authored_chapters"])
        self.assertFalse(frozen["author_accepted"])
        self.assertTrue(frozen["no_auto_retry_no_cropping_no_postprocessing"])
        self.assertEqual(frozen["third_party_judge_model_calls"],0)
        self.assertEqual(frozen["literary_grade"],"UNDETERMINED")
        self.assertTrue(frozen["actual_length_gate_fails_closed_no_cropping"])
        self.assertEqual(frozen["max_relative_length_gap"],0.1)
        self.assertEqual(frozen["comparable_per_arm_range"],[900,1100])

if __name__=="__main__":unittest.main()
