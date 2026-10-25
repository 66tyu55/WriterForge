"""Real G flow with scripted model: signed previous chapter source is offered.

The same writing model first invents its actual turn; same model reader
reports a source-anchored cross-source uncertainty; same original author
chooses MOVE_ON with UNWRITTEN_OR_UNKNOWN, without host replacing prose,
creating accepted Canon, or starting another memory owner.
These are offline model fixtures ONLY, not literary quality evidence.
"""
from pathlib import Path
from tempfile import TemporaryDirectory
from hashlib import sha256
from unittest import TestCase
from unittest.mock import patch
import json

from writerforge import WriterForgeDB,RuntimeEngine
from writerforge.writing_assist import (
    InvisibleWritingAssist,AutonomousWriting,SELF_EDIT_ATTRIBUTION_TOKENS,
)
from writerforge.v114_external_story_state import external_temporal_step
from writerforge.v117_continuity_trace import make_resume
from writerforge.narrative_core import new_graph,advance_graph,record_chapter_memory
from test_v26_invisible_writer import make_db,PLAN
from test_wf_cross_chapter_candidate_fork import (
    PLAN_TURNS,prose_response,visible_prose,sha,
)
from test_wf_reader_first_original_author import source_reader_reply
from test_wf_ai_writer_previous_turn_rewind import moment


EARLIER=(
    "沈砚在旧书铺门口把一册账簿藏进衣襟里，唐蜃还没有碰过这册账簿。"
    "唐蜃知道店外有一盏旧灯，却不知道为何账册的末页被人涂黑。"
    "掌柜还在后院整理信纸，两人都没有看见他手里收着哪封信。"
    "沈砚并未把账簿递给唐蜃，此刻二人尚未交换那件东西。"
)
BEFORE="沈砚在旧书铺门口把一册账簿藏进衣襟里，唐蜃还没有碰过这册账簿。"
AFTER="沈砚看见门外有一盏旧灯，却没有立即认为它是别人留下的暗号。"


def first_reader_reply():
    return json.dumps({
        "observed":[],"inferred_links":[],
        "cross_source_links":[{
            "previous_quote":BEFORE,
            "current_quote":AFTER,
            "reader_imagined_step":"若账簿随后出现不同的持有者，读者仍需要在原文里找到变化的实际动作。",
        }],
        "reader_uncertainty":"此刻我无法确定账簿是否已经移走。",
    },ensure_ascii=False)


def author_with_source_attestation(text):
    return json.dumps({
        "type":"json_object",
        "decision":"MOVE_ON","target_turn":"current",
        "source_sha256":None,
        "evidence_quote":None,"focus":None,
        "why_now":"这一幕只是人物观察环境，不需要借助额外转移来制造人工反转，可以暂时保留。",
        "what_goes_wrong_if_unchanged":None,"intended_reader_effect":None,
        "source_attributions":[{
            "link_index":0,"basis":"UNWRITTEN_OR_UNKNOWN",
            "prior_transition_quote":None,
            "literary_reason":"更早的原文只写了账册在沈砚衣襟里，若后来真要交付应另外在正文写清楚。",
        }],
    },ensure_ascii=False)


class SignedGAuthorCitationFlow(TestCase):
    def test_original_G_recovers_signed_previous_source_and_keeps_own_choice(self):
        with TemporaryDirectory() as tmp:
            root=Path(tmp)
            dbpath=root/"neutral.sqlite"
            published=make_db(dbpath)
            db=WriterForgeDB(dbpath)
            self.addCleanup(db.close)
            rt=RuntimeEngine()
            rt.enter_write(published)
            writer=InvisibleWritingAssist(
                db,rt,"signed-writer-source-claim","prior-check",
                "人物想保护真实来源但仍允许恰当留白。",
                model="same-fixture-author",api_base="http://127.0.0.1:1134/v1")
            prior_path=root/"prior-real-original.md"
            prior_path.write_text(EARLIER,encoding="utf8")
            core=new_graph(project_id=writer.project_id,
                           scene_id=writer.scene_id)
            core=advance_graph(core,project_id=writer.project_id,
                               scene_id=writer.scene_id,
                               chapter_index=1,prose=EARLIER,events=())
            core=record_chapter_memory(
                core,project_id=writer.project_id,scene_id=writer.scene_id,
                chapter_index=1,prose=EARLIER,source_path=str(prior_path))
            temporal=external_temporal_step(
                EARLIER,cast=("沈砚","唐蜃"))
            resume=make_resume(
                project_id=writer.project_id,scene_id=writer.scene_id,
                chapter_index=1,checkpoint=temporal,
                unified_narrative_core=core)
            responses=[
                PLAN,json.dumps(PLAN_TURNS,ensure_ascii=False),
                prose_response(2,1),first_reader_reply(),
                author_with_source_attestation(visible_prose(2,1)),
                prose_response(2,2),
                source_reader_reply(visible_prose(2,2),with_earlier=True),
                moment("MOVE_ON",visible_prose(2,2)),
            ]
            captured=[]
            def reply(packet,*,model,api_base,max_tokens):
                captured.append((packet.prompt,max_tokens))
                return responses[len(captured)-1]
            with patch("writerforge.writing_assist.local_chat_completion",
                       side_effect=reply) as calls:
                result=AutonomousWriting(writer).run(
                    outline="两名同乡在书铺外观察过路人，尚未确认账簿应该交给谁。",
                    chapter_goals=[
                        "由实际来源与当前动作推进小小的认知变化，不能凭空偷换物品。"],
                    output_dir=root/"new-g",
                    draft_mode="continuity_guard",
                    resume_story_checkpoint=resume,
                    self_edit_rounds=1,self_edit_timing="ai_decides",
                    reader_first_self_review=True)
            self.assertEqual(calls.call_count,8)
            self.assertEqual([x[1] for x in captured],
                             [650,1450,1450,1000,1150,1450,1000,600])
            self.assertIn(EARLIER,captured[3][0])
            self.assertIn(EARLIER,captured[4][0])
            self.assertIn("UNWRITTEN_OR_UNKNOWN",captured[4][0])
            self.assertNotIn("WF 已判定移交违规",captured[4][0])
            self.assertEqual(result["wf_self_edit_model_calls"],4)
            chapter=result["chapters"][0]
            self.assertEqual(chapter["story_chapter_index"],2)
            self.assertEqual(chapter["wf_cross_source_unreviewed_reader_hypotheses"],1)
            receipts=chapter["wf_author_source_attribution_receipts"]
            self.assertEqual(len(receipts),1)
            self.assertEqual(receipts[0]["author_declared_unwritten_or_unknown_links"],1)
            self.assertTrue(receipts[0]["source_claims_not_promoted_to_canon"])
            record=json.loads(Path(chapter["turn_evidence"]).read_text("utf8"))
            self.assertEqual(record["wf_author_source_claim_evidence_statuses"],
                             ["SOURCE_ATTRIBUTIONS_RECORDED_LITERAL_ONLY"])
            self.assertEqual(record["wf_author_declared_unwritten_or_unknown_count"],1)
            self.assertTrue(record["wf_source_quote_is_not_transfer_proof"])
            self.assertEqual([m["decision"] for m in
                              record["wf_ai_self_review_moment_receipts"]],
                             ["MOVE_ON","MOVE_ON"])
            self.assertEqual(result["canonical_fact_writes"],0)
            self.assertFalse(result["literary_quality_verified"])
            self.assertIn("沈砚看见门外有一盏旧灯",
                          Path(chapter["candidate"]).read_text("utf8"))
