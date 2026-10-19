"""V75 simulated immutable R2 WF LEARN journal.

No user source, no R2 network, no paid model calls. Server fake enforces the
actual proposed protocol: chronological PASS A units, A seal, then PASS B.
It is NOT a substitute for Cloudflare production deploy or literary review.
"""
from __future__ import annotations

from hashlib import sha256
from io import BytesIO
from urllib.error import HTTPError
from urllib.parse import parse_qs,urlsplit
import json
import unittest

from writerforge.r2_learn_journal import (
    WFLearnJournal,WFLearnJournalError,canonical,hexdigest,identity,
    event_doc,path_for,validation,
)

from writerforge.wf_sequential_learning_trial import (
    WFSequentialLearningTrial,WFSequentialLearnError,
)
from writerforge.deepseek_flash_model import DeepSeekFlashModel,FlashBudget

READER="synthetic-private-source-reader-token-0123456"
WRITER="synthetic-dedicated-learn-writer-token-abcdef"
INDEX_WRITER="synthetic-existing-index-writer-token-abcdef"
ORIGINAL_KEY="writerforge/v1/private-reading/仙侠/合成小说/测试.txt"
SOURCE_HASH=sha256(b"synthetic original novel, not user text").hexdigest()
CHAPTER_HASH=sha256(b"synthetic chapter").hexdigest()
ID=identity(source_key=ORIGINAL_KEY,source_sha=SOURCE_HASH,
            chapter=1,chapter_body_sha=CHAPTER_HASH)
ROOT=path_for(source_key_sha=ID["source_key_sha256"],
              source_sha=ID["source_sha256"],
              chapter=ID["chapter"],stage="seal").rsplit("/",1)[0]+"/"

def make_reaction(question="谁在那里？"):
    return {
      "attention":4,"curiosity":3,"confusion":2,"tension":3,
      "urge_to_continue":4,"question":question,
      "prediction":"会有人出现","what_changed":"出现新问题",
    }

class DummyResponse:
    def __init__(self,body,headers=None,status=200):
        self.status=status
        self.body=BytesIO(body)
        self.headers=headers or {}
    def read(self,limit=None):
        return self.body.read(limit)
    def __enter__(self):return self
    def __exit__(self,*args):self.body.close()

class SimulatedR2Worker:
    def __init__(self):
        self.data={}
        self.record_sha={}
        self.requests=[]
        self.source_bytes_seen=False
        self.writer_calls=0
    def error(self,req,status):
        raise HTTPError(req.full_url,status,"rejected",{},BytesIO(b""))
    def open(self,req,timeout=None):
        url=urlsplit(req.full_url)
        params=parse_qs(url.query)
        self.requests.append(req.get_method())
        if url.path!="/r2/learn/event" or set(params)!={"key"}:
            self.error(req,403)
        key=params["key"][0]
        method=req.get_method()
        authorization=req.get_header("Authorization")
        if method=="GET":
            if authorization!="Bearer "+READER:self.error(req,401)
            if key not in self.data:self.error(req,404)
            return DummyResponse(self.data[key],{
                "X-WF-Learn-SHA256":self.record_sha[key],
            })
        if method!="PUT":self.error(req,405)
        self.writer_calls+=1
        if authorization!="Bearer "+WRITER:self.error(req,401)
        raw=req.data
        try:
            doc=json.loads(raw)
            validation(doc)
        except (ValueError,WFLearnJournalError):
            self.error(req,400)
        computed=sha256(raw).hexdigest()
        if key in self.data:
            if self.record_sha[key]==computed and self.data[key]==raw:
                return DummyResponse(canonical({
                    "ok":True,"created":False,
                    "sha256":computed,"immutable":True,
                }))
            self.error(req,409)
        stage=doc["stage"]
        if stage=="first_read":
            if ROOT+"seal.json" in self.data:
                self.error(req,409)
            if doc["unit"]>1:
                prev=path_for(source_key_sha=ID["source_key_sha256"],
                 source_sha=ID["source_sha256"],chapter=1,
                 stage="first_read",unit=doc["unit"]-1)
                if self.record_sha.get(prev)!=doc["previous_event_sha256"]:
                    self.error(req,409)
        elif stage=="seal":
            last=path_for(source_key_sha=ID["source_key_sha256"],
                  source_sha=ID["source_sha256"],chapter=1,
                  stage="first_read",unit=doc["units_read"])
            if self.record_sha.get(last)!=doc["last_first_read_sha256"]:
                self.error(req,409)
        elif stage=="analysis":
            if self.record_sha.get(ROOT+"seal.json")!=doc["first_read_seal_sha256"]:
                self.error(req,409)
            for mech in doc["mechanisms"]:
                source_key=path_for(
                   source_key_sha=ID["source_key_sha256"],
                   source_sha=ID["source_sha256"],chapter=1,
                   stage="first_read",unit=mech["unit"])
                if source_key not in self.data:
                    self.error(req,409)
                first=json.loads(self.data[source_key])
                if first["source_unit_sha256"]!=mech["evidence_unit_sha256"]:
                    self.error(req,409)
        self.data[key]=raw
        self.record_sha[key]=computed
        return DummyResponse(canonical({
            "ok":True,"created":True,"sha256":computed,"immutable":True,
        }))

