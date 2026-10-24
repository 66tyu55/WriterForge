"""Original WF writer: same model reads prose as reader BEFORE author verdict.

Every model reply here is deterministic offline fixture. These tests prove
source/transaction behavior, not literary quality and not real model success.
"""
import json
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from writerforge import WriterForgeDB,RuntimeEngine
from writerforge.writing_assist import (
    _reader_separates_written_and_inferred,
    _reader_report_for_author,_ai_decides_when_to_revisit,
    AutonomousWriting, InvisibleWritingAssist,
)
from writerforge.verified_flow import (
    GroundedDraftPacket, WritingExecutionError,
)
from test_v26_invisible_writer import make_db,PLAN
from test_wf_cross_chapter_candidate_fork import (
    PLAN_TURNS,prose_response,visible_prose,sha,
)
from test_wf_ai_writer_previous_turn_rewind import moment


def packet(prompt):
    return GroundedDraftPacket(
        project_id="reader-test",scene_id="source-first",
        snapshot_id=1,evidence=(),craft_ids=(),prompt=prompt,
        prompt_sha256=sha(prompt))


def source_reader_reply(prose,*,invent=False,with_earlier=False):
    beginning=prose[:min(len(prose),17)]
    ending=prose[-min(len(prose),23):]
    if len(beginning)<6 or len(ending)<6 or prose.count(beginning)!=1:
        raise AssertionError("test requires unique genuine source slices")
    result={
        "observed":[{
            "quote":beginning,"actor":"沈砚",
            "visible_action":"读者看见原文确实描写的表层行动",
        }],
        "inferred_links":[{
            "before_quote":beginning,
            "after_quote":("没有出现在正文中的虚构引句" if invent else ending),
            "reader_imagined_step":"读者可能自行想象中间发生一次没有写明的转场",
        }],
        "reader_uncertainty":"这是读者推测，不是作者实际写下的事实。",
    }
    if with_earlier:
        result["cross_source_links"]=[]
    return json.dumps(result,ensure_ascii=False)


