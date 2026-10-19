"""V79 synthetic CAS memory tests: real WF PASS A/B state, no remote access.

No R2 originals nor DeepSeek accounts. An injected fake content-addressed
vault only models the existing R2 index chunk API and supports a fresh
reader-only instance after the simulated worker exits.
"""
from __future__ import annotations

from hashlib import sha256
import json
import unittest
from unittest.mock import patch

from writerforge.r2_learn_journal import (
    WFLearnJournalError,canonical,hexdigest,
)
from writerforge.v79_provisional_r2_cas_journal import (
    WFProvisionalR2CASJournal,FORMAT,
)
from writerforge.r2_index_vault import (
    R2IndexError,chunk_key,
)
from writerforge.deepseek_flash_model import (
    DeepSeekFlashModel,FlashBudget,
)
from writerforge.wf_sequential_learning_trial import WFSequentialLearningTrial

READER="synthetic-reader-token-000000000000000000000"
WRITER="synthetic-index-writer-token-99999999999999"
SOURCE="writerforge/v1/private-reading/仙侠/原创合成文本/正文.txt"
SOURCE_SHA="a"*64
BODY_SHA="b"*64

FIRST=("一阵山风吹过荒凉的小城，远处响起陌生的钟声，夜色渐渐深了。"*2)
SECOND=("旅人顺着山路走到城门，听见身后有细微脚步声，心中又生疑问。"*2)
THIRD=("两个人在街边相遇，谁都不肯回答之前的疑惑，故事仍未揭晓。"*2)


class FakeR2CAS:
    def __init__(self,storage):
        self.storage=storage
        self.write_token=WRITER
        self.call_count=0
    def _call(self,path,args,*,method="GET",body=None,write=False,cap=8192):
        if (path=="/r2/index/write" and method=="PUT" and write and
            args["key"]==chunk_key("0"*64)):
            self.call_count+=1
            raise R2IndexError("WF_INDEX_SHA_REJECTED")
        raise AssertionError("unexpected R2 route: "+path)
    def _write_immutable(self,key,payload):
        self.call_count+=1
        h=sha256(payload).hexdigest()
        if key!=chunk_key(h):
            raise AssertionError("not content addressed")
        created=key not in self.storage
        if not created and self.storage[key]!=payload:
            raise R2IndexError("WF_INDEX_IMMUTABLE_COLLISION")
        self.storage.setdefault(key,payload)
        return created
    def _head(self,key):
        if key not in self.storage:
            raise R2IndexError("WF_INDEX_ROUTE_OR_OBJECT_NOT_DEPLOYED")
        return len(self.storage[key]),'"synthetic-etag"'
    def _index_bytes(self,key,length):
        data=self.storage[key]
        if len(data)!=length:
            raise R2IndexError("WF_INDEX_READ_CORRUPT_LENGTH")
        return data


