"""V112 GitHub-native R2 CAS + identical-question 3-arm safety regressions.

All tests have zero external HTTP and zero model requests.
"""
from __future__ import annotations
from io import BytesIO
from hashlib import sha256
from unittest import TestCase
from botocore.exceptions import ClientError
import json
import unittest

from experiments.v112_github_r2_cas import (
    GitHubS3CAS,PREFIX,V112CASException,
)
from experiments import v112_three_arm_github_runner as exp

class FakeS3:
    def __init__(self):
        self.objects={}
        self.writes=0
    @staticmethod
    def err(code):
        return ClientError(
            {"Error":{"Code":code,"Message":"synthetic"}},
            "HeadObject")
    def head_object(self,*,Bucket,Key):
        if Key not in self.objects:raise self.err("404")
        return {"ContentLength":len(self.objects[Key])}
    def put_object(self,*,Bucket,Key,Body,IfNoneMatch,ContentType,Metadata):
        assert IfNoneMatch=="*"
        assert ContentType=="application/octet-stream"
        assert Key not in self.objects
        assert Metadata["sha256"]==sha256(Body).hexdigest()
        self.objects[Key]=Body
        self.writes+=1
        return {"ETag":"fictional"}
    def get_object(self,*,Bucket,Key):
        if Key not in self.objects:raise self.err("NoSuchKey")
        return {"Body":BytesIO(self.objects[Key])}

class GithubNativeTests(TestCase):
    def test_one_content_one_write_and_fresh_readback(self):
        client=FakeS3()
        cfg=type("Cfg",(),{"bucket":"fictional-private-bucket"})()
        store=GitHubS3CAS(config=cfg,client=client)
        raw=b"original synthetic story text"
        sha,created=store._put_content(raw)
        self.assertTrue(created)
        self.assertEqual(store._get_content(sha),raw)
        sha2,created2=store._put_content(raw)
        self.assertFalse(created2)
        self.assertEqual(sha2,sha)
        self.assertEqual(client.writes,1)
        self.assertEqual(list(client.objects),
                         [PREFIX+sha[:2]+"/"+sha])
        self.assertNotIn("libraries",list(client.objects)[0])
        client.objects[list(client.objects)[0]]=b"tampered"
        with self.assertRaisesRegex(V112CASException,
                                    "CAS_CONTENT_HASH_MISMATCH"):
            store._get_content(sha)

    def test_precise_identity_all_arms_and_zero_Railway(self):
        story,_=exp.skill_original()
        ident=exp.freeze(story)
        self.assertEqual(exp.TASK,"给我一个追逐打斗的玄幻1000字")
        self.assertEqual(exp.MODEL,"deepseek-flash")
        self.assertEqual(exp.EXAM,
                         "WF-V112-GITHUB-NATIVE-3WAY-DEEPSEEK-20261021")
        self.assertEqual(ident["source_branch"],
                         "v112-github-native-matched-deepseek")
        self.assertEqual(ident["exact_common_user_question"],exp.TASK)
        self.assertEqual(exp.ARMS,
          ("WF_SINGLE","GITHUB_STORYTELLER","BARE_DEEPSEEK"))
        self.assertEqual(exp.MAX_CALLS,4)
        self.assertEqual(exp.PROSE_TOKENS,2600)
        self.assertEqual(exp.WF_PLAN_TOKENS,650)
        self.assertEqual(exp.MAX_RESERVED_TOKENS,8450)
        self.assertTrue(ident["peer_skill_isolated_from_WF_writing"])
        self.assertEqual(ident["literary_grade"],"UNDETERMINED")
        self.assertEqual(ident["real_15_chapter_history_unchanged"],True)

    def test_pinned_third_party_only_in_peer(self):
        skill,_=exp.skill_original()
        self.assertIn(skill,exp.peer_system(skill))
        self.assertNotIn(skill,exp.bare_system())
        self.assertNotIn("storyteller",exp.common_prose_instruction())
        self.assertEqual(exp.PEER_ORIGIN_COMMIT,
                         "145342ceff6318d2f5ffe8f95473fecc8b27d1e9")

    def test_truthful_prose_length_never_corrected(self):
        text="甲持剑沿石阶逃走，追兵踩碎了身后的冰桥。"*30
        reply=exp.prose_observation({"prose":text})
        self.assertEqual(reply["actual_codepoints"],len(text))
        self.assertEqual(reply["raw_prose"],text)
        self.assertEqual(reply["body_sha256"],sha256(
            text.encode("utf8")).hexdigest())
        self.assertIn(reply["status"],("LENGTH_OFF_TARGET","LENGTH_WITHIN_TARGET"))
        self.assertNotEqual(exp.prose_observation({"other":text})["status"],
                            "LENGTH_WITHIN_TARGET")

    def test_source_uses_only_v112_S3_adapter_and_precommit(self):
        from pathlib import Path
        source=Path(exp.__file__).read_text("utf8")
        self.assertIn("cas=GitHubS3CAS()",source)
        self.assertNotIn("cas=WFProvisionalR2CASJournal",source)
        self.assertNotIn("os.environ.get('WF_API_TOKEN')",source)
        self.assertIn("DEEPSEEK_API_KEY",source)
        self.assertIn("WF112_ONCE_ONLY_PRECOMMIT_REFUSES_DOUBLE_BILL",source)
        self.assertEqual(source.count("model.ask_json("),1)
        self.assertIn("on_response_wire=on_response_wire",source)
        self.assertIn("blind_method_identity_hidden",source)
        self.assertFalse(exp.freeze(exp.skill_original()[0])[
            "WF_neutral_fixture_not_15_authored_chapters"] is False)

if __name__=="__main__":
    unittest.main()
