"""V80 synthetic 150k aggregate budgets and complete chapter CAS checks.

No real user original, no DeepSeek calls, no external R2: all invented text
and a purely in-memory content-addressed blob store. The tests verify that
the V79 three-unit pilot remains immutable, V80 continues at the fourth,
and subsequent chapters can be completely read before analysis.
"""
from __future__ import annotations

from hashlib import sha256
import json
import unittest

from writerforge.deepseek_flash_model import (
    FlashBudget,DeepSeekFlashModel,DeepSeekFlashError,
)
from writerforge.wf_api_usage_supervisor import MeteredDeepSeekFlashModel
from writerforge.v79_provisional_r2_cas_journal import (
    WFProvisionalR2CASJournal,
)
from writerforge.r2_learn_journal import (
    identity,hexdigest,WFLearnJournalError,
)
from writerforge.r2_index_vault import (
    chunk_key,R2IndexError,
)
from writerforge.v80_large_chapter_batch import (
    WFLargeChapterBatch,MAX_BATCH_TOKENS,
    WFLargeStudyError,
)

READER="synthetic-reader-valid-long-test-secret"
WRITER="synthetic-indexwriter-valid-long-test-secret"
SOURCE="writerforge/v1/private-reading/仙侠/模拟书/正文.txt"
SOURCE_SHA="1"*64

class MemoryCAS:
    def __init__(self,storage):
        self.data=storage
    def _call(self,path,args,*,method="GET",body=None,write=False,cap=8192):
        if path=="/r2/index/write" and write:
            raise R2IndexError("WF_INDEX_SHA_REJECTED")
        raise AssertionError("unexpected real-network-like call")
    def _head(self,key):
        data=self.data[key]
        return len(data),'"synthetic"'
    def _index_bytes(self,key,length):
        data=self.data[key]
        if len(data)!=length:raise R2IndexError("corrupt bytes")
        return data
    def _write_immutable(self,key,raw):
        if key!=chunk_key(sha256(raw).hexdigest()):
            raise R2IndexError("invalid content key")
        before=self.data.get(key)
        if before and before!=raw:
            raise R2IndexError("immutable CAS violation")
        self.data.setdefault(key,raw)
        return before is None

def reaction():
    return {
       "attention":3,"curiosity":4,"confusion":2,"tension":3,
       "urge_to_continue":4,
       "question":"这个声音意味着什么",
       "prediction":"下一段可能解释声音",
       "what_changed":"新增了一个不确定线索",
    }

class DummyChapter:
    def __init__(self,ordinal,body):
        self.ordinal=ordinal
        self.printed_number=ordinal
        self.body_sha256=sha256(body.encode("utf8")).hexdigest()
        self.body_characters=len(body)

class ArtificialWFModel:
    name="deepseek-flash"
    def __init__(self):
        self.budget=FlashBudget(
            max_calls=96,
            max_reserved_output_tokens=150000,
            max_total_tokens=150000)
        self.calls=[]
    def ask_json(self,*,role,system,user,max_tokens):
        self.budget.reserve(
            role,max_tokens,len((system+user).encode("utf8"))+256)
        self.budget.add_usage({
            "prompt_tokens":80,"completion_tokens":55,
        })
        self.calls.append((role,user,max_tokens))
        if role=="first_read":
            return reaction()
        if "本章所有单位" in user:
            import re
            match=re.search(r"来源SHA ([a-f0-9]{64})",user)
            if not match:raise AssertionError("no source hash in analysis")
            return {"mechanisms":[{
               "unit":1,"mechanism":"延迟信息透露",
               "reader_effect":"产生新的悬念",
               "uncertainty":"仅是WF的假说",
            }]}
        return {
           "observed_weakness":"无法证明真实读者感受",
           "next_strategy":"留意信息出现的顺序和人物视角",
           "open_question":"下一章会解释哪些疑惑",
           "confidence_limit":"没有外部文学评审",
        }
    def public_usage_report(self):
        return self.budget.public_receipt()