class ContentAddressedTrainTrialTests(unittest.TestCase):
    def setUp(self):
        self.storage={}
        self.messages=[]
        self.journal=WFProvisionalR2CASJournal(
            endpoint="https://synthetic.workers.dev",
            reader_token=READER,writer_token=WRITER,
            progress=self.messages.append,
        )
        self.journal.vault=FakeR2CAS(self.storage)

    def model(self):
        self.calls=[]
        hashes=[hexdigest(x.encode("utf8")) for x in (FIRST,SECOND,THIRD)]
        def fake(req):
            body=json.loads(req.data)
            user=body["messages"][1]["content"]
            self.calls.append(user)
            if len(self.calls)<=3:
                result={
                    "attention":4,"curiosity":3,"confusion":1,"tension":3,
                    "urge_to_continue":4,"question":"声音从何而来",
                    "prediction":"另一位旅人将出现",
                    "what_changed":"听到新的动静",
                }
            else:
                result={"mechanisms":[{
                    "unit":1,"evidence_unit_sha256":hashes[0],
                    "mechanism":"先给声音再推迟揭晓",
                    "reader_effect":"产生等待感",
                    "uncertainty":"模型自述，并非独立读者证据",
                }]}
            return json.dumps({"choices":[{
               "finish_reason":"stop",
               "message":{"role":"assistant",
                          "content":json.dumps(result,ensure_ascii=False)},
            }],"usage":{"prompt_tokens":51,"completion_tokens":80}},
                ensure_ascii=False).encode("utf8")
        return DeepSeekFlashModel(
            api_key="synthetic-deepseek-key-for-test-123456",
            budget=FlashBudget(max_calls=4,max_reserved_output_tokens=2000),
            transport=fake)

    def subject(self,model):
        return WFSequentialLearningTrial(
            model=model,journal=self.journal,
            original_key=SOURCE,source_sha=SOURCE_SHA,
            chapter=1,chapter_body_sha=BODY_SHA)

    def test_three_real_wf_units_sealed_then_craft_analysis_in_cas(self):
        model=self.model()
        trial=self.subject(model)
        a=trial.first_read((FIRST,SECOND,THIRD),expected_unit_count=3)
        self.assertEqual(a["units_seen_in_order"],3)
        self.assertEqual(len(self.calls),3)
        self.assertNotIn(SECOND,self.calls[0])
        self.assertNotIn(THIRD,self.calls[0])
        self.assertEqual(len(self.journal.event_addresses),4)
        b=trial.analyse_after_lock()
        self.assertEqual(b["hypotheses"],1)
        self.assertEqual(model.budget.calls_reserved,4)
        self.assertEqual(len(self.storage),10)
        self.assertEqual(self.journal.checkpoint_sha,
                         self.messages[-1]["checkpoint_sha256"])
        self.assertEqual(len(self.messages),5)
        self.assertEqual(b["status"],"WF_LEARN_PASS_B_HYPOTHESES_R2_STORED")
        self.assertTrue(all(k.startswith(
            "writerforge/v1/indexes/v1/chunks/") for k in self.storage))
        self.assertFalse(b["full_chapter_completed"])
        self.assertFalse(b["literary_skill_promotion_allowed"])

    def test_new_read_only_process_recovers_cas_checkpoint(self):
        trial=self.subject(self.model())
        trial.first_read((FIRST,SECOND,THIRD),expected_unit_count=3)
        trial.analyse_after_lock()
        sha=self.journal.checkpoint_sha
        reader=WFProvisionalR2CASJournal(
            endpoint="https://synthetic.workers.dev",
            reader_token=READER,writer_token=None,read_only=True)
        reader.vault=FakeR2CAS(self.storage)
        receipt=reader.restore_pointer(sha)
        self.assertEqual(receipt["restored_events"],5)
        self.assertTrue(reader.read_only)
        self.assertIsNone(reader.writer)
        with self.assertRaisesRegex(WFLearnJournalError,"CAS_WRITER"):
            reader.require_writer_ready()
        with self.assertRaisesRegex(WFLearnJournalError,"READER_CANNOT_UPLOAD"):
            reader._put_content(b"fake")
        from writerforge.r2_learn_journal import identity
        source_id=identity(source_key=SOURCE,source_sha=SOURCE_SHA,
                           chapter=1,chapter_body_sha=BODY_SHA)
        seal=reader.fetch_event(ident=source_id,stage="seal")
        self.assertIsNotNone(seal)
        self.assertEqual(seal["doc"]["units_read"],3)
        analysis=reader.fetch_event(ident=source_id,stage="analysis")
        self.assertIsNotNone(analysis)
        self.assertFalse(analysis["doc"]["literary_mastery_verified"])

    def test_server_sha_tamper_causes_fail_closed(self):
        trial=self.subject(self.model())
        trial.first_read((FIRST,SECOND,THIRD),expected_unit_count=3)
        key=chunk_key(self.journal.checkpoint_sha)
        self.storage[key]=self.storage[key]+b"x"
        reader=WFProvisionalR2CASJournal(
            endpoint="https://synthetic.workers.dev",
            reader_token=READER,read_only=True)
        reader.vault=FakeR2CAS(self.storage)
        with self.assertRaisesRegex((WFLearnJournalError,R2IndexError),
                                    "SHA_MISMATCH|REMOTE_CAS_SHA"):
            reader.restore_pointer(self.journal.checkpoint_sha)

    def test_source_events_cannot_be_edited_after_local_lock(self):
        trial=self.subject(self.model())
        trial.first_read((FIRST,SECOND,THIRD),expected_unit_count=3)
        from writerforge.r2_learn_journal import identity
        source_id=identity(source_key=SOURCE,source_sha=SOURCE_SHA,
                           chapter=1,chapter_body_sha=BODY_SHA)
        with self.assertRaisesRegex(WFLearnJournalError,
                                    "CAS_EVENT_ALREADY_IMMUTABLE"):
            self.journal.append_first_read(
                ident=source_id,unit=1,
                source_unit_sha=hexdigest(FIRST.encode("utf8")),
                previous_record_sha=None,
                reaction={
                  "attention":0,"curiosity":0,"confusion":0,"tension":0,
                  "urge_to_continue":0,"question":"改写首读反应",
                  "prediction":"暂无","what_changed":"暂无",
                })

if __name__=="__main__":
    unittest.main()
