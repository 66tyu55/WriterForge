"""No paid model calls: frozen memory, examiner tasks and two blind graders."""
from __future__ import annotations
from hashlib import sha256
from types import SimpleNamespace
from unittest.mock import patch
import json,unittest

from writerforge.v31_stage_evidence import record_bytes,record_sha,stage_path
from writerforge.v31_autonomous_core import canonical as card_canonical,digest as card_digest
from writerforge.v32_exam_bank import BANK,selected,question,manifest,manifest_sha256
import scripts.run_v32_examiner_blind as exam

CARD={
    "scope":"适用于信息有限且人物决定可能产生真实后果的原创小说开篇",
    "trigger":"角色在陌生关系或意外冲突中误把初始猜测当作已经确认的事实",
    "operation":"先描写角色确认自己确实知道的事实，再由行动暴露错误判断的代价",
    "avoid":"不要让作者直接解释人物无法知道的隐藏答案，也不堆砌多条无关悬念",
    "self_check":"检查结尾重要转折是否由人物此前看到的具体证据与选择共同引发",
}
class FakeStore:
    def __init__(self):
        self.config=SimpleNamespace(bucket="writerforge-private-library")
        self.objects={};self.writes=0
        self.client=SimpleNamespace(put_object=self.put_object)
        one={"format":"wf.autonomous.v31","index":1,
             "phase":"LEARN_WRITE_SELF_REVIEW","parent_sha256":None,
             "reviewer_external":False,"memory":[CARD],
             "formal_skill_promoted":False}
        sha1=self._put_doc(stage_path(1),one)
        two={"format":"wf.autonomous.v31","index":2,
             "phase":"LEARN_WRITE_SELF_REVIEW","parent_sha256":sha1,
             "reviewer_external":False,"memory":[CARD],
             "prior_memory_hashes":[card_digest(card_canonical(CARD))],
             "formal_skill_promoted":False}
        sha2=self._put_doc(stage_path(2),two)
        self.sha1=sha1;self.sha2=sha2
    def _put_doc(self,path,obj):
        blob=record_bytes(obj);self.objects[path]=blob;return record_sha(blob)
    def _head(self,key):
        return {"ContentLength":len(self.objects[key])} if key in self.objects else None
    def _get_small(self,key,cap):
        data=self.objects[key]
        if len(data)>cap:raise ValueError("CAP")
        return data
    def _put_small_immutable(self,key,blob,sha):
        if record_sha(blob)!=sha:raise ValueError("WRONG_DIGEST")
        if key in self.objects and self.objects[key]!=blob:raise ValueError("OVERWRITE")
        if key not in self.objects:self.writes+=1
        self.objects[key]=blob
    def put_object(self,*,Bucket,Key,Body,ContentType):
        if Bucket!="writerforge-private-library":raise ValueError("BUCKET")
        if Key in self.objects:raise ValueError("NOT_IMMUTABLE")
        self.objects[Key]=Body

class Model:
    def __init__(self,role,name,log):
        self.role=role;self.name=name;self.log=log
    def ask(self,system,user,*,num_predict):
        self.log.append((self.role,self.name,system,user,num_predict))
        if self.role=="writer":
            packet=json.loads(user)
            memory=bool(packet["internal_experimental_rules"])
            paragraph=("夜里少年踌躇在小镇的石路旁，细听远处水声，"
                       "想起自己曾经答应过的一件重要的事。")
            return {"scene":paragraph*(23 if memory else 22)}
        inputs=json.loads(user)
        assert set(inputs)=={"question","anonymous_answer_A","anonymous_answer_B",
                            "fixed_rubric","negative_evidence_priority",
                            "no_draft_labels_or_writer_identity","scores_are_not_human_quality_proof"}
        values={d:{"score":v,"reason":"人物决策因果与前文铺垫仍然不足，应独立逐句复查。"}
                for d,v in zip(("perception","causality","information","continuity","language"),
                               (74,72,70,78,79))}
        return {"A":values,"B":{d:{**v,"score":v["score"]+4} for d,v in values.items()},
                "uncertainty":"这只是合成模型评判，不可以作为实际文学能力晋级的依据。"}
class ExaminerTests(unittest.TestCase):
    def setUp(self):
        self.store=FakeStore()
        self.patch1=patch.object(exam,"STAGE1_SHA",self.store.sha1)
        self.patch2=patch.object(exam,"STAGE2_SHA",self.store.sha2)
        self.patch1.start();self.patch2.start()
        self.addCleanup(self.patch1.stop);self.addCleanup(self.patch2.stop)
    def test_questions_frozen_and_no_prior_v29_exams(self):
        self.assertEqual(len(BANK),6)
        self.assertEqual(len(set(selected())),3)
        self.assertEqual(len(manifest_sha256()),64)
        self.assertTrue(manifest()["no_post_result_question_substitution"])
        self.assertTrue(all(95<=len(question(i))<=490 for i in range(3)))
    def test_load_real_sha_linked_v31_memory(self):
        cards=exam.frozen_memory(self.store)
        self.assertEqual(cards,(CARD,))
        self.store.objects[stage_path(2)]+=b"evil"
        with self.assertRaisesRegex(exam.ExamError,"FROZEN_SELF_TRAINING"):
            exam.frozen_memory(self.store)
    def test_exam_no_coaching_no_self_grader_and_swapped_labels(self):
        log=[]
        result=exam.run(0,vault=self.store,
                        models_factory=lambda role,name:Model(role,name,log))
        self.assertEqual(result["stage"],"REAL_V32_EXAM_VERIFIED")
        self.assertEqual([x[0] for x in log],["writer","writer","critic","critic"])
        self.assertEqual([x[1] for x in log[2:]],list(exam.EXAMINERS))
        self.assertNotIn("internal_experimental_rules",log[2][3])
        self.assertNotIn(CARD["operation"],log[3][3])
        self.assertEqual(json.loads(log[0][3])["internal_experimental_rules"],[])
        self.assertEqual(json.loads(log[1][3])["internal_experimental_rules"],[CARD])
        cache=exam.run(0,vault=self.store,
                       models_factory=lambda role,name:Model(role,name,log))
        self.assertEqual(cache["paid_calls_now"],0)
        self.assertEqual(len(log),4)
        root=exam.exam_root(0)
        pointer=json.loads(self.store.objects[root+"/complete.json"])
        doc=json.loads(self.store.objects[root+"/snapshots/"+pointer["sha256"]+".json"])
        self.assertEqual(doc["exam_protocol"]["grade_status"],
                         "TWO_DIFFERENT_GRADERS_ANONYMOUSLY_SCORED")
        grades=doc["exam_protocol"]["per_grader"]
        self.assertEqual(grades[0]["dimension_deltas_wf_memory_minus_control"]["causality"],4)
        self.assertEqual(grades[1]["dimension_deltas_wf_memory_minus_control"]["causality"],-4)
        self.assertFalse(doc["literary_progress_proven"])
        self.assertFalse(doc["official_core_promoted"])
        self.assertNotIn("夜里少年踌躇",str(doc))
    def test_bad_memory_blocks_exam_before_calls(self):
        self.store.objects[stage_path(2)]+=b"bad"
        log=[]
        with self.assertRaises(exam.ExamError):
            exam.run(0,vault=self.store,
                     models_factory=lambda role,name:Model(role,name,log))
        self.assertEqual(log,[])
        self.assertIsNone(self.store._head(exam.exam_root(0)+"/started.json"))
if __name__=="__main__":
    unittest.main()