class V80BudgetTests(unittest.TestCase):
    def test_model_allows_real_150k_aggregate_training_budget(self):
        budget=FlashBudget(
            max_calls=96,
            max_reserved_output_tokens=150000,
            max_total_tokens=150000)
        seen=[]
        def fake(req):
            data=json.loads(req.data)
            seen.append(data["max_tokens"])
            return json.dumps({
               "choices":[{
                   "finish_reason":"stop",
                   "message":{"content":'{"ok":true}'},
               }],
               "usage":{"prompt_tokens":60,
                        "completion_tokens":20},
            }).encode("utf8")
        model=MeteredDeepSeekFlashModel(
            api_key="synthetic-api-key-very-long-string",
            transport=fake,budget=budget)
        for i in range(25):
            out=model.ask_json(
                role="first_read",
                system='只返回JSON对象 {"ok":true}，这只是合成学习测试。',
                user="第"+str(i)+"段："+"山中听见流水声。"*20,
                max_tokens=900)
            self.assertEqual(out["ok"],True)
        self.assertEqual(len(seen),25)
        self.assertEqual(budget.calls_reserved,25)
        self.assertEqual(budget.prompt_tokens_reported,1500)
        self.assertEqual(budget.completion_tokens_reported,500)
        self.assertEqual(budget.conservative_tokens_committed,2000)
        self.assertEqual(budget.max_total_tokens,150000)
        self.assertEqual(model.public_usage_report()["event_count"],25)

    def test_call_can_request_more_than_former_1500_output_tokens(self):
        model=DeepSeekFlashModel(
            api_key="synthetic-api-key-very-long-string",
            budget=FlashBudget(
                max_calls=2,max_reserved_output_tokens=150000,
                max_total_tokens=150000),
            transport=lambda req: json.dumps({
                "choices":[{
                   "finish_reason":"stop",
                   "message":{"content":'{"answer":"ok"}'},
                }],
                "usage":{"prompt_tokens":70,"completion_tokens":15},
            }).encode(),
        )
        out=model.ask_json(
           role="craft_analysis",
           system='只返回JSON对象 {"answer":"ok"}，不要其他说明。',
           user="合成文本的叙事机制测试",
           max_tokens=8192)
        self.assertEqual(out,{"answer":"ok"})
        self.assertGreater(model.budget.max_reserved_output_tokens,2000)

    def test_cap_blocks_next_call_before_any_network_and_no_fake_150k_usage(self):
        requests=[]
        model=DeepSeekFlashModel(
            api_key="synthetic-api-key-very-long-string",
            budget=FlashBudget(
                max_calls=96,max_reserved_output_tokens=150000,
                max_total_tokens=150000),
            transport=lambda req: requests.append(req) or b"{}",
        )
        with self.assertRaisesRegex(DeepSeekFlashError,
                                    "TOTAL_150K_TOKEN_CAP_REACHED"):
            model.ask_json(
                role="first_read",
                system='只返回JSON对象 {"test":"ok"}，测试大限额。',
                user="虚构的一段话",
                max_tokens=150000)
        self.assertEqual(requests,[])
        self.assertEqual(model.budget.calls_reserved,0)

    def test_missing_usage_keeps_conservative_hold_and_prevents_overrun(self):
        model=DeepSeekFlashModel(
            api_key="synthetic-api-key-very-long-string",
            budget=FlashBudget(
                max_calls=96,max_reserved_output_tokens=150000,
                max_total_tokens=150000),
            transport=lambda _req: (_ for _ in ()).throw(
                DeepSeekFlashError("WF_FLASH_NETWORK_OR_TIMEOUT")),
        )
        with self.assertRaisesRegex(DeepSeekFlashError,"NETWORK_OR_TIMEOUT"):
            model.ask_json(
                role="first_read",
                system='只返回JSON对象 {"ok":true}。这只是合成文本。',
                user="模拟超时",max_tokens=600)
        self.assertGreater(
            model.budget.conservative_tokens_committed,600)
        self.assertEqual(model.budget.calls_with_uncertain_usage,1)