class SourceSeparation(TestCase):
    def test_valid_reader_report_source_quotes_and_authority_is_source_only(self):
        source=visible_prose(1,1)
        original=prose_response(1,1)
        with TemporaryDirectory() as temp:
            outputs=[]
            def model(prompt,*,model,api_base,max_tokens):
                self.assertEqual(max_tokens,1000)
                self.assertIsNone(model)
                self.assertIsNone(api_base)
                outputs.append(prompt.prompt)
                return source_reader_reply(source)
            report=_reader_separates_written_and_inferred(
                raw=original,turn_packet=packet(
                    "SECRET_AUTHOR_PLAN_DO_NOT_SHOW_TO_READER"),
                ask_model=model,directory=Path(temp)/"reader")
            self.assertEqual(report["status"],"SOURCE_ANCHORED_READER_HYPOTHESES")
            self.assertEqual(report["model_calls"],1)
            self.assertEqual(report["receipt"]["observed_count"],1)
            self.assertEqual(report["receipt"]["hypothesized_gap_count"],1)
            self.assertEqual(report["report"]["source_sha256"],sha(source))
            self.assertNotIn("SECRET_AUTHOR_PLAN",outputs[0])
            self.assertIn(source,outputs[0])
            self.assertNotIn("必须修改",outputs[0])
            path=Path(temp)/"reader"/"original-reader-reply.json"
            self.assertEqual(path.read_text("utf8"),source_reader_reply(source))
            hypothesis=report["report"]["inferred_links"][0]
            self.assertTrue(hypothesis["imagined_step_is_not_story_fact"])
            self.assertEqual(hypothesis["first_source_offset"],0)
            self.assertFalse(report["receipt"]["literary_quality_verified"])
            self.assertTrue(report["receipt"]["no_auto_edit_if_reader_guesses_a_gap"])
            note=_reader_report_for_author(report["report"],sha(source))
            self.assertIn("未证实阅读意见",note)
            self.assertIn("仍待你取舍",note)
            self.assertEqual(_reader_report_for_author(
                report["report"],"0"*64),"")  # stale older draft

    def test_fake_reader_quotes_invalid_and_never_reach_author(self):
        source=visible_prose(1,1)
        with TemporaryDirectory() as temp:
            def model(*args,**kwargs):return source_reader_reply(
                source,invent=True)
            outcome=_reader_separates_written_and_inferred(
                raw=prose_response(1,1),turn_packet=packet("x"),
                ask_model=model,directory=Path(temp)/"reader")
            self.assertEqual(outcome["status"],"INVALID_READER_SOURCE")
            self.assertEqual(outcome["model_calls"],1)
            self.assertIsNone(outcome["report"])
            self.assertEqual(outcome["receipt"]["reason_code"],
                             "WF_READER_GAP_SOURCE_ORDER")
            self.assertEqual(_reader_report_for_author(
                outcome["report"],sha(source)),"")
            self.assertTrue((Path(temp)/"reader"/
                             "original-reader-reply.json").is_file())

    def test_reader_can_have_no_hypotheses_without_forcing_rewrite(self):
        prose=visible_prose(1,1)
        response=json.dumps({
            "observed":[],"inferred_links":[],
            "reader_uncertainty":"我没有明显推测，可以继续阅读。",
        },ensure_ascii=False)
        with TemporaryDirectory() as temp:
            result=_reader_separates_written_and_inferred(
                raw=prose_response(1,1),turn_packet=packet("x"),
                ask_model=lambda *a,**kw:response,
                directory=Path(temp)/"reader")
        self.assertEqual(result["status"],"SOURCE_ANCHORED_READER_HYPOTHESES")
        self.assertEqual(result["receipt"]["hypothesized_gap_count"],0)
        self.assertFalse(result["receipt"]["no_auto_edit_if_reader_guesses_a_gap"] is False)

    def test_corrupt_or_missing_source_no_reader_request(self):
        with TemporaryDirectory() as temp:
            with patch("writerforge.writing_assist.local_chat_completion") as model:
                r=_reader_separates_written_and_inferred(
                    raw='{"prose":"不存在完整稿","trace":{}}',
                    turn_packet=packet("x"),ask_model=model,
                    directory=Path(temp)/"reader")
                model.assert_not_called()
            self.assertEqual(r["model_calls"],0)
            self.assertEqual(r["status"],"NO_COMPLETE_SOURCE")

    def test_model_reader_error_does_not_make_author_forced_choice(self):
        source=visible_prose(1,1)
        raw=prose_response(1,1)
        with TemporaryDirectory() as temp:
            reader=_reader_separates_written_and_inferred(
                raw=raw,turn_packet=packet("x"),
                ask_model=lambda *a,**k:source_reader_reply(source),
                directory=Path(temp)/"reader")
            def author(p,*,model,api_base,max_tokens):
                self.assertEqual(max_tokens,600)
                self.assertIn("读者",p.prompt)
                self.assertIn("未证实阅读意见",p.prompt)
                return moment("MOVE_ON",source)
            outcome=_ai_decides_when_to_revisit(
                raw=raw,beat=PLAN_TURNS["turns"][0],accepted=(),
                turn_packet=packet("SECRET_WRITER_INTENT"),
                ask_model=author,directory=Path(temp)/"author",
                reader_report=reader["report"])
            self.assertEqual(outcome["decision"],"MOVE_ON")
            self.assertTrue(outcome["receipt"]["unverified_reader_input_delivered"])
            self.assertTrue(outcome["receipt"]["reader_did_not_preselect_literary_decision"])