class ImmutableLearnJournalTests(unittest.TestCase):
    def setUp(self):
        self.remote=SimulatedR2Worker()
        self.journal=WFLearnJournal(
            endpoint="https://wf-r2-api.synthetic.workers.dev",
            reader_token=READER,writer_token=WRITER,
            index_writer_token=INDEX_WRITER,
            transport=self.remote.open)
        self.unit1=hexdigest(b"synthetic first line")
        self.unit2=hexdigest(b"synthetic second line")

    def first(self):
        return self.journal.append_first_read(
            ident=ID,unit=1,source_unit_sha=self.unit1,
            previous_record_sha=None,reaction=make_reaction())

    def second(self,prev):
        return self.journal.append_first_read(
            ident=ID,unit=2,source_unit_sha=self.unit2,
            previous_record_sha=prev,reaction=make_reaction("这意味着什么？"))

    def finish(self):
        a=self.first()
        b=self.second(a["event_sha256"])
        c=self.journal.seal_first_read(
            ident=ID,units=2,last_record_sha=b["event_sha256"])
        return a,b,c

    def test_cold_process_pass_a_then_pass_b_sealed_immutable(self):
        a,b,seal=self.finish()
        self.assertTrue(a["r2_reader_readback_verified"])
        self.assertTrue(b["r2_reader_readback_verified"])
        self.assertTrue(seal["r2_reader_readback_verified"])
        review=self.journal.append_analysis(
            ident=ID,first_read_seal_sha=seal["event_sha256"],
            mechanisms=[{
              "unit":1,"evidence_unit_sha256":self.unit1,
              "mechanism":"观测到的延迟揭示",
              "reader_effect":"提出未解答的疑问",
              "uncertainty":"仅属于本次模拟判断",
            }])
        self.assertTrue(review["created"])
        fresh=WFLearnJournal(
            endpoint="https://wf-r2-api.synthetic.workers.dev",
            reader_token=READER,writer_token=None,index_writer_token=INDEX_WRITER,
            transport=self.remote.open)
        doc=event_doc(stage="seal",ident=ID,units_read=2,
                last_first_read_sha256=b["event_sha256"],
                future_source_seen=False)
        self.assertEqual(fresh.read(doc),doc)
        self.assertFalse(review["literary_quality_graduated"])
        self.assertTrue(all(k.startswith("writerforge/v1/learn/v1/")
                            for k in self.remote.data))

    def test_analysis_cannot_precede_first_read_lock(self):
        with self.assertRaisesRegex(WFLearnJournalError,"LOCK_OR_ORDER"):
            self.journal.append_analysis(
              ident=ID,first_read_seal_sha="e"*64,
              mechanisms=[{
                "unit":1,"evidence_unit_sha256":self.unit1,
                "mechanism":"未知","reader_effect":"未知","uncertainty":"未知",
              }])

    def test_no_skipping_units_in_pass_a(self):
        with self.assertRaisesRegex(WFLearnJournalError,"LOCK_OR_ORDER"):
            self.second("e"*64)
        self.assertEqual(self.remote.data,{})

    def test_first_read_cannot_be_changed_after_lock(self):
        first=self.first()
        retry=self.first()
        self.assertFalse(retry["created"])
        self.assertEqual(first["event_sha256"],retry["event_sha256"])
        with self.assertRaisesRegex(WFLearnJournalError,"LOCK_OR_ORDER"):
            self.journal.append_first_read(
              ident=ID,unit=1,source_unit_sha=self.unit1,
              previous_record_sha=None,
              reaction=make_reaction("重新写成另一个反应"))
        self.assertEqual(len(self.remote.data),1)

    def test_no_new_first_read_after_seal(self):
        a=self.first()
        self.journal.seal_first_read(
            ident=ID,units=1,last_record_sha=a["event_sha256"])
        with self.assertRaisesRegex(WFLearnJournalError,"LOCK_OR_ORDER"):
            self.second(a["event_sha256"])

    def test_incomplete_pass_a_cannot_be_sealed(self):
        with self.assertRaisesRegex(WFLearnJournalError,"LOCK_OR_ORDER"):
            self.journal.seal_first_read(
                ident=ID,units=4,last_record_sha="e"*64)

    def test_wrong_evidence_source_unit_rejected(self):
        _,_,sealed=self.finish()
        with self.assertRaisesRegex(WFLearnJournalError,"LOCK_OR_ORDER"):
            self.journal.append_analysis(
              ident=ID,first_read_seal_sha=sealed["event_sha256"],
              mechanisms=[{
                 "unit":1,"evidence_unit_sha256":"f"*64,
                 "mechanism":"测试","reader_effect":"测试","uncertainty":"测试",
              }])

    def test_reader_and_index_tokens_cannot_write_learn(self):
        with self.assertRaisesRegex(WFLearnJournalError,
                                    "WRITER_TOKEN_NOT_SEPARATE"):
            WFLearnJournal(
                endpoint="https://wf-r2-api.synthetic.workers.dev",
                reader_token=READER,writer_token=READER,
                index_writer_token=INDEX_WRITER,
                transport=self.remote.open)
        with self.assertRaisesRegex(WFLearnJournalError,
                                    "WRITER_TOKEN_NOT_SEPARATE"):
            WFLearnJournal(
                endpoint="https://wf-r2-api.synthetic.workers.dev",
                reader_token=READER,writer_token=INDEX_WRITER,
                index_writer_token=INDEX_WRITER,
                transport=self.remote.open)

    def test_no_source_text_field_allowed_in_events(self):
        doc=event_doc(stage="first_read",ident=ID,
                      unit=1,source_unit_sha256=self.unit1,
                      previous_event_sha256=None,future_source_seen=False,
                      reaction=make_reaction())
        doc["raw_original"]="fictional source, should never be stored"
        with self.assertRaisesRegex(WFLearnJournalError,"SCHEMA_INVALID"):
            validation(doc)

    def test_tamper_body_or_sha_must_be_detected_on_restoration(self):
        result=self.first()
        record=event_doc(
            stage="first_read",ident=ID,unit=1,
            source_unit_sha256=self.unit1,previous_event_sha256=None,
            future_source_seen=False,reaction=make_reaction())
        key=path_for(source_key_sha=ID["source_key_sha256"],
                     source_sha=ID["source_sha256"],chapter=1,
                     stage="first_read",unit=1)
        self.remote.data[key]+=b" "
        with self.assertRaisesRegex(WFLearnJournalError,"SHA_FAILED"):
            self.journal.read(record,expect_sha=result["event_sha256"])

    def test_wf_model_must_observe_pass_a_one_unit_at_a_time(self):
        a=("雨后的小镇陷入寂静。远处传来脚步声，但屋内的人不知道是谁。"*2)
        b=("外面的声音停下了，主角犹豫是否推开门。读者仍不知道门外是谁。"*2)
        class FakeDeepSeekTransport:
            def __init__(self):
                self.inputs=[]
            def __call__(self,request):
                posted=json.loads(request.data)
                user=posted["messages"][1]["content"]
                self.inputs.append(user)
                if len(self.inputs)<=2:
                    result=make_reaction()
                else:
                    result={
                       "mechanisms":[{
                          "unit":1,
                          "evidence_unit_sha256":hexdigest(a.encode("utf-8")),
                          "mechanism":"先声后人是假说",
                          "reader_effect":"增加未知感",
                          "uncertainty":"合成片段不足以证明效果",
                       }]
                    }
                return json.dumps({
                    "choices":[{
                       "finish_reason":"stop",
                       "message":{"role":"assistant",
                                  "content":json.dumps(result,ensure_ascii=False)},
                    }],
                    "usage":{"prompt_tokens":42,"completion_tokens":68}
                },ensure_ascii=False).encode("utf-8")
        fake=FakeDeepSeekTransport()
        model=DeepSeekFlashModel(
            api_key="synthetic-deepseek-secret-not-real",
            budget=FlashBudget(max_calls=3,max_reserved_output_tokens=1800),
            transport=fake)
        wf=WFSequentialLearningTrial(
            model=model,journal=self.journal,
            original_key=ORIGINAL_KEY,
            source_sha=SOURCE_HASH,
            chapter=1,chapter_body_sha=CHAPTER_HASH)
        with self.assertRaisesRegex(WFSequentialLearnError,
                                     "PASS_A_NOT_SEALED"):
            wf.analyse_after_lock()
        self.assertEqual(len(fake.inputs),0)
        first=wf.first_read((a,b),expected_unit_count=2)
        self.assertEqual(first["status"],"WF_LEARN_PASS_A_R2_LOCKED")
        self.assertEqual(first["first_read_events_written"],2)
        self.assertEqual(len(fake.inputs),2)
        self.assertIn(a,fake.inputs[0])
        self.assertNotIn(b,fake.inputs[0])
        self.assertIn(b,fake.inputs[1])
        self.assertNotIn(a,fake.inputs[1])
        self.assertEqual(len(self.remote.data),3) # A1,A2,seal
        second=wf.analyse_after_lock()
        self.assertEqual(second["status"],"WF_LEARN_PASS_B_HYPOTHESES_R2_STORED")
        self.assertEqual(len(fake.inputs),3)
        self.assertIn(a,fake.inputs[2])
        self.assertIn(b,fake.inputs[2])
        self.assertEqual(len(self.remote.data),4)
        self.assertFalse(second["literary_skill_promotion_allowed"])
        self.assertFalse(second["full_chapter_completed"])
        self.assertEqual(model.budget.calls_reserved,3)

    def test_first_read_bad_model_json_must_not_write_or_analyse(self):
        fake_calls=[0]
        def bad_transport(req):
            fake_calls[0]+=1
            return json.dumps({
              "choices":[{
                "finish_reason":"stop",
                "message":{"content":'{"attention":5,"future_answers":"cheating"}'},
              }]
            }).encode()
        model=DeepSeekFlashModel(
            api_key="synthetic-deepseek-secret-not-real",
            transport=bad_transport)
        wf=WFSequentialLearningTrial(
            model=model,journal=self.journal,
            original_key=ORIGINAL_KEY,source_sha=SOURCE_HASH,
            chapter=1,chapter_body_sha=CHAPTER_HASH)
        first=("一个没有名字的人走在黑暗森林里，突然听见陌生的声音。"*2)
        second=("另一个人在城门口等候，仍然不知道森林里发生了什么。"*2)
        with self.assertRaisesRegex(WFSequentialLearnError,
                                     "FIRST_REACTION_INVALID"):
            wf.first_read((first,second),expected_unit_count=2)
        self.assertEqual(len(self.remote.data),0)
        self.assertEqual(fake_calls[0],1)

    def test_analysis_does_not_certify_mastery(self):
        _,_,sealed=self.finish()
        result=self.journal.append_analysis(
            ident=ID,first_read_seal_sha=sealed["event_sha256"],
            mechanisms=[{
              "unit":1,"evidence_unit_sha256":self.unit1,
              "mechanism":"因果假设",
              "reader_effect":"期待变化",
              "uncertainty":"文学质量未经过校准",
            }])
        self.assertFalse(result["literary_quality_graduated"])

if __name__=="__main__":
    unittest.main()