class V80CASChapterTests(unittest.TestCase):
    def setUp(self):
        self.storage={}
        self.journal=WFProvisionalR2CASJournal(
           endpoint="https://wf-r2-api.synthetic.workers.dev",
           reader_token=READER,writer_token=WRITER)
        self.journal.vault=MemoryCAS(self.storage)
        self.units=[("山风沿着荒城的街道吹过，人们听见远处的钟声。"*8)
                    for _ in range(5)]
        self.units2=[("第二章里有新的人物出现，村庄的灯光暗了下来。"*8)
                     for _ in range(4)]
        first=DummyChapter(1,"".join(self.units))
        self.chapter1=first
        self.chapter2=DummyChapter(2,"".join(self.units2))
        self.ident=identity(
             source_key=SOURCE,source_sha=SOURCE_SHA,chapter=1,
             chapter_body_sha=first.body_sha256)
        prev=None
        for number in range(1,4):
            sent=self.journal.append_first_read(
                ident=self.ident,unit=number,
                source_unit_sha=hexdigest(self.units[number-1].encode()),
                previous_record_sha=prev,reaction=reaction())
            prev=sent["event_sha256"]
        seal=self.journal.seal_first_read(
            ident=self.ident,units=3,last_record_sha=prev)
        self.journal.append_analysis(
            ident=self.ident,first_read_seal_sha=seal["event_sha256"],
            mechanisms=[{
               "unit":1,
               "evidence_unit_sha256":hexdigest(self.units[0].encode()),
               "mechanism":"早期分析","reader_effect":"可能感到疑惑",
               "uncertainty":"此时尚未读完整章",
            }])
        self.previous=seal["event_sha256"]
        self.old_final=self.journal.checkpoint_sha

    def test_archived_three_units_not_rebilled_and_new_chapter_complete(self):
        model=ArtificialWFModel()
        progress=[]
        batch=WFLargeChapterBatch(
            journal=self.journal,model=model,
            original_key=SOURCE,source_sha=SOURCE_SHA,
            progress=progress.append)
        first=batch.complete(
            chapter=self.chapter1,windows=self.units)
        self.assertEqual(first["new_first_read_model_calls"],2)
        self.assertFalse(first["strict_full_chapter_pass_a_before_any_pass_b"])
        self.assertTrue(first["previous_V79_early_analysis_flag"])
        self.assertEqual(
            self.journal.fetch_event(
                ident=self.ident,stage="seal")["event_sha256"],
            self.previous)
        self.assertGreater(len(self.storage),10)
        self.assertEqual(
            self.journal.fetch_event(
                ident=self.ident,stage="first_read",unit=4
            )["doc"]["source_unit_sha256"],
            hexdigest(self.units[3].encode()))
        next_receipt=batch.complete(
            chapter=self.chapter2,windows=self.units2)
        self.assertTrue(
            next_receipt["strict_full_chapter_pass_a_before_any_pass_b"])
        self.assertEqual(next_receipt["unit_count"],4)
        self.assertEqual(next_receipt["new_first_read_model_calls"],4)
        self.assertEqual(
            next_receipt["previous_experience_sha256_used_in_prompts"],
            first["experience_sha256"])
        self.assertTrue(any(
            "上章WF自己形成的阅读检查策略" in text
            for role,text,max_tokens in model.calls if role=="first_read"))
        self.assertEqual(len(batch.finished_chapters),2)
        self.assertLess(model.budget.conservative_tokens_committed,150000)
        self.assertEqual(model.budget.calls_with_uncertain_usage,0)
        self.assertEqual(len(self.journal.event_addresses),5+2+4+2)
        self.assertEqual(self.journal.checkpoint_sha is not None,True)

    def test_analysis_wrapped_in_valid_json_without_rediscovering_source(self):
        class WrappedModel(ArtificialWFModel):
            def ask_json(self,*,role,system,user,max_tokens):
                result=super().ask_json(
                    role=role,system=system,user=user,max_tokens=max_tokens)
                if role=="craft_analysis" and "本章所有单位" in user:
                    return {"mechanisms":result["mechanisms"],
                            "summary":"模型给了多余但非证据字段"}
                return result
        model=WrappedModel()
        batch=WFLargeChapterBatch(
            journal=self.journal,model=model,
            original_key=SOURCE,source_sha=SOURCE_SHA)
        receipt=batch.complete(chapter=self.chapter1,windows=self.units)
        self.assertFalse(
            receipt["strict_full_chapter_pass_a_before_any_pass_b"])
        self.assertEqual(receipt["unit_count"],5)
        self.assertGreater(model.budget.calls_reserved,2)

    def test_one_paid_format_revision_when_prior_analysis_schema_invalid(self):
        class FixableModel(ArtificialWFModel):
            bad_once=True
            def ask_json(self,*,role,system,user,max_tokens):
                if (role=="craft_analysis" and "本章所有单位" in user
                    and self.bad_once):
                    self.bad_once=False
                    self.budget.reserve(
                        role,max_tokens,len((system+user).encode())+200)
                    self.budget.add_usage({
                        "prompt_tokens":83,"completion_tokens":50})
                    self.calls.append((role,user,max_tokens))
                    return {"summary":"原先格式不合格但记录了分析"}
                if role=="craft_analysis" and "不合格结构化分析" in user:
                    self.budget.reserve(
                        role,max_tokens,len((system+user).encode())+200)
                    self.budget.add_usage({
                        "prompt_tokens":110,"completion_tokens":60})
                    self.calls.append((role,user,max_tokens))
                    return {"mechanisms":[{
                         "unit":1,"mechanism":"来自原分析的机制",
                         "reader_effect":"有限度的阅读效果推断",
                         "uncertainty":"合成文本不能证明迁移能力",
                    }]}
                return super().ask_json(
                    role=role,system=system,user=user,max_tokens=max_tokens)
        model=FixableModel()
        batch=WFLargeChapterBatch(
            journal=self.journal,model=model,
            original_key=SOURCE,source_sha=SOURCE_SHA)
        receipt=batch.complete(chapter=self.chapter1,windows=self.units)
        self.assertEqual(receipt["unit_count"],5)
        self.assertTrue(any(
           "不合格结构化分析" in user for role,user,t in model.calls))
        self.assertLess(model.budget.conservative_tokens_committed,150000)

if __name__=="__main__":
    unittest.main()