class TwoActuallyWrittenSources(TestCase):
    def test_existing_reader_exactly_verifies_older_source_and_new_source_quotes(self):
        previous=(
            "江遥站在戏楼的柱后，把一张赎身票据藏进袖里。"
            "宋易站在后门边握着钥匙，尚不知道票据藏在哪里。"
        )
        current=(
            "江遥忽然想起后台旧箱子，里面压着那张赎身票据。"
            "她并没有在这里明说什么时候把票据存进去。"
            "宋易继续听鼓声，却不知道楼上究竟是谁。"
        )*2
        prev_quote="江遥站在戏楼的柱后，把一张赎身票据藏进袖里。"
        curr_quote="江遥忽然想起后台旧箱子，里面压着那张赎身票据。"
        self.assertEqual(previous.count(prev_quote),1)
        self.assertEqual(current.count(curr_quote),2)
        curr_quote="里面压着那张赎身票据。"  # repeated, so choose once only
        current=current[:len(current)//2]
        # Source-only reporter always creates a hypothesis, never a verdict.
        reply=json.dumps({
            "observed":[],"inferred_links":[],
            "cross_source_links":[{
                "previous_quote":prev_quote,
                "current_quote":"江遥忽然想起后台旧箱子，里面压着那张赎身票据。",
                "reader_imagined_step":"这张票据或许曾被人从她袖中移到箱底，原文尚未明写转移。"
            }],
            "reader_uncertainty":"这里只能推测，不知道有没有省略操作。",
        },ensure_ascii=False)
        original=json.dumps({
            "prose":current,"trace":{"action_quote":None,
                                     "effect_quote":None,
                                     "parent_effect_quote":None}
        },ensure_ascii=False)
        with TemporaryDirectory() as td:
            root=Path(td)
            prompts=[]
            def same_model(packet,*,model,api_base,max_tokens):
                prompts.append(packet.prompt)
                self.assertEqual(max_tokens,1000)
                return reply
            received=_reader_separates_written_and_inferred(
                raw=original,turn_packet=packet("OLD_AUTHOR_PLAN"),
                ask_model=same_model,directory=root/"two",
                earlier_source=previous,earlier_source_sha256=sha(previous))
            self.assertEqual(received["status"],
                             "SOURCE_ANCHORED_READER_HYPOTHESES")
            self.assertEqual(received["receipt"]["cross_source_inference_count"],1)
            self.assertEqual(received["receipt"]["earlier_original_sha256"],
                             sha(previous))
            self.assertIn(previous,prompts[0])
            self.assertIn(current,prompts[0])
            self.assertNotIn("OLD_AUTHOR_PLAN",prompts[0])
            report=received["report"]
            self.assertTrue(report["cross_source_links"][0][
                "inference_not_an_accepted_change"])
            self.assertEqual(report["cross_source_links"][0][
                "earlier_original_source_offset"],0)
            self.assertEqual(report["cross_source_links"][0][
                "current_source_offset"],0)
            self.assertIn("reader_cross_source_links",
                          _reader_report_for_author(report,sha(current)))
            self.assertTrue(received["receipt"]["no_auto_edit_if_reader_guesses_a_gap"])

    def test_previous_text_hash_wrong_or_fake_quote_rejected_without_guessing(self):
        old="江遥把票据藏在袖里，宋易握着后门钥匙。"
        current=(
            "江遥在后台听鼓声，旧戏箱就在屋里。"
            "她脚踝隐隐发疼，只能靠着栏杆站着。"
            "宋易在楼梯口叫了一声，仍不能确认是谁。"
        )
        original=json.dumps({"prose":current,"trace":{
            "action_quote":None,"effect_quote":None,
            "parent_effect_quote":None}},ensure_ascii=False)
        with TemporaryDirectory() as td,patch(
            "writerforge.writing_assist.local_chat_completion") as model:
            with self.assertRaisesRegex(
                WritingExecutionError,"EARLIER_SOURCE_HASH_OR_BOUNDS"):
                _reader_separates_written_and_inferred(
                    raw=original,turn_packet=packet("x"),
                    ask_model=model,directory=Path(td)/"bad",
                    earlier_source=old,earlier_source_sha256="0"*64)
            model.assert_not_called()
        bad=json.dumps({
            "observed":[],"inferred_links":[],
            "cross_source_links":[{
                "previous_quote":"不存在的票据交付动作",
                "current_quote":"江遥在后台听鼓声",
                "reader_imagined_step":"这不是原文所述的物件动作。",
            }],
            "reader_uncertainty":"无法验证这个引用。",
        },ensure_ascii=False)
        with TemporaryDirectory() as td:
            response=_reader_separates_written_and_inferred(
                raw=original,turn_packet=packet("x"),
                ask_model=lambda *a,**kw:bad,directory=Path(td)/"wrong",
                earlier_source=old,earlier_source_sha256=sha(old))
            self.assertEqual(response["status"],"INVALID_READER_SOURCE")
            self.assertEqual(response["receipt"]["reason_code"],
                             "WF_READER_CROSS_SOURCE_QUOTE_NOT_EXACT")
            self.assertIsNone(response["report"])
            self.assertTrue((Path(td)/"wrong"/
                             "original-reader-reply.json").is_file())


class RealModelProbeBoundariesOffline(TestCase):
    def test_real_probe_model_adapter_is_same_provider_three_stages_max(self):
        import os
        from experiments import wf_real_deepseek_reader_first_author_once_20261024 as live
        class FakeClient:
            def __init__(self,*,api_key,budget,timeout_seconds,
                         on_response_wire):
                self.sink=on_response_wire
                self.requests=[]
            def ask_json(self,*,role,system,user,max_tokens):
                self.requests.append((role,max_tokens,system))
                self.sink(b'{"choices":[{"finish_reason":"stop"}]}')
                return {"reader_reply":"offline-only"}
        with TemporaryDirectory() as tmp,patch.dict(
                os.environ,{"DEEPSEEK_API_KEY":"offline-mock-key-12345"}),patch.object(
                live,"DeepSeekFlashModel",FakeClient):
            model=live.OriginalModelInTwoRoles(Path(tmp))
            self.assertEqual(live.MAX_CALLS,3)
            self.assertEqual(live.EXPECTED_TOKENS,3400)
            with self.assertRaisesRegex(
                    RuntimeError,"WF_READER_FIRST_STAGE_NOT_AUTHORIZED"):
                model.ask(packet("x"),model=None,api_base=None,max_tokens=600)
            for max_tokens in (1000,600,1800):
                model.ask(packet("generic novel"),model=None,
                          api_base=None,max_tokens=max_tokens)
            self.assertEqual(len(model.events),3)
            self.assertEqual([e["stage"] for e in model.events],[
                "INDEPENDENT_READER","ORIGINAL_AUTHOR","AUTHOR_V119_REVISION"])
            self.assertEqual([e["max_requested_output_tokens"]
                              for e in model.events],[1000,600,1800])
            for i,stage in enumerate((
                    "INDEPENDENT_READER","ORIGINAL_AUTHOR",
                    "AUTHOR_V119_REVISION"),1):
                self.assertTrue((Path(tmp)/f"{i:02d}-{stage}-provider-wire.json"
                                 ).is_file())
                self.assertEqual(model.events[i-1]["provider_wire_preserved_before_decode"],True)
            with self.assertRaisesRegex(
                    RuntimeError,"WF_READER_FIRST_INCORRECT_MODEL_OR_BUDGET"):
                model.ask(packet("x"),model=None,api_base=None,max_tokens=600)


class RealGOptinOffline(TestCase):
    def setUp(self):
        self.temp=TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.dbpath=self.root/"learn.sqlite"
        snapshot=make_db(self.dbpath)
        self.db=WriterForgeDB(self.dbpath)
        self.addCleanup(self.db.close)
        rt=RuntimeEngine();rt.enter_write(snapshot)
        self.assist=InvisibleWritingAssist(
            self.db,rt,"reader-source-project","reader-source-scene",
            "小说作者自己处理有限视角与后续选择；不得凭空写成确定事实。",
            model="same-synthetic-reader-writer",
            api_base="http://127.0.0.1:1234/v1")
        self.outline="两个身份未明的人在一间旧书铺相遇，动机和相互理解尚未确定。"
        self.goals=["沈砚和唐蜃先观察彼此，对未知的事实不作超前说明。"]

    def test_g_same_model_reader_then_author_on_each_real_turn_bounded(self):
        out=self.root/"reader-enabled"
        raw=[]
        for n in (1,2):
            actual=visible_prose(1,n)
            raw.extend([
                prose_response(1,n),
                source_reader_reply(actual,with_earlier=n>1),
                moment("MOVE_ON",actual),
            ])
        answers=[PLAN,json.dumps(PLAN_TURNS,ensure_ascii=False),*raw]
        used=[]
        def callback(packet,*,model,api_base,max_tokens):
            used.append((packet.prompt,max_tokens))
            return answers[len(used)-1]
        with patch("writerforge.writing_assist.local_chat_completion",
                   side_effect=callback) as calls:
            result=AutonomousWriting(self.assist).run(
                outline=self.outline,chapter_goals=self.goals,
                output_dir=out,draft_mode="continuity_guard",
                bootstrap_unified_core=True,self_edit_rounds=1,
                self_edit_timing="ai_decides",
                reader_first_self_review=True)
        self.assertEqual(calls.call_count,8)
        self.assertEqual([x[1] for x in used],
                         [650,1450,1450,1000,600,1450,1000,600])
        self.assertEqual(result["wf_reader_model_calls"],2)
        self.assertEqual(result["wf_self_edit_model_calls"],4)
        self.assertEqual(result["wf_self_edit_previous_turn_rewinds"],0)
        self.assertFalse(result["literary_quality_verified"])
        self.assertEqual(result["canonical_fact_writes"],0)
        chapter=result["chapters"][0]
        evidence=json.loads(Path(chapter["turn_evidence"]).read_text("utf8"))
        self.assertEqual(evidence["wf_source_reader_model_calls"],2)
        self.assertEqual([x["status"] for x in
                          evidence["wf_source_reader_receipts"]],
                         ["SOURCE_ANCHORED_READER_HYPOTHESES"]*2)
        self.assertEqual([x["decision"] for x in
                          evidence["wf_ai_self_review_moment_receipts"]],
                         ["MOVE_ON","MOVE_ON"])
        self.assertTrue(all(
            x["unverified_reader_input_delivered"] for x in
            evidence["wf_ai_self_review_moment_receipts"]))
        self.assertTrue(Path(chapter["candidate"]).is_file())
        job=Path(result["job_dir"])
        self.assertTrue((job/"chapter-001-turn-01-reader-first"/
                         "original-reader-reply.json").is_file())

    def test_invalid_reader_report_does_not_discard_valid_source_or_bypass_author(self):
        replies=[PLAN,json.dumps(PLAN_TURNS,ensure_ascii=False),
                 prose_response(1,1),"{}",
                 moment("MOVE_ON",visible_prose(1,1)),
                 prose_response(1,2),
                 source_reader_reply(visible_prose(1,2),with_earlier=True),
                 moment("MOVE_ON",visible_prose(1,2))]
        with patch("writerforge.writing_assist.local_chat_completion",
                   side_effect=replies) as model:
            result=AutonomousWriting(self.assist).run(
                outline=self.outline,chapter_goals=self.goals,
                output_dir=self.root/"invalid_reader",
                draft_mode="continuity_guard",self_edit_rounds=1,
                self_edit_timing="ai_decides",
                reader_first_self_review=True)
        self.assertEqual(model.call_count,8)
        data=json.loads(Path(result["chapters"][0][
            "turn_evidence"]).read_text("utf8"))
        self.assertEqual(data["wf_source_reader_receipts"][0]["status"],
                         "INVALID_READER_SOURCE")
        self.assertEqual(data["wf_ai_self_review_moment_receipts"][0][
            "decision"],"MOVE_ON")
        self.assertFalse(data["wf_ai_self_review_moment_receipts"][0][
            "unverified_reader_input_delivered"])
        self.assertIn("细雨不停",Path(
            result["chapters"][0]["candidate"]).read_text("utf8"))

    def test_reader_optin_refuses_wrong_mode_before_any_model_or_file(self):
        with patch("writerforge.writing_assist.local_chat_completion") as m:
            with self.assertRaisesRegex(
                WritingExecutionError,"READER_FIRST_REQUIRES_AI_OWNED_G"):
                AutonomousWriting(self.assist).run(
                    outline=self.outline,chapter_goals=self.goals,
                    output_dir=self.root/"should-not-exist",
                    draft_mode="continuity_guard",
                    reader_first_self_review=True)
            m.assert_not_called()
            self.assertFalse((self.root/"should-not-exist").exists())
